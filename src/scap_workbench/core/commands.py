# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#      Maros Barabas        <xbarry@gmail.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

import gtk, logging, sys, re, time, os
import gobject
import webbrowser
import datetime
import time
from datetime import datetime
import tempfile         # Temporary file for XCCDF preview

from scap_workbench import core
from scap_workbench.core.events import EventObject
from scap_workbench.core.htmltextview import HtmlTextView

logger = logging.getLogger("scap-workbench")

try:
    import openscap_api as openscap
except ImportError as ex:
    logger.exception("OpenScap library initialization failed: %s" % (ex))
    openscap=None

from scap_workbench.core.threads import thread as threadSave
       
IMG_GROUP   = "emblem-documents"
IMG_RULE    = "document-new"
IMG_VALUE   = "emblem-downloads"

class DataHandler(object):
    """DataHandler Class implements handling data from Openscap library,
    calling oscap functions and parsing oscap output to models specified by
    tool's objects"""

    CMD_OPER_ADD        = 0
    CMD_OPER_EDIT       = 1
    CMD_OPER_DEL        = 2
    CMD_OPER_BIND       = 3
    RELATION_SIBLING    = 0
    RELATION_CHILD      = 1
    RELATION_PARENT     = 2
    TYPE_GROUP          = 0
    TYPE_RULE           = 1
    TYPE_VALUE          = 2

    def __init__(self, core):
        """DataHandler.__init__ -- initialization of data handler.
        Initialization is done by Core object.
        library => openscap library"""

        self.core = core

    def check_library(self):
        """Check if the library exists and the XCCDF file
        is loaded. If not return False and True otherwise"""
        if not self.core.lib or not self.core.lib.loaded:
            #self.core.notify("Library not initialized or XCCDF file not specified",
            #core.Notification.INFORMATION, msg_id="notify:xccdf:not_loaded")
            logger.debug("Library not initialized or XCCDF file not specified")
            return False
        else: return True

    def open_webbrowser(self, file):
        """Opens client's web browser using the webbrowser module. Assumes given file is a report.
        
        file - file to open with the web browser
        """

        browser_val = webbrowser.open(file)
        if not browser_val: self.core.notify("Failed to open browser \"%s\". Report file is saved in \"%s\"" % (webbrowser.get().name, "report.xhtml"),
            core.Notification.INFORMATION, msg_id="notify:scan:export_report")

    def get_title(self, titles):
        
        if titles == None or len(titles) == 0:
            return None

        parsed = {}
        for title in titles: parsed[title.lang] = title.text
        if self.core.selected_lang in parsed.keys():
            return parsed[self.core.selected_lang]
        elif self.core.lib.benchmark.lang in parsed.keys():
            return "%s [%s]" % (parsed[self.core.lib.benchmark.lang], self.core.lib.benchmark.lang)
        else: return "%s [%s]" % (titles[0].text, titles[0].lang)

    def get_values_by_rule_id(self, id, check=None):

        if not self.check_library(): return None
        items = []
        values = []

        # Case 1: check is not None -- we have recursive call
        if check != None:
            if check.complex:
                # This check is complext so there is more checks within
                for child in check.children: 
                    self.get_values_by_rule_id(id, check=child)
            else:
                for export in check.exports:
                    values.append(export.value)
            return values

        # Case 2: check is None -- this is regular call of function
        item = self.core.lib.benchmark.get_item(id)
        if item.type != openscap.OSCAP.XCCDF_RULE: raise TypeError("Wrong type of item with id \"%s\". Expected XCCDF_RULE, got " % (id, item.type))
        rule = item.to_rule()
        for check in rule.checks:
            if check.complex:
                # This check is complext so there is more checks within
                for child in check.children: 
                    values.extend(self.get_values_by_rule_id(id, check=child))
            else:
                for export in check.exports:
                    values.append(export.value)

        for value in self.core.lib.benchmark.get_all_values():
            if value.id in values:
                items.append(self.parse_value(value))
            
        return items

    def parse_value(self, value):

        # get value properties
        item = {}
        item["item"] = value
        item["id"] = value.id
        #item["lang"] = self.core.lib.benchmark.lang
        item["lang"] = self.core.selected_lang
        item["titles"] = {}
        item["descs"] = {}
        # Titles / Questions
        if len(value.question):
            for question in value.question: item["titles"][question.lang] = question.text
        else: 
            for title in value.title: item["titles"][title.lang] = title.text
        if item["lang"] not in item["titles"]: item["titles"][item["lang"]] = ""
        # Descriptions
        for desc in value.description: item["descs"][desc.lang] = desc.text
        if item["lang"] not in item["descs"]: item["descs"][item["lang"]] = ""
        # Type
        item["type"] = value.type
        # Values
        item["options"] = {}
        item["choices"] = {}
        for instance in value.instances:
            item["options"][instance.selector] = instance.value
            if len(instance.choices): item["choices"][instance.selector] = instance.choices

        #Get regexp match from match of elements

        # Get regexp match from match elements
        item["match"] = "|".join([i.match for i in value.instances if i.match])

        # Get regexp match from type of value
        if not len(item["match"]):
            item["match"] = ["", "^[\\d]+$", "^.*$", "^[01]$"][value.type]

        if self.core.selected_profile == None and self.core.lib.policy_model:
            profile = self.core.lib.policy_model.policies[0].profile
        else: profile = self.get_profile(self.core.selected_profile)
        if profile != None:
            for r_value in profile.refine_values:
                if r_value.item == value.id:
                    try:
                        item["selected"] = (r_value.selector, item["options"][r_value.selector])
                    except KeyError:
                        logger.exception("No selector \"%s\" available in rule %s" % (r_value.selector, item["id"]))
            for s_value in profile.setvalues:
                if s_value.item == value.id:
                    item["selected"] = ('', s_value.value)

        if "selected" not in item:
            if "" in item["options"]: item["selected"] = ('', item["options"][""])
            else: item["selected"] = ('', '')

        return item

    def get_all_item_ids(self, item=None):
        if not self.check_library(): return []
    
        if item == None:
            items = []
            for child in self.core.lib.benchmark.content:
                items.extend(self.get_all_item_ids(child))
            return items

        items = [item]
        if item.type != openscap.OSCAP.XCCDF_RULE:
            for child in item.content:
                items.extend(self.get_all_item_ids(child))

        return items


    def get_all_values(self):
        if not self.check_library(): return []

        return self.core.lib.benchmark.get_all_values()

    def get_languages(self):
        """Get available languages from XCCDF Benchmark
        """
        if not self.check_library(): return []
        return [self.core.lib.benchmark.lang]

    def get_selected(self, item, items_model):
        """DataHandler.get_selected -- get selection of rule/group
        returns boolean value"""

        if not self.core.lib.policy_model or self.core.selected_profile == None or items_model == True:
            return item.selected
        else:
            policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)
            if policy is None:
                raise LookupError("Policy for profile '%s' does not exist" % (self.core.selected_profile))

            # Get selector from policy
            select = policy.get_select_by_id(item.id)
            if select == None: 
                return item.selected
            else: return select.selected

    def get_profile(self, id):
        profile = self.core.lib.benchmark.get_item(id)

        if profile: return profile.to_profile()
        else: return None

    def get_item_values(self, id):
        """Get all values of item with id equal to id parameter
        This could be either XCCDF Group or XCCDF Benchmark
        """

        values = []
        if id == self.core.lib.benchmark.id: item = self.core.lib.benchmark
        else: item = self.core.lib.benchmark.item(id)
        
        if item.type == openscap.OSCAP.XCCDF_RULE:
            return self.get_values_by_rule_id(id)
        else:
            item = item.to_group()
            values.extend( [self.parse_value(i) for i in item.values] )
            for i in item.content:
                if i.type == openscap.OSCAP.XCCDF_GROUP:
                    values.extend( self.get_item_values(i.id) )

        return values

    def get_item_check_exports(self, check=None, item=None):
        if not self.check_library(): return None

        content = []
        if check != None:
            for child in check.children:
                if child.complex: content.extend(self.get_item_check_exports(check=child))
                else: 
                    for ref in child.exports:
                        content.append((ref.value, ref.name))
        else:
            if item == None: item = self.core.lib.benchmark.get_item(self.core.selected_item)
            if item == None: return None
            if item.type == openscap.OSCAP.XCCDF_RULE:
                rule = item.to_rule()
                for check in rule.checks:
                    if check.complex: content.extend(self.get_item_check_exports(check=child))
                    else: 
                        for ref in check.exports:
                            content.append((ref.value, ref.name))
            else: return []

        return content

    def get_item_content(self, check=None, item=None):
        if not self.check_library(): return None

        content = []
        if check != None:
            for child in check.children:
                if child.complex: content.extend(self.get_item_content(check=child))
                else: 
                    for ref in child.content_refs:
                        content.append((ref.name, ref.href))
        else:
            if item == None: item = self.core.lib.benchmark.get_item(self.core.selected_item)
            if item == None: return None
            if item.type == openscap.OSCAP.XCCDF_RULE:
                rule = item.to_rule()
                for check in rule.checks:
                    if check.complex: content.extend(self.get_item_content(check=child))
                    else: 
                        for ref in check.content_refs:
                            content.append((ref.name, ref.href))
            else: return []

        return content

    def set_item_content(self, name=None, href=None, item=None):
        if not self.check_library(): return (None, "Library not initialized.")

        if item == None: item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item == None: return (False, "Item \"%s\" not found" % (item or self.core.selected_item,))

        if item.type == openscap.OSCAP.XCCDF_RULE:
            rule = item.to_rule()
            if len(rule.checks) > 1:
                return (False, "Can't set the content: More then one check is present")
            elif len(rule.checks) == 0:
                if (not name or name == "") and (not href or href == ""): return (True, "")
                check = openscap.xccdf.check()
                check.system="http://oval.mitre.org/XMLSchema/oval-definitions-5"
                rule.add_check(check)

            if rule.checks[0].complex:
                return (False, "Can't set up the content ref when complex check present")
            if len(rule.checks[0].content_refs) > 1:
                return (False, "Can't set up the content: More content refs present")
            elif len(rule.checks[0].content_refs) == 0:
                rule.checks[0].add_content_ref(openscap.xccdf.check_content_ref())

            if name != None and rule.checks[0].content_refs[0].name != name:
                rule.checks[0].content_refs[0].name = name
            if href != None and rule.checks[0].content_refs[0].href != href:
                rule.checks[0].content_refs[0].href = href
                        
        else: return False, "Set content ref fatal: Item is not a rule !"

        return True, ""

    def get_item_details(self, id, items_model=False):
        """Parse details from item with id equal to id parameter to
        the dictionary."""

        if not self.check_library(): return None

        item = self.core.lib.benchmark.item(id or self.core.selected_item)
        if not item: return None

        if self.core.lib.policy_model:
            policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)
            if policy != None:
                new_item = policy.tailor_item(item)
                if new_item: item = new_item

        if item != None:
            values = {
                    "item":             item,
                    "id":               item.id,
                    "type":             item.type,
                    "titles":           dict([(title.lang, title.text) for title in item.title or []]),
                    "descriptions":     dict([(desc.lang, desc.text) for desc in item.description or []]),
                    "cluster_id":       item.cluster_id,
                    "conflicts":        [conflict for conflict in item.conflicts or []],
                    "extends":          item.extends,
                    "hidden":           item.hidden,
                    "platforms":        [platform for platform in item.platforms or []],
                    "prohibit_changes": item.prohibit_changes,
                    "questions":        dict([(question.lang, question.text) for question in item.question or []]),
                    "rationale":        [rationale.text for rationale in item.rationale or []],
                    "references":       self.parse_refs(item.references),
                    "requires":         item.requires,
                    "statuses":         [(status.date, status.status) for status in item.statuses or []],
                    "version":          item.version,
                    "version_time":     item.version_time,
                    "version_update":   item.version_update,
                    "warnings":         [(warning.category, warning.text) for warning in item.warnings or []],
                    "selected":         self.get_selected(item, items_model)
                    }
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                item = item.to_group()
                values.update({
                    "abstract":         item.abstract,
                    "typetext":         "Group",
                    #"content":         item.content,
                    #"values":           self.__item_get_values(item),
                    "selected":         item.selected,
                    "status_current":   item.status_current,
                    "values":           item.values,
                    "weight":           item.weight
                    })
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                item = item.to_rule()
                values.update({
                    #"checks":           item.checks,
                    "abstract":         item.abstract,
                    "typetext":         "Rule",
                    "fixes":            self.__rule_get_fixes(item),
                    "fixtexts":         self.__rule_get_fixtexts(item),
                    "idents":           [(ident.id, ident.system) for ident in item.idents or []],
                    "imapct_metric":    item.impact_metric,
                    "multiple":         item.multiple,
                    "profile_notes":    [(note.reftag, note.text) for note in item.profile_notes or []],
                    "role":             item.role,
                    "selected":         item.selected,
                    "severity":         item.severity,
                    "status_current":   item.status_current,
                    "weight":           item.weight
                    })
            elif item.type == openscap.OSCAP.XCCDF_VALUE:
                item = item.to_value()
                values.update({
                    "abstract":         item.abstract,
                    "typetext":         "Value",
                    "instances":        item.instances,
                    "interactive":      item.interactive,
                    "interface_hint":   item.interface_hint,
                    "oper":             item.oper,
                    "sources":          item.sources,
                    "status_current":   item.status_current,
                    "vtype":            item.type
                    })
            else: 
                logger.error("Item type not supported %d", item.type)
                return None

        else:
            logger.error("No item '%s' in benchmark", id)
            return None

        return values
 
    def set_selected(self, model, path, iter, usr):

        id, view, col = usr
        selection = view.get_selection()
        
        if model.get_value(iter, col) == id:
            view.expand_to_path(path)
            selection.select_path(path)

    def get_item(self, id, items_model=False):
        """Get the item from benchmark
        """
        if not self.check_library(): return None
        return self.core.lib.benchmark.item(id or self.core.selected_item)
        
    def get_profiles(self):
        """Get all profiles of the Benchmark
        """
        if not self.check_library(): return None
        profiles = []
        for item in self.core.lib.benchmark.profiles:
            pvalues = self.get_profile_details(item.id)
            if self.core.selected_lang in pvalues["titles"]: 
                profiles.append((item.id, pvalues["titles"][self.core.selected_lang])) 
            else: 
                profiles.append((item.id, "Unknown profile"))

        return profiles

    def get_profile_details(self, id):
        """Get details of selected Profile represented by id parameter
        """
        if not self.check_library(): return None

        item = self.get_profile(id)
        if item != None:
            values = {
                    "id":               item.id,
                    "titles":           dict([(title.lang, " ".join(title.text.split())) for title in item.title or []]),
                    "descriptions":     dict([(desc.lang, desc.text) for desc in item.description or []]),
                    "abstract":         item.abstract,
                    "extends":          item.extends,
                    "platforms":        [platform.text for platform in item.platforms or []],
                    "prohibit_changes": item.prohibit_changes,
                    "references":       self.parse_refs(item.references),
                    "statuses":         [(status.date, status.text) for status in item.statuses or []],
                    "version":          item.version,
                    "version_time":     item.version_time,
                    "version_update":   item.version_update
                    }
        else:
            logger.error("No item '%s' in benchmark", id)
            return None

        return values
        
    def __rule_get_fixes(self, item):
        fixes = []
        for fix in item.fixes:
            fx = {}
            fx["id"] = fix.id
            fx["complexity"] = fix.complexity
            fx["disruption"] = fix.disruption
            fx["platform"] = fix.platform
            fx["reboot"] = fix.reboot
            fx["strategy"] = fix.strategy
            fx["system"] = fix.system
            fx["text"] = fix.content
            fixes.append(fx)

        return fixes

    def __rule_get_fixtexts(self, item):
        fixtexts = []
        for fixtext in item.fixtexts:
            ft = {}
            ft["fixref"] = fixtext.fixref
            ft["reboot"] = fixtext.reboot
            ft["strategy"] = fixtext.strategy
            ft["text"] = fixtext.text.text
            ft["comlexity"] = fixtext.complexity
            ft["disruption"] = fixtext.disruption
            fixtexts.append(ft)

        return fixtexts

    def file_browse(self, title, file="", action=gtk.FILE_CHOOSER_ACTION_SAVE):

        if action == gtk.FILE_CHOOSER_ACTION_SAVE:
            dialog_buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        else: dialog_buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
 
        file_dialog = gtk.FileChooserDialog(title,
                action=action,
                buttons=dialog_buttons)
        if action == gtk.FILE_CHOOSER_ACTION_SAVE:
            file_dialog.set_do_overwrite_confirmation(True)

        if file:
            path = os.path.dirname(file)
            file_dialog.set_current_folder(path)
            if action == gtk.FILE_CHOOSER_ACTION_SAVE: 
                file_dialog.set_current_name(os.path.basename(file))

        """Init the return value"""
        result = ""
        if file_dialog.run() == gtk.RESPONSE_OK:
                result = file_dialog.get_filename()
        file_dialog.destroy()

        return result

    def parse_refs(self, references):
        refs = []
        for ref in references:
            tmpref = {
                    "isdc": ref.is_dublincore,
                    "contributor": ref.contributor,
                    "coverage": ref.coverage,
                    "creator": ref.creator,
                    "date": ref.date,
                    "description": ref.description,
                    "format": ref.format,
                    "identifier": ref.identifier,
                    "lang": ref.language,
                    "publisher": ref.publisher,
                    "relation": ref.relation,
                    "rights": ref.rights,
                    "source": ref.source,
                    "subject": ref.subject,
                    "title": ref.title,
                    "type": ref.type,
                    }
            refs.append(tmpref)
        return refs

    def get_benchmark(self):
        if not self.core.lib: return None
        return self.core.lib.benchmark

    def get_benchmark_titles(self):
        if not self.core.lib: return {}
        benchmark = self.core.lib.benchmark
        if not benchmark: return None
        titles = {}
        for title in benchmark.title:
            titles[title.lang] = title.text
        return titles

    def get_titles(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.title
        else: return []
    def get_descriptions(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.description
        else: return []
    def get_warnings(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.warnings
        else: return []
    def get_statuses(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.statuses
        else: return []
    def get_questions(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.question
        else: return []
    def get_rationales(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.rationale
        else: return []
    def get_platforms(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: return item.platforms
        else: return []
    def get_idents(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item: item = item.to_rule()
        if item: return item.idents
        else: return []

    def remove_item(self, id):
        item = self.get_item(id)
        logger.info("Removing item %s" %(id,))
        parent = item.parent
        if item.type == openscap.OSCAP.XCCDF_VALUE: item = item.to_value()
        if parent.type == openscap.OSCAP.XCCDF_GROUP: parent = parent.to_group()
        elif parent.type == openscap.OSCAP.XCCDF_BENCHMARK: parent = parent.to_benchmark()

        if item in parent.content:
            parent.content.remove(item)
        elif item in parent.values:
            parent.values.remove(item)
        else:
            raise LookupError("Can't remove item %s from %s, it isn't contained there!" % (item, parent.content + parent.values))

    def edit_title(self, operation, obj, lang, text, overrides, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            title = openscap.common.text()
            title.text = text
            title.lang = lang
            title.overrides = overrides
            return item.add_title(title)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.lang = lang
            obj.text = text
            obj.overrides = overrides
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.title.remove(obj)

        else: raise AttributeError("Edit title: Unknown operation %s" % (operation,))

    def edit_description(self, operation, obj, lang, text, overrides, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            description = openscap.common.text.new_html()
            description.text = text
            description.lang = lang
            description.overrides = overrides
        
            return item.add_description(description)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.lang = lang
            obj.text = text
            obj.overrides = overrides
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.description.remove(obj)

        else: raise AttributeError("Edit description: Unknown operation %s" % (operation,))

    def edit_warning(self, operation, obj, category, lang, text, overrides, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            warning = openscap.xccdf.warning_new()
            new_text = openscap.common.text()
            new_text.text = text
            new_text.lang = lang
            new_text.overrides = overrides
            warning.text = new_text
            if category != None: warning.category = category
    
            return item.add_warning(warning)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.text.lang = lang
            obj.text.text = text
            obj.text.overrides = overrides
            if category != None: obj.category = category
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.warnings.remove(obj)

        else: raise AttributeError("Edit warning: Unknown operation %s" % (operation,))

    def edit_status(self, operation, obj, date, status, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            if date != None: 
                t = datetime.strptime(date, "%Y-%m-%d")
                the_date = time.mktime(t.timetuple())
            else: the_date = time.time()
            new_status = openscap.xccdf.status_new()
            new_status.date = the_date
            new_status.status = status

            return item.add_status(new_status)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            t = datetime.strptime(date, "%Y-%m-%d")
            obj.date = time.mktime(t.timetuple())
            obj.status = status
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.statuses.remove(obj)

        else: raise AttributeError("Edit warning: Unknown operation %s" % (operation,))

    def edit_question(self, operation, obj, lang, overrides, text, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            question = openscap.common.text()
            question.text = text
            question.lang = lang
            question.overrides = overrides
            
            return item.add_question(question)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.lang = lang
            obj.text = text
            obj.overrides = overrides
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.question.remove(obj)

        else: raise AttributeError("Edit question: Unknown operation %s" % (operation,))

    def edit_rationale(self, operation, obj, lang, overrides, text, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            rationale = openscap.common.text()
            rationale.text = text
            rationale.lang = lang
            rationale.overrides = overrides
            
            return item.add_rationale(rationale)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.lang = lang
            obj.text = text
            obj.overrides = overrides
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.rationale.remove(obj)

        else: raise AttributeError("Edit rationale: Unknown operation %s" % (operation,))

    def edit_platform(self, operation, obj, cpe, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            return item.add_platform(cpe)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            #TODO: We have to remove and add in case of edit :'(
            item.platforms.remove(obj)
            item.add_platform(cpe)
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.platforms.remove(obj)

        else: raise AttributeError("Edit platform: Unknown operation %s" % (operation,))

    def __substitute(self, node_type, id, arg=None):
        if not self.check_library(): return None

        post = None
        item = self.core.lib.benchmark.get_item(id)
        if item == None:
            return None

        if item.type == openscap.OSCAP.XCCDF_VALUE:
            item = item.to_value()
            if arg != None: # We have policy, let's return the profile tailored value
                new_item = arg.tailor_item(item.to_item())
                if new_item: 
                    post = new_item.to_value().instances[0].defval_string or new_item.to_value().instances[0].value
                    openscap.OSCAP.oscap_free(new_item)
                else: 
                    instance = item.instance_by_selector(None)
                    post = instance.value
            else: 
                instance = item.instance_by_selector(None) or item.instances[0]
                post = instance.value
            return post
        
        else:
            raise ValueError("Can substitute only VALUE item, got ID of %s" % item.type)
                
        return None

    def edit_ident(self, operation, obj, id, system, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib.benchmark.get_item(self.core.selected_item)
            if item: item = item.to_rule()

        if operation == self.CMD_OPER_ADD:
            ident = openscap.xccdf.ident_new()
            ident.id = id
            ident.system = system
    
            return item.add_ident(ident)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.system = system
            obj.id = id
            return True

        elif operation == self.CMD_OPER_DEL:
            if not item:
                return False
            return item.idents.remove(obj)

        else: raise AttributeError("Edit notice: Unknown operation %s" % (operation,))


    def substitute(self, description, with_policy=False):
        policy = None
        if with_policy: policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)
        sub = openscap.common.text_xccdf_substitute(description, self.__substitute, policy)
        if sub != None:
            return sub
        else: return description

    def get_oval_definitions(self, href):
        if not self.check_library(): return None

        if href not in self.core.lib.files.keys():
            return None

        def_model = self.core.lib.files[href].model
        if def_model: return def_model.definitions
        else: return []


    def parse_oval_definition(self, definition):
        values = {
                "affected":     definition.affected,
                #"class":        definition.class, #Python problem
                "criteria":     definition.criteria,
                "deprecation":  definition.deprecation,
                "description":  definition.description,
                "id":           definition.id,
                "metadata":     definition.metadata,
                "notes":        definition.notes,
                "references":   definition.references,
                "title":        definition.title,
                "version":      definition.version
                }
        return values


class DHXccdf(DataHandler):

    def __init__(self, core):
        super(DHXccdf, self).__init__(core)

    def get_details(self):
    
        if not self.check_library(): return None
        benchmark = self.core.lib.benchmark
        details = {
                "item":             benchmark,
                "descs":            dict([(desc.lang, desc.text) for desc in benchmark.description]),
                "id":               benchmark.id,
                "lang":             benchmark.lang,
                "notices":          [(notice.id, notice.text) for notice in benchmark.notices],
                "resolved":         benchmark.resolved,
                "status_current":   benchmark.status_current,
                "titles":           dict([(title.lang, " ".join(title.text.split())) for title in benchmark.title]),
                "version":          benchmark.version,
                "references":       self.parse_refs(benchmark.references),
                "warnings":         [(warn.category, warn.text) for warn in benchmark.warnings],
                "files":            []
                }
        if self.core.lib.policy_model: details["files"] = self.core.lib.policy_model.files.strings


        return details

    def get_oval_files_info(self):

        if not self.check_library(): return None

        info = {}
        for name in self.core.lib.files.keys():

            def_model = self.core.lib.files[name].model
            info[name] = {}
            info[name]["product_name"] = def_model.generator.product_name
            info[name]["product_version"] = def_model.generator.product_version
            info[name]["schema_version"] = def_model.generator.schema_version
            info[name]["timestamp"] = def_model.generator.timestamp
        
        return info

    def update(self, id=None, version=None, resolved=None, lang=None):

        if not self.check_library(): return None
        benchmark = self.core.lib.benchmark

        if id and benchmark.id != id: benchmark.id = id
        if version and benchmark.version != version: benchmark.version = version
        if resolved != None and benchmark.resolved != resolved: benchmark.resolved = resolved
        if lang and benchmark.lang != lang: benchmark.lang = lang

    def resolve(self):
        """Resolves the current benchmark and returns True if successful and False
        if there are dependency loops.
        """
        
        if not self.check_library():
            return False

        return self.core.lib.benchmark.resolve()

    def export(self, file_name=None):

        if not self.check_library(): return None

        if not file_name:
            file_name = self.file_browse("Save XCCDF file", file=self.core.lib.xccdf)

        if file_name != "":
            # according to openscap API docs, -1 means that an error happened
            if self.core.lib.benchmark.export(file_name) == -1:
                return None
            
            logger.debug("Exported benchmark: %s", file_name)
            return file_name
        return None

    def validate_file(self, file, reporter=None):
        if reporter and not callable(reporter):
            logger.error("Given callback \"%s\" is not callable" % (reporter,))

        if os.access(file or "", os.R_OK):
            retval = openscap.common.validate_document(file, openscap.OSCAP.OSCAP_DOCUMENT_XCCDF, None,
                    reporter or self.__cb_report, None)
        else: return 3
        return retval

    def validate(self, reporter=None):
        if reporter and not callable(reporter):
            logger.error("Given callback \"%s\" is not callable" % (reporter,))

        temp = tempfile.NamedTemporaryFile()
        retval = self.export(temp.name)
        if not retval:
            return retval
        retval = openscap.common.validate_document(temp.name, openscap.OSCAP.OSCAP_DOCUMENT_XCCDF, None,
                reporter or self.__cb_report, None)
        temp.close()
        return retval

    def get_titles(self):
        if not self.check_library(): return None
        return self.core.lib.benchmark.title
    def get_descriptions(self):
        if not self.check_library(): return None
        return self.core.lib.benchmark.description
    def get_notices(self):
        if not self.check_library(): return None
        return self.core.lib.benchmark.notices
    def get_statuses(self):
        if not self.check_library(): return None
        return self.core.lib.benchmark.statuses
    def get_platforms(self):
        if not self.check_library(): return None
        return self.core.lib.benchmark.platforms

    def edit_title(self, operation, obj, lang, text, overrides):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_title(operation, obj, lang, text, overrides, item=self.core.lib.benchmark)

    def edit_description(self, operation, obj, lang, text, overrides):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_description(operation, obj, lang, text, overrides, item=self.core.lib.benchmark)

    def edit_warning(self, operation, obj, category, lang, text, overrides):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_warning(operation, obj, category, lang, text, overrides, item=self.core.lib.benchmark.to_item())

    def edit_status(self, operation, obj=None, date=None, status=None):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_status(operation, obj, date, status, item=self.core.lib.benchmark.to_item())

    def edit_notice(self, operation, obj, id, text):

        if not self.check_library(): return None

        if operation == self.CMD_OPER_ADD:
            notice = openscap.xccdf.notice_new()
            new_text = openscap.common.text()
            new_text.text = text
            notice.text = new_text
            notice.id = id
    
            return self.core.lib.benchmark.add_notice(notice)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.text.text = text
            obj.id = id
            return True

        elif operation == self.CMD_OPER_DEL:
            return self.core.lib.benchmark.notice.remove(obj)

        else: raise AttributeError("Edit notice: Unknown operation %s" % (operation,))

    def __cb_report(self, msg, plugin):
        logger.warning("Validation: %s", msg.string)
        return True

    def export_guide(self, xccdf, file, profile=None, hide=False):
        if not self.core.lib: return False

        params = [
                "result-id",         None,
                "show",              None,
                "profile",           profile,
                "hide-profile-info", [None, "yes"][hide],
                "template",          None,
                "format",            None,
                "oval-template",     None,
                "verbosity",         "1",
                "oscap-version",     openscap.common.oscap_get_version(),
                "pwd",               os.getenv("PWD")
        ]

        retval = openscap.common.oscap_apply_xslt(xccdf, "security-guide.xsl", file, params)
        # TODO If this call (below) is not executed, there will come some strange behaviour
        logger.info("Export guide %s" % (["failed: %s" % (openscap.common.err_desc(),), "done"][retval],))


class DHValues(DataHandler):

    def __init__(self, core, items_model=False):
        super(DHValues, self).__init__(core)
        self.items_model = items_model
        
    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""
        self.treeView = treeView
        self.model = gtk.ListStore(str, str, str, gtk.gdk.Color, gtk.TreeModel)
        self.treeView.set_model(self.model)
        return

    def fill(self, item=None):

        if not self.check_library(): return None

        """If item is None, then this is first call and we need to get the item
        from benchmark. Otherwise it's recursive call and the item is already
        eet up and we recursively add the parent till we hit the benchmark
        """
        if item is None:
            self.model.clear()
            if self.core.selected_item is not None:
                item = self.core.lib.benchmark.get_item(self.core.selected_item)
                if item is None: 
                    logger.error("XCCDF Item \"%s\" does not exists. Can't fill data", self.core.selected_item)
                    raise LookupError("XCCDF Item \"%s\" does not exists. Can't fill data" % (self.core.selected_item))
                
            else:
                return
        
        # Append a couple of rows.
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        values = self.get_item_values(self.core.selected_item)
        # TODO: The 0:gray value is not working cause of error in get_selected that values stay the same color
        # after selecting rule/group
        color = [gtk.gdk.Color("black"), gtk.gdk.Color("black")][self.get_selected(item, self.items_model)]
        for value in values:
            lang = value["lang"]
            model = gtk.ListStore(str, str)
            selected = "Unknown value"
            for key in value["options"].keys():
                if key != '': model.append([key, value["options"][key]])
                if value["options"][key] == value["selected"][1] and value["options"][key]: selected = key
                elif value["selected"][1] != None: selected = value["selected"][1]
            self.model.append([value["id"], value["titles"][lang], selected, color, model])
        self.treeView.columns_autosize()
        
        return True

    def cellcombo_edited(self, cell, path, new_text):

        if not self.check_library(): return None

        if self.core.selected_profile == None:
            policy = self.core.lib.policy_model.policies[0]
        else: policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)

        new_text_value = None
        iter = self.model.get_iter(path)
        id = self.model.get_value(iter, 0)
        value_model = self.model.get_value(iter, 4)
        for value_iter in value_model:
            if value_iter[0] == new_text: new_text_value = value_iter[1]
        if new_text_value == None: new_text_value = new_text

        val = self.core.lib.benchmark.item(id).to_value()
        value = self.parse_value(val)
        logger.debug("Matching %s against %s or %s", new_text_value, value["choices"], value["match"])
        # Match against pattern as "choices or match"
        pattern_list = []
        if value["selected"][0] in value["choices"]: pattern_list.append("|".join(value["choices"][value["selected"][0]]))
        if value["match"]: pattern_list.append(value["match"])
        patterns = [re.compile(pattern) for pattern in pattern_list]

        for i, pattern in enumerate(patterns):
            s = pattern.match(new_text_value)
            if s != None:
                # Dirty hack when matched string has the same length as found one (if no, it's bad)
                if (s.end() - s.start()) != len(new_text_value): continue
                self.model.set_value(iter, 2, new_text)
                logger.debug("Regexp matched: text \"%s\" matched \"%s\"", new_text_value, pattern_list[i])
                policy.set_tailor_items([{"id":id, "value":new_text_value}])
                return
        logger.error("Failed regexp match: text %s does not match %s", new_text_value, "|".join(pattern_list))

    def get_rationales(self):
        raise NotImplementedError("According to XCCDF Version 1.2: No rationale for value item")

    def edit_value(self, id=None, version=None, version_time=None, prohibit_changes=None, abstract=None, cluster_id=None, interactive=None, operator=None):
        if not self.check_library(): return None

        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item:
            item = item.to_value()
            
        if item is None:
            raise RuntimeError("Edit items update: No item selected !")

        if id != None and len(id) > 0 and item.id != id:
            retval = item.set_id(id)
            if not retval: return False
            self.core.selected_item = id
        if version != None and item.version != version:
            item.version = version
        if version_time != None:
            item.version_time = version_time
        if prohibit_changes != None:
            item.prohibit_changes = prohibit_changes
        if abstract != None:
            item.abstract = abstract
        if cluster_id != None and item.cluster_id != cluster_id:
            item.cluster_id = cluster_id
        if interactive != None:
            item.interactive = interactive
        if operator != None:
            item.oper = operator

        return True

    @classmethod
    def set_values_of_item_instance(cls, item, instance, default_value, value):
        if item.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            if default_value: instance.defval_number = float(default_value)
            if value: instance.value_number = float(value)
        elif item.type == openscap.OSCAP.XCCDF_TYPE_STRING:
            if default_value: instance.defval_string = default_value
            if value: instance.value_string = value
        elif item.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
            if default_value != -1: instance.defval_boolean = bool(default_value)
            if value != -1: instance.value_boolean = bool(value)
        else:
            raise NotImplementedError("Type of instance not supported: \"%s\"" % (item.type))

    @classmethod
    def get_values_from_item_instance(cls, item, instance):
        """Returns a tuple (default_value, value)
        """
        
        if item.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            op_defval = float(instance.defval_number)
            op_value  = float(instance.value_number)
        elif item.type == openscap.OSCAP.XCCDF_TYPE_STRING:
            op_defval = instance.defval_string
            op_value  = instance.value_string
        elif item.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
            op_defval = bool(instance.defval_boolean)
            op_value  = bool(instance.value_boolean)
        else:
            raise NotImplementedError("Type of instance not supported: \"%s\"" % (instance.type))
        
        return op_defval, op_value

    def edit_value_of_value(self, operation, obj, selector, value, default, match, upper_bound, lower_bound, must_match):
        if not self.check_library(): return None
        
        item = self.core.lib.benchmark.get_item(self.core.selected_item).to_value()
        if item is None:
            raise RuntimeError("Edit values: No item selected")

        if operation == self.CMD_OPER_ADD:
            new_instance = item.new_instance()
            DHValues.set_values_of_item_instance(item, new_instance, default, value)
            
            if match: new_instance.match = match
            if upper_bound != None: new_instance.upper_bound = upper_bound
            if lower_bound != None: new_instance.lower_bound = lower_bound
            new_instance.must_match = must_match
            new_instance.must_match_given = True
            new_instance.selector = selector

            return item.add_instance(new_instance)

        elif operation == self.CMD_OPER_EDIT:
            if obj is None: 
                logger.error("Can't edit None object")
                return False
            
            DHValues.set_values_of_item_instance(item, obj, default, value)
            
            obj.match = match
            if upper_bound != None: obj.upper_bound = upper_bound
            if lower_bound != None: obj.lower_bound = lower_bound
            obj.must_match = must_match
            obj.must_match_given = True
            obj.selector = selector
            
            return True

        elif operation == self.CMD_OPER_DEL:
            if obj is None: 
                logger.error("Can't remove None object")
                return False
            
            return item.instances.remove(obj)

        else:
            raise NotImplementedError("Edit question: Unknown operation %s" % (operation))

    def get_value_instances(self, item=None):
        if not self.check_library(): return None

        instances = []
        if not item: item = self.core.lib.benchmark.get_item(self.core.selected_item).to_value()

        for instance in item.instances:
            op_defval, op_value = DHValues.get_values_from_item_instance(item, instance)
            
            instances.append({
                    "item":         instance,
                    "choices":      instance.choices,
                    "defval":       op_defval,
                    "lower_bound":  instance.lower_bound,
                    "match":        instance.match,
                    "must_match":   instance.must_match,
                    "selector":     instance.selector,
                    "type":         instance.type,
                    "upper_bound":  instance.upper_bound,
                    "value":        instance.value,
                    "tvalue":       op_value
                    })
        return instances


class DHItemsTree(DataHandler, EventObject):

    COLUMN_TYPE     = 0
    COLUMN_ID       = 1
    COLUMN_NAME     = 2
    COLUMN_PICTURE  = 3
    COLUMN_TEXT     = 4
    COLUMN_COLOR    = 5
    COLUMN_SELECTED = 6
    COLUMN_PARENT   = 7

    def __init__(self, id, core, progress=None, combo_box=None, items_model=False, no_checks=False):
        """
        param items_model if False use selected profile is selected. If true use base model.
        """
        DataHandler.__init__(self, core)
        EventObject.__init__(self, core)

        self.id = id
        self.combo_box = combo_box
        self.items_model = items_model
        self.no_checks = no_checks
        
        core.register(id, self)
        self.add_sender(self.id, "filled")
        self.__progress = progress
        self.__total = None
        self.__step = None
        self.map_filter = None
        self.model = None
        
    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

        self.treeView = treeView
        
        # priperin model for view and filtering
        self.model = self.treeView.get_model()
        self.ref_model = self.model
        return

    def __set_sensitive(self, policy, child, model, pselected):
        """Recursive function init-called from __cb_toggled. Function iterate throught
        all children and check change the foreground color and sensitivity by value
        of pselected attribute. This should give better experience to users when all
        children of unselected group are insensitive and gray colored. Function will
        alter policy selectors when parent group is (de)selected."""

        benchmark = policy.model.benchmark
        iter = model[child.path].iterchildren()
        while iter != None:
            try:
                child = iter.next()
                model[child.path][DHItemsTree.COLUMN_PARENT] = pselected
                model[child.path][DHItemsTree.COLUMN_COLOR] = ["gray", None][model[child.path][DHItemsTree.COLUMN_SELECTED] and pselected]

                """Alter the policy. All underneath rules/groups should 
                be deselected when parent group is deselected.
                """
                if benchmark.item(model[child.path][DHItemsTree.COLUMN_ID]).type == openscap.OSCAP.XCCDF_RULE:
                    select = policy.get_select_by_id(model[child.path][DHItemsTree.COLUMN_ID])
                    if select == None:
                        newselect = openscap.xccdf.select()
                        newselect.item = model[child.path][DHItemsTree.COLUMN_ID]
                        newselect.selected = (model[child.path][DHItemsTree.COLUMN_SELECTED] and pselected)
                        policy.select = newselect
                    else:
                        select.selected = (model[child.path][DHItemsTree.COLUMN_SELECTED] and pselected)

                """Recursive call for all children
                """
                self.__set_sensitive(policy, child, model, pselected and model[child.path][DHItemsTree.COLUMN_SELECTED])
            except StopIteration:
                break


    def cb_toggled(self, cell, path, model=None):
        """Function is called from GTK when checkbox of treeView item is toggled. 
        Function will alter present and previous models (if filters are applied) and
        change the selection of rule/group in policy. At the end is called __set_sensitive
        function for all childs for better user experience with altering the rule/group model"""

        """Check if library is initialized, 
        return otherwise"""
        if not self.check_library(): return None

        """model is alternative attribute for previous
        model if filters were applied"""
        if not model: 
            model = self.treeView.get_model()

            """If there is a reference model and filters are applied
            do this for present  model and call it again for previous model"""
            if self.ref_model != model:
                map_filter, struct = self.map_filter or [None, None]
                iter = model.get_iter(path)
                alt_path = model.get_path(iter)
                if map_filter: alt_path = map_filter[alt_path]
                self.__cb_toggled(cell, alt_path, self.ref_model)

        model[path][DHItemsTree.COLUMN_SELECTED] = not model[path][DHItemsTree.COLUMN_SELECTED]
        model[path][DHItemsTree.COLUMN_COLOR] = ["gray", None][model[path][DHItemsTree.COLUMN_SELECTED]]

        """OpenSCAP library block:
           1) Get selected policy and raise exception if there is no policy - how could this happened ?
           2) Get selector by ID from selected item in treeView
           3) If there is no selector create one and set up by attributes from treeView"""
        policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)
        if policy == None: 
            raise LookupError("Policy for profile '%s' does not exist" % (self.core.selected_profile))

        select = policy.get_select_by_id(model[path][DHItemsTree.COLUMN_ID])
        if select == None:
            newselect = openscap.xccdf.select()
            newselect.item = model[path][DHItemsTree.COLUMN_ID]
            newselect.selected = model[path][DHItemsTree.COLUMN_SELECTED]
            policy.add_select(newselect.clone())
            policy.profile.add_select(newselect)
        else:
            select.selected = model[path][DHItemsTree.COLUMN_SELECTED]
            for select in policy.profile.selects:
                if select.item == model[path][DHItemsTree.COLUMN_ID]:
                    select.selected = model[path][DHItemsTree.COLUMN_SELECTED]

        """This could be a group and we need set the sensitivity
        for all children."""
        self.__set_sensitive(policy, model[path], model, model[path][DHItemsTree.COLUMN_SELECTED])

    def __recursive_fill(self, item=None, parent=None, pselected=True, with_values=False):
        """Function to fill the treeModel. Recursive call through benchmark items
        for constructing the tree structure. Select attribute is from selected policy (profile).
        See profiles.
        
        with_values - if the model has the values of groups
        
        Internal: The commented threads_enter and leave calls are leftover from the past when
        the data model fill was done in a separate worker thread.
        """

        """This is recusive call (item is not None) so let's get type of 
        item and add it to model. If the item is Group continue more deep with
        recursion to get all items to the tree"""
        color = None
        if self.__progress != None:
            #gtk.gdk.threads_enter()
            value = self.__progress.get_fraction()+self.__step
            if value > 1.0: value = 1.0
            self.__progress.set_fraction(value)
            self.__progress.set_text("Adding items %s/%s" % (int(self.__progress.get_fraction()/self.__step), self.__total))
            #gtk.gdk.threads_leave()

        """Check the item if it's selected. If the parent or the item is not selected
        change the color of the font to the gray"""
        selected = self.get_selected(item, self.items_model)
        color = ["gray", None][not self.items_model and selected and pselected]
        
        """If item is not None let's fill the model with groups and rules.
        """
        if item is not None:
            # Get striped titles without white characters
            titles = dict([(title.lang, " ".join(title.text.split())) for title in item.title])
            if self.core.selected_lang in titles.keys(): title = titles[self.core.selected_lang]
            else: title = titles[titles.keys()[0]]

            # TYPE: XCCDF_GROUP
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                item = item.to_group()
                #gtk.gdk.threads_enter()
                item_it = self.model.append(parent, ["group", item.id, title, IMG_GROUP, ""+title, color, selected, pselected])
                self.treeView.queue_draw()
                #gtk.gdk.threads_leave()

                """For all content of the group continue with recursive fill
                """
                for i in item.content:
                    self.__recursive_fill(i, item_it, selected and pselected, with_values=with_values)

                """Get the values of the group and add it to the end of group subtree
                """
                if with_values:
                    for value in item.values:
                        self.__recursive_fill(value.to_item(), item_it, selected and pselected, with_values=with_values)

            # TYPE: XCCDF_RULE
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                #gtk.gdk.threads_enter()
                item_it = self.model.append(parent, ["rule", item.id, title, IMG_RULE, ""+title, color, selected, pselected])
                self.treeView.queue_draw()
                #gtk.gdk.threads_leave()

            # TYPE: XCCDF_VALUE
            elif item.type == openscap.OSCAP.XCCDF_VALUE:
                if len(item.title) == 0: title = item.id
                else:
                    titles = dict([(title.lang, " ".join(title.text.split())) for title in item.title])
                    if self.core.selected_lang in titles.keys(): title = titles[self.core.selected_lang]
                    else: title = titles[titles.keys()[0]]
                #gtk.gdk.threads_enter()
                self.model.append(parent, ["value", item.id, title, IMG_VALUE, ""+title, color, selected, pselected])
                self.treeView.queue_draw()
                #gtk.gdk.threads_leave()

            #TYPE: UNKNOWN
            else: logger.warning("Unknown type of %s, should be Rule or Group (got %s)", item.type, item.id)

        else: 
            raise ValueError("Can't fill because of invalid passed data. Expected XCCDF Item (got %s)" % (item))

    def __item_count(self, item, with_values=False):
        """Recursive function returning count of children.
        if item is RULE return 0"""
        number = 0
        if item.type == openscap.OSCAP.XCCDF_GROUP or item.to_item().type == openscap.OSCAP.XCCDF_BENCHMARK:
            if with_values:
                if item.type == openscap.OSCAP.XCCDF_GROUP: values = item.to_group().values
                else: values = item.values
                for child in values:
                    number += 1
            for child in item.content:
                number += 1
                if child.type == openscap.OSCAP.XCCDF_GROUP:
                    number += self.__item_count(child, with_values=with_values)
        return number

    #@threadSave
    def fill(self, item=None, parent=None, with_values=False):
        """
        Internal: The commented threads_enter and leave calls are leftover from the past when
        the data model fill was done in a separate worker thread.
        """
        
        if not self.check_library(): return None

        """we don't know item so it's first call and we need to clear
        the model, get the item from benchmark and continue recursively
        through content to fill the tree"""

        # Get number of all items
        self.treeView.set_sensitive(False)
        if self.__progress:
            self.__progress.set_fraction(0.0)
            self.__progress.show()
            self.__total = self.__item_count(self.core.lib.benchmark, with_values=with_values)
        self.__step = (100.0/(self.__total or 1.0))/100.0

        try:
            #gtk.gdk.threads_enter()
            self.model.clear()
            if self.combo_box: self.combo_box.set_sensitive(False)
            self.treeView.set_sensitive(False)
            #gtk.gdk.threads_leave()

            """Using generator for list cause we don't want to extend (add) values to content
            of benchmark again (list is benchmark content and adding cause adding to model)"""
            content = [item for item in self.core.lib.benchmark.content]
            if with_values:
                content.extend([item.to_item() for item in self.core.lib.benchmark.values])

            for item in content:
                if self.__progress != None:
                    #gtk.gdk.threads_enter()
                    value = self.__progress.get_fraction()+self.__step
                    if value > 1.0: value = 1.0
                    self.__progress.set_fraction(value)
                    self.__progress.set_text("Adding items %s/%s" % (int(self.__progress.get_fraction()/self.__step), self.__total))
                    #gtk.gdk.threads_leave()
                self.__recursive_fill(item, with_values=with_values)

            #gtk.gdk.threads_enter()
            self.treeView.set_sensitive(True)
            #gtk.gdk.threads_leave()
        finally:
            #gtk.gdk.threads_enter()
            if self.__progress != None:
                self.__progress.set_text("Applying filters ...")
                self.__progress.set_fraction(1.0)
                self.__progress.hide()
            if self.core.selected_item:
                self.treeView.get_model().foreach(self.set_selected, (self.core.selected_item, self.treeView, 1))
            if self.combo_box: self.combo_box.set_sensitive(True)
            #gtk.gdk.threads_leave()
            self.emit("filled")

        return True

    def add_item(self, item_dict, itype, relation, vtype):
        """Add new item into the benchmark relative to the selected position
        in the benchmark tree and choosen relation between selected item and
        new item"""

        if not self.check_library(): return None
        parent = None
        iter = None

        """If no selected item is passed to the function, get the selected
        item from the core"""
        selection = self.treeView.get_selection()
        if selection != None:
            (model, iter) = selection.get_selected()
            if iter != None:
                parent = self.get_item(model[iter][self.COLUMN_ID])

        """There is no item selected therefor we are adding new item to the
        root level: benchmark. Get benchmark and check it for None value"""
        if parent == None: 
            parent = self.core.lib.benchmark.to_item()
            if parent == None:
                return False

        """If relation between selected and new item is SIBLING then we need
        as parent selected item's parent, if selected item is benchmark: 
        return false cause benchmark is a root"""
        if relation == self.RELATION_SIBLING:
            if parent.type == openscap.OSCAP.XCCDF_BENCHMARK:
                return False
            else: 
                parent = parent.parent
                iter = model.iter_parent(iter)
                if not parent: 
                    return False

        """Convert parent of item (which is XCCDF_ITEM now) to the appropriate
        type: BENCHMARK, RULE or GROUP"""
        if parent.type == openscap.OSCAP.XCCDF_RULE:
            parent = parent.to_rule()
        elif parent.type == openscap.OSCAP.XCCDF_GROUP:
            parent = parent.to_group()
        elif parent.type == openscap.OSCAP.XCCDF_BENCHMARK:
            parent = parent.to_benchmark()
        else: 
            logger.error("Unsupported itme format: %s" % (parent.type,))
            return False

        """Fill new created item with the values from the formular. Make an 'op'
        operation related to the type of the parent"""
        title = openscap.common.text()
        title.lang = item_dict["lang"]
        title.text = item_dict["title"]
        if itype == self.TYPE_RULE:
            item = openscap.xccdf.rule()
            select = openscap.xccdf.select()
            select.selected = True
            select.item = item_dict["id"]
            op = parent.add_rule
        elif itype == self.TYPE_GROUP:
            item = openscap.xccdf.group()
            op = parent.add_group
        elif itype == self.TYPE_VALUE:
            item = openscap.xccdf.value(vtype+1) #TODO
            op = parent.add_value
        else: raise AttributeError("Add item: Type \"%s\" not supported" % (itype,))
        item.id = item_dict["id"]
        item.add_title(title)

        # op is a bound callable selected above, depending on which type of item is being added
        op(parent, item)
        
        item_it = self.model.append(iter, [["group", "rule", "value"][itype], item_dict["id"], item_dict["title"], #TODO: type
            ["emblem-documents", "document-new", "emblem-downloads"][itype], ""+item_dict["title"], None, True, parent.selected])
        self.treeView.expand_to_path(model.get_path(item_it))
        selection.select_iter(item_it)
        return True

class DHProfiles(DataHandler):

    def __init__(self, core):
        super(DHProfiles, self).__init__(core)
        
        self.treeView = None
        self.model = None

    def render(self, treeView):
        """Make a model ListStore of Profile object
        """
        self.treeView = treeView
        #self.model = treeView.get_model() TODO
        self.model = gtk.TreeStore(str, str, gobject.TYPE_PYOBJECT, str, str, str)
        self.treeView.set_model(self.model)

    def update(self, id=None, version=None, extends=None, abstract=None, prohibit_changes=None):
        if not self.check_library(): return None

        profile = self.get_profile(self.core.selected_profile)

        if id != None and len(id) > 0 and profile.id != id:
            retval = profile.set_id(id)
            if not retval: return False
            self.core.selected_profile = id
        if extends != None and profile.extends != extends:
            profile.extends = extends
        if version != None and profile.version != version:
            profile.version = version
        if abstract != None and profile.abstract != abstract:
            profile.abstract = abstract
        if prohibit_changes != None and profile.prohibit_changes != prohibit_changes:
            profile.prohibit_changes = prohibit_changes

        return True

    def add(self, id, lang, title):
        """Add a new profile to the benchmark.
        Item is a dictionary specifing profile to be added
        
        This method is using @ref edit method to fill the data from
        item to the XCCDF Profile structure"""

        logger.debug("Adding new profile: \"%s\"", id)
        if not self.check_library(): return None

        profile = openscap.xccdf.profile()
        profile.id = id
        profile.abstract = False
        new_title = openscap.common.text()
        new_title.text = title
        new_title.lang = lang
        profile.title = new_title

        self.core.lib.benchmark.add_profile(profile)
        if self.core.lib.policy_model: self.core.lib.policy_model.add_policy(openscap.xccdf.policy(self.core.lib.policy_model, profile))

    def get_refine_ids(self, profile):
        # -- RULES --
        ids = []
        for rule in profile.selects + profile.refine_rules + profile.setvalues + profile.refine_values:
            if rule.item not in ids: ids.append(rule.item)
        return ids

    def __fill_refines(self, profile, iter):
        """
        Internal: The commented threads_enter and leave calls are leftover from the past when
        the data model fill was done in a separate worker thread.
        """
        
        # -- RULES --
        rules = {}
        color = None
        for rule in profile.selects: rules[rule.item] = [rule]
        for rule in profile.refine_rules:
            if rule.item in rules: rules[rule.item].append(rule)
            else: rules[rule.item] = [rule]

        for rule_k in rules.keys():
            # add list of rules into the profile parent iter
            for rule in rules[rule_k]:
                if rule.object == "xccdf_select":
                    if not rule.selected: color = "gray"
                    else: color = None
                    break
            item = self.core.lib.benchmark.get_item(rule_k)
            if item == None:
                logger.error("%s points to nonexisting item %s" % (rules[rule_k][0].object, rule_k))
                #gtk.gdk.threads_enter()
                self.model.append(iter, ["rule", rule_k, rules[rule_k], "dialog-error", "Broken reference: %s" % (rule_k,), "red"])
                #gtk.gdk.threads_leave()
                continue

            type = {openscap.OSCAP.XCCDF_RULE: "rule", openscap.OSCAP.XCCDF_GROUP: "group"}[item.type]
            #gtk.gdk.threads_enter()
            self.model.append(iter, ["rule", rule_k, rules[rule_k], IMG_RULE, self.get_title(item.title) or item.id+" (ID)", color])
            #gtk.gdk.threads_leave()

        # -- VALUES --
        values = {}
        for value in profile.setvalues: values[value.item] = [value]
        for value in profile.refine_values:
            if value.item in values:
                #gtk.gdk.threads_enter()
                values[value.item].append(value)
                #gtk.gdk.threads_leave()
            else: values[value.item] = [value]

        for value_k in values.keys():
            # add list of values into the profile parent iter
            item = self.core.lib.benchmark.get_item(value_k)
            if item == None: 
                logger.error("%s points to nonexisting value %s" % (values[value_k][0].object, value_k))
                #gtk.gdk.threads_enter()
                self.model.append(iter, ["value", value_k, values[value_k], "dialog-error", "Broken reference: %s" % (value_k,), "red"])
                #gtk.gdk.threads_leave()
                continue
            #gtk.gdk.threads_enter()
            self.model.append(iter, ["value", value_k, values[value_k], IMG_VALUE, self.get_title(item.title) or item.id+" (ID)", None])
            #gtk.gdk.threads_leave()

    #@threadSave
    def fill(self, item=None, parent=None, no_default=False):
        """Fill the model with existing profiles from loaded benchmark
        no_default parameter means that there should not be a default document representation of policy
        
        Internal: The commented threads_enter and leave calls are leftover from the past when
        the data model fill was done in a separate worker thread.
        """
        #gtk.gdk.threads_enter()
        if self.treeView: self.treeView.set_sensitive(False)
        self.model.clear()
        #gtk.gdk.threads_leave()
        if not self.check_library(): return None

        if not no_default:
            logger.debug("Adding profile (No profile)")
            #gtk.gdk.threads_enter()
            if self.model.__class__ == gtk.ListStore: self.model.append([None, "(No profile)"])
            else: self.model.append(None, ["profile", None, item, IMG_GROUP, "(No profile)", None])
            #gtk.gdk.threads_leave()

        # Go thru all profiles from benchmark and add them into the model
        for item in self.core.lib.benchmark.profiles:
            logger.debug("Adding profile \"%s\"", item.id)
            pvalues = self.get_profile_details(item.id)
            title = self.get_title(item.title) or "%s (ID)" % (item.id,)
            color = None
            if self.model.__class__ == gtk.ListStore:
                #gtk.gdk.threads_enter()
                iter = self.model.append([item.id, ""+title])
                #gtk.gdk.threads_leave()
            else:
                #gtk.gdk.threads_enter()
                iter = self.model.append(None, ["profile", item.id, item, IMG_GROUP, ""+title, color])
                #gtk.gdk.threads_leave()
                self.__fill_refines(item, iter)

        #gtk.gdk.threads_enter()
        if self.core.selected_profile and self.treeView:
            self.treeView.get_model().foreach(self.set_selected, (self.core.selected_profile, self.treeView, 0))
        if self.treeView: self.treeView.set_sensitive(True)
        #gtk.gdk.threads_leave()
        return True

    def get_profiles(self):
        if not self.check_library(): return None

        profiles = []
        for item in self.core.lib.benchmark.profiles:
            profiles.append(item)

        return profiles

    def save(self):
        """Save the profile in the benchmark. Profile still exists just as policy and
        all changes made to the policy after tailoring are not mirrored to the profile,
        therefor we need to save it explicitely."""

        policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)
        if policy == None:
            logger.debug("No policy associated to profile %s" % (self.core.selected_profile,))
            return
        rules = dict([(select.item, select.selected) for select in policy.selects])

        profile = policy.profile
        for select in profile.selects:
            if select.item in rules.keys():
                select.selected = rules[select.item]
                rules[select.item] = None
            else: select.selected = policy.model.benchmark.item(select.item).selected
        for item in rules.keys():
            if rules[item] == None: continue
            sel = openscap.xccdf.select()
            sel.item = item
            selected = rules[item]
            sel.selected = selected
            profile.add_select(sel)

    def remove_item(self, id):
        """Remove profile from XCCDF Benchmark
        """
        if not self.check_library(): return None

        profile = self.core.lib.benchmark.get_item(id).to_profile()
        self.core.lib.benchmark.profiles.remove(profile)

    def change_refines(self, weight=None, severity=None, role=None):
        """Call the library to change refines of profile
        """
        if self.core.selected_profile == None: return
        if not self.check_library(): return None

        policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)
        if policy:
            logger.debug("Changing refine_rules: item(%s): severity(%s), role(%s), weight(%s)" % (self.core.selected_item, severity, role, weight))
            refine = policy.set_refine_rule(self.core.selected_item, weight, severity, role)

    def __get_current_profile(self):
        return self.get_profile(self.core.selected_profile)

    def get_titles(self):
        if not self.check_library(): return None
        return self.__get_current_profile().title
    def get_descriptions(self):
        if not self.check_library(): return None
        return self.__get_current_profile().description
    def get_statuses(self):
        if not self.check_library(): return None
        return self.__get_current_profile().statuses

    def edit_title(self, operation, obj, lang, text, overrides):
        if not self.check_library(): return None
        super(DHProfiles, self).edit_title(operation, obj, lang, text, overrides, item=self.__get_current_profile())

    def edit_description(self, operation, obj, lang, text, overrides):
        if not self.check_library(): return None
        super(DHProfiles, self).edit_description(operation, obj, lang, text, overrides, item=self.__get_current_profile())

    def edit_status(self, operation, obj, date, status):
        if not self.check_library(): return None
        super(DHProfiles, self).edit_status(operation, obj, date, status, item=self.__get_current_profile())

    def remove_refine(self, id, items):
        """Remove refine from 
        """
        if not self.check_library(): return None

        profile = self.get_profile(id)
        for item in items:
            if item.object == "xccdf_select": profile.selects.remove(item)
            elif item.object == "xccdf_refine_rule": profile.refine_rules.remove(item)
            elif item.object == "xccdf_setvalue": profile.setvalues.remove(item)
            elif item.object == "xccdf_refine_value": profile.refine_values.remove(item)
            else: raise RuntimeError("Can't remove item \"%s\" from profile %s" % (item, profile))

    def add_refine(self, id, title, item):

        profile_iter = None
        (filter_model, filter_iter) = self.treeView.get_selection().get_selected()
        model = filter_model.get_model()
        iter = filter_model.convert_iter_to_child_iter(filter_iter)
        if model.get_value(iter, 1) == self.core.selected_profile:
            profile_iter = iter
        elif model.iter_parent(iter) and model.get_value(model.iter_parent(iter), 1) == self.core.selected_profile:
            profile_iter = model.iter_parent(iter)
            
        if profile_iter == None: 
            logger.error("Can't add data. No profile specified !")
            return

        num = model.iter_n_children(profile_iter)
        for nth in range(num):
            iter = model.iter_nth_child(profile_iter, nth)
            if model[iter][1] == id: return False

        type = {openscap.OSCAP.XCCDF_RULE: "rule", openscap.OSCAP.XCCDF_GROUP: "group", openscap.OSCAP.XCCDF_VALUE: "value"}[item.type]
        model.append(profile_iter, [type, id, [],
            {"group":IMG_RULE, "rule":IMG_RULE, "value":IMG_VALUE}[type],
            title or item.id+" (ID)", ["gray", None][type=="value"]])

        return True

    def update_refines(self, type, id, items, idref=None, selected=None, weight=None, value=None, selector=None, operator=None, severity=None):
        if not self.check_library(): return None

        # TODO: This happened because we focused out the changed item by clicking on 
        # profile and in the time of calling this function is current item profile
        if type == "profile": return

        profile = self.get_profile(self.core.selected_profile)

        if idref != None and idref != id:
            if len(items) != 0:
                for item in items: item.item = idref
        if type in ["rule", "group"]:
            select = r_rule = None
            for item in items:
                if item.object == "xccdf_select": select = item
                elif item.object == "xccdf_refine_rule": r_rule = item
            if selected != None:
                if not select:
                    # Add new select
                    new_select = openscap.xccdf.select_new()
                    new_select.item = id
                    new_select.selected = selected
                    profile.add_select(new_select)
                    items.append(new_select)
                else: # We have select, let's change his selection
                    select.selected = selected

            if not selector and not weight and severity == None: return
            if not r_rule:
                r_rule = openscap.xccdf.refine_rule_new()
                r_rule.item = id
                items.append(r_rule)
                profile.add_refine_rule(r_rule)
            if weight != None and r_rule.weight != weight:
                r_rule.weight = weight
            if type == "group": return

            if selector != None and r_rule.selector != selector:
                r_rule.selector = selector
            if severity != None and r_rule.severity != severity:
                r_rule.severity = severity

        elif type == "value":
            setvalue = r_value = None
            for item in items:
                if item.object == "xccdf_setvalue": setvalue = item
                elif item.object == "xccdf_refine_value": r_value = item
            if value != None:
                if not setvalue:
                    new_setvalue = openscap.xccdf.setvalue_new()
                    new_setvalue.item = id
                    new_setvalue.value = value
                    profile.add_setvalue(new_setvalue)
                    items.append(new_setvalue)
                elif setvalue.value != value:
                    setvalue.value = value

            if selector == None and operator == None: return
            if not r_value:
                r_value = openscap.xccdf.refine_value_new()
                r_value.item = id
                items.append(r_value)
                profile.add_refine_value(r_value)
            if selector != None:
                """ If we update selector, (which is always overrided by
                setvalue, we need to clear that setvalue or this will have
                no effect.
                """
                if setvalue: items.remove(setvalue)
                if r_value.selector != selector:
                    r_value.set_selector(selector)
            if operator != None and r_value.operator != operator:
                r_value.set_oper(operator)

        else: raise AttributeError("Unknown type of refines in profile: %s" % (type,))

class DHScan(DataHandler, EventObject):

    COLUMN_ID = 0               # id of rule
    COLUMN_RESULT = 1           # Result of scan
    COLUMN_FIX = 2              # fix
    COLUMN_TITLE = 3            # Description of rule
    COLUMN_DESC = 4             # Description of rule
    COLUMN_COLOR_TEXT_TITLE = 5 # Color of text description
    COLUMN_COLOR_BACKG = 6      # Color of cell
    COLUMN_COLOR_TEXT_ID = 7    # Color of text ID
    
    FG_GRAY   = "#333333"
    FG_BLACK  = "#000000"
    FG_GREEN  = "green"
    FG_RED    = "red"


    RESULT_NAME = "SCAP WORKBENCH Test Result"

    def __init__(self, id, core, progress=None):
        DataHandler.__init__(self, core)
        EventObject.__init__(self, core)
        
        self.id = id
        self.__progress=progress
        self.__cancel = False
        self.count_current = 0
        self.result = None

        core.register(id, self)
        self.add_sender(self.id, "filled")
    
    def new_model(self):
        return gtk.TreeStore(str, str, str, str, str, str, str, str)

    def render(self, treeView):
        """ define treeView"""
        
        self.treeView = treeView

        #model: id rule, result, fix, description, color text desc, color background, color text res
        self.model = self.new_model()
        treeView.set_model(self.model)
        #treeView.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        #treeView.set_property("tree-line-width", 10)

        # ID Rule
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Rule ID", txtcell, text=DHScan.COLUMN_ID)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT_ID)
        column.set_resizable(True)
        treeView.append_column(column)

        #Result
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Result", txtcell, text=DHScan.COLUMN_RESULT)
        column.add_attribute(txtcell, 'background', DHScan.COLUMN_COLOR_BACKG)
        # since we control the background in this case, we have to enforce foreground as well so
        # that the text is visible
        txtcell.set_property('foreground', '#000000')
        column.set_resizable(True)
        treeView.append_column(column)

        # Fix
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Fix", txtcell, text=DHScan.COLUMN_FIX)
        column.set_resizable(True)
        column.set_visible(False)
        treeView.append_column(column)

        # Title
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", txtcell, text=DHScan.COLUMN_TITLE)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT_TITLE)
        column.set_resizable(True)
        treeView.append_column(column)

        # Description
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Description", txtcell, text=DHScan.COLUMN_DESC)
        column.set_resizable(True)
        column.set_visible(False)
        id = treeView.append_column(column)
        treeView.set_tooltip_column(id-1)

    def fill(self, item, iter=None):
        BG_RED    = "#F29D9D"
        BG_ERR    = "red"
        BG_GREEN  = "#9DF29D"
        BG_LGREEN = "#ADFFAD"
        BG_FIXED  = "green"
        BG_WHITE  = "white"
        BG_GRAY   = "gray"

        #initialization
        colorText_title = DHScan.FG_BLACK
        color_backG = BG_ERR
        colorText_ID = DHScan.FG_BLACK
        text = ""
        
        # choose color for cell, and text of result
        if  item[DHScan.COLUMN_RESULT] == None:
            text = "Running .."
            color_backG = BG_WHITE
            colorText_title = DHScan.FG_BLACK
            colorText_ID = DHScan.FG_BLACK
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_PASS:
            text = "PASS" # The test passed
            color_backG = BG_GREEN
            colorText_title = DHScan.FG_GRAY
            colorText_ID = DHScan.FG_BLACK
        
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_FAIL:
            text = "FAIL" # The test failed
            color_backG = BG_RED
            colorText_title = DHScan.FG_BLACK
            colorText_ID = DHScan.FG_BLACK
        
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_ERROR:
            text = "ERROR" # An error occurred and test could not complete
            color_backG = BG_ERR
            colorText_title = DHScan.FG_RED
            colorText_ID = DHScan.FG_RED
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_UNKNOWN:
            text = "UNKNOWN" #  Could not tell what happened
            color_backG = BG_GRAY
            colorText_title = DHScan.FG_BLACK
            colorText_ID = DHScan.FG_BLACK
        
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_APPLICABLE:
            text = "NOT_APPLICABLE" # Rule did not apply to test target
            color_backG = BG_WHITE
            colorText_title = DHScan.FG_GRAY
            colorText_ID = DHScan.FG_BLACK
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_CHECKED:
            text = "NOT_CHECKED" # Rule did not cause any evaluation by the checking engine
            color_backG = BG_WHITE
            colorText_title = DHScan.FG_GRAY                
            colorText_ID = DHScan.FG_BLACK

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
            text = "NOT_SELECTED" #Rule was not selected in the @link xccdf_benchmark Benchmark@endlink
            color_backG = BG_WHITE
            colorText_title = DHScan.FG_GRAY                
            colorText_ID = DHScan.FG_BLACK
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_INFORMATIONAL:
            text = "INFORMATIONAL" # Rule was evaluated by the checking engine, but isn't to be scored
            color_backG = BG_LGREEN
            colorText_title = DHScan.FG_GRAY                
            colorText_ID = DHScan.FG_BLACK

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_FIXED:
            text = "FIXED" # Rule failed, but was later fixed
            color_backG = BG_FIXED
            colorText_title = DHScan.FG_GRAY 
            colorText_ID = DHScan.FG_BLACK

        if not iter:
            iter = self.model.append(None)
        self.model.set(iter,
                DHScan.COLUMN_ID,   item[DHScan.COLUMN_ID],
                DHScan.COLUMN_RESULT,   text,
                DHScan.COLUMN_FIX,    item[DHScan.COLUMN_FIX], 
                DHScan.COLUMN_TITLE,  item[DHScan.COLUMN_TITLE],
                DHScan.COLUMN_DESC,  item[DHScan.COLUMN_DESC],
                DHScan.COLUMN_COLOR_TEXT_TITLE,  colorText_title,
                DHScan.COLUMN_COLOR_BACKG,  color_backG,
                DHScan.COLUMN_COLOR_TEXT_ID,  colorText_ID,
                )
        return iter

    @classmethod
    def __decode_callback_message(cls, msg):
        """Decodes a callback message and returns a 3-tuple containing the
        result, title and description of the test performed, in that order.
        
        This method is only to be used in __callback_start and __callback_output.
        """
        
        id = msg.user1str
        result = msg.user2num
        
        # The join of split string is used to convert all whitespace characters,
        # including newlines, tabs, etc, to plain spaces.
        #
        # In this case we need to do this because we are filling a table and
        # only have one line for all entries
        title = " ".join(msg.user3str.split()) if msg.user3str is not None else ""
        desc  = " ".join(msg.string.split()) if msg.string is not None else ""
        
        return (id, result, title, desc)        

    def __callback_start(self, msg, plugin):
        """Start callback is registered in "prepare" method and is called
        when each of the tests to be performed starts.
        
        When a test ends, __callback_output is called for it. __callback_output is always
        called after __callback_start has been called for that particular test.
        
        See __callback_output
        """
        
        id, result, title, desc = DHScan.__decode_callback_message(msg)
        if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED: 
            return self.__cancel

        self.__current_iter = self.fill([msg.user1str, None, False, title, desc])
        
        if self.__progress != None:
            with gtk.gdk.lock:
                # don't let progress fraction exceed 1.0 = 100%
                fract = min(self.__progress.get_fraction() + self.step, 1.0)
                self.__progress.set_fraction(fract)
                self.count_current = int(round(fract / self.step))
                
                self.__progress.set_text("Scanning rule '%s' ... (%s/%s)" % (id, self.count_current, self.count_all))
                logger.debug("[%s/%s] Scanning rule '%s'" % (self.count_current, self.count_all, id))
                
                self.__progress.set_tooltip_text("Scanning rule '%s'" % (title))

        return self.__cancel

    def __callback_output(self, msg, plugin):
        """The output callback is registered in "prepare" method and is called
        when each of the tests to be performed ends (regardless of the result).
        
        See __callback_start
        """
        
        id, result, title, desc = DHScan.__decode_callback_message(msg)
        if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED: 
            return self.__cancel

        with gtk.gdk.lock:    
            self.fill([id, result, False, title, desc], iter=self.__current_iter)
            self.emit("filled")
            self.treeView.queue_draw()
            self.count_current = int(round(self.__progress.get_fraction()/self.step))

        return self.__cancel

    def prepare(self):
        """Prepare system for evaluation
        return False if something goes wrong, True otherwise
        """

        if self.core.registered_callbacks == False:
            self.core.lib.policy_model.register_start_callback(self.__callback_start, self)
            self.core.lib.policy_model.register_output_callback(self.__callback_output, self)
            self.core.registered_callbacks = True
            
        else:
            for oval in self.core.lib.files.values():
                retval = openscap.oval.agent_reset_session(oval.session)
                logger.debug("OVAL Agent session reset: %s" % (retval,))
                if retval != 0: 
                    self.core.notify("Oval agent reset session failed.", core.Notification.ERROR, msg_id="notify:scan:oval_reset")
                    raise RuntimeError("OVAL agent reset session failed, openscap return value: %i" % (retval))
            self.__cancel = False

        self.model.clear()

        if self.core.selected_profile == None:
            self.policy = self.core.lib.policy_model.policies[0]
        else: self.policy = self.core.lib.policy_model.get_policy_by_id(self.core.selected_profile)

        self.count_current = 0
        self.count_all = len(self.policy.selected_rules)
        self.step = (100.0/(self.count_all or 1.0))/100.0
        
        return True
        
    def cancel(self):
        """ Called by user event when stop button pressed
        """
        self.__cancel = True
        if not self.check_library(): return None
        for oval in self.core.lib.files.values():
            retval = openscap.oval.agent_abort_session(oval.session)
            logger.debug("OVAL Agent session abort: %s" % (retval,))

    def export(self, file_name, result):
        """Exports a raw XML results file"""
        
        if self.core.lib == None:
            return False
        
        if file_name is None:
            file_name = self.file_browse("Save results", file="results.xml")
            
        if file_name != "":
            sessions = {}
            for oval in self.core.lib.files.values():
                sessions[oval.path] = oval.session
            files = self.policy.export(result, DHScan.RESULT_NAME, file_name, file_name, self.core.lib.xccdf, sessions)
            
            for file in files:
                logger.debug("Exported: %s", file)
            
            return file_name
        
        else:
            return None

    def perform_xslt_transformation(self, file, xslfile=None, expfile=None, hide_profile=None, result_id=None, oval_path=None):
        """Performs XSLT transformation on given file (raw XML results data, from DHScan.export for example).
        
        The resulting file (expfile) is the given raw XML results file transformed. Depending on the XSLT transformation
        used this can be anything XHTML, PDF, ...
        """
        
        params = [ 
            "result-id",         result_id,
            "show",              None,
            "profile",           self.core.selected_profile,
            "template",          None,
            "format",            None,
            "hide-profile-info", hide_profile,
            "verbosity",         "",
            "oscap-version",     openscap.common.oscap_get_version(),
            "pwd",               os.getenv("PWD"),
            # TODO: oval_path actually can't be None or this fails! We need to find a more sensible default value
            "oval-template",     os.path.join(oval_path,"%.result.xml")
        ]

        if not xslfile:
            xslfile = "xccdf-report.xsl"
            
        if not expfile:
            expfile = "report.xhtml"

        retval = openscap.common.oscap_apply_xslt(file, xslfile, expfile, params)
        # TODO If this call (below) is not executed, there will come some strange behaviour
        logger.debug("Export report file %s" % (["failed: %s" % (openscap.common.err_desc(),), "done"][retval],))
        return expfile

class DHEditItems(DataHandler):
    
    def __init__(self, core=None):
        super(DHEditItems, self).__init__(core)
        
        self.item = None # TODO: bug workaround - commands.py:1589 AttributeError: DHEditItems instance has no attribute 'item'
        
    def get_fixtexts(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item and item.type == openscap.OSCAP.XCCDF_RULE: return item.to_rule().fixtexts
        else: return []

    def get_fixes(self):
        if not self.check_library(): return None
        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item and item.type == openscap.OSCAP.XCCDF_RULE: return item.to_rule().fixes
        else: return []

    def edit_fix(self, operation, fix=None, id=None, content=None, system=None, platform=None, complexity=None, disruption=None, reboot=None, strategy=None):
        if not self.check_library(): return None

        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item is None:
            raise RuntimeError("Edit items update fix: No item selected !")
        
        item = item.to_rule()

        if operation == self.CMD_OPER_ADD:
            newfix = openscap.xccdf.fix_new()
            retval = newfix.set_id(id)
            if not retval: return False
            newfix.content = content

            item.add_fix(newfix)

        elif operation == self.CMD_OPER_EDIT:
            if fix == None: return False
            if id != None and id != fix.id:
                retval = fix.set_id(id)
                if not retval: return False
            if content != None and content != fix.content:
                fix.content = content
            if system != None and system != fix.system:
                fix.system = system
            if platform != None and platform != fix.platform:
                fix.platform = platform
            if complexity != None and complexity != fix.complexity:
                fix.complexity = complexity
            if disruption != None and disruption != fix.disruption:
                fix.disruption = disruption
            if reboot != None and reboot != fix.reboot:
                fix.reboot = reboot
            if strategy != None and strategy != fix.strategy:
                fix.strategy = strategy

        elif operation == self.CMD_OPER_DEL:
            if fix == None: return False
            item.fixes.remove(fix)
            
        else:
            raise NotImplementedError("Edit items update fix: Unsupported operation %s" % (operation))

        return True
        
    def edit_fixtext(self, operation, fixtext=None, lang=None, description=None, fixref=None, complexity=None, disruption=None,
                     reboot=None, strategy=None, overrides=None):
        if not self.check_library(): return None

        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item is None:
            raise RuntimeError("Edit items update fixtext: No item selected!")
        
        item = item.to_rule()

        if operation == self.CMD_OPER_ADD:
            fixtext = openscap.xccdf.fixtext_new()
            fixtext.text = openscap.common.text()
            fixtext.text.lang = lang
            fixtext.text.text = description

            item.add_fixtext(fixtext)

        elif operation == self.CMD_OPER_EDIT:
            if fixtext == None: return False
            if lang != None and lang != fixtext.text.lang:
                fixtext.text.lang = lang
            if description != None and description != fixtext.text.text:
                fixtext.text.text = description
            if fixref != None and fixref != fixtext.fixref:
                fixtext.fixref = fixref
            if complexity != None and complexity != fixtext.complexity:
                fixtext.complexity = complexity
            if disruption != None and disruption != fixtext.disruption:
                fixtext.disruption = disruption
            if reboot != None and reboot != fixtext.reboot:
                fixtext.reboot = reboot
            if strategy != None and strategy != fixtext.strategy:
                fixtext.strategy = strategy
            if overrides != None and overrides != fixtext.text.overrides:
                fixtext.text.overrides = overrides

        elif operation == self.CMD_OPER_DEL:
            if fixtext == None: return False
            item.fixtexts.remove(fixtext)
        else:
            raise NotImplementedError("Edit items update fixtext: Unsupported operation %s" % operation)

        return True
        

    def update(self, id=None, version=None, version_time=None, selected=None, hidden=None, prohibit=None, 
            abstract=None, cluster_id=None, weight=None, severity=None):
        if not self.check_library(): return None

        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item is None:
            raise RuntimeError("Edit items update: No item selected!")

        if id != None and len(id) > 0 and item.id != id:
            retval = item.set_id(id)
            if not retval: return False
            self.core.selected_item = id
        if version != None and item.version != version:
            item.version = version
        if version_time != None:
            item.version_time = version_time
        if selected != None:
            item.selected = selected
        if hidden != None:
            item.hidden = hidden
        if prohibit != None:
            item.prohibit_changes = prohibit
        if abstract != None:
            item.abstract = abstract
        if cluster_id != None and item.cluster_id != cluster_id:
            item.cluster_id = cluster_id
        if weight != None and item.weight != weight:
            item.weight = weight

        if item.type == openscap.OSCAP.XCCDF_RULE:
            item = item.to_rule()
            if severity != None and item.severity != severity:
                item.severity = severity

        return True

    def item_edit_value(self, operation, value, export_name):
        if not self.check_library(): return None

        item = self.core.lib.benchmark.get_item(self.core.selected_item)
        if item.type != openscap.OSCAP.XCCDF_RULE:
            raise RuntimeError("Invalid type of item '%s', expected 'XCCDF_RULE'. We can only edit values of rules!" % (item.type))
        
        item = item.to_rule()

        if operation == self.CMD_OPER_ADD:
            check_add = None
            #add to firts check which will found
            for check_ex in item.checks:
                check_add = check_ex
                break
            
            #check not exist create new
            if not check_add:
                check_add = openscap.xccdf.check_new()
                check_add.system="http://oval.mitre.org/XMLSchema/oval-definitions-5"
                item.add_check(check_add)
            check_export = openscap.xccdf.check_export_new()
            check_export.value = value
            check_export.name = export_name
            check_add.add_export(check_export)

        elif operation == self.CMD_OPER_EDIT:
            check_add = None
            #add to firts check which will found
            for check in item.checks:
                for check_export in check.exports:
                    if check_export.value == value:
                        check_export.value = value
                        check_export.name = export_name
                        return
                    
            raise RuntimeError("Edit operation failed, cant find the specified value '%s' to edit." % (value))
                
        elif operation == self.CMD_OPER_DEL:
            logger.error("Delete of value references not supported.")
            
        else:
            raise NotImplementedError("Operation of type '%i' not implemented" % (operation))

    def add_oval_reference(self, f_OVAL):
        if not self.check_library(): return False

        if os.path.exists(f_OVAL): 
            def_model = openscap.oval.definition_model_import(f_OVAL)
            if def_model.instance == None:
                if openscap.OSCAP.oscap_err(): desc = openscap.OSCAP.oscap_err_desc()
                else: desc = "Unknown error, please report this bug (http://bugzilla.redhat.com/)"
                raise core.XCCDFImportError("Cannot import definition model for \"%s\": %s" % (f_OVAL, desc))
            sess = openscap.oval.agent_new_session(def_model, os.path.basename(f_OVAL))
            if sess == None or sess.instance == None:
                if openscap.OSCAP.oscap_err(): desc = openscap.OSCAP.oscap_err_desc()
                else: desc = "Unknown error, please report this bug (http://bugzilla.redhat.com/)"
                raise core.XCCDFImportError("Cannot create agent session for \"%s\": %s" % (f_OVAL, desc))
            self.core.lib.add_file(os.path.basename(f_OVAL), sess, def_model)
            if self.core.lib.policy_model: self.core.lib.policy_model.register_engine_oval(sess)
        else: logger.warning("Skipping %s file which is referenced from XCCDF content" % (f_OVAL,))

        return True

    def DHEditIdent(self, item, model, iter, column, value, delete=False):

        COLUMN_ID = 0
        COLUMN_SYSTEM = 1
        COLUMN_OBJECT = 2

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.xccdf.ident_new()
                item.add_ident(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif not delete:
                if column == COLUMN_ID:
                    logger.info ("TODO set id Ident.")
                    #object.set_id(value)
                elif column == COLUMN_SYSTEM:
                    logger.info ("TODO set system Ident.")
                    #object.set_system(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.idents.remove(object)
                model.remove(iter)  
        else:
            logger.error("Error: Not read item.")

    def DHEditPlatform(self, item, model, iter, column, value, delete=False):

        COLUMN_TEXT = 0
        COLUMN_OBJECT = 1
        if item:
            if not delete:
                object = model.get_value(iter, COLUMN_OBJECT)
                if not object:
                    model.set_value(iter, COLUMN_OBJECT, value)
                    model.set_value(iter, COLUMN_TEXT, value)
                    item.add_platform(value)
                else:
                    if column == COLUMN_TEXT:
                        old_text = model.get_value(iter, COLUMN_OBJECT)
                        if old_text != value:
                            item.platforms.remove(old_text)
                            model.set_value(iter, COLUMN_TEXT, value)
                            item.add_platform(value)
                    else:
                        logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(value,))
                item.platforms.remove(value)
                model.remove(iter)  
        else:
            logger.error("Error: Not read item.")
            
    def DHEditImpactMetric(self, rule, text):
        if rule:
            if rule != openscap.OSCAP.XCCDF_RULE:
                rule = rule.to_rule()
            if not rule.set_impact_metric(text):
                logger.error("Error: Impact metric not set.")
        else:
            logger.error("Error: Not read rule.")

    def DHEditValueOper(self, value, oper):

        if value:
            value.set_oper(oper)
        else:
            logger.error("Error: Not value.")
    
    def DHChBoxValueInteractive(self, value, state):
        if value:
            value.set_interactive(state)
        else:
            logger.error("Error: Not value.")
    
    def DHEditValueInstance(self, value, item, selector, match, upper, lower, default, mustMuch, model_combo_choices):
        
        logger.debug("Editing value: %s", value)
        instance = item.get_instance_by_selector(selector)
        if not instance:
            instance = item.new_instance()
            item.add_instance(instance)
        else: logger.debug("Found instance for %s", selector)
            
        if item.get_type() == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            if value != None and value != '':
                try:
                    data = int(value)

                except ValueError:
                    #Try float.
                    try:
                        data = float(value)
                        
                    except ValueError:
                        data = float('nan')
            else:
                data = float('nan')
                
        else:
            data = value

        logger.debug("Set selector to %s", selector)
        instance.set_selector(selector)
        [lambda x: logger.error("Unknown type of value: %s", item.get_type()), 
                instance.set_value_number,
                instance.set_value_string,
                instance.set_value_boolean
                ][item.get_type()](data)

        return instance
        
    def DHEditValueInstanceDel(self, item, model, iter):
        COLUMN_SELECTOR = 0
        COLUMN_VALUE = 1
        COLUMN_MODEL_CHOICES = 2
        COLUMN_OBJECT = 3
    
        object = model.get_value(iter, COLUMN_OBJECT)
        logger.debug("Removing %s" %(object,))
        item.instances.remove(object)
        model.remove(iter)
    
    def DHEditBoundMatch(self, value, upper, lower, match):
        # if exist instance without selector take bound and match from this instance
        instance = None
        for ins in value.instances:
            if ins.selector == "" or ins.selector == None:
                instance = ins
                break
        if not instance:
            instance = value.new_instance()
            value.add_instance(instance)
            if value.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
                instance.set_value_number(float('nan'))
                
        if upper != None:
            if not instance.set_upper_bound(upper):
                return None
        if lower != None:
            if not instance.set_lower_bound(lower):
                return None
        if match != None:
            if not instance.set_match(match):
                return None
        return instance
        
    def DHEditRequires(self, item, id, add):
        if add:
            try:
                item.requires.append(id)
            except Exception as e:
                logger.exception("Add requires: %s" % (e))
        else:
            logger.debug("Add requires: Unsupported not-add function")
