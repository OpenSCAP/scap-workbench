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

import pygtk
import gtk
import gobject
import pango

import abstract
import logging
import core
from events import EventObject

import commands
import filter
import render

try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None
    
from htmltextview import HtmlTextView
from threads import thread as threadSave


logger = logging.getLogger("OSCAPEditor")

class ItemList(abstract.List):

    def __init__(self, widget, core, progress=None, filter=None):
        self.core = core
        self.filter = filter
        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, True)
        abstract.List.__init__(self, "gui:edit:item_list", core, widget)
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_receiver("gui:btn:menu:edit", "update", self.__update)
        #self.add_receiver("gui:btn:edit", "update", self.__update)
        self.add_receiver("gui:btn:edit:filter", "search", self.__search)
        self.add_receiver("gui:btn:edit:filter", "filter_add", self.__filter_add)
        self.add_receiver("gui:btn:edit:filter", "filter_del", self.__filter_del)
        self.add_receiver("gui:edit:DHItemsTree", "filled", self.__filter_refresh)

        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.add_sender(self.id, "item_changed")

        self.init_filters(self.filter, self.data_model.model, self.data_model.new_model())

    def __update(self):
        self.get_TreeView().set_model(self.data_model.model)
        self.data_model.fill()
        # Select the last one selected if there is one
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item_edit, self.get_TreeView()))
        self.core.force_reload_items = False

    def __search(self):
        self.search(self.filter.get_search_text(),1)
        
    def __filter_add(self):
        self.data_model.map_filter = self.filter_add(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_del(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_refresh(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))


    @threadSave
    def __cb_item_changed(self, widget, treeView):
        """Make all changes in application in separate threads: workaround for annoying
        blinking when redrawing treeView
        """
        gtk.gdk.threads_enter()
        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: 
                self.core.selected_item_edit = model.get_value(iter, 0)
            else:
                self.core.selected_item_edit = None
        self.emit("update")
        treeView.columns_autosize()
        gtk.gdk.threads_leave()

class MenuButtonEdit(abstract.MenuButton, commands.DHEditItems):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DataHandler(self.core)
        self.item = None

        #draw body
        self.body = self.builder.get_object("edit:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        self.rules_list = ItemList(self.builder.get_object("edit:tw_items"), self.core, self.progress, self.filter)
        self.filter.expander.cb_changed()

        # set signals
        self.add_sender(self.id, "update")
        
        """Get widget for details
        """
        #main
        self.nBook = self.builder.get_object("edit:notebook")
        self.set_sensitive(False)
        self.btn_revert = self.builder.get_object("edit:btn_revert")
        self.btn_save = self.builder.get_object("edit:btn_save")
        self.btn_item_remove = self.builder.get_object("edit:item:btn_remove")
        self.btn_item_add = self.builder.get_object("edit:item:btn_add")
        
        self.btn_revert.connect("clicked", self.__cb_revert)
        self.btn_save.connect("clicked", self.__cb_save)
        self.btn_item_remove.connect("clicked", self.__cb_item_remove)
        self.btn_item_add.connect("clicked", self.__cb_item_add)
        
        #general
        self.item_id = self.builder.get_object("edit:general:lbl_id")
        
        self.entry_version = self.builder.get_object("edit:general:entry_version")
        self.entry_version.connect("focus-out-event",self.cb_entry_version)
        
        self.entry_version_time = self.builder.get_object("edit:general:entry_version_time")
        self.entry_version_time.connect("focus-out-event",self.cb_entry_version_time)
        
        self.chbox_hidden = self.builder.get_object("edit:general:chbox_hidden")
        self.chbox_hidden.connect("toggled",self.cb_chbox_hidden)
        
        self.chbox_prohibit = self.builder.get_object("edit:general:chbox_prohibit")
        self.chbox_prohibit.connect("toggled",self.cb_chbox_prohibit)
        
        self.chbox_abstract = self.builder.get_object("edit:general:chbox_abstract")
        self.chbox_abstract.connect("toggled",self.cb_chbox_abstract)
        
        self.entry_cluster_id = self.builder.get_object("edit:general:entry_cluster_id")
        self.entry_cluster_id.connect("focus-out-event",self.cb_entry_cluster_id)
        
        self.edit_title = EditTitle(self.core, self.builder)
        self.edit_description = EditDescription(self.core, self.builder)
        self.edit_warning = EditWarning(self.core, self.builder)
        self.edit_status = EditStatus(self.core, self.builder)
        self.edit_question = EditQuestion(self.core, self.builder)
        self.edit_rationale = EditRationale(self.core, self.builder)

        self.lbl_extends = self.builder.get_object("edit:dependencies:lbl_extends")
        
        #Dependencies
        self.edit_platform = EditPlatform(self.core, self.builder)
        
        #operations
        self.edit_fixtext = EditFixtext(self.core, self.builder)
        self.edit_fix = EditFix(self.core, self.builder)
        #self.chbox_selected = self.builder.get_object("edit:operations:chbox_selected")

        combo_model_sev = gtk.ListStore(int, str, str)
        combo_model_sev.append([openscap.OSCAP.XCCDF_UNKNOWN, "UNKNOWN", "Unknown."])
        combo_model_sev.append([openscap.OSCAP.XCCDF_INFO, "INFO", "Info."])
        combo_model_sev.append([openscap.OSCAP.XCCDF_LOW, "LOW", "Low."])
        combo_model_sev.append([openscap.OSCAP.XCCDF_MEDIUM, "MEDIUM", "Medium."])
        combo_model_sev.append([openscap.OSCAP.XCCDF_HIGH, "HIGH", "High."])
        
        self.cBox_severity = self.builder.get_object("edit:operations:combo_severity")
        cell = gtk.CellRendererText()
        self.cBox_severity.pack_start(cell, True)
        self.cBox_severity.add_attribute(cell, 'text', 1)  
        self.cBox_severity.set_model(combo_model_sev)
        self.cBox_severity.connect( "changed", self.cb_cBox_severity)
       
        
        self.entry_impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.entry_impact_metric.connect("focus-out-event",self.cb_entry_impact_metric)
        
        self.lv_fixtext = self.builder.get_object("edit:operations:lv_fixtext")
        self.lv_fix = self.builder.get_object("edit:operations:lv_fix")
        self.lv_check = self.builder.get_object("edit:operations:lv_check")
        
        #values
        self.edit_values = EditValues(self.core, self.builder)
        
        #others
        self.chbox_multipl = self.builder.get_object("edit:other:chbox_multipl")
        self.chbox_multipl.connect("toggled",self.cb_chbox_multipl)

        combo_model_role = gtk.ListStore(int, str, str)
        combo_model_sev.append([openscap.OSCAP.XCCDF_ROLE_FULL, "FULL", "Check the rule and let the result contriburte to the score and appear in reports.."])
        combo_model_sev.append([openscap.OSCAP.XCCDF_ROLE_UNSCORED, "UNSCORED", "Check the rule and include the result in reports, but do not include it into score computations"])
        combo_model_sev.append([openscap.OSCAP.XCCDF_ROLE_UNCHECKED, "UNCHECKED", "Don't check the rule, result will be XCCDF_RESULT_UNKNOWN."])
        
        self.cBox_role = self.builder.get_object("edit:other:combo_role")
        cell = gtk.CellRendererText()
        self.cBox_role.pack_start(cell, True)
        self.cBox_role.add_attribute(cell, 'text', 1)  
        self.cBox_role.set_model(combo_model_sev)
        self.cBox_role.connect( "changed", self.cb_cBox_role)

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:item_list", "changed", self.__update)
        
            
    def __cb_revert(self, widget):
        pass

    def __cb_save(self, widget):
        pass

    def __cb_item_remove(self, widget):
        pass

    def __cb_item_add(self, widget):
        pass
    
    def set_sensitive(self, sensitive):
        self.nBook.set_sensitive(sensitive)
        
    def __update(self):
        
        details = self.data_model.get_item_objects(self.core.selected_item_edit)
        
        if details != None:
            self.set_sensitive(True)
            self.item = details["item"]
            self.item_id.set_text(details["id"])
            self.chbox_hidden.set_active(details["hidden"])
            self.chbox_prohibit.set_active(details["prohibit_changes"])
            self.chbox_abstract.set_active(details["abstract"])

            self.edit_title.fill(details["item"], details["titles"])
            self.edit_description.fill(details["item"], details["descriptions"])
            self.edit_warning.fill(details["item"], details["warnings"])
            self.edit_status.fill(details["item"], details["statuses"])
            self.edit_question.fill(details["item"], details["questions"])
            self.edit_rationale.fill(details["item"], details["rationale"])
            self.edit_platform.fill(details["item"], details["platforms"])


            if details["version"] != None:
                self.entry_version.set_text(details["version"])
            else:
                self.entry_version.set_text("")

            if details["version_time"] != None:
                self.entry_version_time.set_text(str(details["version_time"]))
            else:
                self.entry_version_time.set_text("")

            if details["cluster_id"] != None:
                self.entry_cluster_id.set_text(details["cluster_id"])
            else:
                self.entry_cluster_id.set_text("")

            if details["extends"] != None:
                self.lbl_extends.set_text(details["extends"])
            else:
                self.lbl_extends.set_text("None")

            
            # dat only for rule
            if details["typetext"] == "Rule":

                self.cBox_severity.set_sensitive(True)
                if details["severity"] != None:
                    model_sev = self.cBox_severity.get_model()
                    iter_sev = model_sev.get_iter_first()
                    while iter_sev:
                        if model_sev.get_value(iter_sev, 0) == details["severity"]:
                            self.cBox_severity.handler_block_by_func(self.cb_cBox_severity)
                            self.cBox_severity.set_active_iter(iter_sev)
                            self.cBox_severity.handler_unblock_by_func(self.cb_cBox_severity)
                            break
                        iter_sev = model_sev.iter_next(iter_sev)

                self.entry_impact_metric.set_sensitive(True)
                if details["imapct_metric"] != None:
                    self.entry_impact_metric.set_text(details["imapct_metric"])
                else:
                    self.entry_impact_metric.set_text("")

                self.cBox_role.set_sensitive(True)
                if details["role"]:
                    model_role = self.cBox_role.get_model()
                    iter_role = model_role.get_iter_first()
                    while iter_role:
                        if model_role.get_value(iter_role, 0) == details["role"]:
                            self.cBox_role.handler_block_by_func(self.cb_cBox_role)
                            self.cBox_role.set_active_iter(iter_role)
                            self.cBox_role.handler_unblock_by_func(self.cb_cBox_role)
                            break
                        iter_role = model_role.iter_next(iter_role)


                self.chbox_multipl.set_sensitive(True)
                self.chbox_multipl.set_active(details["multiple"])
                
                self.edit_fixtext.set_sensitive(True)
                self.edit_fixtext.fill(details["item"])
                
                self.edit_fix.set_sensitive(True)
                self.edit_fix.fill(details["item"])
                
                # clean hide data only for group and set insensitive
                self.edit_values.set_sensitive(False)
                self.edit_values.fill(None, None)
                
            #data only for Group
            else:
                self.edit_values.set_sensitive(True)
                self.edit_values.fill(details["item"], details["values"])
                
                
                # clean data only for rule and set insensitive
                self.cBox_severity.set_sensitive(False)
                self.cBox_severity.handler_block_by_func(self.cb_cBox_severity)
                self.cBox_severity.set_active(-1)
                self.cBox_severity.handler_unblock_by_func(self.cb_cBox_severity)
                
                self.cBox_role.set_sensitive(False)
                self.cBox_role.handler_block_by_func(self.cb_cBox_role)
                self.cBox_role.set_active(-1)
                self.cBox_role.handler_unblock_by_func(self.cb_cBox_role)
                
                self.chbox_multipl.set_sensitive(False)
                self.chbox_multipl.set_active(False)
                
                self.entry_impact_metric.set_sensitive(False)
                self.entry_impact_metric.set_text("")
                
                self.edit_fixtext.set_sensitive(False)
                self.edit_fixtext.fill(None)
                
                self.edit_fix.set_sensitive(False)
                self.edit_fix.fill(None)
                
        else:
            self.set_sensitive(False)
            return


class Edit_abs:

    combo_model_level = gtk.ListStore(int, str, str)
    combo_model_level.append([openscap.OSCAP.XCCDF_UNKNOWN, "UNKNOWN", "Unknown."])
    combo_model_level.append([openscap.OSCAP.XCCDF_INFO, "INFO", "Info."])
    combo_model_level.append([openscap.OSCAP.XCCDF_LOW, "LOW", "Low."])
    combo_model_level.append([openscap.OSCAP.XCCDF_MEDIUM, "MEDIUM", "Medium"])
    combo_model_level.append([openscap.OSCAP.XCCDF_HIGH, "HIGH", "High."])
    
    combo_model_strategy = gtk.ListStore(int, str, str)
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_UNKNOWN, "UNKNOWN", "Strategy not defined."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_CONFIGURE, "CONFIGURE", "Adjust target config or settings."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_DISABLE, "DISABLE", "Turn off or deinstall something."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_ENABLE, "ENABLE", "Turn on or install something."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_PATCH, "PATCH", "Apply a patch, hotfix, or update."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_POLICY, "POLICY", "Remediation by changing policies/procedures."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_RESTRICT, "RESTRICT", "Adjust permissions or ACLs."])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_UPDATE, "UPDATE", "Install upgrade or update the system"])
    combo_model_strategy.append([openscap.OSCAP.XCCDF_STRATEGY_COMBINATION, "COMBINATION", "Combo of two or more of the above."])
    
        
    def __init__(self, core, lv, values):
        self.core = core
        self.values = values
        self.item = None
        if lv:
            self.lv = lv
            self.model = lv.get_model()
            self.selection = lv.get_selection()
            self.selection.set_mode(gtk.SELECTION_SINGLE)

    def cb_edit_row(self, widget):
        (model,iter) = self.selection.get_selected()
        if iter:
            window = EditDialogWindow(self.item, self.core, self.values, new=False)
        else:
            self.dialogEditNotSelected()

    def cb_add_row(self, widget):
        window = EditDialogWindow(self.item, self.core, self.values, new=True)

    def cb_del_row(self, widget):
        iter = self.dialogEditDel()
        if iter != None:
            self.values["cb"](self.item, self.model, iter, None, None, True)

    def dialogEditDel(self):
        
        (model,iter) = self.selection.get_selected()
        if iter:
            md = gtk.MessageDialog(self.core.main_window, 
                gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_YES_NO, "Do you want delete selected row?")
            md.set_title("Delete row")
            result = md.run()
            md.destroy()
            if result == gtk.RESPONSE_NO: 
                return None
            else: 
                return iter
        else:
            self.dialogInfo("Choose row which you want delete.")

    def dialogEditNotSelected(self):
        self.dialogInfo("Choose row which you want edit.")
        
        
    def dialogInfo(self, text):
        md = gtk.MessageDialog(self.core.main_window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK, text)
        md.set_title("Info")
        md.run()
        md.destroy()

    def addColumn(self, name, column):
        txtcell = abstract.CellRendererTextWrap()
        column = gtk.TreeViewColumn(name, txtcell, text=column)
        column.set_resizable(True)
        self.lv.append_column(column)


    def set_active_comboBox(self, comboBox, data, column):
        """
        Function set active row which is samae as data in column.
        """
        set_c = False
        model =  comboBox.get_model()
        iter = model.get_iter_first()
        while iter:
            if data == model.get_value(iter, column):
                comboBox.set_active_iter(iter) 
                set_c = True
                break
            iter = model.iter_next(iter)
            
        if not set_c:
            comboBox.set_active(-1)
        
    def set_model_to_comboBox(self, combo, model, view_column):
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', view_column)  
        combo.set_model(model)
            
