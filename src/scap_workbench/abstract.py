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

""" Importing standard python libraries
"""
import gtk              # GTK library
import gobject          # gobject.TYPE_PYOBJECT
import re               # Regular expressions
import datetime
import time
import os.path

""" Importing SCAP Workbench modules
"""
import logging                          # Logger for debug/info/error messages
from core import Notification           # core.Notification levels for reference
from events import EventObject          # abstract module EventObject
from htmltextview import HtmlTextView   # Widget for viewing HTML when WebKit is not available
import paths

# Initializing Logger
logger = logging.getLogger("scap-workbench")

""" Importing non-standard python libraries
These libraries are not required and should be always
checked by:
  if HAS_MODULE: do
  else: notify(..)"""
try:
    # Import WebKit module for HTML editing 
    # of descriptions
    import webkit as webkit
    HAS_WEBKIT = True
except ImportError:
    HAS_WEBKIT = False

try:
    # For prettifing the source code of HTML Editors
    from BeautifulSoup import BeautifulSoup
    HAS_BEUTIFUL_SOUP = True
except ImportError:
    HAS_BEUTIFUL_SOUP = False

""" Import OpenSCAP library as backend.
If anything goes wrong just end with exception"""
try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None

class Menu(EventObject):
    """Create Main item for TreeToolBar_toggleButtonGroup and draw all tree Menu

    Menu contains all menu items as MenuButtons. MenuButtons themselves have their
    content contained within.
    """

    def __init__(self, id, widget, core):
        """ Constructor of abstract.Menu item.

        @param id Unique id of the object
        @param widget GTK Widget for menu item
        @param core SWBCore singleton
        """
        
        super(Menu, self).__init__(core)
        
        self.id = id
        self.btnList = []
        self.active_item = None
        self.default_item = None
        self.widget = widget
        core.register(id, self)
    
    def add_item(self, item):
        """ Add item to the menu list
        """

        # Set the first item to be default
        if len(self.btnList) == 0:
            self.set_default(item)

        self.btnList.append(item)
        item.parent = self
        
        # Return added item for further configuration
        return item

    def show(self):
        """ Show the menu and set active itme.
        """
        self.widget.show()
        self.toggle_button(self.active_item)

    def set_active(self, active):
        """ Show or hide menu with MenuButtons.
        """
        if active: self.show()
        else: self.widget.hide()

    def set_default(self, item):
        """ Set default active MenuButton object in menu.
        """
        self.active_item = item
        self.default_item = item

    def toggle_button(self, item):
        """ Toggle selected button.
        """
        # Deselect all buttons
        if self.active_item: self.active_item.set_active(False)
        # Show selected button
        self.active_item = item
        self.active_item.set_active(True)

class MenuButton(EventObject):
    """Class containing GTK Widget button with the content of 
    the page associated with this button.
    """

    def __init__(self, id, widget, core):
        """ Constructor of abstract.MenuButton

        @param id Unique id of the object
        @param widget GTK Widget for menu item
        @param core SWBCore singleton
        """
        
        super(MenuButton, self).__init__(core)

        self.id = id
        self.add_sender(id, "update")
        self.parent = None
        self.menu = None
        self.body = None
        self.widget = widget
        core.register(id, self)

        # signals
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

    def set_sensitive(self, sensitive):
        self.widget.set_sensitive(sensitive)

    def update(self):
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
    """Free floating Window
    """
    
    def __init__(self, id, core = None, skip_registration = False):
        """Constructor
        
        id - unique id of the object
        core - SWBCore singleton instance
        skip_registration - if True the window won't be registered in SWBCore
                            (mainly for windows that get repeatedly created and destroyed)
        """
        
        EventObject.__init__(self, core)

        self.id = id
        
        if not skip_registration and self.core is not None:
            self.core.register(id, self)

