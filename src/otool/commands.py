#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gtk, logging, sys, re, time
import gobject
logger = logging.getLogger("OSCAPEditor")

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")
sys.path.append("/tmp/scap/usr/local/lib/python2.6/site-packages")

try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    logger.error("OpenScap library initialization failed")
    openscap=None

from core import thread as threadSave
import threading

class DataHandler:
    """DataHandler Class implements handling data from Openscap library,
    calling oscap functions and parsing oscap output to models specified by
    tool's objects"""

    def __init__(self, core):
        """DataHandler.__init__ -- initialization of data handler.
        Initialization is done by Core object.
        library => openscap library"""

        self.core = core
        self.selected_profile = None
        self.selected_item = None

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
            item["match"] = ["", "^[\\b]+$", "^.*$", "^[01]$"][value.type]

        if self.selected_profile == None:
            profile = self.core.lib["policy_model"].policies[0].profile
        else: profile = self.core.lib["policy_model"].get_policy_by_id(self.selected_profile).profile
        if profile != None:
            for r_value in profile.refine_values:
                if r_value.item == value.id:
                    item["selected"] = (r_value.selector, item["options"][r_value.selector])
            for s_value in profile.setvalues:
                if s_value.item == value.id:
                    item["selected"] = ('', s_value.value)

        if "selected" not in item:
            if "" in item["options"]: item["selected"] = ('', item["options"][""])
            else: item["selected"] = ('', '')

        return item

    def get_languages(self):
        """Get available languages from XCCDF Benchmark"""
        if self.core.lib == None: return []
        return [self.core.lib["policy_model"].benchmark.lang]

    def get_selected(self, item):
        """DataHandler.get_selected -- get selction of rule/group
        returns boolean value"""

        if self.selected_profile == None:
            return item.selected

        else:
            policy = self.core.lib["policy_model"].get_policy_by_id(self.selected_profile)
            if policy == None: raise Exception, "Policy %s does not exist" % (self.selected_profile,)

            # Get selector from policy
            select = policy.get_select_by_id(item.id)
            if select == None: 
                return item.selected
            else: return select.selected

    def get_item_values(self, id):

        if self.selected_profile == None:
            policy = self.core.lib["policy_model"].policies[0]
        else: policy = self.core.lib["policy_model"].get_policy_by_id(self.selected_profile)

        values = []
        item = self.core.lib["policy_model"].benchmark.item(id)
        if item.type == openscap.OSCAP.XCCDF_RULE:
            return policy.get_values_by_rule_id(id)
        else:
            item = item.to_group()
            values.extend( [self.parse_value(i) for i in item.values] )
            for i in item.content:
                if i.type == openscap.OSCAP.XCCDF_GROUP:
                    values.extend( self.get_item_values(i.id) )

        return values

    def get_item_details(self, id):
        """get_item_details -- get details of XCCDF_ITEM"""

        item = self.core.lib["policy_model"].benchmark.item(id or self.selected_item)
        if item != None:
            values = {
                    "id":               item.id,
                    "type":             item.type,
                    "titles":           dict([(title.lang, title.text) for title in item.title]),
                    "descriptions":     dict([(desc.lang, desc.text) for desc in item.description]),
                    "abstract":         item.abstract,
                    "cluster_id":       item.cluster_id,
                    "conflicts":        [conflict.text for conflict in item.conflicts],
                    "extends":          item.extends,
                    "hidden":           item.hidden,
                    "platforms":        [platform.text for platform in item.platforms],
                    "prohibit_changes": item.prohibit_changes,
                    "questions":        dict([(question.lang, question.text) for question in item.question]),
                    "rationale":        [rationale.text for rationale in item.rationale],
                    "references":       [(ref.text.text, ref.href) for ref in item.references],
                    "requires":         item.requires,
                    "selected":         item.selected,
                    "statuses":         [(status.date, status.text) for status in item.statuses],
                    "version":          item.version,
                    "version_time":     item.version_time,
                    "version_update":   item.version_update,
                    "warnings":         [(warning.category, warning.text) for warning in item.warnings],
                    "weight":           item.weight,
                    "selected":         self.get_selected(item)
                    }
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                item = item.to_group()
                values.update({
                    "typetext":         "Group",
                    #"content":         item.content,
                    #"values":           self.__item_get_values(item),
                    "status_current":   item.status_current
                    })
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                item = item.to_rule()
                values.update({
                    #"checks":          item.checks
                    "typetext":         "Rule",
                    "fixes":            self.__rule_get_fixes(item),
                    "fixtexts":         self.__rule_get_fixtexts(item),
                    "idents":           [(ident.id, ident.system) for ident in item.idents],
                    "imapct_metric":    item.impact_metric,
                    "multiple":         item.multiple,
                    "profile_notes":    [(note.reftag, note.text) for note in item.profile_notes],
                    "role":             item.role,
                    "severity":         item.severity,
                    "status_current":   item.status_current
                    })
            else: 
                logger.error("Item type not supported %d", item.type)
                return None
        else:
            logger.error("No item '%s' in benchmark", id)
            return None

        return values

    def get_profile_details(self, id):
        """get_profile_details -- get details of Profiles"""
        if id != None or self.selected_profile != None:
            item = self.core.lib["policy_model"].benchmark.item(id or self.selected_profile)
            if item != None:
                values = {
                        "id":               item.id,
                        "titles":           dict([(title.lang, title.text) for title in item.title]),
                        "descriptions":     dict([(desc.lang, desc.text) for desc in item.description]),
                        "abstract":         item.abstract,
                        "extends":          item.extends,
                        "platforms":        [platform.text for platform in item.platforms],
                        "prohibit_changes": item.prohibit_changes,
                        "rationale":        [rationale.text for rationale in item.rationale],
                        "references":       [(ref.text.text, ref.href) for ref in item.references],
                        "statuses":         [(status.date, status.text) for status in item.statuses],
                        "version":          item.version,
                        "version_time":     item.version_time,
                        "version_update":   item.version_update
                        }
            else:
                logger.error("No item '%s' in benchmark", id)
                return None

            return values
        return None
        
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
                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=dialog_buttons)

        file_dialog.set_current_name(file)

        """Init the return value"""
        result = ""
        if file_dialog.run() == gtk.RESPONSE_OK:
                result = file_dialog.get_filename()
        file_dialog.destroy()

        return result


