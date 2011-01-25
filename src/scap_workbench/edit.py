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
import datetime
import time
import re

import abstract
import logging
import core
from events import EventObject
logger = logging.getLogger("scap-workbench")
try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None
    
import commands
import filter
import render

logger = logging.getLogger("scap-workbench")
    
from htmltextview import HtmlTextView
from threads import thread as threadSave


logger = logging.getLogger("OSCAPEditor")

class Edit_abs:
    
    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2
    
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
    
    combo_model_status = gtk.ListStore(int, str, str)
    combo_model_status.append([openscap.OSCAP.XCCDF_STATUS_NOT_SPECIFIED, "NOT SPECIFIED", "Status was not specified by benchmark."])
    combo_model_status.append([openscap.OSCAP.XCCDF_STATUS_ACCEPTED, "ACCEPTED", "Accepted."])
    combo_model_status.append([openscap.OSCAP.XCCDF_STATUS_DEPRECATED, "DEPRECATED", "Deprecated."])
    combo_model_status.append([openscap.OSCAP.XCCDF_STATUS_DRAFT, "DRAFT ", "Draft item."])
    combo_model_status.append([openscap.OSCAP.XCCDF_STATUS_INCOMPLETE, "INCOMPLETE", "The item is not complete. "])
    combo_model_status.append([openscap.OSCAP.XCCDF_STATUS_INTERIM, "INTERIM", "Interim."])
    
    combo_model_warning = gtk.ListStore(int, str, str)
    combo_model_warning.append([0, "UNKNOWN", "Unknown."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_GENERAL, "GENERAL", "General-purpose warning."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_FUNCTIONALITY, "FUNCTIONALITY", "Warning about possible impacts to functionality."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_PERFORMANCE, "PERFORMANCE", "  Warning about changes to target system performance."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_HARDWARE, "HARDWARE", "Warning about hardware restrictions or possible impacts to hardware."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_LEGAL, "LEGAL", "Warning about legal implications."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_REGULATORY, "REGULATORY", "Warning about regulatory obligations."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_MANAGEMENT, "MANAGEMENT", "Warning about impacts to the mgmt or administration of the target system."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_AUDIT, "AUDIT", "Warning about impacts to audit or logging."])
    combo_model_warning.append([openscap.OSCAP.XCCDF_WARNING_DEPENDENCY, "DEPENDENCY", "Warning about dependencies between this Rule and other parts of the target system."])

    combo_model_role = gtk.ListStore(int, str, str)
    combo_model_role.append([openscap.OSCAP.XCCDF_ROLE_FULL, "FULL", "Check the rule and let the result contriburte to the score and appear in reports.."])
    combo_model_role.append([openscap.OSCAP.XCCDF_ROLE_UNSCORED, "UNSCORED", "Check the rule and include the result in reports, but do not include it into score computations"])
    combo_model_role.append([openscap.OSCAP.XCCDF_ROLE_UNCHECKED, "UNCHECKED", "Don't check the rule, result will be XCCDF_RESULT_UNKNOWN."])

    combo_model_type = gtk.ListStore(int, str, str)
    combo_model_type.append([openscap.OSCAP.XCCDF_TYPE_NUMBER, "NUMBER", ""])
    combo_model_type.append([openscap.OSCAP.XCCDF_TYPE_STRING, "STRING", ""])
    combo_model_type.append([openscap.OSCAP.XCCDF_TYPE_BOOLEAN, "BOOLEAN", ""])

    combo_model_operator_number = gtk.ListStore(int, str, str)
    combo_model_operator_number.append([openscap.OSCAP.XCCDF_OPERATOR_EQUALS, "EQUALS", "Equality"])
    combo_model_operator_number.append([openscap.OSCAP.XCCDF_OPERATOR_NOT_EQUAL, "NOT EQUAL", "Inequality"])
    combo_model_operator_number.append([openscap.OSCAP.XCCDF_OPERATOR_GREATER, "GREATER", "Greater than"])
    combo_model_operator_number.append([openscap.OSCAP.XCCDF_OPERATOR_GREATER_EQUAL, "GREATER OR EQUAL", "Greater than or equal."])
    combo_model_operator_number.append([openscap.OSCAP.XCCDF_OPERATOR_LESS , "LESS", "Less than."])
    combo_model_operator_number.append([openscap.OSCAP.XCCDF_OPERATOR_LESS_EQUAL, "LESS OR EQUAL", "Less than or equal."])

    combo_model_operator_bool = gtk.ListStore(int, str, str)
    combo_model_operator_bool.append([openscap.OSCAP.XCCDF_OPERATOR_EQUALS, "EQUALS", "Equality"])
    combo_model_operator_bool.append([openscap.OSCAP.XCCDF_OPERATOR_NOT_EQUAL, "NOT EQUAL", "Inequality"])

    combo_model_operator_string = gtk.ListStore(int, str, str)
    combo_model_operator_string.append([openscap.OSCAP.XCCDF_OPERATOR_EQUALS, "EQUALS", "Equality"])
    combo_model_operator_string.append([openscap.OSCAP.XCCDF_OPERATOR_NOT_EQUAL, "NOT EQUAL", "Inequality"])
    combo_model_operator_string.append([openscap.OSCAP.XCCDF_OPERATOR_PATTERN_MATCH, "PATTERN_MATCH", "Match a regular expression."])

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
        
        
    def dialogInfo(self, text, window=None):
        if not window:
            window = self.core.main_window
            
        md = gtk.MessageDialog(window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK, text)
        md.set_title("Info")
        md.run()
        md.destroy()

    def addColumn(self, name, column, expand=False):
        #txtcell = abstract.CellRendererTextWrap()
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(name, txtcell, text=column)
        column.set_expand(expand)
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

    def controlDate(self, text):
        """
        Function concert sting to timestamp (gregorina). 
        If set text is incorrect format return False and show message.
        """
        if text != "":
            date = text.split("-")
            if len(date) != 3:
                self.dialogInfo("The date is in incorrect format. \n Correct format is YYYY-MM-DD.")
                return False
            try :
                d = datetime.date(int(date[0]), int(date[1]), int(date[2]))
            except Exception as ex:
                error = "Date is incorrect format:\n" + str(ex)
                self.dialogInfo(error)
                return False
            try:
                timestamp = time.mktime(d.timetuple()) 
            except Exception as ex:
                error = "Date is out of range. "
                self.dialogInfo(error)
            return timestamp
        return False
            
    def controlImpactMetric(self, text):
        """
        Function control impact metrix
        """
        #pattern = re.compile ("^AV:[L,A,N]/AC:[H,M,L]/Au:[M,S,N]/C:[N,P,C]/I:[N,P,C]/A:[N,P,C]$|^E:[U,POC,F,H,ND]/RL:[OF,TF,W,U,ND]/RC:[UC,UR,C,ND]$|^CDP:[N,L,LM,MH,H,ND]/TD:[N,L,M,H,ND]/CR:[L,M,H,ND]/ IR:[L,M,H,ND]/AR:[L,M,H,ND]$",re.IGNORECASE)
        patternBase = re.compile("^AV:[L,A,N]/AC:[H,M,L]/Au:[M,S,N]/C:[N,P,C]/I:[N,P,C]/A:[N,P,C]$",re.IGNORECASE)
        patternTempo = re.compile("^E:(U|(POC)|F|H|(ND))/RL:((OF)|(TF)|W|U|(ND))/RC:((UC)|(UR)|C|(ND))$",re.IGNORECASE)
        patternEnvi = re.compile("^CDP:(N|L|H|(LM)|(MH)|(ND))/TD:(N|L|M|H|(ND))/CR:(L|M|H|(ND))/IR:(L|M|H|(ND))/AR:(L|M|H|(ND))$",re.IGNORECASE)
        
        if patternBase.search(text) != None or patternTempo.search(text) != None or patternEnvi.search(text) != None:
            return True
        else:
            error = "Incorrect value of Impact Metrix, correct is:\n\n"
            error = error + "Metric Value    Description \n\n"
            error = error + "Base =    AV:[L,A,N]/AC:[H,M,L]/Au:[M,S,N]/C:[N,P,C]/I:[N,P,C]/A:[N,P,C]\n\n"
            error = error + "Temporal =     E:[U,POC,F,H,ND]/RL:[OF,TF,W,U,ND]/RC:[UC,UR,C,ND]\n\n"
            error = error + "Environmental =    CDP:[N,L,LM,MH,H,ND]/TD:[N,L,M,H,ND]/CR:[L,M,H,ND]/IR:[L,M,H,ND]/AR:[L,M,H,ND]"
            
            self.dialogInfo(error)
            return False

class ProfileList(abstract.List):
    
    def __init__(self, widget, core, builder=None, progress=None, filter=None):
        self.core = core
        self.builder = builder
        self.data_model = commands.DHProfiles(core)
        abstract.List.__init__(self, "gui:edit:profile_list", core, widget)

        # Popup Menu
        self.builder.get_object("edit:profile_list:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("edit:profile_list:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("edit:profile_list:popup"))

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        self.section_list = self.builder.get_object("edit:section_list")
        self.profilesList = self.builder.get_object("edit:tw_profiles:sw")

        # actions
        self.add_sender(self.id, "update_profiles")
        self.add_receiver("gui:btn:menu:edit", "update", self.__update)
        selection.connect("changed", self.cb_item_changed, self.get_TreeView())

    def __update(self, new=False):

        if self.section_list.get_model()[self.section_list.get_active()][0] == "PROFILES":
            self.profilesList.set_visible(True)
            if "profile" not in self.__dict__ or self.core.force_reload_profiles:
                self.data_model.fill()
                self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_profile, self.get_TreeView()))
                self.core.force_reload_profiles = False
            if new: self.emit("update_profiles")
        else:
            self.profilesList.set_visible(False)

    def cb_item_changed(self, widget, treeView):

        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: self.core.selected_profile = model.get_value(iter, 0)
        self.emit("update")

    def __cb_button_pressed(self, treeview, event, menu):
        if event.button == 3:
            time = event.time
            menu.popup(None, None, None, event.button, event.time)

    def __cb_item_remove(self, widget):
        selection = self.get_TreeView().get_selection()
        (model,iter) = selection.get_selected()
        if iter:
            self.data_model.remove_item(model[iter][0])
            model.remove(iter)
        else: raise AttributeError, "Removing non-selected item or nothing selected."
        self.emit("update_profiles")

    def __cb_item_add(self, widget):
        EditAddProfileDialogWindow(self.core, self.data_model, self.__update)