class List(EventObject):
    
    def __init__(self, id, core=None, widget=None):
        super(List, self).__init__(core)
        
        #create view
        self.id = id
        self.core.register(id, self)
        self.filter_model = None
        self.selected = None
        
        # TODO: Does it really make sense to have "None" as default value of widget if that's not permitted? 
        if widget is None:
            raise ValueError("No widget for List specified")
        else:
            self.treeView = widget
        self.add_sender(id, "update")
        # FIXME: self.data_model has to be set at this point, otherwise render() will fail!
        self.render()

    def filter_listview(self, model, iter, data):
        search, columns = data
        text = search.get_text()
        if len(text) == 0: 
            return True
        pattern = re.compile(text, re.I)
        for col in data:
            found = re.search(pattern, model[iter][col])
            if found != None: return True
        return False

    def search_treeview(self, widget, treeview):
        treeview.get_model().refilter()
        return

    def set_selected(self, model, path, iter, usr):
        
        id, view, col = usr
        selection = view.get_selection()
        
        if iter and model.get_value(iter, col) == id:
            view.expand_to_path(path)
            selection.select_path(path)
            view.scroll_to_cell(path)
            return True

    def set_selected_profile_item(self, model, path, iter, usr):

        profile, id, view, col = usr
        selection = view.get_selection()
        if iter and model.get_value(iter, col) != id:
            return False
        if iter and model.get_value(iter, col) == id and model.iter_parent(iter) and model.get_value(model.iter_parent(iter), col) == profile:
            view.expand_to_path(path)
            selection.select_path(path)
            view.scroll_to_cell(path)
            return True

    def get_TreeView(self):
        """Returns treeView"""
        return self.treeView

    def get_widget(self):
        """Returns top widget"""
        return self.scrolledWindow

    def render(self):
        if self.data_model: self.data_model.render(self.get_TreeView())
        else: logger.error("Data model does not exist")

    def __match_func(self, model, iter, data):
        """ search pattern in column of model"""
        column, key = data # data is a tuple containing column number and key
        pattern = re.compile(key,re.IGNORECASE)
        return pattern.search(model.get_value(iter, column)) != None

    def __search_branch(self, model, iter, iter_start, data):
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

            result = self.__search_branch(model, model.iter_children(iter), iter_start, data)
            if result: 
                return result

            iter = model.iter_next(iter)
        return None

    def search(self, key, column):
        """ search in treeview"""
        logger.warning("Deprecation warning: This function should not be used.") # TODO
        selection = self.treeView.get_selection()
        model, iter =  selection.get_selected()
        iter_old = iter
        
        if iter == None:
            # nothing selected
            iter = model.get_iter_root()
            iter = self.__search_branch(model, iter, None, (column, key))

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
                iter = self.__search_branch(model, iter, iter_start, (column, key))
                while iter == None:
                    iter_parent = model.iter_parent(iter_old)
                    while iter_parent != None:
                        iter = model.iter_next(iter_parent)
                        if iter != None:
                            iter_old = iter
                            iter = self.__search_branch(model, iter, iter_start, (column, key))
                            break
                        else:
                            iter_parent = model.iter_parent(iter_parent)
                    if iter_parent == None:
                        # searched to end (not found) and will go to search from start 
                        iter = self.__search_branch(model, model.get_iter_root(), iter_start, (column, key))
                        break

        # if find search text
        if iter != None:
            path = model.get_path(iter)
            self.get_TreeView().expand_to_path(path)
            selection.select_path(path)
            self.get_TreeView().scroll_to_cell(path)

    def recursive_search(self, pattern, columns, parent=None):
        """ Search the treeview by regular expression
        in "pattern" variable. Search in columns specified by the
        list in "columns" variable.

        Let parent None if you want to start the search. "parent"
        variable is used to set recursivity.
        
        iter - local variable used for iteration thru iters
        """
        if pattern == None or columns == None or len(columns) == 0:
            return False

        selection = self.treeView.get_selection()
        model, i_start =  selection.get_selected()
        if not parent:
            if i_start == None:
                # Nothing selected, search from the first iter
                i_start = model.get_iter_root()
                # TODO: Add check here to cover the root iter
                if not i_start: return True # Tree is empty

        iter = model.iter_children(parent or i_start)
        while iter:
            # Look for the pattern in specified columns
            for col in columns:
                found = re.search(pattern or "", model[iter][col] or "")
                if found != None:
                    path = model.get_path(iter)
                    self.treeView.expand_to_path(path)
                    selection.select_path(path)
                    self.treeView.scroll_to_cell(path)
                    return True

            # Look within this child.
            retval = self.recursive_search(pattern, columns, iter)
            if retval: return True
            
            # Not found, let's continue
            iter = model.iter_next(iter)
        """ If the the iter is None there is no more items as
        children of the start item. We have to continue to next
        iter in parent level of the tree """

        """ We have parent specified but no child is found
        This is the point we are returning up from recursive call
        """
        if parent != None: return False

        """ This is the start of the second recursive search because
        we haven't found anything within the selected item. 

        We have to go thru parents now, but not the parent of selected
        item. """
        i_parent = i_start
        while i_parent:
            iter = model.iter_next(i_parent)
            if iter:
                # Look for the pattern in specified columns
                for col in columns:
                    found = re.search(pattern or "", model[iter][col] or "")
                    if found != None:
                        path = model.get_path(iter)
                        self.treeView.expand_to_path(path)
                        selection.select_path(path)
                        self.treeView.scroll_to_cell(path)
                        return True

                # Look within this child.
                retval = self.recursive_search(pattern, columns, iter)
                if retval: return retval
            
            # Not found, let's continue
            i_parent = model.iter_parent(i_parent)

        """ We didn't find anything
        """
        return False


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
            except Exception as e:
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