class EditTitle(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:general:lv_title")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit title",
                        "view":         lv,
                        "cb":           self.DHEditTitle,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Title",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_title_add")
        btn_edit = builder.get_object("edit:general:btn_title_edit")
        btn_del = builder.get_object("edit:general:btn_title_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Title",self.COLUMN_TEXT)
        
    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data.lang, (" ".join(data.text.split())), data])

class EditDescription(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_DES = 1
    COLUMN_OBJECTS = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:general:lv_description")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit description",
                        "view":         lv,
                        "cb":           self.DHEditDescription,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Description",
                                        "column":   self.COLUMN_DES,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_description_add")
        btn_edit = builder.get_object("edit:general:btn_description_edit")
        btn_del = builder.get_object("edit:general:btn_description_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Description",self.COLUMN_DES)

    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data.lang, data.text, data])


class EditWarning(commands.DHEditItems,Edit_abs):

    COLUMN_CATEGORY_TEXT= 0
    COLUMN_CATEGORY_ITER = 1
    COLUMN_LAN = 2
    COLUMN_TEXT = 3
    COLUMN_OBJECT = 4

    CB_COLUMN_DATA = 0
    CB_COLUMN_VIEW = 1
    
    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:general:lv_warning")
        model = gtk.ListStore(str, gobject.TYPE_PYOBJECT, str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        

        
        self.combo_model = gtk.ListStore(int, str, str)
        self.combo_model.append([1, "GENERAL", "  General-purpose warning."])
        self.combo_model.append([2, "FUNCTIONALITY", "Warning about possible impacts to functionality."])
        self.combo_model.append([3, "PERFORMANCE", "  Warning about changes to target system performance."])
        self.combo_model.append([4, "HARDWARE", "Warning about hardware restrictions or possible impacts to hardware."])
        self.combo_model.append([5, "LEGAL", "Warning about legal implications."])
        self.combo_model.append([6, "REGULATORY", "Warning about regulatory obligations."])
        self.combo_model.append([7, "MANAGEMENT", "Warning about impacts to the mgmt or administration of the target system."])
        self.combo_model.append([8, "AUDIT", "Warning about impacts to audit or logging."])
        self.combo_model.append([9, "DEPENDENCY", "Warning about dependencies between this Rule and other parts of the target system."])
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit title",
                        "view":         lv,
                        "cb":           self.DHEditWarning,
                        "cBox":         {"name":    "Category",
                                        "column":   self.COLUMN_CATEGORY_ITER,
                                        "column_view":   self.COLUMN_CATEGORY_TEXT,
                                        "cBox_view":self.CB_COLUMN_VIEW,
                                        "cBox_data":self.CB_COLUMN_DATA,
                                        "model":    self.combo_model,
                                        "empty":    False, 
                                        "unique":   False},
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    True, 
                                        "unique":   False},
                        "textView":     {"name":    "Warning",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_warning_add")
        btn_edit = builder.get_object("edit:general:btn_warning_edit")
        btn_del = builder.get_object("edit:general:btn_warning_del")
        
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Category",self.COLUMN_CATEGORY_TEXT)
        self.addColumn("Warning",self.COLUMN_TEXT)
        
    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:

                iter = self.combo_model.get_iter_first()
                while iter:
                    if data.category == self.combo_model.get_value(iter, self.CB_COLUMN_DATA):
                        category = self.combo_model.get_value(iter, self.CB_COLUMN_VIEW )
                        break
                    iter = self.combo_model.iter_next(iter)
                if iter == None: 
                    logger.error("Unexpected category XCCDF_WARNING.")
                    category = "Uknown"

                self.model.append([category, iter,data.text.lang, data.text.text, data])


class EditStatus(commands.DHEditItems,Edit_abs):

    COLUMN_STATUS_TEXT= 0
    COLUMN_STATUS_ITER = 1
    COLUMN_DATE = 2
    COLUMN_OBJECT = 3

    CB_COLUMN_DATA = 0
    CB_COLUMN_VIEW = 1
    
    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:general:lv_status")
        model = gtk.ListStore(str, gobject.TYPE_PYOBJECT, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        
        self.combo_model = gtk.ListStore(int, str, str)
        self.combo_model.append([0, "NOT SPECIFIED", "Status was not specified by benchmark."])
        self.combo_model.append([1, "ACCEPTED", "Accepted."])
        self.combo_model.append([2, "DEPRECATED", "Deprecated."])
        self.combo_model.append([3, "DRAFT ", "Draft item."])
        self.combo_model.append([4, "INCOMPLETE", "The item is not complete. "])
        self.combo_model.append([5, "INTERIM", "Interim."])

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit title",
                        "view":         lv,
                        "cb":           self.DHEditStatus,
                        "cBox":         {"name":    "Status",
                                        "column":   self.COLUMN_STATUS_ITER,
                                        "column_view":   self.COLUMN_STATUS_TEXT,
                                        "cBox_view":self.CB_COLUMN_VIEW,
                                        "cBox_data":self.CB_COLUMN_DATA,
                                        "model":    self.combo_model,
                                        "empty":    False, 
                                        "unique":   False},
                        "textEntry":    {"name":    "Date",
                                        "column":   self.COLUMN_DATE,
                                        "empty":    False, 
                                        "unique":   False},

                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_status_add")
        btn_edit = builder.get_object("edit:general:btn_status_edit")
        btn_del = builder.get_object("edit:general:btn_status_del")
        
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Date",self.COLUMN_DATE)
        self.addColumn("Status",self.COLUMN_STATUS_TEXT)
        
    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                iter = self.combo_model.get_iter_first()
                while iter:
                    if data.status == self.combo_model.get_value(iter, self.CB_COLUMN_DATA):
                        status = self.combo_model.get_value(iter, self.CB_COLUMN_VIEW )
                        break
                    iter = self.combo_model.iter_next(iter)
                if iter == None: 
                    logger.error("Unexpected category XCCDF_WARNING.")
                    status = "Uknown"

                self.model.append([status, iter,data.date, data])


class EditQuestion(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECTS = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:general:lv_question")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit Question",
                        "view":         lv,
                        "cb":           self.DHEditQuestion,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    True, 
                                        "unique":   False},
                        "textView":     {"name":    "Question",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_question_add")
        btn_edit = builder.get_object("edit:general:btn_question_edit")
        btn_del = builder.get_object("edit:general:btn_question_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Question",self.COLUMN_TEXT)

    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data.lang, data.text, data])


class EditRationale(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECTS = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:general:lv_rationale")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit Rationale",
                        "view":         lv,
                        "cb":           self.DHEditRationale,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    True, 
                                        "unique":   False},
                        "textView":     {"name":    "Ratinale",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_rationale_add")
        btn_edit = builder.get_object("edit:general:btn_rationale_edit")
        btn_del = builder.get_object("edit:general:btn_rationale_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Rationale",self.COLUMN_TEXT)

    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data.lang, data.text, data])


