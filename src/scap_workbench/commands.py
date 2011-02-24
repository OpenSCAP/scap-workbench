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
#      Maros Barabas        <mbarabas@redhat.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

import gtk, logging, sys, re, time, os
import gobject
import webbrowser
import datetime
import time
from datetime import datetime

from events import EventObject
from htmltextview import HtmlTextView

logger = logging.getLogger("scap-workbench")

try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None

from threads import thread as threadSave

class DataHandler(object):
    """DataHandler Class implements handling data from Openscap library,
    calling oscap functions and parsing oscap output to models specified by
    tool's objects"""

    CMD_OPER_ADD    = 0
    CMD_OPER_EDIT   = 1
    CMD_OPER_DEL    = 2

    def __init__(self, core):
        """DataHandler.__init__ -- initialization of data handler.
        Initialization is done by Core object.
        library => openscap library"""

        self.core = core

    def check_library(self):
        """Check if the library exists and the XCCDF file
        is loaded. If not return False and True otherwise"""
        if not self.core.lib or self.core.xccdf_file == None:
            self.core.notify("Library not initialized or XCCDF file not specified", 1, msg_id="notify:xccdf:not_loaded")
            return False
        else: return True

    def parse_value(self, value):

        # get value properties
        item = {}
        item["id"] = value.id
        item["lang"] = self.core.lib["policy_model"].benchmark.lang
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

        if self.core.selected_profile == None:
            profile = self.core.lib["policy_model"].policies[0].profile
        else: profile = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile).profile
        if profile != None:
            for r_value in profile.refine_values:
                if r_value.item == value.id:
                    try:
                        item["selected"] = (r_value.selector, item["options"][r_value.selector])
                    except KeyError:
                        logger.error("No selector \"%s\" available in rule %s" % (r_value.selector, item["id"]))
            for s_value in profile.setvalues:
                if s_value.item == value.id:
                    item["selected"] = ('', s_value.value)

        if "selected" not in item:
            if "" in item["options"]: item["selected"] = ('', item["options"][""])
            else: item["selected"] = ('', '')

        return item

    def get_languages(self):
        """Get available languages from XCCDF Benchmark
        """
        if not self.check_library(): return []
        return [self.core.lib["policy_model"].benchmark.lang]

    def get_selected(self, item, items_model):
        """DataHandler.get_selected -- get selction of rule/group
        returns boolean value"""

        if self.core.selected_profile == None or items_model == True:
            return item.selected
        else:
            policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)
            if policy == None: raise Exception, "Policy %s does not exist" % (self.core.selected_profile,)

            # Get selector from policy
            select = policy.get_select_by_id(item.id)
            if select == None: 
                return item.selected
            else: return select.selected

    def get_item_values(self, id):
        """Get all values of item with id equal to id parameter
        This could be either XCCDF Group or XCCDF Benchmark
        """

        if self.core.selected_profile == None:
            policy = self.core.lib["policy_model"].policies[0]
        else: policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)

        values = []
        if id == self.core.lib["policy_model"].benchmark.id: item = self.core.lib["policy_model"].benchmark
        else: item = self.core.lib["policy_model"].benchmark.item(id)
        
        if item.type == openscap.OSCAP.XCCDF_RULE:
            return policy.get_values_by_rule_id(id)
        else:
            item = item.to_group()
            values.extend( [self.parse_value(i) for i in item.values] )
            for i in item.content:
                if i.type == openscap.OSCAP.XCCDF_GROUP:
                    values.extend( self.get_item_values(i.id) )

        return values

    def get_item_details(self, id, items_model=False):
        """Parse details from item with id equal to id parameter to
        the dictionary."""

        if not self.check_library(): return None

        item = self.core.lib["policy_model"].benchmark.item(id or self.core.selected_item)
        if not item: return None

        policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)
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
                    #"checks":          item.checks
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
                    "instances":        item.instances,
                    "interactive":      item.interactive,
                    "interface_hint":   item.interface_hint,
                    "oper":             item.oper,
                    "sources":          item.sources,
                    "status_current":   item.status_current
                    })
            else: 
                logger.error("Item type not supported %d", item.type)
                return None

        else:
            logger.error("No item '%s' in benchmark", id)
            return None

        return values
 
    def get_item(self, id, items_model=False):
        """Get the item from benchmark
        """
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.item(id or self.core.selected_item)
        
    def get_profiles(self):
        """Get all profiles of the Benchmark
        """
        if not self.check_library(): return None
        profiles = []
        for item in self.core.lib["policy_model"].benchmark.profiles:
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

        policy = self.core.lib["policy_model"].get_policy_by_id(id or self.core.selected_profile)
        if not policy: return None
        item = policy.profile
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

        file_dialog.set_current_folder(os.path.dirname(file))
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
                    "lang": ref.lang,
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

    def get_benchmark_titles(self):
        if not self.core.lib: return {}
        benchmark = self.core.lib["policy_model"].benchmark
        if not benchmark: return None
        titles = {}
        for title in benchmark.title:
            titles[title.lang] = title.text
        return titles

    def remove_item(self, id):
        item = self.get_item(id)
        logger.info("Removing item %s" %(id,))
        parent = item.parent
        parent.content.remove(item)

    def edit_title(self, operation, obj, lang, text, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            title = openscap.common.text()
            title.text = text
            title.lang = lang
            return item.add_title(title)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.lang = lang
            obj.text = text
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.title.remove(obj)

        else: raise AttributeError("Edit title: Unknown operation %s" % (operation,))

    def edit_description(self, operation, obj, lang, text, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            description = openscap.common.text()
            description.text = text
            description.lang = lang
        
            return item.add_description(description)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.lang = lang
            obj.text = text
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.description.remove(obj)

        else: raise AttributeError("Edit description: Unknown operation %s" % (operation,))

    def edit_warning(self, operation, obj, category, lang, text, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            warning = openscap.xccdf.warning_new()
            new_text = openscap.common.text()
            new_text.text = text
            new_text.lang = lang
            warning.text = new_text
            if category != None: warning.category = category
    
            return item.add_warning(warning)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.text.lang = lang
            obj.text.text = text
            if category != None: obj.category = category
            return True

        elif operation == self.CMD_OPER_DEL:
            return item.warnings.remove(obj)

        else: raise AttributeError("Edit warning: Unknown operation %s" % (operation,))

    def edit_status(self, operation, obj, date, status, item=None):

        if not self.check_library(): return None

        if item == None:
            item = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item)

        if operation == self.CMD_OPER_ADD:
            t = datetime.strptime(date, "%Y-%m-%d")
            the_date = time.mktime(t.timetuple())
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

class DHXccdf(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def get_details(self):
    
        if not self.check_library(): return None
        benchmark = self.core.lib["policy_model"].benchmark
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
                "files":            self.core.lib["policy_model"].files.strings
                }


        return details

    def get_oval_files_info(self):

        if not self.check_library(): return None

        info = {}
        for name in self.core.lib["names"].keys():
            if len(self.core.lib["names"][name]) != 2: 
                logger.error("No sesion and/or definition model loaded for %s: ", name, self.core.lib["names"][name])
                return

            def_model = self.core.lib["names"][name][1]
            info[name] = {}
            info[name]["product_name"] = def_model.generator.product_name
            info[name]["product_version"] = def_model.generator.product_version
            info[name]["schema_version"] = def_model.generator.schema_version
            info[name]["timestamp"] = def_model.generator.timestamp
            info[name]["valid"] = ["yes", "no"][def_model.is_valid()]
        
        return info

    def update(self, id=None, version=None, resolved=None, lang=None):

        if not self.check_library(): return None
        benchmark = self.core.lib["policy_model"].benchmark

        if id and benchmark.id != id: benchmark.id = id
        if version and benchmark.version != version: benchmark.version = version
        if resolved and benchmark.resolved != resolved: benchmark.resolved = resolved
        if lang and benchmark.lang != lang: benchmark.lang = lang

    def export(self):

        if not self.check_library(): return None

        file_name = self.file_browse("Save XCCDF file", file=self.core.xccdf_file)
        if file_name != "":
            self.core.lib["policy_model"].benchmark.export(file_name)
            logger.debug("Exported benchmark: %s", file_name)
            return file_name
        return None

    def validate(self):
        if not self.check_library(): return 2

        retval = openscap.common.validate_document(self.core.xccdf_file, openscap.OSCAP.OSCAP_DOCUMENT_XCCDF, None, self.__cb_report, None)
        return retval

    def get_titles(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.title
    def get_descriptions(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.description
    def get_warnings(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.warnings
    def get_notices(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.notices
    def get_statuses(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.statuses

    def edit_title(self, operation, obj, lang, text):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_title(operation, obj, lang, text, item=self.core.lib["policy_model"].benchmark)

    def edit_description(self, operation, obj, lang, text):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_description(operation, obj, lang, text, item=self.core.lib["policy_model"].benchmark)

    def edit_warning(self, operation, obj, category, lang, text):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_warning(operation, obj, category, lang, text, item=self.core.lib["policy_model"].benchmark.to_item())

    def edit_status(self, operation, obj, date, status):
        if not self.check_library(): return None
        super(DHXccdf, self).edit_status(operation, obj, date, status, item=self.core.lib["policy_model"].benchmark.to_item())

    def edit_notice(self, operation, obj, id, text):

        if not self.check_library(): return None

        if operation == self.CMD_OPER_ADD:
            notice = openscap.xccdf.notice_new()
            new_text = openscap.common.text()
            new_text.text = text
            notice.text = new_text
            notice.id = id
    
            return self.core.lib["policy_model"].benchmark.add_notice(notice)

        elif operation == self.CMD_OPER_EDIT:
            if obj == None: 
                return False
            obj.text.text = text
            obj.id = id
            return True

        elif operation == self.CMD_OPER_DEL:
            return self.core.lib["policy_model"].benchmark.notice.remove(obj)

        else: raise AttributeError("Edit notice: Unknown operation %s" % (operation,))

    def __cb_report(self, msg, plugin):
        return True

class DHValues(DataHandler):

    def __init__(self, core, items_model=False):
        self.items_model = items_model
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""
        self.treeView = treeView
        self.model = gtk.ListStore(str, str, str, str, gtk.TreeModel)
        self.treeView.set_model(self.model)

        """This Cell is used to be first hidden column of tree view
        to identify the item in list"""
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Unique ID", txtcell, text=0)
        column.set_visible(False)
        column.set_resizable(True)
        self.treeView.append_column(column)

        # Text
        txtcell = gtk.CellRendererText()
        txtcell.set_property("editable", False)
        column.pack_start(txtcell, False)
        column.set_attributes(txtcell, text=1)
        column = gtk.TreeViewColumn("Value Name", txtcell, text=1, foreground=3)
        column.set_resizable(True)
        self.treeView.append_column(column)

        #combo
        cellcombo = gtk.CellRendererCombo()
        cellcombo.set_property("editable", True)
        cellcombo.set_property("text-column", 0)
        cellcombo.connect("edited", self.cellcombo_edited)
        column = gtk.TreeViewColumn("Values", cellcombo, text=2, model=4, foreground=3)
        column.set_resizable(True)
        self.treeView.append_column(column)

    def fill(self, item=None):

        if not self.check_library(): return None

        """If item is None, then this is first call and we need to get the item
        from benchmark. Otherwise it's recursive call and the item is already
        eet up and we recursively add the parent till we hit the benchmark
        """
        if item == None:
            self.model.clear()
            if self.core.selected_item != None:
                item = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item)
                if item == None: 
                    logger.error("XCCDF Item \"%s\" does not exists. Can't fill data", self.core.selected_item)
                    raise Exception("XCCDF Item \"%s\" does not exists. Can't fill data" % (self.core.selected_item,))
            else: return
        
        # Append a couple of rows.
        item = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item)
        values = self.get_item_values(self.core.selected_item)
        # TODO: The 0:gray value is not working cause of error in get_selected that values stay the same color
        # after selecting rule/group
        color = ["black", "black"][self.get_selected(item, self.items_model)]
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
            policy = self.core.lib["policy_model"].policies[0]
        else: policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)

        model = self.treeView.get_model()
        iter = model.get_iter(path)
        id = model.get_value(iter, 0)
        logger.debug("Altering value %s", id)
        val = self.core.lib["policy_model"].benchmark.item(id).to_value()
        value = self.parse_value(val)
        logger.debug("Matching %s agains %s or %s", new_text, value["choices"], value["match"])
        # Match against pattern as "choices or match"
        choices = ""
        if value["selected"][0] in value["choices"]:
            choices = "|".join(value["choices"][value["selected"][0]])
            pattern = re.compile(value["match"]+"|"+choices)
        else: 
            pattern = re.compile(value["match"])

        if pattern.match(new_text):
            model.set_value(iter, 2, new_text)
            logger.debug("Regexp matched: text %s match %s", new_text, "|".join([value["match"], choices]))
            policy.set_tailor_items([{"id":id, "value":new_text}])
        else: logger.error("Failed regexp match: text %s does not match %s", new_text, "|".join([value["match"], choices]))


class DHItemsTree(DataHandler, EventObject):

    COLUMN_TYPE     = 0
    COLUMN_ID       = 1
    COLUMN_NAME     = 2
    COLUMN_PICTURE  = 3
    COLUMN_TEXT     = 4
    COLUMN_COLOR    = 5
    COLUMN_SELECTED = 6
    COLUMN_PARENT   = 7

    def __init__(self, id, core, progress=None, items_model=False, no_checks=False):
        """
        param items_model if False use selected profile is selected. If true use base model.
        """
        self.items_model = items_model
        self.id = id
        EventObject.__init__(self)
        DataHandler.__init__(self, core)
        self.no_checks = no_checks
        
        core.register(id, self)
        self.add_sender(self.id, "filled")
        self.__progress = progress
        self.__total = None
        self.__step = None
        self.map_filter = None
        
    def new_model(self):
        # Type, ID, Name, Picture, Text, Font color, selected, parent-selected
        return gtk.TreeStore(str, str, str, str, str, str, bool, bool)
        
    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

        self.treeView = treeView
        
        # priperin model for view and filtering
        self.model = self.new_model()
        self.ref_model = self.model
        treeView.set_model(self.model)

        """This Cell is used to be first hidden column of tree view
        to identify the type of item"""
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Type", txtcell, text=DHItemsTree.COLUMN_TYPE)
        column.set_visible(False)
        treeView.append_column(column)

        if not self.no_checks:
            render = gtk.CellRendererToggle()
            column = gtk.TreeViewColumn("", render, active=DHItemsTree.COLUMN_SELECTED,
                                                            sensitive=DHItemsTree.COLUMN_PARENT,
                                                            activatable=DHItemsTree.COLUMN_PARENT)
            #cb call for filter_model and ref_model
            render.connect('toggled', self.__cb_toggled)
            column.set_resizable(True)
            treeView.append_column(column)

        """This Cell is used to be first second column of tree view
        to identify the item in list"""
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Unique ID", txtcell, text=DHItemsTree.COLUMN_ID)
        column.set_visible(False)
        treeView.append_column(column)

        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name", txtcell, text=DHItemsTree.COLUMN_NAME)
        column.set_visible(False)
        treeView.append_column(column)

        """Cell that contains title of showed item with picture as prefix.
        Picture represent type of item: group or rule and text should start
        with "Group" and "Rule" text"""
        column = gtk.TreeViewColumn() 
        column.set_title("Rule/Group Title")
        column.set_expand(True)
        # Picture
        pbcell = gtk.CellRendererPixbuf()
        pbcell.set_property("stock-size", gtk.ICON_SIZE_SMALL_TOOLBAR)
        column.pack_start(pbcell, False)
        column.add_attribute(pbcell, 'icon-name', DHItemsTree.COLUMN_PICTURE)
        # Text
        txtcell = gtk.CellRendererText()
        column.pack_start(txtcell, True)
        column.set_attributes(txtcell, text=DHItemsTree.COLUMN_TEXT)
        column.add_attribute(txtcell, 'foreground', DHItemsTree.COLUMN_COLOR)
        column.set_resizable(True)
        treeView.append_column(column)
        #treeView.set_expander_column(column)

        treeView.set_enable_search(False)
        treeView.set_expander_column(column)

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


    def __cb_toggled(self, cell, path, model=None):
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
           3) If there is no selector create one and set up by attributes from treeView
           """
        policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)
        if policy == None: 
            raise Exception, "Policy %s does not exist" % (self.core.selected_profile,)

        select = policy.get_select_by_id(model[path][DHItemsTree.COLUMN_ID])
        if select == None:
            newselect = openscap.xccdf.select()
            newselect.item = model[path][DHItemsTree.COLUMN_ID]
            newselect.selected = model[path][DHItemsTree.COLUMN_SELECTED]
            policy.select = newselect
        else:
            select.selected = model[path][DHItemsTree.COLUMN_SELECTED]

        """This could be a group and we need set the sensitivity
        for all childs."""
        self.__set_sensitive(policy, model[path], model, model[path][DHItemsTree.COLUMN_SELECTED])

    def __recursive_fill(self, item=None, parent=None, pselected=True, with_values=False):
        """Function to fill the treeModel. Recursive call through benchmark items
        for constructing the tree structure. Select attribute is from selected policy (profile).
        See profiles.
        
        with_values - if the model has the values of groups"""

        """This is recusive call (item is not None) so let's get type of 
        item and add it to model. If the item is Group continue more deep with
        recursion to get all items to the tree"""
        color = None
        if self.__progress != None:
            gtk.gdk.threads_enter()
            value = self.__progress.get_fraction()+self.__step
            if value > 1.0: value = 1.0
            self.__progress.set_fraction(value)
            self.__progress.set_text("Adding items %s/%s" % (int(self.__progress.get_fraction()/self.__step), self.__total))
            gtk.gdk.threads_leave()

        """Check the item if it's selected. If the parent or the item is not selected
        change the color of the font to the fgray"""
        if self.items_model:
            selected = self.get_selected(item, self.items_model)
        else:
            selected = self.get_selected(item, self.items_model)
            color = ["gray", None][selected and pselected]
        
        """If item is not None let's fill the model with groups and rules.
        """
        if item != None:
            # Get striped titles without white characters
            titles = dict([(title.lang, " ".join(title.text.split())) for title in item.title])
            if self.core.selected_lang in titles.keys(): title = titles[self.core.selected_lang]
            else: title = titles[titles.keys()[0]]

            # TYPE: XCCDF_RULE
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                item = item.to_group()
                img = "emblem-documents"
                gtk.gdk.threads_enter()
                item_it = self.model.append(parent, ["group", item.id, title, img, ""+title, color, selected, pselected])
                self.treeView.queue_draw()
                gtk.gdk.threads_leave()

                """For all content of the group continue with recursive fill
                """
                for i in item.content:
                    self.__recursive_fill(i, item_it, selected and pselected, with_values=with_values)

                """Get the values of the group and add it to the end of group subtree
                """
                if with_values:
                    img = "emblem-downloads"
                    for value in item.values:
                        if len(value.title) == 0: title = value.id
                        titles = dict([(title.lang, " ".join(title.text.split())) for title in value.title])
                        if self.core.selected_lang in titles.keys(): title = titles[self.core.selected_lang]
                        else: title = titles[titles.keys()[0]]
                        gtk.gdk.threads_enter()
                        self.model.append(item_it, ["value", value.id, title, img, ""+title, color, selected, pselected])
                        self.treeView.queue_draw()
                        gtk.gdk.threads_leave()

            # TYPE: XCCDF_RULE
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                img = "document-new"
                gtk.gdk.threads_enter()
                item_it = self.model.append(parent, ["rule", item.id, title, img, ""+title, color, selected, pselected])
                self.treeView.queue_draw()
                gtk.gdk.threads_leave()

            #TYPE: UNKNOWN
            else: logger.warning("Unknown type of %s, should be Rule or Group (got %s)", item.type, item.id)

        else: 
            raise Exception, "Can't get data to fill. Expected XCCDF Item (got %s)" % (item,)

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

    @threadSave
    def fill(self, item=None, parent=None, with_values=False):
        """Thread save function to fill the treeView."""
        if not self.check_library(): return None

        """we don't know item so it's first call and we need to clear
        the model, get the item from benchmark and continue recursively
        through content to fill the tree"""

        # Get number of all items
        if self.__progress:
            self.__progress.set_fraction(0.0)
            self.__progress.show()
            self.__total = self.__item_count(self.core.lib["policy_model"].benchmark, with_values=with_values)
        self.__step = (100.0/(self.__total or 1.0))/100.0

        try:
            gtk.gdk.threads_enter()
            self.model.clear()
            self.treeView.set_sensitive(False)
            gtk.gdk.threads_leave()

            for item in self.core.lib["policy_model"].benchmark.content:
                if self.__progress != None:
                    gtk.gdk.threads_enter()
                    self.__progress.set_fraction(self.__progress.get_fraction()+self.__step)
                    self.__progress.set_text("Adding items %s/%s" % (int(self.__progress.get_fraction()/self.__step), self.__total))
                    gtk.gdk.threads_leave()
                self.__recursive_fill(item, with_values=with_values)

            gtk.gdk.threads_enter()
            self.treeView.set_sensitive(True)
            gtk.gdk.threads_leave()
        finally:
            gtk.gdk.threads_enter()
            if self.__progress != None:
                self.__progress.set_text("Applying filters ...")
                self.__progress.set_fraction(1.0)
                self.__progress.hide()
            self.emit("filled")
            gtk.gdk.threads_leave()

        return True


class DHProfiles(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Profile object
        """

        self.model = gtk.ListStore(str, str)
        treeView.set_model(self.model)

        """This Cell is used to be first hidden column of tree view
        to identify the item in list"""
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Unique ID", txtcell, text=0)
        column.set_visible(False)
        treeView.append_column(column)

        """Cell that contains title of showed item
        """
        column = gtk.TreeViewColumn() 
        column.set_title("Profile title")
        column.set_expand(True)
        # Text
        txtcell = gtk.CellRendererText()
        column.pack_start(txtcell, True)
        column.set_attributes(txtcell, text=1)
        column.set_resizable(True)
        treeView.append_column(column)

    def add(self, item):
        """Add a new profile to the benchmark.
        Item is a dictionary specifing profile to be added
        
        This method is using @ref edit method to fill the data from
        item to the XCCDF Profile structure"""

        logger.debug("Adding new profile: \"%s\"", item["id"])
        if not self.check_library(): return None

        profile = openscap.xccdf.profile()
        self.edit(item, profile)

        self.core.lib["policy_model"].benchmark.add_profile(profile)
        self.core.lib["policy_model"].add_policy(openscap.xccdf.policy(self.core.lib["policy_model"], profile))

    def edit(self, item, profile=None):
        """Edit profile (if it's not None) with the values from
        item parameter.

        If profile is None try to get the profile from benchmark instead.
        If this failed and selected profile does not exist return False"""

        logger.debug("Editing profile: \"%s\"", item["id"])
        if not self.check_library(): return None

        # Try to find the selected profile if it exists
        if not profile: profile = self.core.lib["policy_model"].benchmark.get_item(self.core.selected_profile)
        if not profile: 
            self.core.notify("Saving profile failed: No profile \"%s\" in benchmark." % (self.core.selected_profile), 2)
            logger.error("No profile \"%s\" in benchmark", self.core.selected_profile)
            return False

        # Fill the profile with details from the item parameter
        profile.id = item["id"]
        profile.abstract = item["abstract"]
        profile.version = item["version"]
        if item["extends"] != None: profile.extends = item["extends"]
        for detail in item["details"]:
            if detail["title"]:
                title = openscap.common.text()
                title.text = detail["title"]
                title.lang = detail["lang"]
                profile.title = title
            if detail["description"]:
                description = openscap.common.text()
                description.text = detail["description"]
                description.lang = detail["lang"]
                profile.description = description

    def fill(self, item=None, parent=None, no_default=False):
        """Clear the model and fill it with existing profiles from loaded benchmark
        no_default parameter means that there should not be a default document representation of policy
        """

        self.model.clear()
        if not self.check_library(): return None

        if not no_default:
            logger.debug("Adding profile (No profile)")
            self.model.append([None, "(No profile)"])

        # Go thru all profiles from benchmark and add them into the model
        for item in self.core.lib["policy_model"].benchmark.profiles:
            logger.debug("Adding profile \"%s\"", item.id)
            pvalues = self.get_profile_details(item.id)
            if self.core.selected_lang in pvalues["titles"]:
                self.model.append([item.id, "Profile: "+pvalues["titles"][self.core.selected_lang]])
            else:
                self.core.notify("No title with \"%s\" language in \"%s\" profile. Change language to proper view." % (self.core.selected_lang, item.id), 
                                  1, msg_id="notify:global:profile:fill:no_lang") # TODO
                self.model.append([item.id, "Profile: %s (ID)" % (item.id,)])
                return False

        return True

    def save(self):
        """Save the profile in the benchmark. Profile still exists just as policy and
        all changes made to the policy after tailoring are not mirrored to the profile,
        therefor we need to save it explicitely."""

        policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)
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

        logger.info("Removing profile %s" %(id,))
        profile = self.core.lib["policy_model"].benchmark.get_item(id).to_profile()
        self.core.lib["policy_model"].benchmark.profiles.remove(profile)

    def change_refines(self, weight=None, severity=None, role=None):
        """Call the library to change refines of profile
        """
        if self.core.selected_profile == None: return
        if not self.check_library(): return None

        policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)
        if policy:
            logger.debug("Changing refine_rules: item(%s): severity(%s), role(%s), weight(%s)" % (self.core.selected_item, severity, role, weight))
            refine = policy.set_refine_rule(self.core.selected_item, weight, severity, role)


class DHScan(DataHandler, EventObject):

    COLUMN_ID = 0               # id of rule
    COLUMN_RESULT = 1           # Result of scan
    COLUMN_FIX = 2              # fix
    COLUMN_TITLE = 3            # Description of rule
    COLUMN_DESC = 4             # Description of rule
    COLUMN_COLOR_TEXT_TITLE = 5 # Color of text description
    COLUMN_COLOR_BACKG = 6      # Color of cell
    COLUMN_COLOR_TEXT_ID = 7    # Color of text ID
    
    BG_RED      = "#F29D9D"
    BG_ERR      = "red"
    BG_GREEN    = "#9DF29D"
    BG_LGREEN   = "#ADFFAD"
    BG_FIXED    = "green"
    BG_WHITE    = "white"
    BG_GRAY     = "gray"
    
    FG_GRAY   = "gray"
    FG_BLACK  = "black"
    FG_GREEN  = "green"
    FG_RED    = "red"


    RESULT_NAME = "SCAP WORKBENCH Test Result"

    def __init__(self, id, core, progress=None):

        self.id = id
        EventObject.__init__(self)
        DataHandler.__init__(self, core)
        self.__progress=progress
        self.__cancel = False
        self.__last = 0
        self.__result = None
        self.__cancel_notify = None
        self.__lock = False

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
        column = gtk.TreeViewColumn("Role ID", txtcell, text=DHScan.COLUMN_ID)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT_ID)
        column.set_resizable(True)
        treeView.append_column(column)

        #Result
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("     Result     ", txtcell, text=DHScan.COLUMN_RESULT)
        column.add_attribute(txtcell, 'background', DHScan.COLUMN_COLOR_BACKG)
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

        #initialization
        colorText_title = DHScan.FG_BLACK
        colorText_res = DHScan.FG_BLACK
        color_backG = DHScan.BG_ERR
        colorText_ID = DHScan.FG_BLACK
        text = ""
        
        # choose color for cell, and text of result
        if  item[DHScan.COLUMN_RESULT] == None:
            text = "Runnig .."
            color_backG = DHScan.BG_WHITE
            colorText_title = DHScan.FG_BLACK
            colorText_ID = DHScan.FG_BLACK
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_PASS:
            text = "PASS" # The test passed
            color_backG = DHScan.BG_GREEN
            colorText_title = DHScan.FG_GRAY
            colorText_ID = DHScan.FG_BLACK
        
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_FAIL:
            text = "FAIL" # The test failed
            color_backG = DHScan.BG_RED
            colorText_title = DHScan.FG_BLACK
            colorText_ID = DHScan.FG_BLACK
        
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_ERROR:
            color_text = DHScan.FG_BLACK
            text = "ERROR" # An error occurred and test could not complete
            color_backG = DHScan.BG_ERR
            colorText_title = DHScan.FG_RED
            colorText_ID = DHScan.FG_RED
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_UNKNOWN:
            text = "UNKNOWN" #  Could not tell what happened
            color_backG = DHScan.BG_GRAY
            colorText_title = DHScan.FG_BLACK
            colorText_ID = DHScan.FG_BLACK
        
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_APPLICABLE:
            text = "NOT_APPLICABLE" # Rule did not apply to test target
            color_backG = DHScan.BG_WHITE
            colorText_title = DHScan.FG_GRAY
            colorText_ID = DHScan.FG_BLACK
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_CHECKED:
            text = "NOT_CHECKED" # Rule did not cause any evaluation by the checking engine
            color_backG = DHScan.BG_WHITE
            colorText_title = DHScan.FG_GRAY                
            colorText_ID = DHScan.FG_BLACK

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
            text = "NOT_SELECTED" #Rule was not selected in the @link xccdf_benchmark Benchmark@endlink
            color_backG = DHScan.BG_WHITE
            colorText_title = DHScan.FG_GRAY                
            colorText_ID = DHScan.FG_BLACK
            
        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_INFORMATIONAL:
            text = "INFORMATIONAL" # Rule was evaluated by the checking engine, but isn't to be scored
            color_backG = DHScan.BG_LGREEN
            colorText_title = DHScan.FG_GRAY                
            colorText_ID = DHScan.FG_BLACK

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_FIXED:
            text = "FIXED" # Rule failed, but was later fixed
            color_backG = DHScan.BG_FIXED
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

    def __callback_start(self, msg, plugin):
        result = msg.user2num
        if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED: 
            return self.__cancel

        if msg.user3str == None: title = ""
        else: title = " ".join(msg.user3str.split())
        if msg.string == None: desc = ""
        else: desc = " ".join(msg.string.split())
        self.__current_iter = self.fill([msg.user1str, None, False, title, desc])
        if self.__progress != None:
            gtk.gdk.threads_enter()
            fract = self.__progress.get_fraction()+self.step
            if fract < 1.0: self.__progress.set_fraction(fract)
            else: self.__progress.set_fraction(1.0)
            self.__progress.set_text("Scanning rule %s ... (%s/%s)" % (msg.user1str, int(self.__progress.get_fraction()/self.step), self.__rules_count))
            logger.debug("[%s/%s] Scanning rule %s" % (int(self.__progress.get_fraction()/self.step), self.__rules_count, msg.user1str))
            self.__progress.set_tooltip_text("Scanning rule %s" % (" ".join(msg.user3str.split()),))
            gtk.gdk.threads_leave()

        return self.__cancel

    def __callback_end(self, msg, plugin):
        result = msg.user2num
        if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED: 
            return self.__cancel

        gtk.gdk.threads_enter()
        #ID, Result, Fix, Title, Desc
        if msg.user3str == None: title = ""
        else: title = " ".join(msg.user3str.split())
        if msg.string == None: desc = ""
        else: desc = " ".join(msg.string.split())
        self.fill([msg.user1str, msg.user2num, False, title, desc], iter=self.__current_iter)
        self.emit("filled")
        self.treeView.queue_draw()
        self.__last = int(round(self.__progress.get_fraction()/self.step))
        gtk.gdk.threads_leave()

        return self.__cancel

    def __prepaire(self):
        """Prepaire system for evaluation
        return False if something goes wrong, True otherwise
        """

        if self.core.registered_callbacks == False:
            self.core.lib["policy_model"].register_start_callback(self.__callback_start, self)
            self.core.lib["policy_model"].register_output_callback(self.__callback_end, self)
        else:
            for sess in self.core.lib["sessions"]:
                retval = openscap.oval.agent_reset_session(sess)
                logger.debug("OVAL Agent session reset: %s" % (retval,))
                if retval != 0: 
                    self.core.notify("Oval agent reset session failed.", 2, msg_id="notify:scan:oval_reset")
                    raise Exception, "OVAL agent reset session failed"
            self.__cancel = False
            self.__last = 0

        self.model.clear()

        if self.core.selected_profile == None:
            self.policy = self.core.lib["policy_model"].policies[0]
        else: self.policy = self.core.lib["policy_model"].get_policy_by_id(self.core.selected_profile)

        #self.__rules_count = 0
        #for item in self.policy.selected_rules:
            #self.__rules_count += 1
        self.__rules_count = len(self.policy.selected_rules)
        self.core.registered_callbacks = True
        self.step = (100.0/(self.__rules_count or 1.0))/100.0
        return True
        
    def cancel(self):
        if not self.check_library(): return None

        if not self.__cancel:
            self.__cancel = True
            self.__cancel_notify = self.core.notify("Scanning canceled. Please wait for openscap to finish current task.", 0, msg_id="notify:scan:cancel")
        for sess in self.core.lib["sessions"]:
            retval = openscap.oval.agent_abort_session(sess)
            logger.debug("OVAL Agent session abort: %s" % (retval,))

    def export(self):
        if not self.core.lib or self.__result == None: return False
        file_name = self.file_browse("Save results", file="results.xml")
        if file_name != "":
            files = self.policy.export(self.__result, self.core.lib, DHScan.RESULT_NAME, file_name, file_name)
            for file in files:
                logger.debug("Exported: %s", file)
            return file_name
        else: return None

    def export_report(self, file):
        params = [ 
            "result-id",         None,
            "show",              None,
            "profile",           None,
            "template",          None,
            "format",            None,
            "hide-profile-info", None,
            "verbosity",         "1",
            "oscap-version",     openscap.common.oscap_get_version(),
            "pwd",               os.getenv("PWD"),
            "oval-template",    "%.result.xml", None]

        retval = openscap.common.oscap_apply_xslt(file, "xccdf-report.xsl", "report.xhtml", params)
        logger.info("Export report file %s" % (["failed: %s" % (openscap.common.err_desc(),), "done"][retval],))
        browser_val = webbrowser.open("report.xhtml")
        if not browser_val: self.core.notify("Failed to open browser \"%s\". Report file is saved in \"%s\"" % (webbrowser.get().name, "report.xhtml"), 1, msg_id="notify:scan:export_report")

    def scan(self):
        if self.__lock: 
            logger.error("Scan already running")
        elif self.core.selected_profile: 
            self.__prepaire()
            self.__lock = True
            self.th_scan()

    @threadSave
    def th_scan(self):
        if not self.check_library(): return None

        logger.debug("Scanning %s ..", self.policy.id)
        if self.__progress != None:
            gtk.gdk.threads_enter()
            self.__progress.set_fraction(0.0)
            self.__progress.set_text("Prepairing ...")
            gtk.gdk.threads_leave()

        self.__result = self.policy.evaluate()
        if self.__progress: 
            self.__progress.set_fraction(1.0)
            self.__progress.set_text("Finished %s of %s rules" % (self.__last, self.__rules_count))
            self.__progress.set_has_tooltip(False)
        logger.debug("Finished scanning")
        if self.__cancel_notify: self.__cancel_notify.destroy()
        self.__lock = False