class Func(object):
    """Provides miscellaneous functionality like preview, datetime helper methods, etc...
    The only reason the methods are not classmethods or staticmethods are the notifications
    (self.notifications).
    
    The intended usage is probably as a mixin class to a class with EventObject as one of the
    base classes.
    """
    
    # FIXME: This is almost exclusively used as a mixin class and its constructor is not called
    #        IMO it creates a very strange pseudo-diamond hierarchy that should be removed
    #        at some point in the future
    
    def __init__(self, core=None):

        self.core = core
        self.notifications = []

    def destroy_preview(self, widget=None):
        if 'preview_dialog' in self.__dict__ and self.preview_dialog != None:
            self.preview_dialog.destroy()
            self.preview_dialog = None

    def prepare_preview(self):

        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        self.preview_dialog = builder.get_object("dialog:preview")
        self.preview_scw = builder.get_object("dialog:preview:scw")
        self.info_box = builder.get_object("dialog:preview:info_box")
        self.save = builder.get_object("dialog:preview:btn_save")
        self.save.set_property("visible", False)
        builder.get_object("dialog:preview:btn_ok").connect("clicked", self.destroy_preview)
        self.preview_dialog.connect("destroy", self.destroy_preview)
        # Get the background color from window and destroy it
        window = gtk.Window()
        window.realize()
        bg_color = window.get_style().bg[gtk.STATE_NORMAL]
        window.destroy()

        desc="""
        <style type="text/css">
            #center { position:relative; top:50%; height:10em; margin-top:-5em }
            body { text-align: center; }
        </style>
        <html>
          <body>
            <div id="center">
                    <center><h1>Loading ...</h1></center>
            </div>
          </body>
        </html>
        """
        if HAS_WEBKIT:
            self.description_widget = webkit.WebView()
            self.description_widget.load_html_string(desc, "file:///")
            self.description_widget.set_zoom_level(0.75)
            #description.modify_bg(gtk.STATE_NORMAL, bg_color)
            #description.parent.modify_bg(gtk.STATE_NORMAL, bg_color)
        else:
            self.description_widget = HtmlTextView()
            self.description_widget.set_wrap_mode(gtk.WRAP_WORD)
            self.description_widget.modify_base(gtk.STATE_NORMAL, bg_color)
            try:
                self.description_widget.display_html(desc)
            except Exception as err:
                logger.error("Exception: %s", err)
        
        self.preview_scw.add(self.description_widget)
        self.description_widget.show()
        #self.preview_dialog.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

        self.preview_dialog.set_transient_for(self.core.main_window)
        self.preview_dialog.show()

    def preview(self, widget=None, desc=None, save=None):

        if widget:
            selection = self.widget.get_selection()
            if selection != None: 
                (model, iter) = selection.get_selected()
                if not iter: return False
            else: return False
        
        if 'preview_dialog' not in self.__dict__ or self.preview_dialog == None:
            self.prepare_preview()

        if not desc:
            desc = self.model.get_value(iter, self.COLUMN_TEXT) or ""
            desc = re.sub("xmlns:xhtml=\"[^\"]*\"", lambda x: "", desc or "")
            desc = desc.replace("xhtml:","")
            desc = desc.replace("xmlns:", "")
            desc = self.data_model.substitute(desc)
            if desc == "": desc = "No description"
            desc = "<body><div>"+desc+"</div></body>"

        if HAS_WEBKIT:
            self.description_widget.load_html_string(desc, "file:///")
        else:
            try:
                self.description_widget.display_html(desc)
            except Exception as err:
                logger.error("Exception: %s", err)
        #self.preview_dialog.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.ARROW))

        self.save.set_property("visible", save != None)
        if save != None:
            """ We want to have option to save what we see in the preview dialog.
            In this case pass the callback function as "save" parameter it should
            have format as widget callback method
            """
            if not callable(save):
                raise ValueError("Passed invalid callback to the preview function")

            def __callback_wrapper(widget, self):
                """ Nested function to call callback function from parent
                and show the notification in the info_box of the preview dialog
                """
                retval, text = save()
                if retval != None:
                    self.notifications.append(self.core.notify(text, retval, info_box=self.info_box))

            self.save.connect("clicked", __callback_wrapper, self)


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
        logger.warning("Deprecation warning: This function should not be used.") # TODO
        return
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

    def controlDate(self, text):
        """
        Function concert sting to timestamp (gregorina). 
        If set text is incorrect format return False and show message.
        """
        self.core.notify_destroy("notify:date_format")
        if text != "":
            date = text.split("-")
            if len(date) != 3:
                self.notifications.append(self.core.notify("The date is in incorrect format. Correct format is YYYY-MM-DD.",
                    Notification.ERROR, msg_id="notify:date_format"))
                return None
            try:
                d = datetime.date(int(date[0]), int(date[1]), int(date[2]))
            except ValueError as ex:
                self.notifications.append(self.core.notify("The date is in incorrect format. Correct format is YYYY-MM-DD.",
                    Notification.ERROR, msg_id="notify:date_format"))
                return None
            
            try:
                timestamp = int(time.mktime(d.timetuple())) 
            except (OverflowError, ValueError):
                self.notifications.append(self.core.notify("The date is out of range.",
                    Notification.ERROR, msg_id="notify:date_format"))

            self.core.notify_destroy("notify:date_format")
            return timestamp
        else:
            self.core.notify_destroy("notify:date_format")
            return None
            
    def controlImpactMetric(self, text, core):
        """
        Function control impact metric
        """
        #pattern = re.compile ("^AV:[L,A,N]/AC:[H,M,L]/Au:[M,S,N]/C:[N,P,C]/I:[N,P,C]/A:[N,P,C]$|^E:[U,POC,F,H,ND]/RL:[OF,TF,W,U,ND]/RC:[UC,UR,C,ND]$|^CDP:[N,L,LM,MH,H,ND]/TD:[N,L,M,H,ND]/CR:[L,M,H,ND]/ IR:[L,M,H,ND]/AR:[L,M,H,ND]$",re.IGNORECASE)
        patternBase = re.compile("^AV:[L,A,N]/AC:[H,M,L]/Au:[M,S,N]/C:[N,P,C]/I:[N,P,C]/A:[N,P,C]$",re.IGNORECASE)
        patternTempo = re.compile("^E:(U|(POC)|F|H|(ND))/RL:((OF)|(TF)|W|U|(ND))/RC:((UC)|(UR)|C|(ND))$",re.IGNORECASE)
        patternEnvi = re.compile("^CDP:(N|L|H|(LM)|(MH)|(ND))/TD:(N|L|M|H|(ND))/CR:(L|M|H|(ND))/IR:(L|M|H|(ND))/AR:(L|M|H|(ND))$",re.IGNORECASE)
        
        if patternBase.search(text) != None or patternTempo.search(text) != None or patternEnvi.search(text) != None:
            return True
        else:
            error = "Incorrect value of Impact Metric, correct is: Metric Value Description \n"
            error = error + "Base =    AV:[L,A,N]/AC:[H,M,L]/Au:[M,S,N]/C:[N,P,C]/I:[N,P,C]/A:[N,P,C]\n"
            error = error + "Temporal =     E:[U,POC,F,H,ND]/RL:[OF,TF,W,U,ND]/RC:[UC,UR,C,ND]\n"
            error = error + "Environmental =    CDP:[N,L,LM,MH,H,ND]/TD:[N,L,M,H,ND]/CR:[L,M,H,ND]/IR:[L,M,H,ND]/AR:[L,M,H,ND]"
            
            self.notifications.append(core.notify(error, Notification.ERROR, msg_id="notify:control:metric"))
            return False

    def controlFloat(self, data, text, info_box=None):
        self.core.notify_destroy("notify:float_format")
        if data != "" and data != None:
            try:
                data = float(data)
                if data < 0:
                    self.notifications.append(self.core.notify("Invalid number in %s. Please insert positive real number." % (text,),
                        Notification.ERROR, info_box, msg_id="notify:float_format"))
                    return None
            except ValueError:
                self.notifications.append(self.core.notify("Invalid number in %s." % (text,),
                    Notification.ERROR, info_box, msg_id="notify:float_format"))
                return None
            return data
        else:
            return float('nan')