class DHValues(DataHandler):

    def __init__(self, core):
        
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
        column = gtk.TreeViewColumn("Value Name", txtcell, text=1) 
        column.add_attribute(txtcell, 'foreground', 3)
        column.set_resizable(True)
        self.treeView.append_column(column)

        #combo
        cellcombo = gtk.CellRendererCombo()
        cellcombo.set_property("editable", True)
        cellcombo.set_property("text-column", 0)
        cellcombo.connect("edited", self.cellcombo_edited)
        column = gtk.TreeViewColumn("Values", cellcombo, text=2, model=4)
        column.add_attribute(txtcell, 'foreground', 3)
        column.set_resizable(True)
        self.treeView.append_column(column)

    def fill(self, item=None):

        # !!!!
        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

        """If item is None, then this is first call and we need to get the item
        from benchmark. Otherwise it's recursive call and the item is already
        eet up and we recursively add the parent till we hit the benchmark
        """
        if item == None:
            self.model.clear()
            if self.selected_item != None:
                item = self.core.lib["policy_model"].benchmark.get_item(self.selected_item)
                if item == None: 
                    logger.error("XCCDF Item \"%s\" does not exists. Can't fill data", self.selected_item)
                    raise Error, "XCCDF Item \"%s\" does not exists. Can't fill data", self.selected_item
            else: return
        
        # Append a couple of rows.
        item = self.core.lib["policy_model"].benchmark.get_item(self.selected_item)
        values = self.get_item_values(self.selected_item)
        color = ["gray", "black"][self.get_selected(item)]
        for value in values:
            lang = value["lang"]
            model = gtk.ListStore(str, str)
            selected = "Unknown value"
            for key in value["options"].keys():
                if key != '': model.append([key, value["options"][key]])
                if value["options"][key] == value["selected"][1]: selected = key
            self.model.append([value["id"], value["titles"][lang], selected, color, model])
        self.treeView.columns_autosize()
        
        return True

    def cellcombo_edited(self, cell, path, new_text):

        if self.selected_profile == None:
            policy = self.core.lib["policy_model"].policies[0]
        else: policy = self.core.lib["policy_model"].get_policy_by_id(self.selected_profile)

        model = self.treeView.get_model()
        iter = model.get_iter(path)
        id = model.get_value(iter, 0)
        logger.info("Altering value %s", id)
        val = self.core.lib["policy_model"].benchmark.item(id).to_value()
        value = self.parse_value(val)
        logger.info("Matching %s agains %s or %s", new_text, value["choices"], value["match"])
        # Match against pattern as "choices or match"
        choices = ""
        if value["selected"][0] in value["choices"]:
            choices = "|".join(value["choices"][value["selected"][0]])
            pattern = re.compile(value["match"]+"|"+choices)
        else: pattern = re.compile(value["match"])
        if pattern.match(new_text):
            model.set_value(iter, 2, new_text)
            logger.error("Regexp matched: text %s match %s", new_text, "|".join([value["match"], choices]))
            policy.set_tailor_items([{"id":id, "value":new_text}])
        else: logger.error("Failed regexp match: text %s does not match %s", new_text, "|".join([value["match"], choices]))

        

