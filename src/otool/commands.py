#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gtk, logging, sys
logger = logging.getLogger("OSCAPEditor")

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")
sys.path.append("/tmp/scap/usr/local/lib/python2.6/site-packages")

try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    logger.error("OpenScap library initialization failed")
    openscap=None



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

    def get_selected(self, item):
        """DataHandler.get_selected -- get selction of rule/group
        returns boolean value"""

        if self.selected_profile == None:
            return item.selected

        else:
            policy = self.lib["policy_model"].get_policy_by_id(self.selected_profile)
            if policy == None: raise Exception, "Policy %s does not exist" % (self.selected_profile,)
            # Get selector from policy
            for select in policy.selected_rules:
                if select.item == item.id:
                    if select.selected: 
                        return True
                    return False
            return item.selected

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
        return None

    def __rule_get_fixtexts(self, item):
        return None


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


class DHItemsTree(DataHandler):

    def __init__(self, core):
        
        DataHandler.__init__(self, core)

    def render(self, treeView):
        """Make a model ListStore of Dependencies object"""

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

    def fill(self, item=None, parent=None):

        # !!!!
        self.selected_profile   = self.core.selected_profile
        self.selected_item      = self.core.selected_item

        """This is recusive call (item is not None) so let's get type of 
        item and add it to model. If the item is Group continue more deep with
        recursion to get all items to the tree"""
        if item != None:
            selected = [None, gtk.STOCK_APPLY][self.get_selected(item)]
            # If item is group, store it ..
            if item.type == openscap.OSCAP.XCCDF_GROUP:
                item_it = self.model.append(parent, [item.id, gtk.STOCK_DND_MULTIPLE, "Group: "+item.title[0].text, selected])
                # .. call recursive
                for i in item.content:
                    self.fill(i, item_it)
            # item is rule, store it to model
            elif item.type == openscap.OSCAP.XCCDF_RULE:
                item_it = self.model.append(parent, [item.id, gtk.STOCK_DND, "Rule: "+item.title[0].text, selected])
            else: logger.warning("Unknown type of %s, should be Rule or Group (got %s)", item.type, item.id)

            return # we need to return otherwise it would continue to next block

        """We don't know item so it's first call and we need to clear
        the model, get the item from benchmark and continue recursively
        through content to fill the tree"""
        self.model.clear()
        for item in self.benchmark.content:
            self.fill(item)

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