class ListEditor(EventObject, Func):
    """ Abstract class for implementing all edit formulars that appear as list/tree view and 
    has add, edit and del buttons """

    COLUMN_LANG = 0
    COLUMN_TEXT = 1
    COLUMN_OBJ  = 2

    def __init__(self, id, core, widget=None, model=None):
        EventObject.__init__(self, core)
        Func.__init__(self, core)

        self.id = id
        self.core.register(self.id, self)

        self.widget         = widget
        self.__treeView     = widget
        self.model        = model or widget.get_model()

        if model: self.__treeView.set_model(model)

    def append_column(self, column):
        """For ControlEditWindow, remove after
        """
        retval = self.widget.append_column(column)
        if retval: return column
        else: return None

    def get_model(self):
        """For ControlEditWindow, remove after
        """
        return self.model

    def get_selection(self):
        """For ControlEditWindow, remove after
        """
        return self.widget.get_selection()

    def cb_edit_row(self, widget=None, values=None):
        """From ControlEditWindow
        """
        (model,iter) = self.get_selection().get_selected()
        if iter:
            window = EditDialogWindow(None, self.core, values, new=False)
        else:
            self.dialogNotSelected(self.core.main_window)

    def cb_add_row(self, widget=None, values=None):
        """From ControlEditWindow
        """
        window = EditDialogWindow(None, self.core, values, new=True)

    def cb_del_row(self, widget=None, values=None):
        """From ControlEditWindow
        """
        iter = self.dialogDel(self.core.main_window, self.get_selection())
        if iter != None:
            values["cb"](self.item, self.get_model(), iter, None, None, True)

    def set_model(self, model):
        self.__treeView.set_model(model)

    def clear(self):
        self.model.clear()

    def append(self, item):
        try:
            self.model.append(item)
        except ValueError as err:
            raise ValueError("Value Error in model appending \"%s\": %s" % (item, err))

    def filter_listview(self, model, iter, data):
        search, columns = data
        text = search.get_text()
        if len(text) == 0: 
            return True
        pattern = re.compile(text, re.I)
        for col in columns:
            found = re.search(pattern, model[iter][col])
            if found != None: return True
        return False

    def search_treeview(self, widget, treeview):
        treeview.get_model().refilter()
        return


