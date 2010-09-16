#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gtk, logging, sys, re
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

from core import thread as threading

class DataHandler:
    """DataHandler Class implements handling data from Openscap library,
    calling oscap functions and parsing oscap output to models specified by
    tool's objects"""

    def __init__(self, core):
        """DataHandler.__init__ -- initialization of data handler.
        Initialization is done by Core object.
        library => openscap library"""

        self.core = core
        self.lib = core.lib
        self.selected_profile = None
        self.selected_item = None

        self.benchmark = self.lib["policy_model"].benchmark
        if self.benchmark == None or self.benchmark.instance == None:
            logger.error("XCCDF benchmark does not exists. Can't fill data")
            raise Error, "XCCDF benchmark does not exists. Can't fill data"

    def parse_value(self, value):

        # get value properties
        item = {}
        item["id"] = value.id
        item["lang"] = self.lib["policy_model"].benchmark.lang
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
            profile = self.lib["policy_model"].policies[0].profile
        else: profile = self.lib["policy_model"].get_policy_by_id(self.selected_profile).profile
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
        return [self.lib["policy_model"].benchmark.lang]

    def get_selected(self, item):
        """DataHandler.get_selected -- get selction of rule/group
        returns boolean value"""

        if self.selected_profile == None:
            return item.selected

        else:
            policy = self.lib["policy_model"].get_policy_by_id(self.selected_profile)
            if policy == None: raise Exception, "Policy %s does not exist" % (self.selected_profile,)
            # Get selector from policy
            for select in policy.selects:
                if select.item == item.id:
                    if select.selected: 
                        return True
                    return False
            return item.selected

    def get_item_values(self, id):

        if self.selected_profile == None:
            policy = self.lib["policy_model"].policies[0]
        else: policy = self.lib["policy_model"].get_policy_by_id(self.selected_profile)

        values = []
        item = self.benchmark.item(id)
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

        item = self.benchmark.item(id or self.selected_item)
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
            item = self.benchmark.item(id or self.selected_profile)
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


