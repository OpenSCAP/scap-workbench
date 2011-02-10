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
import re

from events import EventObject
from htmltextview import HtmlTextView
import core
import logging

logger = logging.getLogger("scap-workbench")

try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None

class Menu(EventObject):
    """ 
    Create Main item for TreeToolBar_toggleButtonGroup and draw all tree Menu
    """
    def __init__(self, id, widget, core):
        """
        @param id
        """
        self.id = id
        self.core = core
        super(Menu, self).__init__()
        self.btnList = []
        self.active_item = None
        self.default_item = None
        self.widget = widget
        core.register(id, self)
	
    def add_item(self, item, position=None):
        """ 
        Add item to the menu list
        @param item MenuButton which is added to menu.
        @param position Position of MenuButton in menu.
        """

        if len(self.btnList) == 0:
            self.set_default(item)
        self.btnList.append(item)
        # vizual
        item.parent = self

        return item

    def show(self):
        """
        Show the menu and set active itme.
        """
        self.widget.show()
        self.toggle_button(self.active_item)

    def set_active(self, active):
        """
        Show or hide menu with MenuButtons.
        @param active True/False - Show/Hide 
        """
        if active: self.show()
        else: self.widget.hide()

    def set_default(self, item):
        """
        Set default active MenuButton object in menu.
        @param item Default active item.
        """
        self.active_item = item
        self.default_item = item

    def toggle_button(self, item):
        """ 
        Toggle selected button.
        @param item selected MenuButton object
        """
        # Deselect all buttons
        if self.active_item: self.active_item.set_active(False)
        # Show selected button
        self.active_item = item
        self.active_item.set_active(True)
		
    def refresh(self):
        """ Refresh graphic content
        Async. method called after data change
        """
        raise NotImplementedError, "Function \"refresh\" is not implemented yet"