class ItemList(abstract.List):

    def __init__(self, widget, core, builder=None, progress=None, filter=None):

        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, True)
        self.edit_model = commands.DHEditItems()
        abstract.List.__init__(self, "gui:edit:item_list", core, widget)
        self.core = core
        self.loaded_new = True
        self.old_selected = None
        self.filter = filter
        self.map_filter = {}
        self.builder = builder

        # Popup Menu
        self.builder.get_object("edit:list:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("edit:list:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("edit:list:popup"))

        self.section_list = self.builder.get_object("edit:section_list")
        self.itemsList = self.builder.get_object("edit:tw_items:sw")
        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_receiver("gui:btn:menu:edit", "update", self.__update)
        self.add_receiver("gui:btn:edit:filter", "search", self.__search)
        self.add_receiver("gui:btn:edit:filter", "filter_add", self.__filter_add)
        self.add_receiver("gui:btn:edit:filter", "filter_del", self.__filter_del)
        self.add_receiver("gui:edit:DHItemsTree", "filled", self.__filter_refresh)
        self.add_receiver("gui:btn:main:xccdf", "load", self.__loaded_new_xccdf)

        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.add_sender(self.id, "item_changed")

        self.init_filters(self.filter, self.data_model.model, self.data_model.new_model())

    def __update(self):
        if self.section_list.get_model()[self.section_list.get_active()][0] == "XCCDF":
            self.itemsList.set_visible(True)
            if self.loaded_new == True:
                self.get_TreeView().set_model(self.data_model.model)
                self.data_model.fill()
                self.loaded_new = False
            # Select the last one selected if there is one         #self.core.selected_item_edi
            if self.old_selected != self.core.selected_item:
                self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))
                self.core.force_reload_items = False
                self.old_selected = self.core.selected_item
        else:
            self.itemsList.set_visible(False)

            
    def __loaded_new_xccdf(self):
        self.loaded_new = True
        
    def __search(self):
        self.search(self.filter.get_search_text(),1)
        
    def __filter_add(self):
        self.map_filter = self.filter_add(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_del(self):
        self.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_refresh(self):
        self.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __cb_button_pressed(self, treeview, event, menu):
        if event.button == 3:
            time = event.time
            menu.popup(None, None, None, event.button, event.time)

    def __cb_item_remove(self, widget):
        selection = self.get_TreeView().get_selection()
        (model,iter) = selection.get_selected()
        if iter:
            self.data_model.remove_item(model[iter][0])
            model.remove(iter)
        else: raise AttributeError, "Removing non-selected item or nothing selected."

    def __cb_item_add(self, widget):
        selection = self.get_TreeView().get_selection()
        (model,iter) = selection.get_selected()
        if iter:
            EditAddDialogWindow(self.core, self.data_model.get_item(model[iter][0]), self, self.ref_model, self.edit_model.DHEditAddItem )

    @threadSave
    def __cb_item_changed(self, widget, treeView):
        """Make all changes in application in separate threads: workaround for annoying
        blinking when redrawing treeView
        """
        gtk.gdk.threads_enter()
        details = self.data_model.get_item_objects(self.core.selected_item_edit)
        if details != None:
            self.item = details["item"]
        else: self.item = None
        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: 
                self.core.selected_item = model.get_value(iter, 0)
                self.core.selected_item_edit = model.get_value(iter, 0)
            else:
                self.core.selected_item = None
                self.core.selected_item_edit = None
        self.emit("update")
        treeView.columns_autosize()
        gtk.gdk.threads_leave()


class MenuButtonEdit(abstract.MenuButton, commands.DHEditItems, Edit_abs):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DataHandler(self.core)
        self.profile_model = commands.DHProfiles(self.core)
        self.item = None

        #draw body
        self.body = self.builder.get_object("edit:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        self.section_list = self.builder.get_object("edit:section_list")
        self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        self.tw_items = self.builder.get_object("edit:tw_items")
        self.tw_profiles = self.builder.get_object("edit:tw_profiles")
        titles = self.data_model.get_benchmark_titles()
        self.list_item = ItemList(self.tw_items, self.core, builder, self.progress, self.filter)
        self.list_profile = ProfileList(self.tw_profiles, self.core, builder, self.progress, self.filter)
        self.ref_model = self.list_item.get_TreeView().get_model() # original model (not filtered)

        self.section_list.connect("changed", self.__content_changed, self.section_list.get_model())
        
        self.filter.expander.cb_changed()

        # set signals
        self.add_sender(self.id, "update")
        self.add_sender(self.id, "update_profiles")
        
        """Get widget for details
        """
        #main
        self.itemsPage = self.builder.get_object("edit:notebook")
        self.profilePage = self.builder.get_object("edit:profile")
        
        # remove just for now (missing implementations and so..)
        self.itemsPage.remove_page(1)
        self.itemsPage.remove_page(3)

        self.set_sensitive(False)

        #general
        self.item_id = self.builder.get_object("edit:general:lbl_id")
        
        self.entry_version = self.builder.get_object("edit:general:entry_version")
        self.entry_version.connect("focus-out-event",self.cb_entry_version)
        
        self.entry_version_time = self.builder.get_object("edit:general:entry_version_time")
        self.entry_version_time.connect("focus-out-event",self.cb_control_version_time)

        self.chbox_selected = self.builder.get_object("edit:general:chbox_selected")
        self.chbox_selected.connect("toggled",self.cb_chbox_selected)
        
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
        self.edit_conflicts = EditConflicts(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.edit_requires = EditRequires(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.edit_ident = EditIdent(self.core, self.builder)
        
        self.lbl_extends = self.builder.get_object("edit:dependencies:lbl_extends")
        
        #Dependencies
        self.edit_platform = EditPlatform(self.core, self.builder)
        
        #operations
        self.edit_fixtext = EditFixtext(self.core, self.builder)
        self.edit_fix = EditFix(self.core, self.builder)
        
        self.cBox_severity = self.builder.get_object("edit:operations:combo_severity")
        cell = gtk.CellRendererText()
        self.cBox_severity.pack_start(cell, True)
        self.cBox_severity.add_attribute(cell, 'text', self.COMBO_COLUMN_VIEW)  
        self.cBox_severity.set_model(self.combo_model_level)
        self.cBox_severity.connect( "changed", self.cb_cBox_severity)
       
        
        self.entry_impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.entry_impact_metric.connect("focus-out-event",self.cb_control_impact_metrix)

        self.lv_check = self.builder.get_object("edit:operations:lv_check")
        
        #values
        self.edit_values = EditValues(self.core, self.builder)
        
        #others
        self.chbox_multiple = self.builder.get_object("edit:other:chbox_multiple")
        self.chbox_multiple.connect("toggled",self.cb_chbox_multipl)

        self.cBox_role = self.builder.get_object("edit:other:combo_role")
        cell = gtk.CellRendererText()
        self.cBox_role.pack_start(cell, True)
        self.cBox_role.add_attribute(cell, 'text', self.COMBO_COLUMN_VIEW)  
        self.cBox_role.set_model(self.combo_model_role)
        self.cBox_role.connect( "changed", self.cb_cBox_role)

        # PROFILES
        self.info_box_lbl = self.builder.get_object("edit:profile:info_box:lbl")
        self.profile_id = self.builder.get_object("edit:profile:entry_id")
        self.profile_cb_lang = self.builder.get_object("edit:profile:cbentry_lang")
        for lang in self.core.langs:
            self.profile_cb_lang.get_model().append([lang])
        self.profile_title = self.builder.get_object("edit:profile:entry_title")
        self.profile_version = self.builder.get_object("edit:profile:entry_version")
        self.profile_description = self.builder.get_object("edit:profile:entry_description")
        self.profile_abstract = self.builder.get_object("edit:profile:cbox_abstract")
        self.profile_extends = self.builder.get_object("edit:profile:cb_extends")
        self.tw_langs = self.builder.get_object("edit:profile:tw_langs")

        self.profile_btn_revert = self.builder.get_object("edit:profile:btn_revert")
        self.profile_btn_revert.connect("clicked", self.__cb_profile_revert)
        self.profile_btn_save = self.builder.get_object("edit:profile:btn_save")
        self.profile_btn_save.connect("clicked", self.__cb_profile_save)
        self.profile_btn_add = self.builder.get_object("edit:profile:btn_add")
        self.profile_btn_add.connect("clicked", self.__cb_profile_add_lang)

        selection = self.tw_langs.get_selection()
        selection.connect("changed", self.__cb_profile_lang_changed)
        self.langs_model = gtk.ListStore(str, str, str)
        self.tw_langs.set_model(self.langs_model)
        self.tw_langs.append_column(gtk.TreeViewColumn("Lang", gtk.CellRendererText(), text=0))
        self.tw_langs.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=1))
        self.tw_langs.append_column(gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=2))

        self.add_receiver("gui:edit:item_list", "update", self.__update_items)
        self.add_receiver("gui:edit:item_list", "changed", self.__update_items)
        self.add_receiver("gui:edit:profile_list", "update", self.__update_profile)
        self.add_receiver("gui:btn:main:xccdf", "load", self.__section_list_load)
        self.__section_list_load() #TODO

    def __section_list_load(self):
        self.section_list.get_model().clear()
        titles = self.data_model.get_benchmark_titles()
        if len(titles.keys()) != 0:
            if self.core.selected_lang in titles: 
                title = self.data_model.get_benchmark_titles()[self.core.selected_lang]
            else: 
                self.data_model.get_benchmark_titles()[0]
            self.section_list.get_model().append(["XCCDF", "XCCDF: "+title])
            self.section_list.get_model().append(["PROFILES", "XCCDF: "+title+" (Profiles)"])
            self.section_list.set_active(0)

    def __content_changed(self, widget, model):
        if model[widget.get_active()][0] == "XCCDF":
            self.profilePage.set_visible(False)
            self.itemsPage.set_visible(True)
        elif model[widget.get_active()][0] == "PROFILES":
            self.profilePage.set_visible(True)
            self.itemsPage.set_visible(False)
        self.__update()
        self.emit("update")

    def cb_control_impact_metrix(self, widget, event):
        text = widget.get_text()
        if text != "" and self.controlImpactMetric(text):
            self.DHEditImpactMetrix(self.item, text)
            
    def cb_control_version_time(self, widget, event):
        timestamp = self.controlDate(widget.get_text())
        if timestamp:
            self.DHEditVersionTime(self.item, timestamp)

    def __cb_profile_revert(self, widget):
        self.__update_profile()

    def __cb_profile_save(self, widget):
        if self.profile_id.get_text() == "":
            logger.error("No ID of profile specified")
            md = gtk.MessageDialog(self.window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_OK, "ID of profile has to be specified !")
            md.run()
            md.destroy()
            return
        values = {}
        values["id"] = self.profile_id.get_text()
        values["abstract"] = self.profile_abstract.get_active()
        values["version"] = self.profile_version.get_text()
        if self.profile_extends.get_active() >= 0: values["extends"] = self.profile_extends.get_model()[self.profile_extends.get_active()][0]
        else: values["extends"] = None
        values["details"] = []
        for row in self.tw_langs.get_model():
            item = {"lang": row[0],
                    "title": row[1],
                    "description": row[2]}
            values["details"].append(item)

        self.profile_model.edit(values)
        self.core.force_reload_profiles = True
        self.profile_model.save()
        self.emit("update")
        self.emit("update_profiles")

    def set_sensitive(self, sensitive):
        self.itemsPage.set_sensitive(sensitive)

    def __set_profile_description(self, description):
        """
        Set description to the textView.
        @param text Text with description
        """
        self.profile_description.get_buffer().set_text("")
        if description == "": description = "No description"
        description = "<body>"+description+"</body>"
        self.profile_description.display_html(description)
        
    def __update(self, active=""):
        if active == "PROFILES":
            self.__update_profile()
        else: self.__update_items()

    def __update_profile(self):

        details = self.data_model.get_profile_details(self.core.selected_profile)
        if not details:
            self.profile_id.set_text("")
            self.profile_abstract.set_text("")
            #self.profile_extend.set_text("")
            self.profile_version.set_text("")
            self.profile_title.set_text("")
            #self.__set_description("")
            return

        self.profile_description.set_sensitive(details["id"] != None)
        self.profile_title.set_sensitive(details["id"] != None)
        self.profile_abstract.set_sensitive(details["id"] != None)
        self.profile_id.set_sensitive(details["id"] != None)
        self.profile_version.set_sensitive(details["id"] != None)
        self.tw_langs.set_sensitive(details["id"] != None)
        self.profile_cb_lang.set_sensitive(details["id"] != None)
        self.profile_btn_add.set_sensitive(details["id"] != None)
        self.profile_btn_save.set_sensitive(details["id"] != None)
        self.profile_btn_revert.set_sensitive(details["id"] != None)

        self.profile_id.set_text(details["id"] or "")
        self.profile_abstract.set_active(details["abstract"])
        #self.profile_extend.set_text(str(details["extends"] or ""))
        self.profile_version.set_text(details["version"] or "")

        self.tw_langs.get_model().clear()
        title = None
        description = None
        for lang in details["titles"]:
            if lang in details["titles"]: title = details["titles"][lang]
            if lang in details["descriptions"]: description = details["descriptions"][lang]
            self.tw_langs.get_model().append([lang, title, description])

    def __cb_profile_lang_changed(self, widget):
        selection = self.tw_langs.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: 
                self.profile_cb_lang.set_text(model.get_value(iter, 0))
                self.profile_title.set_text(model.get_value(iter, 1))
                self.profile_description.get_buffer().set_text(model.get_value(iter, 2))

    def __cb_profile_add_lang(self, widget):
        result = None
        for row in self.tw_langs.get_model():
            if row[0] == self.profile_cb_lang.get_active_text():
                md = gtk.MessageDialog(self.core.main_window, 
                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_YES_NO, "Language \"%s\" already specified.\n\nRewrite stored data ?" % (row[0],))
                md.set_title("Language found")
                result = md.run()
                md.destroy()
                if result == gtk.RESPONSE_NO: 
                    return
                else: self.langs_model.remove(row.iter)

        buffer = self.profile_description.get_buffer()
        self.tw_langs.get_model().append([self.profile_cb_lang.get_active_text(), 
            self.profile_title.get_text(),
            buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)])

        # Add lang to combo box model
        found = False
        for item in self.profile_cb_lang.get_model():
            if item[0] == self.profile_cb_lang.get_active_text(): 
                found = True
        if not found: 
            self.profile_cb_lang.get_model().append([self.profile_cb_lang.get_active_text()])
            self.profile_cb_lang.set_active_iter(self.profile_cb_lang.get_model()[-1].iter)
            self.core.langs.append(self.profile_cb_lang.get_active_text())

        # Clear
        self.profile_cb_lang.set_active(-1)
        self.profile_title.set_text("")
        self.profile_description.get_buffer().set_text("")


    def __update_items(self):
 
        if self.core.selected_item_edit != None:
            details = self.data_model.get_item_objects(self.core.selected_item_edit)
        else:
            details = None
            self.item = None
        
        self.chbox_hidden.handler_block_by_func(self.cb_chbox_hidden)
        self.chbox_selected.handler_block_by_func(self.cb_chbox_selected)
        self.chbox_prohibit.handler_block_by_func(self.cb_chbox_prohibit)
        self.chbox_abstract.handler_block_by_func(self.cb_chbox_abstract)
        self.chbox_multiple.handler_block_by_func(self.cb_chbox_multipl)
        self.cBox_severity.handler_block_by_func(self.cb_cBox_severity)
        self.cBox_role.handler_block_by_func(self.cb_cBox_role)
        
        if details != None:
            self.set_sensitive(True)
            self.item = details["item"]
            self.item_id.set_text(details["id"])
            self.chbox_hidden.set_active(details["hidden"])
            self.chbox_selected.set_active(details["selected"])
            self.chbox_prohibit.set_active(details["prohibit_changes"])
            self.chbox_abstract.set_active(details["abstract"])

            self.edit_title.fill(details["item"])
            self.edit_description.fill(details["item"])
            self.edit_warning.fill(details["item"])
            self.edit_status.fill(details["item"])
            self.edit_question.fill(details["item"])
            self.edit_rationale.fill(details["item"])
            self.edit_platform.fill(details["item"])
            self.edit_conflicts.fill(details["item"])
            self.edit_requires.fill(details["item"])

            if details["version"] != None:
                self.entry_version.set_text(details["version"])
            else:
                self.entry_version.set_text("")

            if details["version_time"] != 0:
                self.entry_version_time.set_text(str(datetime.date.fromtimestamp(details["version_time"])))
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
                            self.cBox_severity.set_active_iter(iter_sev)
                            break
                        iter_sev = model_sev.iter_next(iter_sev)
                else:
                    self.cBox_severity.set_active(-1)

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
                            self.cBox_role.set_active_iter(iter_role)
                            break
                        iter_role = model_role.iter_next(iter_role)
                else:
                    self.cBox_role.set_active(-1)

                self.edit_values.set_sensitive(True)
                self.edit_values.fill(details["item"])

                self.chbox_multiple.set_sensitive(True)
                self.chbox_multiple.set_active(details["multiple"])
                
                self.edit_fixtext.set_sensitive(True)
                self.edit_fixtext.fill(details["item"])
                
                self.edit_fix.set_sensitive(True)
                self.edit_fix.fill(details["item"])
                
                self.edit_ident.set_sensitive(True)
                self.edit_ident.fill(details["item"])
                
                # clean hide data only for group and set insensitive

            #data only for Group
            else:
                # clean data only for rule and set insensitive
                self.cBox_severity.set_sensitive(False)
                self.cBox_severity.handler_block_by_func(self.cb_cBox_severity)
                self.cBox_severity.set_active(-1)
                self.cBox_severity.handler_unblock_by_func(self.cb_cBox_severity)
                
                self.cBox_role.set_sensitive(False)
                self.cBox_role.handler_block_by_func(self.cb_cBox_role)
                self.cBox_role.set_active(-1)
                self.cBox_role.handler_unblock_by_func(self.cb_cBox_role)

                self.edit_values.set_sensitive(False)
                self.edit_values.fill(None)
                
                self.chbox_multiple.set_sensitive(False)
                self.chbox_multiple.set_active(False)
                
                self.entry_impact_metric.set_sensitive(False)
                self.entry_impact_metric.set_text("")
                
                self.edit_fixtext.set_sensitive(False)
                self.edit_fixtext.fill(None)
                
                self.edit_fix.set_sensitive(False)
                self.edit_fix.fill(None)
                
                self.edit_ident.set_sensitive(False)
                self.edit_ident.fill(None)
                
        else:
            self.item = None
            self.set_sensitive(False)
            self.edit_title.fill(None)
            self.edit_description.fill(None)
            self.edit_warning.fill(None)
            self.edit_status.fill(None)
            self.edit_question.fill(None)
            self.edit_rationale.fill(None)
            self.edit_conflicts.fill(None)
            self.edit_requires.fill(None)
            self.edit_platform.fill(None)
            self.edit_fix.fill(None)
            self.edit_fixtext.fill(None)
            self.item_id.set_text("")
            self.chbox_hidden.set_active(False)
            self.chbox_selected.set_active(False)
            self.chbox_prohibit.set_active(False)
            self.chbox_abstract.set_active(False)
            self.entry_version.set_text("")
            self.entry_version_time.set_text("")
            self.entry_cluster_id.set_text("")
            self.lbl_extends.set_text("None")

        self.chbox_hidden.handler_unblock_by_func(self.cb_chbox_hidden)
        self.chbox_selected.handler_unblock_by_func(self.cb_chbox_selected)
        self.chbox_prohibit.handler_unblock_by_func(self.cb_chbox_prohibit)
        self.chbox_abstract.handler_unblock_by_func(self.cb_chbox_abstract)
        self.chbox_multiple.handler_unblock_by_func(self.cb_chbox_multipl)
        self.cBox_severity.handler_unblock_by_func(self.cb_cBox_severity)
        self.cBox_role.handler_unblock_by_func(self.cb_cBox_role)
            