class DHDependencies(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

        self.model = gtk.ListStore(str, str, str, str)
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
        treeView.append_column(column)

        """Cell with picture representing if the item is selected or not
        """
        render = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Selected", render, stock_id=3)
        treeView.append_column(column)

    def fill(self, item=None):

        # !!!!
        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

        """If item is None, then this is first call and we need to get the item
        from benchmark. Otherwise it's recursive call and the item is already
        set up and we recursively add the parent till we hit the benchmark
        """
        if item == None:
            self.model.clear()
            if self.selected_item != None:
                item = self.benchmark.get_item(self.selected_item)
                if item == None: 
                    logger.error("XCCDF Item \"%s\" does not exists. Can't fill data", self.selected_item)
                    raise Error, "XCCDF Item \"%s\" does not exists. Can't fill data", self.selected_item
            else: return

        # TODO: Add requires / conflicts

        """let's go recursively through parents and add them. This should be more 
        complex and check if all parents meet their requirements
        """
        if item.parent.type != openscap.OSCAP.XCCDF_BENCHMARK:
            selected = [gtk.STOCK_CANCEL, gtk.STOCK_APPLY][self.get_selected(item.parent)]
            logger.info("Added line %s | %s | %s", item.parent.id, "Group: "+item.parent.title[0].text, selected)
            item_it = self.model.prepend([item.parent.id, gtk.STOCK_DND_MULTIPLE, "Group: "+item.parent.title[0].text, selected])
            self.fill(item.parent)

        return True

    def get_item_dependencies(self):
        
        item = self.benchmark.item(id)
        if item != None:
            pass
        else:
            logger.error("No item '%s' in benchmark", id)
            return None

class DHValues(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""
        self.treeView = treeView
        self.model = gtk.ListStore(str, str, str, gtk.TreeModel)
        self.treeView.set_model(self.model)

        """This Cell is used to be first hidden column of tree view
        to identify the item in list"""
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Unique ID", txtcell, text=0)
        column.set_visible(False)
        self.treeView.append_column(column)

        # Text
        txtcell = gtk.CellRendererText()
        txtcell.set_property("editable", False)
        column.pack_start(txtcell, False)
        column.set_attributes(txtcell, text=1)
        column = gtk.TreeViewColumn("Value Name", txtcell, text=1) 
        self.treeView.append_column(column)

        #combo
        cellcombo = gtk.CellRendererCombo()
        cellcombo.set_property("editable", True)
        cellcombo.set_property("text-column", 0)
        cellcombo.connect("edited", self.cellcombo_edited)
        column = gtk.TreeViewColumn("Values", cellcombo, text=2, model=3)
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
                item = self.benchmark.get_item(self.selected_item)
                if item == None: 
                    logger.error("XCCDF Item \"%s\" does not exists. Can't fill data", self.selected_item)
                    raise Error, "XCCDF Item \"%s\" does not exists. Can't fill data", self.selected_item
            else: return
        
        # Append a couple of rows.
        item = self.benchmark.get_item(self.selected_item)
        values = self.get_item_values(self.selected_item)
        for value in values:
            lang = value["lang"]
            model = gtk.ListStore(str, str)
            selected = "Unknown value"
            for key in value["options"].keys():
                if key != '': model.append([key, value["options"][key]])
                if value["options"][key] == value["selected"][1]: selected = key
            self.model.append([value["id"], value["titles"][lang], selected, model])
        self.treeView.columns_autosize()
        
        return True

    def cellcombo_edited(self, cell, path, new_text):

        if self.selected_profile == None:
            policy = self.lib["policy_model"].policies[0]
        else: policy = self.lib["policy_model"].get_policy_by_id(self.selected_profile)

        model = self.treeView.get_model()
        iter = model.get_iter(path)
        id = model.get_value(iter, 0)
        logger.info("Altering value %s", id)
        val = self.benchmark.item(id).to_value()
        value = self.parse_value(val)
        logger.info("Matching %s agains %s or %s", new_text, value["choices"], value["match"])
        # Match against pattern as "choices or match"
        choices = ""
        if value["selected"][0] in value["choices"]:
            choices = "|".join(value["choices"][value["selected"][0]])
            print choices
            pattern = re.compile(value["match"]+"|"+choices)
        else: pattern = re.compile(value["match"])
        if pattern.match(new_text):
            model.set_value(iter, 2, new_text)
            logger.error("Regexp matched: text %s match %s", new_text, "|".join([value["match"], choices]))
            policy.set_tailor_items([{"id":id, "value":new_text}])
        else: logger.error("Failed regexp match: text %s does not match %s", new_text, "|".join([value["match"], choices]))

        

class DHItemsTree(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

        self.treeView = treeView
        self.model = gtk.TreeStore(str, str, str, str)
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
        treeView.append_column(column)

        """Cell with picture representing if the item is selected or not
        """
        render = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Selected", render, stock_id=3)
        treeView.append_column(column)

    def __recursive_fill(self, item=None, parent=None):

        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

        """This is recusive call (item is not None) so let's get type of 
        item and add it to model. If the item is Group continue more deep with
        recursion to get all items to the tree"""
        if item != None:
            if item.type == openscap.OSCAP.XCCDF_RULE:
                selected = [None, gtk.STOCK_APPLY][self.get_selected(item)]
            else: selected = None
            # If item is group, store it ..
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                gtk.gdk.threads_enter()
                item_it = self.model.append(parent, [item.id, gtk.STOCK_DND_MULTIPLE, "Group: "+item.title[0].text, selected])
                self.treeView.queue_draw()
                gtk.gdk.threads_leave()
                # .. call recursive
                for i in item.content:
                    self.__recursive_fill(i, item_it)
            # item is rule, store it to model
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                gtk.gdk.threads_enter()
                item_it = self.model.append(parent, [item.id, gtk.STOCK_DND, "Rule: "+item.title[0].text, selected])
                self.treeView.queue_draw()
                gtk.gdk.threads_leave()
            else: logger.warning("Unknown type of %s, should be Rule or Group (got %s)", item.type, item.id)

            return # we need to return otherwise it would continue to next block
        else: return # TODO

    @threading
    def fill(self, item=None, parent=None):

        # !!!!
        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

        """we don't know item so it's first call and we need to clear
        the model, get the item from benchmark and continue recursively
        through content to fill the tree"""
        self.model.clear()
        self.treeView.set_sensitive(False)
        child_win = self.treeView.get_window()
        cursor = child_win.get_cursor()
        child_win.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        for item in self.benchmark.content:
            self.__recursive_fill(item)
        self.treeView.set_sensitive(True)
        child_win.set_cursor(cursor)

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
        treeView.append_column(column)

    def fill(self, item=None, parent=None):

        self.model.clear()
        logger.debug("Adding profile (Default document)")
        self.model.append([None, "(Default document)"])

        for item in self.benchmark.profiles:
            logger.debug("Adding profile %s", item.id)
            self.model.append([item.id, "Profile: "+item.title[0].text])

        return True


class DHScan(DataHandler):

    COLUMN_ID = 0 #id of rule
    COLUMN_RESULT = 1 #Result of scan
    COLUMN_FIX = 2 #fix
    COLUMN_DESC = 3 #Description of rule
    COLUMN_COLOR_TEXT = 4 #Color of cell
    COLUMN_COLOR_BACKG = 5 #Color of cell
    
    list_model = [
                        # id rule,  result,         fix,        description 
            ('1', 'XCCDF_RESULT_ERROR',             True,           'adasd' ),
            ('2', 'XCCDF_RESULT_ERROR',             True,           'asdasd' ),
            ('3', 'XCCDF_RESULT_NOT_CHECKED',       False,          'rasdasd' ),
            ('4', 'XCCDF_RESULT_NOT_CHECKED',       False,          'rasdasd' )

    ]
    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """ define treeView"""
         
        #model: id rule, result, fix, description, color text, color background
        self.model = gtk.ListStore(str, str, str, str, str, gtk.gdk.Color)
        treeView.set_model(self.model)
        #treeView.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        #treeView.set_property("tree-line-width", 10)

        # ID Rule
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Role ID", txtcell, text=DHScan.COLUMN_ID)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT)
        column.add_attribute(txtcell, 'background-gdk', DHScan.COLUMN_COLOR_BACKG)
        treeView.append_column(column)

        #Result
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Result", txtcell, text=DHScan.COLUMN_RESULT)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT)
        column.add_attribute(txtcell, 'background-gdk', DHScan.COLUMN_COLOR_BACKG)
        column.set_spacing(15)
        treeView.append_column(column)

        # Fix
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Fix", txtcell, text=DHScan.COLUMN_FIX)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT)
        column.add_attribute(txtcell, 'background-gdk', DHScan.COLUMN_COLOR_BACKG)
        treeView.append_column(column)

        # Description
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Description", txtcell, text=DHScan.COLUMN_DESC)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT)
        column.add_attribute(txtcell, 'background-gdk', DHScan.COLUMN_COLOR_BACKG)
        treeView.append_column(column)

    def fill(self, item=None):

        backG_red = gtk.gdk.Color(red=65500, green=15303, blue=10453, pixel=0)
        backG_green = gtk.gdk.Color(red=20200, green=65535, blue=41500, pixel=0)
        text_gray = "gray"
        text_black = "black"

        #TODO
        for i in DHScan.list_model:
            # choose color for widget
            iter = self.model.append()
            if  i[DHScan.COLUMN_RESULT] == "XCCDF_RESULT_ERROR":
                color_text = text_black
                color_backG = backG_red
            else:
                color_text = text_gray
                color_backG = backG_green
            
            self.model.set(iter,
                    DHScan.COLUMN_ID,   i[DHScan.COLUMN_ID],
                    DHScan.COLUMN_RESULT,    i[DHScan.COLUMN_RESULT],
                    DHScan.COLUMN_FIX,    i[DHScan.COLUMN_FIX], 
                    DHScan.COLUMN_DESC,  i[DHScan.COLUMN_DESC],
                    DHScan.COLUMN_COLOR_TEXT,  color_text,
                    DHScan.COLUMN_COLOR_BACKG,  color_backG
                    )
        return True