class DHItemsTree(DataHandler):

    def __init__(self, core, progress=None):
        
        DataHandler.__init__(self, core)
        self.__progress = progress
        self.__total = None
        self.__step = None

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

        self.lock = threading.Lock()
        self.treeView = treeView
        # ID, Picture, Text, Font color, selected, parent-selected
        self.model = gtk.TreeStore(str, str, str, str, bool, bool)
        treeView.set_model(self.model)

        """This Cell is used to be first hidden column of tree view
        to identify the item in list"""
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Unique ID", txtcell, text=0)
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
        column.pack_start(pbcell, False)
        column.set_attributes(pbcell, stock_id=1)
        # Text
        txtcell = gtk.CellRendererText()
        column.pack_start(txtcell, True)
        column.set_attributes(txtcell, text=2)
        column.add_attribute(txtcell, 'foreground', 3)
        column.set_resizable(True)
        treeView.append_column(column)

        """Cell with picture representing if the item is selected or not
        """
        render = gtk.CellRendererToggle()
        column = gtk.TreeViewColumn("Selected", render, active=4, sensitive=5, activatable=5)
        render.connect('toggled', self.__cb_toggled, self.model)
        column.set_resizable(True)
        treeView.append_column(column)

    def __set_sensitive(self, policy, child, path, model):

        benchmark = policy.model.benchmark
        iter = model[child.path].iterchildren()
        while iter != None:
            try:
                child = iter.next()
                model[child.path][5] = model[path][4]
                model[child.path][3] = ["gray", None][model[path][4]]

                # Alter selector
                if benchmark.item(model[child.path][0]).type == openscap.OSCAP.XCCDF_RULE:
                    select = policy.get_select_by_id(model[child.path][0])
                    if select == None:
                        newselect = openscap.xccdf.select()
                        newselect.item = model[child.path][0]
                        newselect.selected = (model[child.path][4] and model[path][4])
                        policy.select = newselect
                    else:
                        select.selected = (model[child.path][4] and model[path][4])

                self.__set_sensitive(policy, child, path, model)
            except StopIteration:
                break


    def __cb_toggled(self, cell, path, model):
        #for cell in cells:
        model[path][4] = not model[path][4]
        model[path][3] = ["gray", None][model[path][4]]

        policy = self.core.lib["policy_model"].get_policy_by_id(self.selected_profile)
        if policy == None: raise Exception, "Policy %s does not exist" % (self.selected_profile,)

        # Get selector from policy
        select = policy.get_select_by_id(model[path][0])
        if select == None:
            newselect = openscap.xccdf.select()
            newselect.item = model[path][0]
            newselect.selected = model[path][4]
            policy.select = newselect
        else:
            select.selected = model[path][4]

        self.__set_sensitive(policy, model[path], path, model)

    def __recursive_fill(self, item=None, parent=None, pselected=True):

        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

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

        # Check select status of item
        selected = self.get_selected(item)
        color = ["gray", None][selected and pselected]

        if item != None:
            # If item is group, store it ..
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                gtk.gdk.threads_enter()
                item_it = self.model.append(parent, [item.id, gtk.STOCK_DND_MULTIPLE, "Group: "+item.title[0].text, color, selected, pselected])
                self.treeView.queue_draw()
                gtk.gdk.threads_leave()
                # .. call recursive
                for i in item.content:
                    self.__recursive_fill(i, item_it, selected and pselected)
            # item is rule, store it to model
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                gtk.gdk.threads_enter()
                item_it = self.model.append(parent, [item.id, gtk.STOCK_DND, "Rule: "+item.title[0].text, color, selected, pselected])
                self.treeView.queue_draw()
                gtk.gdk.threads_leave()
            else: logger.warning("Unknown type of %s, should be Rule or Group (got %s)", item.type, item.id)

            return # we need to return otherwise it would continue to next block
        else: 
            raise Exception, "Can't get data to fill. Expected XCCDF Item (got %s)" % (item,)

    def __item_count(self, item):

        number = 0
        if item.type == openscap.OSCAP.XCCDF_GROUP or item.to_item().type == openscap.OSCAP.XCCDF_BENCHMARK:
            for child in item.content:
                number += 1
                if child.type == openscap.OSCAP.XCCDF_GROUP:
                    number += self.__item_count(child)
        return number

    @threadSave
    def fill(self, item=None, parent=None):

        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

        """we don't know item so it's first call and we need to clear
        the model, get the item from benchmark and continue recursively
        through content to fill the tree"""

        # Get number of all items
        if self.__progress:
            self.__progress.set_fraction(0.0)
            self.__progress.show()
            self.__total = self.__item_count(self.core.lib["policy_model"].benchmark)
        self.__step = (100.0/(self.__total or 1.0))/100.0

        self.lock.acquire()
        try:
            gtk.gdk.threads_enter()
            self.model.clear()
            self.treeView.set_sensitive(False)
            gtk.gdk.threads_leave()

            child_win = self.treeView.get_window()
            cursor = child_win.get_cursor()
            child_win.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

            for item in self.core.lib["policy_model"].benchmark.content:
                if self.__progress != None:
                    gtk.gdk.threads_enter()
                    self.__progress.set_fraction(self.__progress.get_fraction()+self.__step)
                    self.__progress.set_text("Adding items %s/%s" % (int(self.__progress.get_fraction()/self.__step), self.__total))
                    gtk.gdk.threads_leave()
                self.__recursive_fill(item)

            gtk.gdk.threads_enter()
            self.treeView.set_sensitive(True)
            gtk.gdk.threads_leave()
            child_win.set_cursor(cursor)
        finally:
            if self.__progress != None:
                gtk.gdk.threads_enter()
                self.__progress.set_fraction(1.0)
                self.__progress.hide()
                gtk.gdk.threads_leave()
            self.lock.release()

        return True