class DHEditItems(DataHandler):
    
    def __init__(self, core=None):

        self.item = None # TODO: bug workaround - commands.py:1589 AttributeError: DHEditItems instance has no attribute 'item'
        self.core = core

    def get_titles(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item).title
    def get_descriptions(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item).description
    def get_warnings(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item).warnings
    def get_statuses(self):
        if not self.check_library(): return None
        return self.core.lib["policy_model"].benchmark.get_item(self.core.selected_item).statuses

    def DHEditAddItem(self, item_to_add, group, data):

        ID = 0
        TITLE_LANG = 1
        TITLE = 2

        if group:
            item = openscap.xccdf.group_new()
            item.set_id(data[ID])
            vys = item_to_add.add_group(item)
    
        else:
            item = openscap.xccdf.rule_new()
            item.set_id(data[ID])
            vys = item_to_add.add_rule(item)
        if not vys:
            return vys
        title = openscap.common.text_new()
        title.set_lang(data[TITLE_LANG])
        title.set_text(data[TITLE]) 
        item.add_title(title)
        return vys
        
    def DHEditTitle(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2

        if not item: item = self.get_item(self.core.selected_item)
        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_title(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.text = value
                    #object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.title.remove(object)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")
            
    def DHEditDescription(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2
 
        if not item: item = self.get_item(self.core.selected_item)
        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_description(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.description.remove(object)
                model.remove(iter)  
        else:
            logger.error("Error: Not read item.")
            
    def DHEditWarning(self, item, model, iter, column, value, delete=False):

        COLUMN_CATEGORY_TEXT= 0
        COLUMN_CATEGORY_ITER = 1
        COLUMN_LAN = 2
        COLUMN_TEXT = 3
        COLUMN_OBJECT = 4

        if not item: item = self.get_item(self.core.selected_item)
        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.xccdf.warning_new()
                object.set_text(openscap.common.text_new())
                item.add_warning(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_CATEGORY_ITER:
                    object.set_category(value)
                elif column == COLUMN_TEXT:
                    object_text = openscap.xccdf.warning_get_text(object)
                    object_text.set_text(value)
                elif column == COLUMN_LAN:
                    object_text = openscap.xccdf.warning_get_text(object)
                    object_text.set_lang(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.warnings.remove(object)
                model.remove(iter) 
        else:
            logger.error("Error: Not read item.")
            
    def DHEditStatus(self, item, model, iter, column, value, delete=False):

        COLUMN_STATUS_TEXT= 0
        COLUMN_STATUS_ITER = 1
        COLUMN_DATE = 2
        COLUMN_OBJECT = 3

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.xccdf.status_new()
                item.add_status(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_STATUS_ITER:
                    object.set_status(value)
                elif column == COLUMN_DATE:
                    object.set_date(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.statuses.remove(object)
                model.remove(iter) 
        else:
            logger.error("Error: Not read item.")

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

    def DHEditQuestion(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_question(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.question.remove(object)
                model.remove(iter)  
        else:
            logger.error("Error: Not read item.")
                
    def DHEditRationale(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2
        
        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_rationale(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.rationale.remove(object)
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

    def DHEditVersionTime(self, item, timestamp):
        if item:
            item.set_version_time(timestamp)
        else:
            logger.error("Error: Not read item.")


    def cb_entry_version(self, widget, event):
        item = self.get_item(self.core.selected_item)
        if item:
            item.set_version(widget.get_text())
        else:
            logger.error("Error: Not read item.")

    def DHEditChboxSelected(self, widget, item=None):
        if item:
            item.set_selected(widget.get_active())
        else:
            logger.error("Error: Not read item.")

    def cb_chbox_hidden(self, widget):
        item = self.get_item(self.core.selected_item)
        if item:
            item.set_hidden(widget.get_active())
        else:
            logger.error("Error: Not read item.")

    def cb_chbox_prohibit(self, widget):
        item = self.get_item(self.core.selected_item)
        if item:
            item.set_prohibit_changes(widget.get_active())
        else:
            logger.error("Error: Not read item.")

    def cb_chbox_abstract(self, widget):
        item = self.get_item(self.core.selected_item)
        if item:
            item.set_abstract(widget.get_active())
        else:
            logger.error("Error: Not read item.")

    def cb_entry_cluster_id(self, widget, event):
        item = self.get_item(self.core.selected_item)
        if item:
            item.set_cluster_id(widget.get_text())
        else:
            logger.error("Error: Not read item.")

    def DHEditWeight(self, data):
        item = self.get_item(self.core.selected_item)
        if item:
            item.set_weight(data)
        else:
            logger.error("Error: Not read item.")

    def cb_chbox_multipl(self, widget):
        rule = self.get_item(self.core.selected_item).to_rule()
        if rule:
            rule.set_multiple(widget.get_active())
        else:
            logger.error("Error: Not read item.")

    def  cb_cBox_severity(self, widget):

        COLUMN_DATA = 0

        rule = self.item.to_rule()
        if rule:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                rule.set_severity(model[active][COLUMN_DATA])
        else:
            logger.error("Error: Not rule.")
            
    def  cb_cBox_role(self, widget):

        COLUMN_DATA = 0

        rule = self.item.to_rule()
        if rule:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                rule.set_role(model[active][COLUMN_DATA])
        else:
            logger.error("Error: Not rule.")
            
    def DHEditImpactMetrix(self, rule, text):
        if rule:
            if rule != openscap.OSCAP.XCCDF_RULE:
                rule = rule.to_rule()
            if not rule.set_impact_metric(text):
                logger.error("Error: Impact metrix not set.")
        else:
            logger.error("Error: Not read rule.")

    def DHEditValue(self, item, model, iter, column, value, delete=False):

        COLUMN_ID = 0
        COLUMN_TITLE = 1
        COLUMN_TYPE_ITER = 2
        COLUMN_TYPE_TEXT = 3
        COLUMN_OBJECT = 4
        COLUMN_CHECK = 5
        COLUMN_CHECK_EXPORT = 6
        
        if self.item:
            if not delete:
                # column == None new data 
                if column == None:
                    parent = self.item.get_parent()
                    value = openscap.xccdf.value_new(value)
                    
                    # if parent si benchmark or rule
                    if parent.type ==  openscap.OSCAP.XCCDF_GROUP:
                        parent = parent.to_group()
                    else:
                        parent = self.item.get_benchmark()
                        
                    parent.add_value(value)
                    model.set_value(iter, COLUMN_OBJECT, value)
                elif column == COLUMN_ID:
                    object = model.get_value(iter, COLUMN_OBJECT)
                    object.set_id(value)
                    check_add = None
                    #add to firts check which will found
                    for check_ex in self.item.checks:
                        check_add = check_ex
                        break
                    
                    #check not exist create new
                    if not check_add:
                        check_add = openscap.xccdf.check_new()
                        self.item.add_check(check_add)
                    model.set_value(iter, COLUMN_CHECK, check_add)
                    check_export = openscap.xccdf.check_export_new()
                    check_export.set_value(value)
                    check_add.add_export(check_export)
                        
                elif column == COLUMN_TYPE_ITER:
                    pass
                else:
                    logger.error("Bad number of column.")
            else:
                check = model.get_value(iter, COLUMN_CHECK)
                check_export = model.get_value(iter, COLUMN_CHECK_EXPORT)
                logger.debug("Removing %s" %(check_export,))
                check.exports.remove(check_export)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")

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
    
    def DHEditValueTitle(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_title(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.title.remove(object)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")
            
    def DHEditValueDescription(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_description(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.description.remove(object)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")
            
    def DHEditValueQuestion(self, item, model, iter, column, value, delete=False):

        COLUMN_LAN = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)

            if not object:
                object = openscap.common.text_new()
                item.add_question(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_LAN:
                    object.set_lang(value)
                elif column == COLUMN_TEXT:
                    object.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                item.question.remove(object)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")
            
    def DHEditConflicts(self, item, id, add):
        if add:
            try:
                item.add_conflicts(id)
            except Exception, e:
                logger.error("Add conflicts: %s" % (e,))
        else:
            pass

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
                    data = float(value)
            else:
                data = float('nan')
        else: data = value

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
            except Exception, e:
                logger.error("Add requires: %s" % (e,))
        else:
            logger.debug("Add requires: Unsupported not-add function")
        
    # DH fixtext ===============================
    def DHEditFixtextText(self, item, model, iter, column, value, delete=False):
        
        COLUMN_TEXT = 0
        COLUMN_OBJECT = 1

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)
            rule = item.to_rule()
            if not object:
                object = openscap.xccdf.fixtext_new()
                rule.add_fixtext(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_TEXT:
                    object_text = object.get_text()
                    if not object_text: 
                        object_text  = openscap.common.text_new()
                        object.set_text(object_text) 
                    object_text.set_text(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                rule.fixtexts.remove(object)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")
            
    def cb_entry_fixtext_reference(self, widget, event):
        if self.item :
            self.item.set_fixref(widget.get_text())
        else:
            logger.error("Error: Not read rule.")

    def cb_combo_fixtext_strategy(self, widget):
        
        COLUMN_DATA = 0
        if self.item:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                if not self.item.set_strategy(model[active][COLUMN_DATA]):
                    logger.error("Strategy have not set in Fixtext.")
        else:
            logger.error("Error: Not fixtex.")

    def cb_combo_fixtext_complexity(self, widget):

        COLUMN_DATA = 0
        if self.item:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                if not self.item.set_complexity(model[active][COLUMN_DATA]):
                    logger.error("Strategy have not setted in Fixtext.")
        else:
            logger.error("Error: Not fixtex.")
    
    def cb_combo_fixtext_disruption(self, widget):
        COLUMN_DATA = 0
        if self.item:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                if not self.item.set_disruption(model[active][COLUMN_DATA]):
                    logger.error("Disruption have not set in Fixtext.")
        else:
            logger.error("Error: Not fixtex.")
    
    def cb_chbox_fixtext_reboot(self, widget):

        if self.item:
            self.item.set_reboot(widget.get_active())
        else:
            logger.error("Error: Not fixtex.")
    
    # DH fix ======================================================
    def DHEditFix(self, item, model, iter, column, value, delete=False):
        
        COLUMN_ID = 0
        COLUMN_TEXT = 1
        COLUMN_OBJECT = 2

        if item:
            object = model.get_value(iter, COLUMN_OBJECT)
            rule = item.to_rule()
            
            if not object:
                object = openscap.xccdf.fix_new()
                rule.add_fix(object)
                model.set_value(iter, COLUMN_OBJECT, object)
            elif  not delete:
                if column == COLUMN_TEXT:
                    object.set_content(value)
                elif column == COLUMN_ID:
                    object.set_id(value)
                else:
                    logger.error("Bad number of column.")
            else:
                logger.debug("Removing %s" %(object,))
                rule.fixes.remove(object)
                model.remove(iter)
        else:
            logger.error("Error: Not read item.")
           
    def cb_entry_fix_system(self, widget, event):
        if self.item:
            self.item.set_system(widget.get_text())
        else:
            logger.error("Error: Not read fix.")
    
    def cb_entry_fix_platform(self, widget, event):
        if self.item:
            self.item.set_platform(widget.get_text())
        else:
            logger.error("Error: Not read fix.")
    
    def cb_combo_fix_strategy(self, widget):
        
        COLUMN_DATA = 0
        if self.item:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                self.item.set_strategy(model[active][COLUMN_DATA])
        else:
            logger.error("Error: Not fix.")

    def cb_combo_fix_complexity(self, widget):

        COLUMN_DATA = 0
        if self.item:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                self.item.set_complexity(model[active][COLUMN_DATA])
        else:
            logger.error("Error: Not fix.")
    
    def cb_combo_fix_disruption(self, widget):
        COLUMN_DATA = 0
        if self.item:
            active = widget.get_active()
            if active > 0:
                model = widget.get_model()
                self.item.set_disruption(model[active][COLUMN_DATA])
        else:
            logger.error("Error: Not fix.")
            
    def cb_chbox_fix_reboot(self, widget):

        if self.item:
            self.item.set_reboot(widget.get_active())
        else:
            logger.error("Error: Not fix.")