class EditPlatform(commands.DHEditItems,Edit_abs):

    COLUMN_TEXT = 0
    COLUMN_OBJECTS = 1

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:dependencies:lv_platform")
        model = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit Platform",
                        "view":         lv,
                        "cb":           self.DHEditPlatform,
                        "textView":     {"name":    "Platform",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:dependencies:btn_platform_add")
        btn_edit = builder.get_object("edit:dependencies:btn_platform_edit")
        btn_del = builder.get_object("edit:dependencies:btn_platform_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("Question",self.COLUMN_TEXT)

    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data, objects])

#======================================= EDIT VALUES ==========================================

class EditValues(commands.DHEditItems, Edit_abs, EventObject):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_SELECT_VAL = 2
    COLUMN_OBJECT = 3
    
    def __init__(self, core, builder):
        
        self.id = "gui:btn:menu:edit:values"
        self.builder = builder
        self.core = core
        
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(self.id, "item_changed")
        
        self.add_receiver("gui:btn:menu:edit:values", "item_changed", self.__update)
        
        self.model = gtk.ListStore(str, str, str, gobject.TYPE_PYOBJECT)
        lv = self.builder.get_object("edit:values:tv_values")
        lv.set_model(self.model)
        
        Edit_abs.__init__(self, core, lv, None)
        self.selection.connect("changed", self.__cb_item_changed, lv)
        
        #edit data of values
        self.edit_values_title = EditValueTitle(self.core, self.builder)
        self.edit_values_description = EditValueDescription(self.core, self.builder)
        self.edit_values_question = EditValueQuestion(self.core, self.builder)
        self.edit_values_value = EditValueValue(self.core, self.builder)
        
        self.sw_main = self.builder.get_object("edit:values:sw_main")
        self.value_nbook = self.builder.get_object("edit:values:notebook")
        btn_value_add = self.builder.get_object("edit:values:btn_add")
        btn_value_remove = self.builder.get_object("edit:values:btn_remove")
        
        btn_value_add.connect("clicked", self.__cd_value_add)
        btn_value_remove.connect("clicked", self.__cd_value_remove)
        
        self.addColumn("ID",self.COLUMN_ID)
        self.addColumn("Title",self.COLUMN_TITLE)
        
    def fill(self, item, values):
        self.model.clear()
        self.emit("item_changed")
        self.item = item
        self.values = values
        if values:
            for value in values:
                lang = self.core.lib["policy_model"].benchmark.lang
                title_lang = ""
                for title in value.title: 
                    if title.lang == lang:
                        title_lang = title.text
                        break
                    title_lang = title.text
                self.model.append([value.id, title_lang, "", value])


    def __cd_value_add(self, widget):
        pass

    def __cd_value_remove(self, widget):
        pass
    
    def set_sensitive(self, sensitive):
        self.sw_main.set_sensitive(sensitive)
        
    def __cb_item_changed(self, widget, treeView):
        self.emit("item_changed")
        treeView.columns_autosize()
    
    def __update(self):
        (model,iter) = self.selection.get_selected()
        if iter:
            self.value_nbook.set_sensitive(True)
            value = model.get_value(iter, self.COLUMN_OBJECT)
            self.edit_values_title.fill(value)
            self.edit_values_description.fill(value)
            self.edit_values_question.fill(value)
            self.edit_values_value.fill(value)
            
        else:
            self.value_nbook.set_sensitive(False)
            self.edit_values_title.fill(None)
            self.edit_values_description.fill(None)
            self.edit_values_question.fill(None)
            self.edit_values_value.fill(None)
            