class DHProfiles(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

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

    def fill(self, item=None, parent=None):

        self.model.clear()
        logger.debug("Adding profile (Default document)")
        self.model.append([None, "(Default document)"])

        for item in self.core.lib["policy_model"].benchmark.profiles:
            logger.debug("Adding profile %s", item.id)
            self.model.append([item.id, "Profile: "+item.title[0].text])

        return True


class DHScan(DataHandler):

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

    def __init__(self, core, progress=None):
        
        DataHandler.__init__(self, core)
        self.__progress=progress
        self.__prepaired = False
        self.__cancel = False
        self.__last = 0

    def render(self, treeView):
        """ define treeView"""
         
        self.treeView = treeView

        #model: id rule, result, fix, description, color text desc, color background, color text res
        self.model = gtk.ListStore(str, str, str, str, str, str, str, str)
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

    def fill(self, item):

        #initialization
        colorText_title = DHScan.FG_BLACK
        colorText_res = DHScan.FG_BLACK
        color_backG = DHScan.BG_ERR
        colorText_ID = DHScan.FG_BLACK
        text = ""
        
        # choose color for cell, and text of result
        if  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_PASS:
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


        iter = self.model.append()
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
        return True

    def __callback_start(self, msg, plugin):
        result = msg.user2num
        if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED: 
            return self.__cancel

        step = (100.0/(self.__rules_count or 1.0))/100.0

        if self.__progress != None:
            gtk.gdk.threads_enter()
            self.__progress.set_fraction(self.__progress.get_fraction()+step)
            self.__progress.set_text("Scanning rule %s ... (%s/%s)" % (msg.user1str, int(self.__progress.get_fraction()/step), self.__rules_count))
            self.__progress.set_tooltip_text("Scanning rule %s" % (msg.user3str,))
            gtk.gdk.threads_leave()

        self.__last = int(self.__progress.get_fraction()/step)
        return self.__cancel

    def __callback_end(self, msg, plugin):
        result = msg.user2num
        if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED: 
            return self.__cancel

        gtk.gdk.threads_enter()
        self.fill([msg.user1str, msg.user2num, False, msg.user3str, msg.string])
        self.treeView.queue_draw()
        gtk.gdk.threads_leave()

        return self.__cancel

    def __prepaire(self):

        if self.__progress != None:
            gtk.gdk.threads_enter()
            self.__progress.set_fraction(0.0)
            self.__progress.set_text("Prepairing ...")
            gtk.gdk.threads_leave()

        if self.__prepaired == False:
            self.core.lib["policy_model"].register_start_callback(self.__callback_start, self)
            self.core.lib["policy_model"].register_output_callback(self.__callback_end, self)
        else: 
            self.model.clear()
            self.__cancel = False
            self.__last = 0

        self.selected_profile = self.core.selected_profile
        if self.selected_profile == None:
            self.policy = self.core.lib["policy_model"].policies[0]
        else: self.policy = self.core.lib["policy_model"].get_policy_by_id(self.selected_profile)

        self.__rules_count = 0
        for item in self.policy.selected_rules:
            if item.selected: self.__rules_count += 1
        # TODO: library bug
        #self.__rules_count = len(self.policy.selected_rules)
        self.__prepaired = True
        
    def cancel(self):
        self.__cancel = True

    def export(self):
        file_name = self.file_browse("Save results", file="results.xml")
        if file_name != "":
            files = self.policy.export(self.__result, self.core.lib, "LockDown Test Result", file_name, file_name)
            md = gtk.MessageDialog(self.core.main_window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, 
                    gtk.BUTTONS_OK, "Results were exported successfuly")
            md.run()
            md.destroy()
            for file in files:
                logger.debug("Exported: %s", file)

    @threadSave
    def scan(self):
        self.__prepaire()
        logger.debug("Scanning %s ..", self.policy.id)
        self.__result = self.policy.evaluate()
        if self.__progress: 
            self.__progress.set_fraction(1.0)
            self.__progress.set_text("Finished %s of %s rules" % (self.__last, self.__rules_count))
            self.__progress.set_has_tooltip(False)
        logger.debug("Finished scanning")