class EditConflicts(commands.DHEditItems,Edit_abs):
    
    COLUMN_ID = 0
    
    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_conflict")
        model = gtk.ListStore(str)
        lv.set_model(model)
        
        Edit_abs.__init__(self, core, lv, None)
        btn_add = builder.get_object("edit:dependencies:btn_conflict_add")
        btn_del = builder.get_object("edit:dependencies:btn_conflict_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.__cb_add)
        btn_del.connect("clicked", self.__cb_del_row)

        self.addColumn("ID Item",self.COLUMN_ID)

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.conflicts:
                self.model.append([data])
    
    def __cb_add(self, widget):
        EditSelectIdDialogWindow(self.item, self.core, self.model, self.model_item, self.DHEditConflicts)
    
    
    def __cb_del_row(self, widget):
        pass

class EditRequires(commands.DHEditItems,Edit_abs):
    
    COLUMN_ID = 0
    
    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_requires")
        model = gtk.ListStore(str)
        lv.set_model(model)

        Edit_abs.__init__(self, core, lv, None)
        btn_add = builder.get_object("edit:dependencies:btn_requires_add")
        btn_del = builder.get_object("edit:dependencies:btn_requires_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.__cb_add)
        btn_del.connect("clicked", self.__cb_del_row)

        self.addColumn("ID Item", self.COLUMN_ID)

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.requires:
                self.model.append([data])
    
    def __cb_add(self, widget):
        EditSelectIdDialogWindow(self.item, self.core, self.model, self.model_item, self.DHEditRequires)
    
    def __cb_del_row(self, widget):
        pass
    
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
        
    def fill(self, item):

        self.item = item
        self.model.clear()
        if item:
            for data in item.title:
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

    def fill(self, item):

        self.item = item
        self.model.clear()
        if item:
            for data in item.description:
                self.model.append([data.lang, re.sub("[\t ]+" , " ", data.text).strip(), data])


class EditWarning(commands.DHEditItems,Edit_abs):

    COLUMN_CATEGORY_TEXT= 0
    COLUMN_CATEGORY_ITER = 1
    COLUMN_LAN = 2
    COLUMN_TEXT = 3
    COLUMN_OBJECT = 4

    
    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:general:lv_warning")
        model = gtk.ListStore(str, gobject.TYPE_PYOBJECT, str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit title",
                        "view":         lv,
                        "cb":           self.DHEditWarning,
                        "cBox":         {"name":    "Category",
                                        "column":   self.COLUMN_CATEGORY_ITER,
                                        "column_view":   self.COLUMN_CATEGORY_TEXT,
                                        "cBox_view":self.COMBO_COLUMN_VIEW,
                                        "cBox_data":self.COMBO_COLUMN_DATA,
                                        "model":    self.combo_model_warning,
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

    def fill(self, item):

        self.item = item
        self.model.clear()
        if item:
            for data in item.warnings:
                iter = self.combo_model_warning.get_iter_first()
                while iter:
                    if data.category == self.combo_model_warning.get_value(iter, self.COMBO_COLUMN_DATA):
                        category = self.combo_model_warning.get_value(iter, self.COMBO_COLUMN_VIEW )
                        break
                    iter = self.combo_model_warning.iter_next(iter)
                if iter == None: 
                    logger.error("Unexpected category XCCDF_WARNING.")
                    category = "Uknown"

                self.model.append([category, iter,data.text.lang, data.text.text, data])


class EditStatus(commands.DHEditItems,Edit_abs):

    COLUMN_STATUS_TEXT= 0
    COLUMN_STATUS_ITER = 1
    COLUMN_DATE = 2
    COLUMN_OBJECT = 3
    
    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:general:lv_status")
        model = gtk.ListStore(str, gobject.TYPE_PYOBJECT, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit title",
                        "view":         lv,
                        "cb":           self.DHEditStatus,
                        "cBox":         {"name":    "Status",
                                        "column":   self.COLUMN_STATUS_ITER,
                                        "column_view":   self.COLUMN_STATUS_TEXT,
                                        "cBox_view":self.COMBO_COLUMN_VIEW,
                                        "cBox_data":self.COMBO_COLUMN_DATA,
                                        "model":    self.combo_model_status,
                                        "empty":    False, 
                                        "unique":   False},
                        "textEntry":    {"name":    "Date",
                                        "column":   self.COLUMN_DATE,
                                        "empty":    False, 
                                        "unique":   False,
                                        "control_fce": self.controlDate}

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
        
    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.statuses:
                iter = self.combo_model_status.get_iter_first()
                while iter:
                    if data.status == self.combo_model_status.get_value(iter, self.COMBO_COLUMN_DATA):
                        status = self.combo_model_status.get_value(iter, self.COMBO_COLUMN_VIEW )
                        break
                    iter = self.combo_model_status.iter_next(iter)
                if iter == None: 
                    logger.error("Unexpected category XCCDF_WARNING.")
                    status = "Uknown"

                self.model.append([status, iter,datetime.date.fromtimestamp(data.date), data])

class EditIdent(commands.DHEditItems,Edit_abs):

    COLUMN_ID = 0
    COLUMN_SYSTEM = 1
    COLUMN_OBJECTS = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:dependencies:lv_ident")
        self.box_ident = builder.get_object("edit:dependencies:box_ident")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit Question",
                        "view":         lv,
                        "cb":           self.DHEditIdent,
                        "textEntry":    {"name":    "ID",
                                        "column":   self.COLUMN_ID,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "System",
                                        "column":   self.COLUMN_SYSTEM,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:dependencies:btn_ident_add")
        btn_edit = builder.get_object("edit:dependencies:btn_ident_edit")
        btn_del = builder.get_object("edit:dependencies:btn_ident_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("ID",self.COLUMN_ID)
        self.addColumn("System",self.COLUMN_SYSTEM)

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            self.item = item.to_rule()
            for data in self.item.idents:
                self.model.append([data.id, data.system, data])
                
    def set_sensitive(self, sensitive):
        self.box_ident.set_sensitive(sensitive)

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

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.question:
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

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.rationale:
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
                                        "unique":   False,
                                        "init_data": ""}
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:dependencies:btn_platform_add")
        btn_edit = builder.get_object("edit:dependencies:btn_platform_edit")
        btn_del = builder.get_object("edit:dependencies:btn_platform_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("Platform CPE",self.COLUMN_TEXT)

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.platforms:
                self.model.append([data, data])

#======================================= EDIT VALUES ==========================================

class EditValues(commands.DHEditItems, Edit_abs, EventObject):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_TYPE_ITER = 2
    COLUMN_TYPE_TEXT = 3
    COLUMN_OBJECT = 4
    COLUMN_CHECK = 5
    COLUMN_CHECK_EXPORT = 6
    
    def __init__(self, core, builder):
        
        self.id = "gui:btn:menu:edit:values"
        self.builder = builder
        self.core = core
        self.selector_empty = None
        
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(self.id, "item_changed")
        
        self.add_receiver("gui:btn:menu:edit:values", "item_changed", self.__update)
        
        self.model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, str, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)
        lv = self.builder.get_object("edit:values:tv_values")
        lv.set_model(self.model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Value",
                        "view":         lv,
                        "cb":           self.DHEditValue,
                        "textEntry":    {"name":    "ID",
                                        "column":   self.COLUMN_ID,
                                        "empty":    False, 
                                        "unique":   False},
                        "cBox":         {"name":    "Type",
                                        "column":   self.COLUMN_TYPE_ITER,
                                        "column_view":   self.COLUMN_TYPE_TEXT,
                                        "cBox_view":self.COMBO_COLUMN_VIEW,
                                        "cBox_data":self.COMBO_COLUMN_DATA,
                                        "model":    self.combo_model_type,
                                        "empty":    False, 
                                        "unique":   False,
                                        "init_data": ""}
                        }

        Edit_abs.__init__(self, core, lv, values)
        self.selection.connect("changed", self.__cb_item_changed, lv)
        
        #edit data of values
        self.edit_values_title = EditValueTitle(self.core, self.builder)
        self.edit_values_description = EditValueDescription(self.core, self.builder)
        self.edit_values_question = EditValueQuestion(self.core, self.builder)
        self.edit_values_value = EditValueValue(self.core, self.builder)
        
        self.lbl_type = self.builder.get_object("edit:values:lbl_type")
        
        self.combo_operator = self.builder.get_object("edit:values:combo_operator")
        cell = gtk.CellRendererText()
        self.combo_operator.pack_start(cell, True)
        self.combo_operator.add_attribute(cell, 'text', self.COMBO_COLUMN_VIEW)  
        self.combo_operator.connect( "changed", self.cb_combo_value_operator)
        self.combo_operator.set_model(self.combo_model_operator_number)
        
        self.lbl_match = self.builder.get_object("edit:values:lbl_match")
        self.lbl_upper_bound = self.builder.get_object("edit:values:lbl_upper_bound")
        self.lbl_lower_bound = self.builder.get_object("edit:values:lbl_lower_bound")
        self.text_match = self.builder.get_object("edit:values:text_match")
        self.text_upper_bound = self.builder.get_object("edit:values:text_upper_bound")
        self.text_lower_bound = self.builder.get_object("edit:values:text_lower_bound")
        self.text_upper_bound.connect("focus-out-event", self.cb_control_bound, "upper")
        self.text_lower_bound.connect("focus-out-event", self.cb_control_bound, "lower")
        self.text_match.connect("focus-out-event", self.cb_match)
        
        self.chBox_interactive = self.builder.get_object("edit:values:chBox_interactive")
        self.chBox_interactive.connect( "toggled",self.cb_combo_value_interactive)
        
        self.sw_main = self.builder.get_object("edit:values:sw_main")
        self.value_nbook = self.builder.get_object("edit:values:notebook")
        btn_value_add = self.builder.get_object("edit:values:btn_add")
        btn_value_remove = self.builder.get_object("edit:values:btn_remove")
        
        btn_value_add.connect("clicked", self.cb_add_row)
        btn_value_remove.connect("clicked", self.cb_del_row)
        
        self.addColumn("ID",self.COLUMN_ID)
        self.addColumn("Title",self.COLUMN_TITLE)
        
    def fill(self, item):
        self.model.clear()
        self.emit("item_changed")
        if item:
            self.item = item.to_rule() 
            for check in self.item.checks:
                for export in check.exports:
                    value = item.get_benchmark().item(export.value)
                    #value = self.core.lib["policy_model"].benchmark.item(export.value)
                    value = value.to_value()
                    #lang = self.core.lib["policy_model"].benchmark.lang
                    lang = self.core.selected_lang
                    title_lang = ""
                    
                    for title in value.title: 
                        if title.lang == lang:
                            title_lang = title.text
                            break
                        title_lang = title.text
                    
                    iter = self.combo_model_type.get_iter_first()
                    
                    type = None
                    while iter:
                        if value.type == self.combo_model_type.get_value(iter, self.COMBO_COLUMN_DATA):
                            type = self.combo_model_type.get_value(iter, self.COMBO_COLUMN_VIEW )
                            break
                        iter = self.combo_model_type.iter_next(iter)
                    self.model.append([value.id, title_lang, iter, type, value, check, export])
        
    def __cd_value_remove(self, widget):
        pass
    
    def set_sensitive(self, sensitive):
        self.sw_main.set_sensitive(sensitive)
        
    def __cb_item_changed(self, widget, treeView):
        self.emit("item_changed")
        treeView.columns_autosize()
    
    def __update(self):
        self.combo_operator.handler_block_by_func(self.cb_combo_value_operator)
        self.chBox_interactive.handler_block_by_func(self.cb_combo_value_interactive)
        (model,iter) = self.selection.get_selected()
        if iter:
            self.value_nbook.set_sensitive(True)
            value = model.get_value(iter, self.COLUMN_OBJECT)
            self.value_akt = value
            self.edit_values_title.fill(value)
            self.edit_values_description.fill(value)
            self.edit_values_question.fill(value)
            self.edit_values_value.fill(value)
            
            # if exist instance without selector take bound and match from this instance
            self.selector_empty = None
            for ins in value.instances:
                if ins.selector == "" or ins.selector == None:
                    self.selector_empty = ins
                    break

            #show bound and match
            self.text_lower_bound.set_sensitive(True)
            self.text_upper_bound.set_sensitive(True)
            self.text_match.set_sensitive(True)
            self.lbl_lower_bound.set_sensitive(True)
            self.lbl_upper_bound.set_sensitive(True)
            self.lbl_match.set_sensitive(True)
            self.text_lower_bound.set_text("")
            self.text_upper_bound.set_text("")
            self.text_match.set_text("")
            
            if value.get_type()  == openscap.OSCAP.XCCDF_TYPE_NUMBER:
                self.lbl_type.set_text("Number")
                self.combo_operator.set_model(self.combo_model_operator_number)
                self.set_active_comboBox(self.combo_operator, value.oper, 0)
                if self.selector_empty:
                    if str(self.selector_empty.get_lower_bound()) != "nan":
                        self.text_lower_bound.set_text(str(self.selector_empty.get_lower_bound()))
                    if str(self.selector_empty.get_upper_bound()) != "nan":
                        self.text_upper_bound.set_text(str(self.selector_empty.get_upper_bound()))
                    if self.selector_empty.get_match() != None:
                        self.text_match.set_text(self.selector_empty.get_match())

            elif value.get_type()  == openscap.OSCAP.XCCDF_TYPE_STRING:
                self.lbl_type.set_text("String")
                self.combo_operator.set_model(self.combo_model_operator_string)
                self.set_active_comboBox(self.combo_operator, value.oper, 0)
                if self.selector_empty:
                    if self.selector_empty.get_match() != None:
                        self.text_match.set_text(self.selector_empty.get_match())
                self.text_lower_bound.set_sensitive(False)
                self.text_upper_bound.set_sensitive(False)
                self.lbl_lower_bound.set_sensitive(False)
                self.lbl_upper_bound.set_sensitive(False)
                
            elif value.get_type()  == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
                self.lbl_type.set_text("Boolean")
                self.combo_operator.set_model(self.combo_model_operator_bool)
                self.set_active_comboBox(self.combo_operator, value.oper, 0)
                self.text_lower_bound.set_sensitive(False)
                self.text_upper_bound.set_sensitive(False)
                self.text_match.set_sensitive(False)
                self.lbl_lower_bound.set_sensitive(False)
                self.lbl_upper_bound.set_sensitive(False)
                self.lbl_match.set_sensitive(False)
        else:
            self.value_nbook.set_sensitive(False)
            self.edit_values_title.fill(None)
            self.edit_values_description.fill(None)
            self.edit_values_question.fill(None)
            self.edit_values_value.fill(None)
            self.combo_operator.set_active(-1)
            self.chBox_interactive.set_active(False)
            self.lbl_type.set_text("")
            self.text_lower_bound.set_text("")
            self.text_upper_bound.set_text("")
            self.text_match.set_text("")
            
        self.combo_operator.handler_unblock_by_func(self.cb_combo_value_operator)
        self.chBox_interactive.handler_unblock_by_func(self.cb_combo_value_interactive)

    def cb_combo_value_operator(self,widget):
        COLUMN_DATA = 0
        (model,iter) = self.selection.get_selected()
        if iter:
            value = model.get_value(iter, self.COLUMN_OBJECT)
            active = widget.get_active()
            if active > 0:
                combo_model = widget.get_model()
                self.DHEditValueOper(value, combo_model[active][COLUMN_DATA])
        else:
            logger.error("Error: Not select value.")
            
    def cb_combo_value_interactive(self,widget):
        COLUMN_DATA = 0
        (model,iter) = self.selection.get_selected()
        if iter:
            self.value_nbook.set_sensitive(True)
            value = model.get_value(iter, self.COLUMN_OBJECT)
            self.DHChBoxValueInteractive(value, widget.get_active())
        else:
            logger.error("Error: Not select value.")

    def cb_match(self, widget, event):

        vys = self.DHEditBoundMatch(self.value_akt, None, None, widget.get_text())
        if not vys:
            logger.error("Not changed value match")
        else:
            self.emit("item_changed")
            
    def cb_control_bound(self, widget, event, type):
        
        if widget.get_text() == "":
            data = "nan"
        else:
            data = widget.get_text()
            
        try:
            data = float(data)
        except:
            self.dialogInfo("Invalid number in %s bound." % (type))
            if self.selector_empty:
                if type == "lower":
                    if str(self.selector_empty.get_lower_bound()) != "nan":
                        widget.set_text(str(self.selector_empty.get_lower_bound()))
                else:
                    if str(self.selector_empty.get_upper_bound()) != "nan":
                        widget.set_text(str(self.selector_empty.get_upper_bound()))
            else:
                widget.set_text("")
            return

        upper = self.text_upper_bound.get_text()
        lower = self.text_lower_bound.get_text()

        if upper != "" and upper != "nan" and lower != "" and lower != "nan":
            if lower >= upper:
                self.dialogInfo("Upper bound must be greater then lower bound.")
                if self.selector_empty:
                    if type == "lower":
                        if str(self.selector_empty.get_lower_bound()) != "nan":
                            widget.set_text(str(self.selector_empty.get_lower_bound()))
                    else:
                        if str(self.selector_empty.get_upper_bound()) != "nan":
                            widget.set_text(str(self.selector_empty.get_upper_bound()))
                else:
                    widget.set_text("")
                return
        #add bound
        if type == "upper":
            vys = self.DHEditBoundMatch(self.value_akt, data, None, None)
        else:
            vys = self.DHEditBoundMatch(self.value_akt, None, data, None)
        
        if not vys:
            logger.error("Not changed value bound.")
        else:
            self.emit("item_changed")
            
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
                
class EditValueValue(commands.DHEditItems, Edit_abs):

    COLUMN_SELECTOR = 0
    COLUMN_VALUE = 1
    COLUMN_MODEL_CHOICES = 2
    COLUMN_OBJECT = 3

    def __init__(self, core, builder):
        
        #set listView and model
        lv = builder.get_object("edit:values:lv_value")
        model = gtk.ListStore(str, str, gtk.TreeModel, gobject.TYPE_PYOBJECT)
        self.model = model
        lv.set_model(model)
        self.selection = lv.get_selection()

        #information for new/edit dialog

        Edit_abs.__init__(self, core, lv, None)
        btn_add = builder.get_object("edit:values:btn_value_add")
        btn_edit = builder.get_object("edit:values:btn_value_edit")
        btn_del = builder.get_object("edit:values:btn_value_del")

        # set callBack to btn
        btn_add.connect("clicked", self.__cb_add)
        btn_edit.connect("clicked", self.__cb_edit_row)
        btn_del.connect("clicked", self.__cb_del_row)

        self.addColumn("Selector",self.COLUMN_SELECTOR)
        self.addColumn("Selector",self.COLUMN_VALUE)
        
        #cellcombo = gtk.CellRendererCombo()
        #cellcombo.set_property("editable", True)
        #cellcombo.set_property("text-column", 1)
        #column = gtk.TreeViewColumn("Choice", cellcombo, text=self.COLUMN_VALUE, model=self.COLUMN_MODEL_CHOICES)
        #column.set_resizable(True)
        #lv.append_column(column)

    def fill(self, value):
        self.item = value
        self.model.clear()
        selected = ""
        if value:
            instanses = value.get_instances()
            for instance in instanses:
                
                model_choices = gtk.ListStore(str,str)
                choices = instance.choices
                for choice in choices:
                    iter_choice = model_choices.append(["",choice])
                
                #read value
                if instance.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
                    value = str(instance.get_value_boolean())
                elif instance.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
                    value = str(instance.value)
                elif instance.type == openscap.OSCAP.XCCDF_TYPE_STRING:
                    value = instance.get_value_string()
                    
                self.model.append([instance.selector, value, model_choices, instance])
                
    def __cb_add(self, widget):
        EditValueDialogWindow(self.item, self.core, self.lv, self.DHEditValueInstance, False)
    
    def __cb_edit_row(self, widget):
        EditValueDialogWindow(self.item, self.core, self.lv, self.DHEditValueInstance, True)
    
    def __cb_del_row(self, widget):
        iter = self.dialogEditDel()
        if iter != None:
            object = self.model.get_value(iter, self.COLUMN_OBJECT)
            if object.selector == "" or object.selector == None:
                if self.item.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
                    if  (not (object.get_match() == None or object.get_match() == '') or str(object.get_lower_bound()) != "nan" or str(object.get_upper_bound()) != "nan"):
                        self.dialogInfo("Can't del velue instnace, because is set Match or Bound in general.")
                        return
                if self.item.type == openscap.OSCAP.XCCDF_TYPE_STRING:
                    if not (object.get_match() == None or object.get_match() == ''):
                        self.dialogInfo("Can't del velue instnace, because is set Match in general.")
                        return
            self.DHEditValueInstanceDel(self.item, self.model, iter)
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
                    self.model.append([re.sub("[\t ]+" , " ", object.text.text).strip(), object])
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
    
    def __init__(self, core, builder):
    
        # set  models
        self.core = core
        self.builder = builder
        Edit_abs.__init__(self, core, None, None)
        
        #edit data of fictext
        self.entry_reference = self.builder.get_object("edit:operations:fixtext:entry_reference1")
        self.entry_reference.connect("focus-out-event",self.cb_entry_fixtext_reference)
        
        self.combo_strategy = self.builder.get_object("edit:operations:fixtext:combo_strategy1")
        cell = gtk.CellRendererText()
        self.combo_strategy.pack_start(cell, True)
        self.combo_strategy.add_attribute(cell, 'text',self.COMBO_COLUMN_VIEW)  
        self.combo_strategy.set_model(self.combo_model_strategy)
        self.combo_strategy.connect( "changed", self.cb_combo_fixtext_strategy)
        
        self.combo_complexity = self.builder.get_object("edit:operations:fixtext:combo_complexity1")
        cell = gtk.CellRendererText()
        self.combo_complexity.pack_start(cell, True)
        self.combo_complexity.add_attribute(cell, 'text', self.COMBO_COLUMN_VIEW)  
        self.combo_complexity.set_model(self.combo_model_level)
        self.combo_complexity.connect( "changed", self.cb_combo_fixtext_complexity)
    
        self.combo_disruption = self.builder.get_object("edit:operations:fixtext:combo_disruption1")
        cell = gtk.CellRendererText()
        self.combo_disruption.pack_start(cell, True)
        self.combo_disruption.add_attribute(cell, 'text', self.COMBO_COLUMN_VIEW)  
        self.combo_disruption.set_model(self.combo_model_level)
        self.combo_disruption.connect( "changed", self.cb_combo_fixtext_disruption)
    
        self.chbox_reboot = self.builder.get_object("edit:operations:fixtext:chbox_reboot1")
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
            self.set_active_comboBox(self.combo_strategy, fixtext.strategy, self.COMBO_COLUMN_DATA)
            self.set_active_comboBox(self.combo_complexity, fixtext.complexity, self.COMBO_COLUMN_DATA)
            self.set_active_comboBox(self.combo_disruption, fixtext.disruption, self.COMBO_COLUMN_DATA)
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
        self.set_model_to_comboBox(self.combo_strategy,self.combo_model_strategy, self.COMBO_COLUMN_VIEW)
        self.combo_strategy.connect( "changed", self.cb_combo_fix_strategy)
        
        self.combo_complexity = self.builder.get_object("edit:operations:fix:combo_complexity")
        self.set_model_to_comboBox(self.combo_complexity, self.combo_model_level, self.COMBO_COLUMN_VIEW)
        self.combo_complexity.connect( "changed", self.cb_combo_fix_complexity)
    
        self.combo_disruption = self.builder.get_object("edit:operations:fix:combo_disruption")
        self.set_model_to_comboBox(self.combo_disruption, self.combo_model_level, self.COMBO_COLUMN_VIEW)
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
            self.set_active_comboBox(self.combo_strategy, fix.strategy, self.COMBO_COLUMN_DATA)
            self.set_active_comboBox(self.combo_complexity, fix.complexity, self.COMBO_COLUMN_DATA)
            self.set_active_comboBox(self.combo_disruption, fix.disruption, self.COMBO_COLUMN_DATA)
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

class EditAddProfileDialogWindow(EventObject, Edit_abs):

    def __init__(self, core, data_model, cb):
        self.core = core
        self.data_model = data_model
        self.__update = cb
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")
        self.window = builder.get_object("dialog:profile_add")

        builder.get_object("profile_add:btn_ok").connect("clicked", self.__cb_do)
        builder.get_object("profile_add:btn_cancel").connect("clicked", self.__delete_event)
        self.id = builder.get_object("profile_add:entry_id")
        self.info_box = builder.get_object("profile_add:info_box")

        self.show()

    def __cb_do(self, widget):

        if len(self.id.get_text()) == 0: 
            self.core.notify("Can't add profile with no ID !", 2, self.info_box)
            return

        values = {}
        values["id"] = self.id.get_text()
        values["abstract"] = False
        values["version"] = ""
        values["extends"] = None
        values["details"] = []
        self.data_model.add(values)
        self.core.selected_profile = self.id.get_text()
        self.core.force_reload_profiles = True
        self.window.destroy()
        self.__update(new=True)

    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()
        

class EditAddDialogWindow(EventObject, Edit_abs):
    
    CREATE_AS_CHILD = 0
    CREATE_AS_SIBLING = 1
    CREATE_AS_PARENT = 2

    
    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2
    
    def __init__(self, core, item, list_item, ref_model, cb):
        
        self.core = core
        self.item = item
        self.cb = cb
        self.view = list_item.get_TreeView()
        self.ref_model = ref_model#list_item.get_TreeView().get_model()
        self.map_filterInfo = list_item.map_filter
        
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")

        self.combo_model = gtk.ListStore(int, str, str)

        #self.combo_model.append([self.CREATE_AS_CHILD,"Child","Create the item as a child."])
        #self.combo_model.append([self.CREATE_AS_SIBLING,"Sibling","Create the item as a sibling."])
        #self.combo_model.append([self.CREATE_AS_PARENT,"Parent","Create the item as a parent."])
        
        self.window = builder.get_object("dialog:add_item")
        self.window.connect("delete-event", self.__delete_event)
        #self.window.resize(400, 150)
        
        btn_ok = builder.get_object("add_item:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("add_item:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)

        self.rb_type_group = builder.get_object("add_item:rb_type_group")
        self.rb_type_rule = builder.get_object("add_item:rb_type_rule")
        self.text_id = builder.get_object("add_item:text_id")
        self.text_lang = builder.get_object("add_item:text_lang")
        self.text_title = builder.get_object("add_item:text_title")
        self.combo_create_as = builder.get_object("add_item:combo_create_as")
            
        cell = gtk.CellRendererText()
        self.combo_create_as.set_model(self.combo_model)
        self.combo_create_as.pack_start(cell, True)
        self.combo_create_as.add_attribute(cell, 'text', self.COMBO_COLUMN_VIEW)
        self.combo_create_as.set_active(self.CREATE_AS_CHILD)
        
        struct = self.map_filterInfo[1]
        # if is active filter_model and truct is list, can be added only child
        if not struct:
            self.combo_model.append([self.CREATE_AS_CHILD,"Child","Create the item as a child."])
            self.combo_create_as.set_active(0)
            self.combo_create_as.set_sensitive(False)
            self.item = self.item.to_group()
        
        # not selected item add to root -> only child
        elif self.item == None:
            self.combo_model.append([self.CREATE_AS_CHILD,"Child","Create the item as a child."])
            self.combo_create_as.set_active(0)
            self.combo_create_as.set_sensitive(False)
        
        elif self.item.type == openscap.OSCAP.XCCDF_GROUP:
            self.combo_model.append([self.CREATE_AS_CHILD,"Child","Create the item as a child."])
            self.combo_model.append([self.CREATE_AS_SIBLING,"Sibling","Create the item as a sibling."])
            self.combo_create_as.set_active(0)
            self.item = self.item.to_group()
        
        # ir rule cen by add only as sibling
        else:
            self.combo_model.append([self.CREATE_AS_SIBLING,"Sibling","Create the item as a sibling."])
            self.combo_create_as.set_sensitive(False)
            self.combo_create_as.set_active(0)
            self.item = self.item.to_rule()
        self.show()

    def __cb_do(self, widget):
        
        item_to_add = None
        active = self.combo_create_as.get_active()
        if active < 0:
            self.dialogInfo("Set field Create as.")
            return
        create_as = self.combo_model[active][self.COMBO_COLUMN_DATA]
        
        if self.text_id.get_text() == "":
            self.dialogInfo("Id Item can't be empty.")
            return

        if self.text_lang.get_text() == "":
            self.dialogInfo("Title language can't be empty.")
            return

        if self.text_title.get_text() == "":
            self.dialogInfo("Title can't be empty.")
            return
        
        selection = self.view.get_selection()
        (model ,iter) = selection.get_selected()
        
        if self.item != None:
            
            if create_as == self.CREATE_AS_CHILD:
                item_to_add = self.item
                
            if create_as == self.CREATE_AS_SIBLING:
                item_to_add = self.item.get_parent().to_group()
                if item_to_add == None:
                    item_to_add = self.core.lib["policy_model"].benchmark
                    iter = None
                else:
                    iter = model.iter_parent(iter)
        else:
            item_to_add = self.core.lib["policy_model"].benchmark
            iter = None
        
        type = "Rule: "
        group = False
        icon = gtk.STOCK_DND
        if self.rb_type_group.get_active():
            type = "Group: "
            group = True
            icon = gtk.STOCK_DND_MULTIPLE
            
        vys = self.cb(item_to_add, group, [self.text_id.get_text(),"EN", self.text_title.get_text()] )
        if vys:
            iter_new_ref = None
            
            # if actual model is filter model - must change ref model too
            if self.ref_model != model:
                
                map_filter = self.map_filterInfo[0]
                #if item none add to root or iter == None
                if self.item != None and iter != None:
                    iter_filter = map_filter[model.get_path(iter)]
                    iter_ref = self.ref_model.get_iter(iter_filter)
                else:
                    iter_ref = None

                iter_new_ref = self.ref_model.append(iter_ref,[self.text_id.get_text(), self.text_title.get_text(), 
                                            icon, type+self.text_title.get_text(), None, False, False])

            iter_new = model.append(iter, [self.text_id.get_text(), self.text_title.get_text(), icon, 
                                            type+self.text_title.get_text(), None, False, False])
            
            #If actual model si filter model add information to map_filter 
            if iter_new_ref:
                map_filter.update({model.get_path(iter_new):self.ref_model.get_path(iter_new_ref)})
                
            self.view.expand_to_path(model.get_path(iter_new))
            selection.select_iter(iter_new)
            self.window.destroy()
        else:
            self.dialogInfo("Id item exist.")
            return
            
    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()
        
class EditDialogWindow(EventObject):
    
    def __init__(self, item, core, values, new=True):
        
        self.core = core
        self.new = new
        self.values = values
        self.item = item
        self.init_data = None
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")
        
        self.window = builder.get_object("dialog:edit_item")
        self.window.connect("delete-event", self.__delete_event)
        self.window.resize(400, 150)
        
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
            self.window.resize(650, 400)
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

        self.show()
        
    def __cb_do(self, widget):
        
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
            
            # if exist control function for data
            if "control_fce" in self.values["textEntry"]:
                if self.values["textEntry"]["control_fce"](text_textEntry) == False:
                    return
                   
                    
        if "textView" in self.values:
            buff = self.textView.get_buffer()
            iter_start = buff.get_start_iter()
            iter_end = buff.get_end_iter()
            text_textView = buff.get_text(iter_start, iter_end, True)
            
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

            if "init_data" in self.values["textView"]:
                self.init_data = text_textView
                
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
                    
            if "init_data" in self.values["cBox"]:
                self.init_data = data_selected
                
        # new row and unique => add new row
        if dest_path == None:
            iter = self.model.append()
            self.values["cb"](self.item, self.model, iter, None, self.init_data, False)
            self.selection.select_path(self.model.get_path(iter))

        # row exist delete row
        else:
            iter = self.model.get_iter(dest_path)
            if self.iter and dest_path != self.model.get_path(self.iter):
                self.values["cb"](self.item, self.model, self.iter, None, None, True)

        # if insert data are correct, put them to the model
        if "textEntry" in self.values:
            self.model.set_value(iter,self.values["textEntry"]["column"], text_textEntry)
            
            if "control_fce" in self.values["textEntry"]:
                text_textEntry = self.values["textEntry"]["control_fce"](text_textEntry)
            self.values["cb"](self.item, self.model, iter, self.values["textEntry"]["column"], text_textEntry, False)
                    
        if "textView" in self.values:
            self.values["cb"](self.item, self.model, iter, self.values["textView"]["column"], text_textView, False)
            self.model.set_value(iter,self.values["textView"]["column"], text_textView)

        if "cBox" in self.values:
            self.model.set_value(iter,self.values["cBox"]["column"], iter_selected)
            self.model.set_value(iter,self.values["cBox"]["column_view"], view_selected)
            self.values["cb"](self.item, self.model, iter, self.values["cBox"]["column"], data_selected, False)
            
        self.window.destroy()

    def __delete_event(self, widget, event=None):
        self.window.destroy()

    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()
        
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

class EditSelectIdDialogWindow():
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_SELECTED = 2
    
    def __init__(self, item, core, model_conflict, model_item, cb):
        self.core = core
        self.item = item
        self.cb = cb
        self.model_conflict = model_conflict
        self.model_item = model_item
        
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")

        self.window = builder.get_object("dialog:add_id")
        self.window.connect("delete-event", self.__delete_event)
        self.window.resize(800, 600)
        
        btn_ok = builder.get_object("add_id:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("add_id:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)

        btn_add = builder.get_object("add_id:btn_add")
        btn_add.connect("clicked", self.cb_btn_add)
        btn_remove = builder.get_object("add_id:btn_remove")
        btn_remove.connect("clicked", self.__cb_del_row)
        
        self.btn_search = builder.get_object("add_id:btn_search")
        self.btn_search.connect("clicked",self.__cb_search)
        self.btn_search_reset = builder.get_object("add_id:btn_search_reset")
        self.btn_search_reset.connect("clicked",self.__cb_search_reset)
        
        self.text_search_id = builder.get_object("add_id:text_search_id")
        self.text_search_title = builder.get_object("add_id:text_search_title")
        
        #treeView for search item for select to add
        self.model_search = gtk.TreeStore(str, str, bool)
        self.tw_search = builder.get_object("add_id:tw_search")
        
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ID Item", cell, text=self.COLUMN_ID)
        column.set_resizable(True)
        self.tw_search.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", cell, text=self.COLUMN_TITLE)
        column.set_expand(True)
        column.set_resizable(True)
        self.tw_search.append_column(column)
        
        self.tw_search.set_model(self.model_search)
        
        #treeView for item, which will be add
        self.model_to_add = gtk.ListStore(str, str)
        self.tw_add = builder.get_object("add_id:tw_add")
        
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ID Item", cell, text=self.COLUMN_ID)
        column.set_resizable(True)
        self.tw_add.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", cell, text=self.COLUMN_TITLE)
        column.set_expand(True)
        column.set_resizable(True)
        self.tw_add.append_column(column)

        self.tw_add.set_model(self.model_to_add)
        
        menu = gtk.Menu()
        menu_item = gtk.MenuItem("Remove from add")
        menu_item.show()
        menu.append(menu_item)
        menu_item.connect("activate", self.__cb_del_row)
        self.tw_add.connect ("button_press_event",self.cb_popupMenu_to_add, menu)
        self.tw_add.connect("key-press-event", self.__cb_del_row1,)

        menu_search = gtk.Menu()
        menu_item = gtk.MenuItem("Copy to add")
        menu_item.show()
        menu_search.append(menu_item)
        menu_item.connect("activate", self.cb_btn_add)
        self.tw_search.connect ("button_press_event",self.cb_popupMenu_to_add, menu_search)

        
        self.model_search.clear()
        self.copy_model(model_item, model_item.get_iter_first(), self.model_search, None)
        self.show()

    def __cb_do(self, widget):
        
        iter_add =  self.model_to_add.get_iter_first()
        while iter_add:
            #add row, which not added before
            exist = False
            iter = self.model_conflict.get_iter_first()
            id_add = self.model_to_add.get_value(iter_add,self.COLUMN_ID)
            while iter:
                if id_add == self.model_conflict.get_value(iter,self.COLUMN_ID):
                    exist = True
                iter = self.model_conflict.iter_next(iter)
            if not exist:
                self.cb(self.item, id_add, True)
                self.model_conflict.append([id_add])
            iter_add = self.model_to_add.iter_next(iter_add)
        self.window.destroy()
            
    def __cb_del_row1(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Delete":
            selection = self.tw_add.get_selection( )
            if selection != None: 
                (model, iter) = selection.get_selected( )
                if  iter != None:
                    model.remove(iter)

                        
    def __cb_del_row(self, widget):
        selection = self.tw_add.get_selection()
        (model, iter) = selection.get_selected()
        if iter != None:
            model.remove(iter)
    
    def cb_popupMenu_to_add (self, treeview, event, menu):
        if event.button == 3:
            time = event.time
            menu.popup(None,None,None,event.button,event.time)
            
    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()
            
    def __cb_toggled(self, cell, path ):
        
        self.model_search[path][self.COLUMN_SELECTED] = not self.model_search[path][self.COLUMN_SELECTED]
        id_item = self.model_search[path][self.COLUMN_ID]
        if not self.model_search[path][self.COLUMN_SELECTED]:
            # remve from model to add
            iter = self.model_to_add.get_iter_first()
            while iter:
                if self.model_to_add.get_value(iter,self.COLUMN_ID) == id_item:
                    self.model_to_add.remove(iter)
                    break
                iter = self.model_to_add.iter_next(iter)
        else:
            # move from serch model to model for add, if not there
            iter = self.model_to_add.get_iter_first()
            while iter:
                if self.model_to_add.get_value(iter,self.COLUMN_ID) == id_item:
                    return
                iter = self.model_to_add.iter_next(iter)
            self.model_to_add.append([id_item,self.model_search[path][self.COLUMN_TITLE]])
        # change state check box

    def cb_btn_add(self, widget):
        selection = self.tw_search.get_selection( )
        if selection != None: 
            (model, iter_add) = selection.get_selected( )
            if  iter_add != None:
                id_item = self.model_search.get_value(iter_add, self.COLUMN_ID)
                iter = self.model_to_add.get_iter_first()
                while iter:
                    if self.model_to_add.get_value(iter,self.COLUMN_ID) == id_item:
                        return
                    iter = self.model_to_add.iter_next(iter)
                self.model_to_add.append([id_item,self.model_search.get_value(iter_add, self.COLUMN_TITLE)])
            
    def copy_model(self, model_item, iter, model_search, iter_parent):
        """
        copy_model to search model
        """
        while iter:
            row = []
            row.append(model_item.get_value(iter,0))
            row.append(model_item.get_value(iter,3))
            row.append(False)
            iter_self = model_search.append(iter_parent, row)
            self.copy_model(model_item, model_item.iter_children(iter), model_search, iter_self)
            iter = model_item.iter_next(iter)
        return
    
    def __cb_search(self, widget):
        self.model_search.clear()
        self.search(self.model_item, self.model_item.get_iter_first(), self.model_search, 
                                self.text_search_id.get_text(), self.text_search_title.get_text())

    def __cb_search_reset(self, widget):
        self.model_search.clear()
        self.copy_model(self.model_item, self.model_item.get_iter_first(), self.model_search, None)
                                
    def search(self, model_item, iter, model_search, id, title):
        """ 
        Filter data to list
        """
        while iter:
            if self.match_fiter(id, title,  model_item, iter):
                row = []
                row.append(model_item.get_value(iter,0))
                row.append(model_item.get_value(iter,3))
                row.append(False)
                iter_to = model_search.append(None, row)
            self.search(model_item, model_item.iter_children(iter), model_search, id, title)
            iter = model_item.iter_next(iter)
    
    
    def match_fiter(self, id, title,  model_item, iter):
        try:
            pattern = re.compile(id,re.IGNORECASE)
            res_id = pattern.search(model_item.get_value(iter,0)) 
            pattern = re.compile(title,re.IGNORECASE)
            res_title = pattern.search(model_item.get_value(iter,3)) 
            
            if res_id == None or res_title == None:
                return False
            return True
        except Exception, e:
            #self.core.notify("Can't filter items: %s" % (e,), 3)
            logger.error("Can't filter items: %s" % (e,))
            return False
    


class EditValueDialogWindow(abstract.Window, Edit_abs):
    
    COLUMN_SELECTOR = 0
    COLUMN_VALUE = 1
    COLUMN_MODEL_CHOICES = 2
    COLUMN_OBJECT = 3
    
    def __init__(self, value, core, tw_instance, cb, edit=False):
        self.core = core
        self.item = value
        self.cb = cb
        self.edit = edit
        self.tw_instance = tw_instance
        self.model_combo_choices = gtk.ListStore(str, str)
        
        if edit:
            selection = tw_instance.get_selection()
            (self.model, self.iter) = selection.get_selected()
            if self.iter:
                self.instance= self.model.get_value(self.iter, self.COLUMN_OBJECT)
                #self.model_combo_choices = self.model.get_value(iter, self.COLUMN_MODEL_CHOICES)
            else:
                self.dialogInfo("Choose row which you want Edit.")
                return
        else:
            self.model = tw_instance.get_model()
        self.type = value.type

        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")

        self.window = builder.get_object("dialog:edit_value")
        self.window.connect("delete-event", self.__delete_event)
        self.window.resize(800, 600)
        
        self.lbl_type = builder.get_object("edit_value:lbl_type")
        self.text_selector = builder.get_object("edit_value:text_selector")
        self.text_value = builder.get_object("edit_value:text_value")
        
        self.lbl_match = builder.get_object("edit_value:lbl_match")
        self.lbl_value = builder.get_object("edit_value:lbl_value")
        self.lbl_uper_bound = builder.get_object("edit_value:lbl_uper_bound")
        self.lbl_lower_bound = builder.get_object("edit_value:lbl_lower_bound")
        self.lbl_mustMatch = builder.get_object("edit_value:lbl_mustMatch")
        self.box_choices = builder.get_object("edit_value:box_choices")
        
        self.text_match = builder.get_object("edit_value:text_match")
        self.combo_value = builder.get_object("edit_value:combo_value")
        self.text_uper_bound = builder.get_object("edit_value:text_uper_bound")
        self.text_lower_bound = builder.get_object("edit_value:text_lower_bound")
        #self.text_uper_bound.connect("focus-out-event", self.cb_control_bound, "upper")
        #self.text_lower_bound.connect("focus-out-event", self.cb_control_bound, "lower")
        
        self.lbl_default = builder.get_object("edit_value:lbl_default")
        self.combo_default = builder.get_object("edit_value:combo_default")
        cell = gtk.CellRendererText()
        self.combo_default.pack_start(cell, True)
        self.combo_default.add_attribute(cell, 'text', 1)  
        self.combo_default.connect( "changed", self.cb_combo_default)
        self.combo_default.set_model(self.model_combo_choices)

        self.comboEntry_default = builder.get_object("edit_value:comboEntry_default")
        self.comboEntry_default.set_text_column(1)
        self.comboEntry_default.connect( "changed", self.cb_combo_default)
        self.comboEntry_default.set_model(self.model_combo_choices)
        
        self.chBox_mustMatch = builder.get_object("edit_value:chBox_mustMatch")
        self.chBox_mustMatch.connect("toggled", self.cb_mustMatch)
        self.tv_choices = builder.get_object("edit_value:tv_choices")

        btn_ok = builder.get_object("edit_value:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("edit_value:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)


        if self.type  == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            self.lbl_type.set_text("Number")
            self.combo_value.hide()
            if edit:
                if self.instance.get_value_number() != float("nan"):
                    self.text_value.set_text(str(self.instance.get_value_number()))
            #if edit:
                #self.text_uper_bound.set_text(str(self.instance.upper_bound))
                #self.text_lower_bound.set_text(str(self.instance.lower_bound))
                #for choice in self.instance.choices:
                    #self.model_combo_choices.append(["", choice])
            ## hide information for others type
            #self.lbl_match.set_sensitive(False)
            #self.text_match.set_sensitive(False)

        elif self.type  == openscap.OSCAP.XCCDF_TYPE_STRING:
            self.lbl_type.set_text("String")
            self.combo_value.hide()
            if edit:
                if self.instance.value:
                    self.text_value.set_text(self.instance.get_value_string())
            #if edit:
                #if self.instance.match:
                    #self.text_match.set_text(self.instance.match)
                #for choice in self.instance.choices:
                    #self.model_combo_choices.append(["", choice])

            # hide information for others type
            #self.text_uper_bound.set_sensitive(False)
            #self.lbl_uper_bound.set_sensitive(False)
            #self.text_lower_bound.set_sensitive(False)
            #self.lbl_lower_bound.set_sensitive(False)

            
        elif self.type  == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
            self.lbl_type.set_text("Boolean")
            
            self.text_value.hide()
            self.model_bool = gtk.ListStore(bool, str)
            self.model_bool.append([True, "True"])
            self.model_bool.append([False, "False"])
            
            cell = gtk.CellRendererText()
            self.combo_value.pack_start(cell, True)
            self.combo_value.add_attribute(cell, 'text', 1)  
            self.combo_value.set_model(self.model_bool)
            
            if self.edit:
                if self.instance.get_value_boolean() == True:
                    self.combo_value.set_active(0)
                else:
                    self.combo_value.set_active(1)
            else:
                self.combo_value.set_active(1)
                    
            #self.model_combo_choices.append(["", "True"])
            #self.model_combo_choices.append(["", "False"])

            ## hide information for others type
            #self.text_uper_bound.set_sensitive(False)
            #self.lbl_uper_bound.set_sensitive(False)
            #self.text_lower_bound.set_sensitive(False)
            #self.lbl_lower_bound.set_sensitive(False)
            #self.lbl_match.set_sensitive(False)
            #self.text_match.set_sensitive(False)
            #self.box_choices.hide()
            #self.chBox_mustMatch.hide()
            #self.lbl_mustMatch.hide()
            #self.window.resize(400, 200)

        #hide alll
        self.text_uper_bound.hide()
        self.lbl_uper_bound.hide()
        self.text_lower_bound.hide()
        self.lbl_lower_bound.hide()
        self.box_choices.hide()
        self.chBox_mustMatch.hide()
        self.lbl_mustMatch.hide()
        self.comboEntry_default.hide()
        self.combo_default.hide()
        self.lbl_default.hide()
        self.window.resize(300, 200)
            
        ## choices
        #EditValueChoice (core, self.model_combo_choices, self.tv_choices, self.window)
       
        if edit  and self.instance.selector:
            self.text_selector.set_text(self.instance.selector)

            #self.chBox_mustMatch.set_active(self.instance.must_match)
            #if self.instance.must_match:
                #self.comboEntry_default.hide()
                #self.combo_default.show()
            #else:
                #self.comboEntry_default.show()
                #self.combo_default.hide()
        #else:
            #self.comboEntry_default.show()
            #self.combo_default.hide()
            
            
        self.show()

    def cb_combo_default(self, widget):
        active = widget.get_active()
        if widget == self.combo_default:
            self.comboEntry_default.set_active(active)
        else:
            self.combo_default.set_active(active)

    def cb_mustMatch(self, widget):
        if widget.get_active():
            self.comboEntry_default.hide()
            self.combo_default.show()
        else:
            self.comboEntry_default.show()
            self.combo_default.hide()

    def __cb_do(self, widget):
        poc = 0
        selector_empty = None
        
        # control if selector not exist or empty
        for ins in self.item.instances:
            if ins.selector == self.text_selector.get_text():
                poc = poc + 1
            if ins.selector == "":
                selector_empty = ins
        
        if self.edit and self.instance.selector == "" and self.text_selector.get_text() != "":
            if  (not (self.instance.get_match() == None or self.instance.get_match() == '') or str(self.instance.get_lower_bound()) != "nan" or str(self.instance.get_upper_bound()) != "nan"):
                self.dialogInfo("Can't change empty selector if is set Bound or Match in Grnral. ", self.window)
                return
                
        if (poc == 1 and not self.edit) or (self.edit and poc == 1 and self.text_selector.get_text() != self.instance.selector):
            self.dialogInfo("Selector already exist. \n Change selector.", self.window)
            return
        
        # control value
        if self.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
            active = self.combo_value.get_active_iter()
            if active:
                value = self.model_bool.get_value(active, 0)
            else:
                value = None
                
        else:
            value = self.text_value.get_text()
            if not self.control_data(value, selector_empty, "value"):
                return

        
        ##control default
        #if (not self.chBox_mustMatch.get_active()) and self.comboEntry_default.get_active() == -1:
            #if not self.control_data(self.comboEntry_default.get_active_text(), "Default"):
                #return
            
        ## control choices must be at the end of control, becouse remove mark row from model
        #iter_ch = self.model_combo_choices.get_iter_first()
        #while iter_ch:
            
            ##if model has * in mark_column is it end  
            #mark = self.model_combo_choices.get_value(iter_ch, 0)
            #if mark == "*":
                ## after remove * must control finish by succead
                #self.model_combo_choices.remove(iter_ch)
                #break

            ##control data
            #data = self.model_combo_choices.get_value(iter_ch, 1)
            #if not self.control_data(data, "choices"):
                #return
            #iter_ch = self.model_combo_choices.iter_next(iter_ch)

        #all control ready
        selector = self.text_selector.get_text()
        upper = None
        lower = None
        match = None
        mustMuch = None
        

        
        #if self.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            #upper = float(self.text_uper_bound.get_text())
            #lower = float(self.text_lower_bound.get_text())
        #if self.type == openscap.OSCAP.XCCDF_TYPE_STRING:
            #match = self.text_match.get_text()

        #mustMuch = self.chBox_mustMatch.get_active()

        if not mustMuch:
            default = self.comboEntry_default.get_active_text()
        else:
            default = self.combo_default.get_active_text()

        if self.edit:
            if self.cb(self.edit, value, self.instance, self.type, selector, match, upper, lower, default, mustMuch, self.model_combo_choices):
                self.model.set_value(self.iter, self.COLUMN_SELECTOR, selector)
                self.model.set_value(self.iter, self.COLUMN_VALUE, value)
        else:
            vys = self.cb(self.edit, value, self.item, self.type, selector, match, upper, lower, default, mustMuch, self.model_combo_choices)
            if vys != -1:
                self.model.append([selector, value, None, vys])

        self.window.destroy()

    def control_data(self, data, selector_empty, text):
        """Control data about type and set parameter
            param data is string
            return False if data is incorrect
        """
        if data != "":
            if self.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
                try:
                    data = float(data)
                except Exception, e:
                    self.dialogInfo("Invalid number '%s' in %s." % (data, text), self.window)
                    return False
                
                if selector_empty:
                    low = selector_empty.lower_bound
                    upper = selector_empty.upper_bound
                else:
                    low = "nan"
                    upper = "nan"
                    
                # control low
                if low != "" and low != "nan":
                    low = float(low)
                    if data < low:
                        self.dialogInfo("Number %f can't be less then Lower bound." % (data), self.window)
                        return False
                #control upper
                if upper != "" and upper != "nan":
                    upper = float(upper)
                    if data > upper:
                        self.dialogInfo("Number %f can't be over Upper bound." % (data), self.window)
                        return False

            elif self.type == openscap.OSCAP.XCCDF_TYPE_STRING:
                if selector_empty:
                    if selector_empty.match:
                        pattern = re.compile(selector_empty.match,re.IGNORECASE)
                        if pattern.search(data) == None:
                            self.dialogInfo("String '%s' isn't match with regular expression in field match." % data, self.window)
                            return False
        return True
        
    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show_all()

    def __delete_event(self, widget, event=None):
        self.window.destroy()

class EditValueChoice(commands.DataHandler, abstract.EnterList):
    
    COLUMN_MARK_ROW = 0
    COLUMN_CHOICE = 1

    def __init__(self, core, model, treeView, window):

        self.model = model
        self.treeView = treeView
        abstract.EnterList.__init__(self, core, "EditValueCoice",self.model, self.treeView, self.cb_lv_edit , window)
        
        cell = self.set_insertColumnText("Choice", self.COLUMN_CHOICE, True, True)
        iter = self.model.append(None)
        self.model.set(iter,self.COLUMN_MARK_ROW,"*")

    def cb_lv_edit(self, action):
    
        if action == "edit":
            self.model[self.edit_path][self.edit_column] = self.edit_text
        elif action == "del":
            self.model.remove(self.iter_del)
        elif action == "add":
            self.model[self.edit_path][self.edit_column] = self.edit_text

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
