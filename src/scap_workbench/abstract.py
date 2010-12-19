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
            self.emit("update")
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

