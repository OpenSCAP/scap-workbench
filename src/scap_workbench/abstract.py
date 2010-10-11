# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Authors:
#      Maros Barabas        <mbarabas@redhat.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

import pygtk
import gtk
import gobject
import re

from events import EventObject
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

    def set_active(self, active):
        """
        Show or hide MenuButton object and dependent menu, body.
        @param active True/False - Show/Hide 
        """
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
        column, key = data # data is a tuple containing column number, key
        pattern = re.compile(key,re.IGNORECASE)
        if pattern.search(model.get_value(iter, column)) != None:
            return True
        else:
            return False

    def search_branch(self, model, iter, iter_start, data):
        """ Search data in model from iter next. Search terminates when a row is found. 
            @param model is gtk.treeModel
            @param iter is start position
            @param data is a tuple containing column number, key
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
        vys = True
        for item in filters:
            func = item["filtr_info"]["func"]
            param = item["filtr_info"]["param"]
            vys = vys and func(model, iter, param)
        return vys

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
        vys_branch = False

        while iter:
            iter_self = self.copy_row(model, iter, new_model, iter_parent, n_column)

            vys = self.match_fiter(filters, model, iter)
            vys_child = self.filtering_tree(model, model.iter_children(iter), new_model, iter_self, filters, n_column)

            vys_branch = vys_branch or vys_child  or vys

            if not (vys_child or vys):
                new_model.remove(iter_self)
            else:
                self.map_filter.update({new_model.get_path(iter_self):model.get_path(iter)})
            iter = model.iter_next(iter)

        return vys_branch

    def init_filters(self, filter, filter_model):
        """ init filter for first use or model changed"""
        self.filter_model = filter_model
        filter.init_filter()
        self.ref_model = ref_filter

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
            struct = struct and item["filtr_info"]["result_tree"]
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

        
class ProgressBar(EventObject):

    def __init__(self, id, core=None):

        self.core = core
        self.core.register(id, self)
        self.widget_btn = gtk.ProgressBar()
        self.widget_btn.show()
        self.widget = gtk.ToolItem()
        self.widget.add(self.widget_btn)
        self.widget.set_is_important(True)
        self.widget.show()