class EditValueTitle(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2

    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:values:lv_title")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Value title",
                        "view":         lv,
                        "cb":           self.DHEditValueTitle,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Value title",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:values:btn_title_add")
        btn_edit = builder.get_object("edit:values:btn_title_edit")
        btn_del = builder.get_object("edit:values:btn_title_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Value title",self.COLUMN_TEXT)
        
    def fill(self, value):
        self.item = value
        self.model.clear()
        if value:
            for data in value.title:
                self.model.append([data.lang, (" ".join(data.text.split())), data])
                
class EditValueDescription(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2

    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:values:lv_description")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Value description",
                        "view":         lv,
                        "cb":           self.DHEditValueDescription,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Value Description",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:values:btn_description_add")
        btn_edit = builder.get_object("edit:values:btn_description_edit")
        btn_del = builder.get_object("edit:values:btn_description_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Value description",self.COLUMN_TEXT)
        
    def fill(self, value):
        self.item = value
        self.model.clear()
        if value:
            for data in value.description:
                self.model.append([data.lang, data.text, data])

class EditValueQuestion(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2

    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:values:lv_question")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Value question",
                        "view":         lv,
                        "cb":           self.DHEditValueQuestion,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Value question",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:values:btn_question_add")
        btn_edit = builder.get_object("edit:values:btn_question_edit")
        btn_del = builder.get_object("edit:values:btn_question_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Value questionn",self.COLUMN_TEXT)
        
    def fill(self, value):
        self.item = value
        self.model.clear()
        if value:
            for data in value.question:
                self.model.append([data.lang, data.text, data])
                