class MenuButton(EventObject):
    """ Class for tree of toogleBar with toggleButtons in group
    """

    def __init__(self, id, widget, core):
        """
        @param id
        @param name Name of MenuButton
        @param C_body Conteiner for draw of body.
        @param sensitivity Filter function for set sensitivity of MenuButton
        """
        # structure
        self.core = core
        self.id = id
        super(MenuButton, self).__init__()
        self.add_sender(id, "update")
        self.parent = None      #menu for this MenuButton
        self.menu = None
        self.body = None
        self.widget = widget
        core.register(id, self)
        self.notifications = []

        # setings
        self.widget.connect("toggled", self.cb_toggle)

    def add_frame_vp(self,body, text,pos = 1):
        frame = gtk.Frame(text)
        frame.set_shadow_type(gtk.SHADOW_NONE)
        #frame.set_border_width(5)        
        label = frame.get_label_widget()
        label.set_use_markup(True)        
        if pos == 1: body.pack1(frame,  resize=False, shrink=False)
        else: body.pack2(frame,  resize=False, shrink=False)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return frame, alig

    def add_frame(self, body, text):
        label = gtk.Label(text)
        label.set_use_markup(True)
        label.set_justify(gtk.JUSTIFY_LEFT)
        label.set_alignment(0, 0)
        body.pack_start(label, True, True, padding=4)
        body.pack_start(gtk.HSeparator(), False, False, padding=2)
        alig = gtk.Alignment(0, 0, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        body.pack_start(alig, False, False)
        return alig

    #draw functions
    def add_frame_cBox(self, body, text, expand):
        frame = gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)        
        frame.set_shadow_type(gtk.SHADOW_NONE)
        if expand: body.pack_start(frame, True, True)
        else: body.pack_start(frame, False, True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return alig

    def update(self):
        pass

    def activate(self, active):
        pass

    def set_active(self, active):
        """
        Show or hide MenuButton object and dependent menu, body.
        @param active True/False - Show/Hide 
        """
        self.activate(active)
        if active: logger.debug("Switching active button to %s" % (self.id))
        self.widget.handler_block_by_func(self.cb_toggle)
        self.widget.set_active(active)
        self.set_body(active)
        if self.menu: 
            self.menu.set_active(active)
            if self.menu.active_item and not active:
                self.menu.active_item.set_active(active)
        self.widget.handler_unblock_by_func(self.cb_toggle)
        if active: 
            self.emit_signal("update")
            self.update()

    def set_menu(self, menu):
        """
        Add sudmenu tu MenuButton.
        @param menu Submenu which is set to MenuButton
        """
        self.menu = menu

    def cb_toggle(self, widget):
        """ 
        CallBack function which change active of toggleButtons in current toolBar
        and visibility of child.
        """
        self.parent.toggle_button(self)

    def set_body(self,active):
        """
        Show or hide content of body if exist.
        @param active True/False - Show/Hide 
        """
        if self.body:
            if active:
                self.body.show()
            else:
                self.body.hide()

class Window(EventObject):
    pass

class List(EventObject):
    
    def __init__(self, id, core=None, widget=None):
        
        #create view
        self.core = core
        self.id = id
        self.core.register(id, self)
        super(List, self).__init__(core)
        self.filter_model = None
        
        if not widget:
            self.scrolledWindow = gtk.ScrolledWindow()
            self.scrolledWindow.set_shadow_type(gtk.SHADOW_IN)
            self.scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            self.treeView = gtk.TreeView()
            self.treeView.set_headers_clickable(True)
            self.scrolledWindow.add(self.treeView)
        else:
            self.treeView = widget
        self.add_sender(id, "update")
        self.render()

    def set_selected(self, model, path, iter, usr):

        id, view = usr
        selection = view.get_selection()
        
        if model.get_value(iter, 0) == id:
            view.expand_to_path(path)
            selection.select_path(path)

    def get_TreeView(self):
        """Returns treeView"""
        return self.treeView

    def get_widget(self):
        """Returns top widget"""
        return self.scrolledWindow

    def render(self):
        assert self.data_model, "Data model of %s does not exist !" % (self.id,)
        self.data_model.render(self.get_TreeView())

    def __match_func(self, model, iter, data):
        """ search pattern in column of model"""
        column, key = data # data is a tuple containing column number and key
        pattern = re.compile(key,re.IGNORECASE)
        return pattern.search(model.get_value(iter, column)) != None

    def search_branch(self, model, iter, iter_start, data):
        """ Search data in model from iter next. Search terminates when a row is found. 
            @param model is gtk.treeModel
            @param iter is start position
            @param data is a tuple containing column number and key
            @return iter or None
        """
        while iter:
            # If all data was searched, stop the search. 
            if iter_start == model.get_string_from_iter(iter):
                return None

            if self.__match_func(model, iter, data):
                return iter

            result = self.search_branch(model, model.iter_children(iter), iter_start, data)
            if result: 
                return result

            iter = model.iter_next(iter)
        return None

    def search(self, key, column):
        """ search in treeview"""
        selection = self.treeView.get_selection()
        model, iter =  selection.get_selected()
        iter_old = iter
        
        if iter == None:
            # nothing selected
            iter = model.get_iter_root()
            iter = self.search_branch(model, iter, None, (column, key))

        else:
            # row selected move to next node
            iter_start = model.get_string_from_iter(iter)
            iter = model.iter_children(iter)
            if iter == None:
                iter = model.iter_next(iter_old)
                if iter == None:
                    iter_parent = model.iter_parent(iter_old)
                    while iter_parent != None:
                        iter = model.iter_next(iter_parent)
                        if iter != None:
                            break
                        iter_parent = model.iter_parent(iter_parent)
                    else:
                        iter = model.get_iter_root()

            # for search in parent node and search from end to start
            if iter != None:
                iter_old = iter
                iter = self.search_branch(model, iter, iter_start, (column, key))
                while iter == None:
                    iter_parent = model.iter_parent(iter_old)
                    while iter_parent != None:
                        iter = model.iter_next(iter_parent)
                        if iter != None:
                            iter_old = iter
                            iter = self.search_branch(model, iter, iter_start, (column, key))
                            break
                        else:
                            iter_parent = model.iter_parent(iter_parent)
                    if iter_parent == None:
                        # searched to end (not found) and will go to search from start 
                        iter = self.search_branch(model, model.get_iter_root(), iter_start, (column, key))
                        break

        # if find search text
        if iter != None:
            path = model.get_path(iter)
            self.get_TreeView().expand_to_path(path)
            selection.select_path(path)
            self.get_TreeView().scroll_to_cell(path)

    def copy_row(self, model, iter , new_model, iter_parent, n_columns):
        row = []
        for i in range(n_columns):
            row.append(model.get_value(iter,i))
        return new_model.append(iter_parent, row)

    def match_fiter(self, filters, model, iter):
        res = True
        for item in filters:
            try:
                res = res and item.func(model, iter, item.params)
            except Exception, e:
                #self.core.notify("Can't filter items: %s" % (e,), 3)
                logger.error("Can't filter items: %s" % (e,))

        return res

    def filtering_list(self, model, iter, new_model, filters, n_column):
        """ 
        Filter data to list
        """
        while iter:
            if self.match_fiter(filters, model, iter):
                iter_to = self.copy_row(model, iter, new_model, None, n_column)
                self.map_filter.update({new_model.get_path(iter_to):model.get_path(iter)})
            self.filtering_list(model, model.iter_children(iter), new_model, filters, n_column)
            iter = model.iter_next(iter)


    def filtering_tree(self, model, iter, new_model, iter_parent, filters, n_column):
        """
        Filter data to tree
        """
        res_branch = False

        while iter:
            iter_self = self.copy_row(model, iter, new_model, iter_parent, n_column)

            res = self.match_fiter(filters, model, iter)
            res_child = self.filtering_tree(model, model.iter_children(iter), new_model, iter_self, filters, n_column)

            res_branch = res_branch or res_child  or res

            if not (res_child or res):
                new_model.remove(iter_self)
            else:
                self.map_filter.update({new_model.get_path(iter_self):model.get_path(iter)})
            iter = model.iter_next(iter)

        return res_branch

    def init_filters(self, filter, ref_model, filter_model):
        """ init filter for first use or model changed"""
        self.filter_model = filter_model
        filter.init_filter()
        self.ref_model = ref_model

    def filter_add(self, filters):
        """ function add filter on model"""

        # if filtering is set
        if self.filter_model == None:
            logger.error("filter is not init use function init.filters(new_model)")

        # if filters are empty
        if filters == []:
            self.map_filter = {}
            self.treeView.set_model(self.ref_model)
            return (self.map_filter,True)

        # clean maping from filter model to ref
        self.map_filter = {}

        iter = self.ref_model.get_iter_root()
        n_column = self.ref_model.get_n_columns()
        self.filter_model.clear()
        
        # get final struct (tree or list)
        struct = True
        for item in filters:
            struct = struct and item.istree
        if struct:
            self.filtering_tree(self.ref_model, iter, self.filter_model, None, filters, n_column)
        else:
            self.filtering_list(self.ref_model, iter, self.filter_model, filters, n_column)

        self.treeView.set_model(self.filter_model)
        return (self.map_filter,struct)

    def filter_del(self, filters, propagate_changes = None):
        """find a deleted filter
        @propagate_change is list of column wich should be control and propagate
        """
        if propagate_changes != None:
            for key in self.map_filter.keys():
                path = self.map_filter[key]
                iter = self.ref_model.get_iter(path)
                for column in propagate_changes:
                    if self.ref_model[path][column] <> self.filter_model [key][column]:
                        self.ref_model.set(iter, column, self.filter_model [key][column])

        #refilter filters after deleted filter
        return self.filter_add(filters)

class CellRendererTextWrap(gtk.CellRendererText):
    """ pokus asi nebude pouzito necham najindy pozeji smazu"""
    def __init__(self):
        self.__gobject_init__()
        gtk.CellRendererText.__init__( self )
        self.callable = None
        self.table = None
        self.set_property("wrap-mode", True)
        
    def do_render(self, window, wid, bg_area, cell_area, expose_area, flags):
       self.set_property("wrap-width", cell_area.width )
       gtk.CellRendererText.do_render( self, window, wid, bg_area,cell_area, expose_area, flags)
       
gobject.type_register(CellRendererTextWrap)

class EnterList(EventObject):
    """
    Abstrac class for enter listView
    """
    COLUMN_MARK_ROW = 0

    def __init__(self, core, id, model, treeView, cb_action=None, window=None):
        # class send signal del and edit if not set param cb_action
        self.core = core
        self.id = id
        self.cb_action = cb_action
        if not cb_action:
            self.selected_old = None
            super(EnterList, self).__init__(core)
            self.core.register(id, self)
            self.add_sender(id, "del")
            self.add_sender(id, "edit")
        if window:
            self.window = window
        else:
            self.window = self.core.main_window
        self.selected_old = None
        self.control_empty = []
        self.control_unique = []
        self.model = model
        self.treeView = treeView
        self.treeView.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        self.treeView.set_model(self.model)
        self.treeView.connect("key-press-event", self.__cb_del_row)
        self.treeView.connect("focus-out-event", self.__cb_leave_row)
        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("", txtcell, text=EnterList.COLUMN_MARK_ROW)
        self.treeView.append_column(column)

        self.selection = self.treeView.get_selection()
        self.selection.set_mode(gtk.SELECTION_SINGLE)
        self.hendler_item_changed = self.selection.connect("changed", self.__cb_item_changed_control)
    
    def set_insertColumnText(self, name, column_n, empty=True, unique=False ):
        
        txtcell = CellRendererTextWrap()
        column = gtk.TreeViewColumn(name, txtcell, text=column_n)
        column.set_resizable(True)
        self.treeView.append_column(column)
        txtcell.set_property("editable",True)
        txtcell.connect("edited", self.__cb_edit, column_n)

        #for control if dat in columns should be unique
        if unique:
            self.control_unique.append([column_n, name])
            return txtcell
        
        #for control if can not be empty
        if empty == False:
            self.control_empty.append([column_n, name])
        return txtcell

    def set_insertColumnInfo(self, name, column_n, empty= True):
        
        txtcell = CellRendererTextWrap()
        column = gtk.TreeViewColumn(name, txtcell, text=column_n)
        column.set_resizable(True)
        txtcell.set_property("foreground", "gray")
        self.treeView.append_column(column)
        
        #for control if can not be empty
        if empty == False:
            self.control_empty.append([column_n, name])
        return txtcell
    
    def __cb_item_changed_control(self, widget):
        
        if self.selected_old != None:
            iter = self.selected_old
            if iter != None:
                status = self.model.get_value(iter, 0)
                if status != "*":
                    
                    #control if is empty
                    for cell in self.control_empty:
                        (column, name) = cell
                        data = self.model.get_value(iter, column)
                        if (data == "" or data == None):
                            md = gtk.MessageDialog(self.window, 
                                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                                    gtk.BUTTONS_OK, " Column \"%s\" can't be empty." % (name))
                            md.set_title("Info")
                            md.run()
                            md.destroy()
                            
                            self.selection.handler_block(self.hendler_item_changed)
                            self.selection.select_path(self.model.get_path(iter))
                            self.selection.handler_unblock(self.hendler_item_changed)
                            return
                            
                    # control is unique
                    for cell in self.control_unique:
                        (column, name) = cell
                        path = self.model.get_path(iter)
                        new_text = self.model.get_value(iter, column)
                        for row in self.model:
                            if row[column] == new_text and self.model.get_path(row.iter) != path:
                                md = gtk.MessageDialog(self.window, 
                                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                                        gtk.BUTTONS_YES_NO, "%s \"%s\" already specified.\n\nRewrite stored data ?" % (name, new_text,))
                                md.set_title("Language found")
                                result = md.run()
                                md.destroy()
                                if result == gtk.RESPONSE_NO:
                                    iter = self.selected_old
                                    self.selection.handler_block(self.hendler_item_changed)
                                    self.selection.select_path(self.model.get_path(iter))
                                    self.selection.handler_unblock(self.hendler_item_changed)
                                    return
                                else: 
                                    self.iter_del = row.iter
                                    if self.cb_action:
                                        self.cb_action("del")
                                    else:
                                        self.emit("del")
                                    return

        model, self.selected_old = self.selection.get_selected()

    def __cb_edit(self, cellrenderertext, path, new_text, column):

        self.edit_path = path
        self.edit_column = column
        self.edit_text = new_text
        
        if self.model[path][EnterList.COLUMN_MARK_ROW] == "*" and new_text != "":
            self.model[path][EnterList.COLUMN_MARK_ROW] = ""
            iter = self.model.append(None)
            self.model.set(iter,EnterList.COLUMN_MARK_ROW,"*")
            if self.cb_action:
                self.cb_action("add")
            else:
                self.emit("add")
        else:
            if self.cb_action:
                self.cb_action("edit")
            else:
                self.emit("edit")
            
    def __cb_del_row(self, widget, event):

        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Delete":
            selection = self.treeView.get_selection( )
            if selection != None: 
                (model, iter) = selection.get_selected( )
                if  iter != None and self.model.get_value(iter, EnterList.COLUMN_MARK_ROW) != "*":
                    md = gtk.MessageDialog(self.window, 
                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_YES_NO, "Do you want delete selected row?")
                    md.set_title("Delete row")
                    result = md.run()
                    md.destroy()
                    if result == gtk.RESPONSE_NO: 
                        return
                    else: 
                        self.selected_old = None
                        self.iter_del = iter
                        if self.cb_action:
                            self.cb_action("del")
                        else:
                            self.emit("del")

    def __cb_leave_row(self,widget, event):
        pass


class Enum_type:
    
    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2
    
    # 0 is undefined here 
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

class Func:
    
    def dialogDel(self, window, selection):
        """
        Function Show dialogue if you wont to delete row if yes return iter of row.
        @param window Widget of window for parent in dialogue.
        @param selection Selection of TreeView.
        @return Iter of treViw fi yes else return None
        """
        (model,iter) = selection.get_selected()
        if iter:
            md = gtk.MessageDialog(window, 
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
            self.dialogInfo("Choose row which you want delete.", window)

    def dialogNotSelected(self, window):
        self.dialogInfo("Choose row which you want edit.", window)
        
        
    def dialogInfo(self, text, window):
        #window = self.core.main_window
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


    def set_active_comboBox(self, comboBox, data, column, text = ""):
        """
        Function set active row which is same as data in column.
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
            if text != "":
                text = "(" + text + ") "
            logger.error("Invalid data passed to combobox: \"%s\"" % (text))
            comboBox.set_active(-1)
        
    def set_model_to_comboBox(self, combo, model, view_column):
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', view_column)  
        combo.set_model(model)

    def controlDate(self, text, window):
        """
        Function concert sting to timestamp (gregorina). 
        If set text is incorrect format return False and show message.
        """
        if text != "":
            date = text.split("-")
            if len(date) != 3:
                self.dialogInfo("The date is in incorrect format. \n Correct format is YYYY-MM-DD.", window)
                return False
            try :
                d = datetime.date(int(date[0]), int(date[1]), int(date[2]))
            except Exception as ex:
                error = "Date is incorrect format:\n" + str(ex)
                self.dialogInfo(error, window)
                return False
            try:
                timestamp = time.mktime(d.timetuple()) 
            except Exception as ex:
                error = "Date is out of range. "
                self.dialogInfo(error, window)
            return timestamp
        return False
            
    def controlImpactMetric(self, text, window):
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
            
            self.dialogInfo(error, window)
            return False

    def controlFloat(self, data, text, window):
        if data != "" or data != None:
            try:
                data = float(data)
            except:
                self.dialogInfo("Invalid number in %s." % (text), window)
                return None
            return data
        else:
            data = float(nan)

class ControlEditWindow(Func, Enum_type):
    
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
            self.dialogNotSelected(self.core.main_window)

    def cb_add_row(self, widget):
        window = EditDialogWindow(self.item, self.core, self.values, new=True)

    def cb_del_row(self, widget):
        iter = self.dialogDel(self.core.main_window, self.selection)
        if iter != None:
            self.values["cb"](self.item, self.model, iter, None, None, True)



class EditDialogWindow(EventObject):
    """ 
    Class create window for add/edit data acording the information in strucure.
    Class control set data acordin data in structure
    Example of struct
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
    """
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