class HTMLEditor(ListEditor):

    """ Abstract class for implementing all edit formulars that appear as list/tree view and 
    has add, edit and del buttons """

    COLUMN_LANG = 0
    COLUMN_TEXT = 1
    COLUMN_OBJ  = 2

    def __init__(self, id, core, widget=None, model=None):
        super(HTMLEditor, self).__init__(id, core, widget, model)

        self.__html = None
        self.__plain = None

    def render(self, box, toolbar, switcher):
        self.__switcher = switcher
        # Make active 1 if you want to have plain text default
        # and 0 if you want to have HTML WebKit as default
        self.__switcher.set_active(1)
        self.__switcher.connect("changed", self.__propagate)
        self.__toolbar = toolbar

        # Make ScrollWindows for both HTML and PLAIN views
        self.__html_sw = gtk.ScrolledWindow()
        box.pack_start(self.__html_sw, True, True)
        self.__plain_sw = gtk.ScrolledWindow()
        box.pack_start(self.__plain_sw, True, True)
        self.__plain = gtk.TextView()
        self.__plain_sw.add(self.__plain)
        self.__plain_sw.show_all()

        if not HAS_WEBKIT:
            label = gtk.Label("Missing WebKit python module")
            label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color("red"))
            self.__html_sw.add_with_viewport(label)
            self.__toolbar.set_sensitive(False)
            self.__html_sw.show_all()
            self.core.notify("Missing WebKit python module, HTML editing disabled.",
                    Notification.INFORMATION, info_box=self.info_box, msg_id="")
        else:
            self.__html = webkit.WebView()
            self.__html.set_zoom_level(0.75)
            self.__html_sw.add(self.__html)
            self.__html_sw.show_all()

        self.__html_sw.set_property("visible", self.__switcher.get_active() == 0)
        self.__plain_sw.set_property("visible", self.__switcher.get_active() == 1)

        for child in self.__toolbar.get_children():
            child.set_sensitive(False)
        self.__switcher.parent.set_sensitive(True)

    def load_html(self, text, url):
        if self.__switcher.get_active() == 0 and self.__html:
            # contenteditable is a new attribute in HTML5 that marks the element as WYSIWYG editable in the browser
            self.__html.load_html_string("<body contenteditable=\"true\">%s</body>" % (text), url)
            #self.__html.set_editable(True)
            
        else:
            self.__plain.get_buffer().set_text(text)

    def get_text(self):

        if self.__switcher.get_active() == 1:
            desc = self.__plain.get_buffer().get_text(self.__plain.get_buffer().get_start_iter(), self.__plain.get_buffer().get_end_iter())
        else:
            self.__html.execute_script("document.title=document.documentElement.innerHTML;")
            desc = self.__html.get_main_frame().get_title()
            if HAS_BEUTIFUL_SOUP:
                # Use Beutiful soup to prettify the HTML
                soup = BeautifulSoup(desc)
                desc = soup.prettify()
        desc = re.sub("(< */* *)([^>/ ]*) *([^>]*?)/?>", self.__regexp, desc)
        return desc

    def __regexp(self, regexp):
        match = regexp.groups()

        """ If there is no xhtml: prefix of HTML tag, we need to add it
        due validity of document """
        if match[1][:6] == "xhtml:": TAG = ""
        else: TAG = "xhtml:"

        """ If there is no long namespace defined and this is not ending
        tag of paired tags we need to define long namespace """
        if match[2].find("xmlns:xhtml") != -1 or match[0] == "</": NS_TAG = ""
        #else: NS_TAG = ' xmlns:xhtml="http://www.w3.org/1999/xhtml"'
        else: NS_TAG = ""

        # Bugfix: Correction of double "//" inserted in the end (present in match[2] after group)
        if len(match[2]) > 0 and match[2][-1] == "/": END_TAG = ">"
        else: END_TAG = "/>"

        """ Head and Body should be removed
        Unpaired tags should have format <xhtml:TAG xmlns:xhtml="..." />
        if tag is sub and contains idref attribute it should have format <sub ... />
        Paired tags should have format <xhtml:TAG xmlns:xhtml="..."> ... </TAG> """
        if match[1] in ["head", "body"]:
            return ""
        elif match[1] in ["br", "hr"]: return match[0]+TAG+" ".join(match[1:3])+NS_TAG+END_TAG # unpaired tags
        elif match[1] in ["sub"]: 
            if match[2].find("idref") != -1: return match[0]+" ".join(match[1:3])+NS_TAG+END_TAG # <sub>
            else: return "" # </sub>
        else: return match[0]+TAG+" ".join(match[1:3]).strip()+NS_TAG+">" # paired tags

    def set_htmlwidget(self, widget):
        self.__html = widget

    def on_color_set(self, widget):
        dialog = gtk.ColorSelectionDialog("Select Color")
        if dialog.run() == gtk.RESPONSE_OK:
            gc = str(dialog.colorsel.get_current_color())
            color = "#" + "".join([gc[1:3], gc[5:7], gc[9:11]])
            self.__html.execute_script("document.execCommand('forecolor', null, '%s');" % color)
        dialog.destroy()

    def on_font_set(self, widget):
        dialog = gtk.FontSelectionDialog("Select a font")
        if dialog.run() == gtk.RESPONSE_OK:
            fname, fsize = dialog.fontsel.get_family().get_name(), dialog.fontsel.get_size()
            self.__html.execute_script("document.execCommand('fontname', null, '%s');" % fname)
            self.__html.execute_script("document.execCommand('fontsize', null, '%s');" % fsize)
        dialog.destroy()

    def on_link_set(self, widget):
        dialog = gtk.Dialog("Enter a URL:", self.core.main_window, 0,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))

        entry = gtk.Entry()
        dialog.vbox.pack_start(entry)
        dialog.show_all()

        if dialog.run() == gtk.RESPONSE_OK:
            text = entry.get_text()
            text = "<sub xmlns=\"http://checklists.nist.gov/xccdf/1.1\" idref=\""+text+"\"/>"
            self.__html.execute_script("document.execCommand('InsertHTML', true, '%s');" % text)
        dialog.destroy()

    def on_code_set(self, action):
        self.__html.execute_script("document.execCommand('SetMark', null, 'code');")

    def on_action(self, action, command):
        """
        """
        self.__html.execute_script("document.execCommand('%s', false, false);" % command)

    def on_zoom(self, action):
        """
        """
        if action.get_name().split(":")[-1] == "zoomin":
            self.__html.zoom_in()
        else: self.__html.zoom_out()

    def __propagate(self, widget=None):
        
        if self.__switcher.get_active() == 0: # TEXT -> HTML
            self.__html_sw.set_property("visible", True)
            self.__plain_sw.set_property("visible", False)
            desc = self.__plain.get_buffer().get_slice(self.__plain.get_buffer().get_start_iter(), self.__plain.get_buffer().get_end_iter())
            self.load_html(desc or "", "file:///")

        elif self.__switcher.get_active() == 1: # HTML -> TEXT
            self.__html_sw.set_property("visible", False)
            self.__plain_sw.set_property("visible", True)
            
            # the following is a JavaScript trick to get exact innerHTML inside <body></body> out
            # using document's title
            self.__html.execute_script("document.title=document.documentElement.innerHTML;")
            desc = self.__html.get_main_frame().get_title()
            
            desc = desc.replace("<head></head>", "")
            desc = desc.replace("<body contenteditable=\"true\">", "").replace("</body>", "")

            """ We use Beautiful soup to pretify formatting of plain text
            when we switched from HTML to PLAIN view, cause we get only one-line
            text from WebView (WebKit module)"""
            if HAS_BEUTIFUL_SOUP:
                # Use Beutiful soup to prettify the HTML
                soup = BeautifulSoup(desc)
                desc = soup.prettify()
            else: 
                self.core.notify("Missing BeautifulSoup python module, HTML processing disabled.",
                    Notification.INFORMATION, info_box=self.info_box, msg_id="")
            self.__plain.get_buffer().set_text(desc)

        """ Set sensitivity of HTML toolbar. If swither is 0 (we have switched to HTML)
        we need to enable toolbar to set properties of HTML text """
        for child in self.__toolbar.get_children():
            child.set_sensitive(self.__switcher.get_active() == 0)

        """ Switcher has to stay enabled in all cases
        """
        self.__switcher.parent.set_sensitive(True)


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
    Abstract class for enter listView
    """
    COLUMN_MARK_ROW = 0

    def __init__(self, core, id, model, treeView, cb_action=None, window=None):
        # class send signal del and edit if not set param cb_action
        self.core = core
        self.id = id
        self.cb_action = cb_action
        if not cb_action:
            self.selected_old = None
            # FIXME: Only calling constructor of the super class conditionally?!
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


class ControlEditWindow(Func):
    def __init__(self, core, lv, values):
        super(ControlEditWindow, self).__init__(core)
        
        self.values = values
        self.item = None
        if lv:
            self.lv = lv
            self.model = lv.get_model()
            self.selection = lv.get_selection()
            self.selection.set_mode(gtk.SELECTION_SINGLE)

    def cb_edit_row(self, widget=None):
        (model,iter) = self.selection.get_selected()
        if iter:
            window = EditDialogWindow(self.item, self.core, self.values, new=False)
        else:
            self.dialogNotSelected(self.core.main_window)

    def cb_add_row(self, widget=None):
        window = EditDialogWindow(self.item, self.core, self.values, new=True)

    def cb_del_row(self, widget=None):
        iter = self.dialogDel(self.core.main_window, self.selection)
        if iter != None:
            self.values["cb"](self.item, self.model, iter, None, None, True)



class EditDialogWindow(EventObject):
    """ 
    Class create window for add/edit data acording the information in structure.
    Class control set data acording to data in the structure
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
        super(EditDialogWindow, self).__init__(core)

        self.new = new
        self.values = values
        self.item = item
        self.init_data = None
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        
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