class EditValueValue(commands.DHEditItems,Edit_abs):

    COLUMN_SELECTOR = 0
    COLUMN_VALUE = 1
    COLUMN_SELECTED = 2
    COLUMN_OBJECT = 3

    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:values:lv_value")
        model = gtk.ListStore(str, str, bool, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Value question",
                        "view":         lv,
                        "cb":           self.DHEditValueValue,
                        "textEntry":    {"name":    "Selector",
                                        "column":   self.COLUMN_SELECTOR,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Value",
                                        "column":   self.COLUMN_VALUE,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:values:btn_value_add")
        btn_edit = builder.get_object("edit:values:btn_value_edit")
        btn_del = builder.get_object("edit:values:btn_value_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Selector",self.COLUMN_SELECTOR)
        self.addColumn("Value",self.COLUMN_VALUE)
        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect( 'toggled', self.__cb_toggled, self.model )
        column = gtk.TreeViewColumn("Selected", cell )
        column.add_attribute( cell, "active", self.COLUMN_SELECTED)
        self.lv.append_column(column )

        
    def fill(self, value):
        self.item = value
        self.model.clear()
        selected = ""
        if value:
            for data in value.instances:
                if data.selector == "":
                    selected = data.value
                else:
                    self.model.append([data.selector, data.value, False, data])
            iter = self.model.get_iter_first()
            while iter:
                if self.model.get_value(iter, self.COLUMN_VALUE) == selected:
                    self.model.set_value(iter, self.COLUMN_SELECTED, True)
                    break
                iter = self.model.iter_next(iter)
                
    def __cb_toggled(self, cell, path, model ):
        iter = model.get_iter_first()
        while iter:
            model.set_value(iter, self.COLUMN_SELECTED, False)
            iter = model.iter_next(iter)
        model[path][self.COLUMN_SELECTED] = not model[path][self.COLUMN_SELECTED]
            
#=========================================  End edit values ===================================

#======================================= EDIT FIXTEXT ==========================================

class EditFixtext(commands.DHEditItems, Edit_abs, EventObject):
    
    COLUMN_TEXT = 0
    COLUMN_OBJECT = 1
    
    def __init__(self, core, builder):
        
        self.id = "gui:btn:menu:edit:fixtext"
        self.builder = builder
        self.core = core
        
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(self.id, "item_changed")
        
        self.edit_fixtext_option = EditFixtextOption(core, builder)
        self.add_receiver("gui:btn:menu:edit:fixtext", "item_changed", self.__update)
        
        self.model = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        lv = self.builder.get_object("edit:operations:lv_fixtext")
        lv.set_model(self.model)
        
                #information for new/edit dialog
        values = {
                    "name_dialog":  "Fixtext",
                    "view":         lv,
                    "cb":           self.DHEditFixtextText,            
                    "textView":     {"name":    "Value",
                                    "column":   self.COLUMN_TEXT,
                                    "empty":    False, 
                                    "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:operations:btn_fixtext_add")
        btn_edit = builder.get_object("edit:operations:btn_fixtext_edit")
        btn_del = builder.get_object("edit:operations:btn_fixtext_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.selection.connect("changed", self.__cb_item_changed, lv)
        
        self.box_main = self.builder.get_object("edit:operations:fixtext:box")
        
        self.addColumn("Text",self.COLUMN_TEXT)
        
    def fill(self, item):
        self.model.clear()
        self.emit("item_changed")
        if item:
            self.item = item
            rule = item.to_rule()
            if rule.fixtexts:
                for object in rule.fixtexts:
                    self.model.append([object.text.text, object])
        else:
            self.item = None
    
    def set_sensitive(self, sensitive):
        self.box_main.set_sensitive(sensitive)
        
    def __cb_item_changed(self, widget, treeView):
        self.emit("item_changed")
        treeView.columns_autosize()
    
    def __update(self):
        (model,iter) = self.selection.get_selected()
 
        if iter:
            self.edit_fixtext_option.fill(model.get_value(iter,self.COLUMN_OBJECT))
        else:
            self.edit_fixtext_option.fill(None)

            
class EditFixtextOption(commands.DHEditItems,Edit_abs):
    
    CB_COLUMN_DATA = 0
    CB_COLUMN_VIEW = 1
    
    def __init__(self, core, builder):
    
        # set  models
        self.core = core
        self.builder = builder
        Edit_abs.__init__(self, core, None, None)
        
        #edit data of fictext
        self.entry_reference = self.builder.get_object("edit:operations:fixtext:entry_reference")
        self.entry_reference.connect("focus-out-event",self.cb_entry_fixtext_reference)
        
        self.combo_strategy = self.builder.get_object("edit:operations:fixtext:combo_strategy")
        cell = gtk.CellRendererText()
        self.combo_strategy.pack_start(cell, True)
        self.combo_strategy.add_attribute(cell, 'text',self.CB_COLUMN_VIEW)  
        self.combo_strategy.set_model(self.combo_model_strategy)
        self.combo_strategy.connect( "changed", self.cb_combo_fixtext_strategy)
        
        self.combo_complexity = self.builder.get_object("edit:operations:fixtext:combo_complexity")
        cell = gtk.CellRendererText()
        self.combo_complexity.pack_start(cell, True)
        self.combo_complexity.add_attribute(cell, 'text', self.CB_COLUMN_VIEW)  
        self.combo_complexity.set_model(self.combo_model_level)
        self.combo_complexity.connect( "changed", self.cb_combo_fixtext_complexity)
    
        self.combo_disruption = self.builder.get_object("edit:operations:fixtext:combo_disruption")
        cell = gtk.CellRendererText()
        self.combo_disruption.pack_start(cell, True)
        self.combo_disruption.add_attribute(cell, 'text', self.CB_COLUMN_VIEW)  
        self.combo_disruption.set_model(self.combo_model_level)
        self.combo_disruption.connect( "changed", self.cb_combo_fixtext_disruption)
    
        self.chbox_reboot = self.builder.get_object("edit:operations:fixtext:chbox_reboot")
        self.chbox_reboot.connect("toggled",self.cb_chbox_fixtext_reboot)

        self.box_detail= self.builder.get_object("edit:operations:fixtext:frame")
        
    def fill(self, fixtext):
        self.item = fixtext
        self.combo_strategy.handler_block_by_func(self.cb_combo_fixtext_strategy)
        self.combo_complexity.handler_block_by_func(self.cb_combo_fixtext_complexity)
        self.combo_disruption.handler_block_by_func(self.cb_combo_fixtext_disruption)
        self.chbox_reboot.handler_block_by_func(self.cb_chbox_fixtext_reboot)
        if fixtext:

            self.box_detail.set_sensitive(True)

            if fixtext.fixref:
                self.entry_reference.set_text(fixtext.fixref)
            else:
                self.entry_reference.set_text("")
            
            self.chbox_reboot.set_active(fixtext.reboot)
            self.set_active_comboBox(self.combo_strategy, fixtext.strategy, self.CB_COLUMN_DATA)
            self.set_active_comboBox(self.combo_complexity, fixtext.complexity, self.CB_COLUMN_DATA)
            self.set_active_comboBox(self.combo_disruption, fixtext.disruption, self.CB_COLUMN_DATA)
        else:
            self.item = None
            self.box_detail.set_sensitive(False)
            self.entry_reference.set_text("")
            self.chbox_reboot.set_active(False)
            self.combo_strategy.set_active(-1)
            self.combo_complexity.set_active(-1)
            self.combo_disruption.set_active(-1)
            
        self.combo_strategy.handler_unblock_by_func(self.cb_combo_fixtext_strategy)
        self.combo_complexity.handler_unblock_by_func(self.cb_combo_fixtext_complexity)
        self.combo_disruption.handler_unblock_by_func(self.cb_combo_fixtext_disruption)
        self.chbox_reboot.handler_unblock_by_func(self.cb_chbox_fixtext_reboot)
            
            

#======================================= EDIT FIX ==========================================

class EditFix(commands.DHEditItems, Edit_abs, EventObject):
    
    COLUMN_ID = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2
    
    def __init__(self, core, builder):
        
        self.id = "gui:btn:menu:edit:fix"
        self.builder = builder
        self.core = core
        
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(self.id, "item_changed")
        
        self.edit_fix_option = EditFixOption(core, builder)
        self.add_receiver("gui:btn:menu:edit:fix", "item_changed", self.__update)
        
        self.model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv = self.builder.get_object("edit:operations:lv_fix")
        lv.set_model(self.model)
        
                #information for new/edit dialog
        values = {
                    "name_dialog":  "Fix",
                    "view":         lv,
                    "cb":           self.DHEditFix,
                    "textEntry":    {"name":    "ID",
                                    "column":   self.COLUMN_ID,
                                    "empty":    False, 
                                    "unique":   True},
                    "textView":     {"name":    "Content",
                                    "column":   self.COLUMN_TEXT,
                                    "empty":    False, 
                                    "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:operations:btn_fix_add")
        btn_edit = builder.get_object("edit:operations:btn_fix_edit")
        btn_del = builder.get_object("edit:operations:btn_fix_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        Edit_abs.__init__(self, core, lv, values)
        self.selection.connect("changed", self.__cb_item_changed, lv)
        
        self.box_main = self.builder.get_object("edit:operations:fix:box")
        
        self.addColumn("ID",self.COLUMN_ID)
        self.addColumn("Content",self.COLUMN_TEXT)
        
    def fill(self, item):
        self.model.clear()
        self.emit("item_changed")
        if item:
            self.item = item
            rule = item.to_rule()
            for object in rule.fixes:
                self.model.append([object.id, object.content, object])
        else:
            self.item = None
    
    def set_sensitive(self, sensitive):
        self.box_main.set_sensitive(sensitive)
        
    def __cb_item_changed(self, widget, treeView):
        self.emit("item_changed")
        treeView.columns_autosize()
    
    def __update(self):
        (model,iter) = self.selection.get_selected()
 
        if iter:
            self.edit_fix_option.fill(model.get_value(iter,self.COLUMN_OBJECT))
        else:
            self.edit_fix_option.fill(None)

            
class EditFixOption(commands.DHEditItems,Edit_abs):
    
    CB_COLUMN_DATA = 0
    CB_COLUMN_VIEW = 1
    
    def __init__(self, core, builder):
    
        # set  models
        self.core = core
        self.builder = builder

        #edit data of fictext
        self.entry_system = self.builder.get_object("edit:operations:fix:entry_system")
        self.entry_system.connect("focus-out-event",self.cb_entry_fix_system)
        
        self.entry_platform = self.builder.get_object("edit:operations:fix:entry_platform")
        self.entry_platform.connect("focus-out-event",self.cb_entry_fix_platform)
        
        self.combo_strategy = self.builder.get_object("edit:operations:fix:combo_strategy")
        self.set_model_to_comboBox(self.combo_strategy,self.combo_model_strategy, self.CB_COLUMN_VIEW)
        self.combo_strategy.connect( "changed", self.cb_combo_fix_strategy)
        
        self.combo_complexity = self.builder.get_object("edit:operations:fix:combo_complexity")
        self.set_model_to_comboBox(self.combo_complexity, self.combo_model_level, self.CB_COLUMN_VIEW)
        self.combo_complexity.connect( "changed", self.cb_combo_fix_complexity)
    
        self.combo_disruption = self.builder.get_object("edit:operations:fix:combo_disruption")
        self.set_model_to_comboBox(self.combo_disruption, self.combo_model_level, self.CB_COLUMN_VIEW)
        self.combo_disruption.connect( "changed", self.cb_combo_fix_disruption)
    
        self.chbox_reboot = self.builder.get_object("edit:operations:fix:chbox_reboot")
        self.chbox_reboot.connect("toggled",self.cb_chbox_fix_reboot)

        self.box_detail= self.builder.get_object("edit:operations:fix:frame")
        
    def fill(self, fix):
        self.item = fix
        self.combo_strategy.handler_block_by_func(self.cb_combo_fix_strategy)
        self.combo_complexity.handler_block_by_func(self.cb_combo_fix_complexity)
        self.combo_disruption.handler_block_by_func(self.cb_combo_fix_disruption)
        self.chbox_reboot.handler_block_by_func(self.cb_chbox_fix_reboot)
        if fix:

            self.box_detail.set_sensitive(True)

            if fix.system:
                self.entry_system.set_text(fix.system)
            else:
                self.entry_system.set_text("")

            if fix.platform:
                self.entry_platform.set_text(fix.platform)
            else:
                self.entry_platform.set_text("")
                
            self.chbox_reboot.set_active(fix.reboot)
            self.set_active_comboBox(self.combo_strategy, fix.strategy, self.CB_COLUMN_DATA)
            self.set_active_comboBox(self.combo_complexity, fix.complexity, self.CB_COLUMN_DATA)
            self.set_active_comboBox(self.combo_disruption, fix.disruption, self.CB_COLUMN_DATA)
        else:
            self.item = None
            self.box_detail.set_sensitive(False)
            self.entry_system.set_text("")
            self.entry_platform.set_text("")
            self.chbox_reboot.set_active(False)
            self.combo_strategy.set_active(-1)
            self.combo_complexity.set_active(-1)
            self.combo_disruption.set_active(-1)
            
        self.combo_strategy.handler_unblock_by_func(self.cb_combo_fix_strategy)
        self.combo_complexity.handler_unblock_by_func(self.cb_combo_fix_complexity)
        self.combo_disruption.handler_unblock_by_func(self.cb_combo_fix_disruption)
        self.chbox_reboot.handler_unblock_by_func(self.cb_chbox_fix_reboot)
            
class EditDialogWindow(EventObject):
    
    def __init__(self, item, core, values, new=True):
        
        self.core = core
        self.new = new
        self.values = values
        self.item = item
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")
        
        self.window = builder.get_object("dialog:edit_item")
        self.window.set_keep_above(True)
        self.window.connect("delete-event", self.__delete_event)
        
        btn_ok = builder.get_object("btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)
        
        #info for change
        self.iter_del = None

        table = builder.get_object("table")
        table.hide_all()
        table.show()
        
        self.selection = values["view"].get_selection()
        (self.model, self.iter) = self.selection.get_selected()

        if "textEntry" in values:
            self.textEntry = builder.get_object("entryText")
            self.textEntry.show_all()
            lbl_entryText = builder.get_object("lbl_entryText")
            lbl_entryText.set_label(values["textEntry"]["name"])
            lbl_entryText.show_all()
            if new == False:
                text_edit = self.model.get_value(self.iter,values["textEntry"]["column"])
                if text_edit:
                    self.textEntry.set_text(text_edit)
                else:
                    self.textEntry.set_text("")

        if "textView" in values:
            self.textView = builder.get_object("textView")
            sw_textView = builder.get_object("sw_textView")
            sw_textView.show_all()
            lbl_textView = builder.get_object("lbl_textView")
            lbl_textView.set_label(values["textView"]["name"])
            lbl_textView.show()
            if new == False:
                buff = self.textView.get_buffer()
                buff.set_text(self.model.get_value(self.iter,values["textView"]["column"]))

        if "cBox" in values:
            self.cBox = builder.get_object("cBox")
            cell = gtk.CellRendererText()
            self.cBox.pack_start(cell, True)
            self.cBox.add_attribute(cell, 'text',values["cBox"]["cBox_view"])  
            self.cBox.set_model(values["cBox"]["model"])
            lbl_cBox = builder.get_object("lbl_cBox")
            lbl_cBox.set_label(values["cBox"]["name"])
            self.cBox.show_all()
            lbl_cBox.show()
            if new == False:
                self.cBox.set_active_iter(self.model.get_value(self.iter,values["cBox"]["column"]))

        self.window.show()

    def __cb_do(self, widget):
        
        init_data = None
        if self.new == True:
            dest_path = None
            self.iter = None
        else:
            dest_path = self.model.get_path(self.iter)
        
        if "textEntry" in self.values:
            text_textEntry = self.textEntry.get_text()
            
            # if data should not be empty and control
            if self.values["textEntry"]["empty"] == False:
                if not self.control_empty(text_textEntry, self.values["textEntry"]["name"]):
                    return
            
            # if data sould be unique and control
            if self.values["textEntry"]["unique"] == True:
                path = self.control_unique(self.values["textEntry"]["name"], self.model, 
                                            self.values["textEntry"]["column"], text_textEntry, self.iter)
                if path == False:
                    return
                else:
                    dest_path = path
                    
        if "textView" in self.values:
            buff = self.textView.get_buffer()
            iter_start = buff.get_start_iter()
            iter_end = buff.get_end_iter()
            text_textView = buff.get_text(iter_start, iter_end, True)
            init_data = text_textView
            
            # if data should not be empty and control
            if self.values["textView"]["empty"] == False:
                if not self.control_empty(text_textView, self.values["textView"]["name"]):
                    return

            # if data sould be unique and control
            if self.values["textView"]["unique"] == True:
                path = self.control_unique(self.values["textView"]["name"], self.model, 
                                            self.values["textView"]["column"], text_textView, self.iter)
                if path == False:
                    return
                else:
                    dest_path = path
        
        if "cBox" in self.values:
            active = self.cBox.get_active()
            if active < 0:
                data_selected = ""
                view_selected = ""
                iter_selected = None
            else:
                data_selected = self.values["cBox"]["model"][active][self.values["cBox"]["cBox_data"]]
                view_selected = self.values["cBox"]["model"][active][self.values["cBox"]["cBox_view"]]
                iter_selected = self.cBox.get_active_iter()
                
            # if data should not be empty and control
            if self.values["cBox"]["empty"] == False:
                if not self.control_empty(data_selected, self.values["cBox"]["name"]):
                    return
            
            # if data sould be unique and control
            if self.values["cBox"]["unique"] == True:
                path = self.control_unique(self.values["cBox"]["name"], self.model, 
                                            self.values["cBox"]["column"], data_selected, self.iter)
                if path == False:
                    return
                else:
                    dest_path = path
                    
                    
        # new row and unique => add new row
        if dest_path == None:
            iter = self.model.append()
            self.values["cb"](self.item, self.model, iter, None, None)
            self.selection.select_path(self.model.get_path(iter))

        # edit row
        else:
            iter = self.model.get_iter(dest_path)
            if self.iter and dest_path != self.model.get_path(self.iter):
                self.values["cb"](self.item, self.model, self.iter, None, None, True)

        # if insert data are correct, put them to the model
        if "textEntry" in self.values:
            self.model.set_value(iter,self.values["textEntry"]["column"], text_textEntry)
            self.values["cb"](self.item, self.model, iter, self.values["textEntry"]["column"], text_textEntry)
                    
        if "textView" in self.values:
            self.values["cb"](self.item, self.model, iter, self.values["textView"]["column"], text_textView)
            self.model.set_value(iter,self.values["textView"]["column"], text_textView)

        if "cBox" in self.values:
            self.model.set_value(iter,self.values["cBox"]["column"], iter_selected)
            self.model.set_value(iter,self.values["cBox"]["column_view"], view_selected)
            self.values["cb"](self.item, self.model, iter, self.values["cBox"]["column"], data_selected)
            
        self.window.destroy()

    def __delete_event(self, widget, event=None):
        self.window.destroy()

    def control_unique(self, name, model, column, data, iter):
        """
        Control if data is unique.
        @return None if data are dulplicat and user do not want changed exist data. Return Iter for store date
                if data are not duplicate or data are duplicate and user can change them.
        """
        if iter:
            path = model.get_path(iter)
        else:
            path = None
            
        for row in model:
            if row[column] == data and self.model.get_path(row.iter) != path:
                md = gtk.MessageDialog(self.window, 
                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_YES_NO, "%s \"%s\" already specified.\n\nRewrite stored data ?" % (name, data,))
                md.set_title("Information exist")
                result = md.run()
                md.destroy()
                if result == gtk.RESPONSE_NO:
                    return False
                else: 
                    return model.get_path(row.iter)
        return path
    
    def control_empty(self, data, name):
        """
        Control data if are not empty.
        @return True if not empty else return false
        """
        if (data == "" or data == None):
            md = gtk.MessageDialog(self.window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK, " \"%s\" can't be empty." % (name))
            md.set_title("Info")
            md.run()
            md.destroy()
            return False
        return True


            
            
#class EditTitle(commands.DataHandler, abstract.EnterList):
    
    #COLUMN_MARK_ROW = 0
    #COLUMN_LAN = 1
    #COLUMN_TITLE = 2
    
    #def __init__(self, core, treeView):
        #commands.DataHandler.__init__(self, core)
        #self.core = core
        #self.treeView = treeView
        #self.iter_del=None
        #self.model = gtk.ListStore(str, str, str)
        #abstract.EnterList.__init__(self, core, "EditTitle",self.model, self.treeView)
        
        #self.add_receiver("EditTitle", "del", self.__del_row)
        #self.add_receiver("EditTitle", "edit", self.__edit_row)
        
        #cell = self.set_insertColumnText("Language", EditTitle.COLUMN_LAN, True, True)
        #cell = self.set_insertColumnText("Title", EditTitle.COLUMN_TITLE, False, False)
        
    #def __del_row(self):
        #self.model.remove(self.iter_del)
    
    #def __edit_row(self):
        #self.model[self.edit_path][self.edit_column] = self.edit_text
    
    #def fill(self,data):

        #self.selected_old = None
        #self.model.clear()
        #if data != None:
            #for key in data.keys():
                #self.model.append(["", key, data[key]])
        #iter = self.model.append(None)
        #self.model.set(iter,EditTitle.COLUMN_MARK_ROW,"*")
        
#class DHEditDescription(DataHandler, abstract.EnterList):
    
    #COLUMN_MARK_ROW = 0
    #COLUMN_LANG = 1
    #COLUMN_DES_INFO = 2
    #COLUMN_DES = 3
    
    #def __init__(self, core, treeView, sw_description):
        #DataHandler.__init__(self, core)
        #self.core = core
        #self.treeView = treeView
        #self.iter_del=None
        #self.selected_des = None
        #model = gtk.ListStore(str, str, str, str)
        #abstract.EnterList.__init__(self, core, "DHEditDescription",model, self.treeView)
        
        #self.add_receiver("DHEditDescription", "del", self.__del_row)
        
        #cell = self.set_insertColumnText("Language", DHEditDescription.COLUMN_LANG)
        #cell.connect("edited", self.__cd_editLang, DHEditDescription.COLUMN_LANG)
        #cell = self.set_insertColumnInfo("Description", DHEditDescription.COLUMN_DES_INFO, True)
                
        #self.description = HtmlTextView()
        #self.description.set_wrap_mode(gtk.WRAP_WORD)
        #self.description.set_editable(True)
        #self.description.connect("key-release-event", self.__edit_des)
        #sw_description.add(self.description)
        #sw_description.show_all()

        #self.selection.connect("changed", self.__cb_item_changed)
        
    #def __cb_item_changed(self, widget):

        #self.description.get_buffer().set_text("")
        #if self.selection != None: 
            #(model, iter) = self.selection.get_selected( )
            #if iter: 
                #self.selected_des = iter
                #text = self.model.get_value(iter, DHEditDescription.COLUMN_DES) 
                #if  text != "" and text != None:
                    #self.description.display_html(self.model.get_value(iter, DHEditDescription.COLUMN_DES))
            #else:
                #self.selected_des = None
                
    #def __edit_des(self, widget, event):
        #if self.selected_des != None:
            #buff = self.description.get_buffer()
            #iter_start = buff.get_start_iter()
            #iter_end = buff.get_end_iter()
            #des = buff.get_text(iter_start, iter_end, True)
            #self.model.set(self.selected_des, DHEditDescription.COLUMN_DES, "<body>"+des+"</body>")
            #self.model.set(self.selected_des, DHEditDescription.COLUMN_DES_INFO, des)
    
    #def __del_row(self):
        #self.model.remove(self.iter_del)
        
    #def __cd_editLang(self, cellrenderertext, path, new_text, column):
        #self.model[path][column] = new_text

    #def __cd_editDes(self, cellrenderertext, path, new_text, column):
        #self.model[path][column] = new_text
    
    #def fill(self,data):
        
        #self.selected_old = None
        #self.model.clear()
        #if data != []:
            #for key in data.keys():
                #des = data[key].replace("xhtml:","")
                #des = des.replace("xmlns:", "")
                #des_info = des[:30].replace("\n","")
                #des_info = des_info.replace("\t","")
                #des = "<body>"+des+"</body>"
                #self.model.append(["", key, des, des])
        #iter = self.model.append(None)
        #self.model.set(iter,DHEditDescription.COLUMN_MARK_ROW,"*")
        
        ##self.combo_model_strategy = gtk.ListStore(int, str, str)
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])
        ##self.combo_model_strategy.append([openscap.OSCAP., "", ""])