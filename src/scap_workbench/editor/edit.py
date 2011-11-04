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
import gobject          # GObject.TYPE_PYOBJECT
import time             # Time functions in calendar data ::EditStatus
import re               # Regular expressions 
import os               # os Path join/basename, ..
import datetime
import logging                  # Logger for debug/info/error messages

""" Importing SCAP Workbench modules
"""
from scap_workbench import core
from scap_workbench.core import abstract
from scap_workbench.core import commands
from scap_workbench.core.events import EventObject
import scap_workbench.core.enum as ENUM
from scap_workbench.core import paths

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

""" Import OpenSCAP library as backend.
If anything goes wrong just end with exception"""
try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None
    raise ex

class EditTitle(abstract.ListEditor):

    COLUMN_LANG         = 0
    COLUMN_OVERRIDES    = 1
    COLUMN_TEXT         = 2
    COLUMN_OBJ          = 3

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model
        super(EditTitle, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, bool, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn("Language", Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn("Overrides", Gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(Gtk.TreeViewColumn("Title", Gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.title.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_title(self.operation, item, self.lang.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()), 
                                            self.overrides.get_active())
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_title.glade"))
        
        self.wdialog = builder.get_object("dialog:edit_title")
        self.info_box = builder.get_object("dialog:edit_title:info_box")
        self.lang = builder.get_object("dialog:edit_title:lang")
        self.title = builder.get_object("dialog:edit_title:title")
        self.overrides = builder.get_object("dialog:edit_title:overrides")
        builder.get_object("dialog:edit_title:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_title:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.overrides.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.title.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for title dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):
        """
        """
        self.clear()
        for data in self.data_model.get_titles() or []:
            self.append([data.lang, data.overrides, (" ".join(data.text.split())), data])

class EditDescription(abstract.HTMLEditor):

    COLUMN_LANG         = 0
    COLUMN_OVERRIDES    = 1
    COLUMN_TEXT         = 2
    COLUMN_OBJ          = 3

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditDescription, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, bool, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn("Language", Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn("Overrides", Gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(Gtk.TreeViewColumn("Description", Gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_description(self.operation, item, None, None, None)
        else:
            desc = self.get_text().strip()
            retval = self.data_model.edit_description(self.operation, item, self.lang.get_text(), desc, self.overrides.get_active())

        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_description.glade"))
        self.wdialog = builder.get_object("dialog:edit_description")
        self.info_box = builder.get_object("dialog:edit_description:info_box")
        self.lang = builder.get_object("dialog:edit_description:lang")
        self.overrides = builder.get_object("dialog:edit_description:overrides")
        self.toolbar = builder.get_object("dialog:edit_description:toolbar")
        self.html_box = builder.get_object("dialog:edit_description:html:box")
        builder.get_object("dialog:edit_description:action:bold").connect("activate", self.on_action, "bold")
        builder.get_object("dialog:edit_description:action:italic").connect("activate", self.on_action, "italic")
        builder.get_object("dialog:edit_description:action:underline").connect("activate", self.on_action, "underline")
        builder.get_object("dialog:edit_description:action:code").connect("activate", self.on_code_set, "code")
        builder.get_object("dialog:edit_description:action:num_list").connect("activate", self.on_action, "InsertOrderedList")
        builder.get_object("dialog:edit_description:action:bul_list").connect("activate", self.on_action, "InsertUnorderedList")
        builder.get_object("dialog:edit_description:action:outdent").connect("activate", self.on_action, "Outdent")
        builder.get_object("dialog:edit_description:action:indent").connect("activate", self.on_action, "Indent")
        builder.get_object("dialog:edit_description:action:link").connect("activate", self.on_link_set)
        builder.get_object("dialog:edit_description:action:zoomin").connect("activate", self.on_zoom)
        builder.get_object("dialog:edit_description:action:zoomout").connect("activate", self.on_zoom)
        builder.get_object("dialog:edit_description:tb:color").connect("clicked", self.on_color_set)
        builder.get_object("dialog:edit_description:tb:font").connect("clicked", self.on_font_set)
        builder.get_object("dialog:edit_description:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_description:btn_ok").connect("clicked", self.__do)
        self.switcher = builder.get_object("dialog:edit_description:switcher")

        self.render(self.html_box, self.toolbar, self.switcher)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
            self.load_html("", "file:///")
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                self.overrides.set_active(model[iter][self.COLUMN_OVERRIDES])
                desc = model[iter][self.COLUMN_TEXT]
                desc = desc.replace("xhtml:","")
                self.load_html(desc or "", "file:///")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                retval = self.dialogDel(self.core.main_window, self.get_selection())
                if retval != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def fill(self):

        self.clear()
        for data in self.data_model.get_descriptions() or []:
            self.append([data.lang, data.overrides, re.sub("[\t ]+" , " ", data.text or "").strip(), data])

class EditWarning(abstract.ListEditor):

    COLUMN_LANG         = 0
    COLUMN_OVERRIDES    = 1
    COLUMN_CATEGORY     = 2
    COLUMN_TEXT         = 3
    COLUMN_OBJ          = 4

    def __init__(self, core, id, widget, data_model):
        
        self.data_model = data_model
        super(EditWarning, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, bool, str, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn("Language", Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn("Overrides", Gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(Gtk.TreeViewColumn("Category", Gtk.CellRendererText(), text=self.COLUMN_CATEGORY))
        self.widget.append_column(Gtk.TreeViewColumn("Warning", Gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        category = None
        buffer = self.warning.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]
        if self.category.get_active() != -1:
            category = self.category.get_model()[self.category.get_active()][0]

        retval = self.data_model.edit_warning(self.operation, item, category, self.lang.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()),
                                              self.overrides.get_active())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_warning.glade"))
        self.wdialog = builder.get_object("dialog:edit_warning")
        self.info_box = builder.get_object("dialog:edit_warning:info_box")
        self.lang = builder.get_object("dialog:edit_warning:lang")
        self.overrides = builder.get_object("dialog:edit_warning:overrides")
        self.warning = builder.get_object("dialog:edit_warning:warning")
        self.category = builder.get_object("dialog:edit_warning:category")
        self.category.set_model(ENUM.WARNING.get_model())
        builder.get_object("dialog:edit_warning:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_warning:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.category.set_active(ENUM.WARNING.pos(model[self.iter][self.COLUMN_OBJ].category) or -1)
                self.overrides.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.warning.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for item in self.data_model.get_warnings() or []:
            category = ENUM.WARNING.map(item.category)
            index = ENUM.WARNING.pos(item.category)
            self.append([item.text.lang, item.text.overrides, category[1], re.sub("[\t ]+" , " ", item.text.text).strip(), item])

class EditStatus(abstract.ListEditor):

    COLUMN_DATE = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditStatus, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn("Date", Gtk.CellRendererText(), text=self.COLUMN_DATE))
        self.widget.append_column(Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        # Check input data
        if self.operation != self.data_model.CMD_OPER_DEL and self.status.get_active() == -1:
            self.core.notify("Status has to be choosen.",
                    core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            self.status.grab_focus()
            return

        item = None
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        year, month, day = self.calendar.get_date()
        retval = self.data_model.edit_status(self.operation, item, "%s-%s-%s" % (year, month, day), self.status.get_active())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_status.glade"))
        self.wdialog = builder.get_object("dialog:edit_status")
        self.info_box = builder.get_object("dialog:edit_status:info_box")
        self.calendar = builder.get_object("dialog:edit_status:calendar")
        self.status = builder.get_object("dialog:edit_status:status")
        self.status.set_model(ENUM.STATUS_CURRENT.get_model())
        builder.get_object("dialog:edit_status:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_status:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            day, month, year = time.strftime("%d %m %Y", time.gmtime()).split()
            self.calendar.select_month(int(month), int(year))
            self.calendar.select_day(int(day))
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                day, month, year = time.strftime("%d %m %Y", time.localtime(model[self.iter][self.COLUMN_OBJ].date)).split()
                self.calendar.select_month(int(month), int(year))
                self.calendar.select_day(int(day))
                self.status.set_active(ENUM.STATUS_CURRENT.pos(model[self.iter][self.COLUMN_OBJ].status) or -1)
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for item in self.data_model.get_statuses() or []:
            status = ENUM.STATUS_CURRENT.map(item.status)
            index = ENUM.STATUS_CURRENT.pos(item.status)
            self.append([time.strftime("%d-%m-%Y", time.localtime(item.date)), status[1], item])

class EditSelectIdDialogWindow(object):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_SELECTED = 2
    
    def __init__(self, item, core, model_conflict, model_item, cb):
        self.core = core
        self.item = item
        self.cb = cb
        self.model_conflict = model_conflict
        self.model_item = model_item
        
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))

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
        self.model_search = Gtk.TreeStore(str, str, bool)
        self.tw_search = builder.get_object("add_id:tw_search")
        
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("ID Item", cell, text=self.COLUMN_ID)
        column.set_resizable(True)
        self.tw_search.append_column(column)

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", cell, text=self.COLUMN_TITLE)
        column.set_expand(True)
        column.set_resizable(True)
        self.tw_search.append_column(column)
        
        self.tw_search.set_model(self.model_search)
        
        #treeView for item, which will be add
        self.model_to_add = Gtk.ListStore(str, str)
        self.tw_add = builder.get_object("add_id:tw_add")
        
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("ID Item", cell, text=self.COLUMN_ID)
        column.set_resizable(True)
        self.tw_add.append_column(column)

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", cell, text=self.COLUMN_TITLE)
        column.set_expand(True)
        column.set_resizable(True)
        self.tw_add.append_column(column)

        self.tw_add.set_model(self.model_to_add)
        
        menu = Gtk.Menu()
        menu_item = Gtk.MenuItem("Remove from add")
        menu_item.show()
        menu.append(menu_item)
        menu_item.connect("activate", self.__cb_del_row)
        self.tw_add.connect ("button_press_event",self.cb_popupMenu_to_add, menu)
        self.tw_add.connect("key-press-event", self.__cb_del_row1,)

        menu_search = Gtk.Menu()
        menu_item = Gtk.MenuItem("Copy to add")
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
        keyname = Gdk.keyval_name(event.keyval)
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
        self.set_transient_for(self.core.main_window)
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
        except Exception as e:
            #self.core.notify("Can't filter items: %s" % (e,), 3)
            logger.exception("Can't filter items: %s" % (e))
            return False

class FindOvalDef(abstract.Window, abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1

    def __init__(self, core, id, data_model):

        self.data_model = data_model
        self.core = core
        abstract.Window.__init__(self, id, core)
        # FIXME: We can't call the constructor of abstract.ListEditor here because it would register our id
        #        and instance again (Window's constructor has already done that)
        self.add_sender(id, "update")

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        (model, iter) = self.definitions.get_selection().get_selected()
        if not iter:
            self.core.notify("You have to choose the definition !",
                    core.Notification.ERROR, self.info_box, msg_id="notify:dialog_notify")
            return
        ret, err = self.data_model.set_item_content(name=model[iter][self.COLUMN_ID])
        self.emit("update")
        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, href):
        """
        """
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:find_definition")
        self.info_box = builder.get_object("dialog:find_definition:info_box")
        self.definitions = builder.get_object("dialog:find_definition:definitions")
        self.search = builder.get_object("dialog:find_definition:search")
        self.search.connect("changed", self.search_treeview, self.definitions)
        builder.get_object("dialog:find_definition:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_definition:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        self.definitions.append_column(Gtk.TreeViewColumn("ID of Definition", Gtk.CellRendererText(), text=self.COLUMN_ID))
        self.definitions.append_column(Gtk.TreeViewColumn("Title", Gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.definitions.set_model(Gtk.ListStore(str, str))
        modelfilter = self.definitions.get_model().filter_new()
        modelfilter.set_visible_func(self.filter_listview, data=(self.search, (0,1)))
        self.definitions.set_model(modelfilter)

        definitions = self.data_model.get_oval_definitions(href)
        for definition in definitions: 
            self.definitions.get_model().get_model().append([definition.id, definition.title])

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()


class FindItem(abstract.Window, abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1
    COLUMN_OBJ      = 2

    def __init__(self, core, id, data_model):

        self.data_model = data_model
        self.core = core
        abstract.Window.__init__(self, id, core)
        # FIXME: We can't call the constructor of abstract.ListEditor here because it would register our id
        #        and instance again (Window's constructor has already done that)
        self.add_sender(id, "update")

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        (model, iter) = self.items.get_selection().get_selected()
        if not iter:
            self.core.notify("You have to chose the item !",
                    core.Notification.ERROR, self.info_box, msg_id="notify:dialog_notify")
            return
        retval = self.data_model.add_refine(model[iter][self.COLUMN_ID], model[iter][self.COLUMN_VALUE], model[iter][self.COLUMN_OBJ])
        if not retval:
            self.core.notify("Item already exists in selected profile.", core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            return
        self.core.selected_item = model[iter][self.COLUMN_ID]
        self.emit("update")
        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, type):
        """
        """
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:find_value")
        self.info_box = builder.get_object("dialog:find_value:info_box")
        self.items = builder.get_object("dialog:find_value:values")
        self.search = builder.get_object("dialog:find_value:search")
        self.search.connect("changed", self.search_treeview, self.items)
        builder.get_object("dialog:find_value:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_value:btn_ok").connect("clicked", self.__do)
        builder.get_object("dialog:find_value:export_name:box").set_property('visible', False)
        builder.get_object("dialog:find_value:export_name:separator").set_property('visible', False)

        self.core.notify_destroy("notify:not_selected")
        self.items.append_column(Gtk.TreeViewColumn("ID", Gtk.CellRendererText(), text=self.COLUMN_ID))
        self.items.append_column(Gtk.TreeViewColumn("Title", Gtk.CellRendererText(), text=self.COLUMN_VALUE))

        if type == "rule":
            items = self.data_model.get_all_item_ids()
        elif type == "value":
            items = [value.to_item() for value in self.data_model.get_all_values()]
        else:
            raise NotImplementedError("Type \"%s\" not supported!" % (type))

        self.items.set_model(Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
        modelfilter = self.items.get_model().filter_new()
        modelfilter.set_visible_func(self.filter_listview, data=(self.search, (0,1)))
        self.items.set_model(modelfilter)

        refines = self.data_model.get_refine_ids(self.data_model.get_profile(self.core.selected_profile))
        for item in items:
            if item.id not in refines:
                title = self.data_model.get_title(item.title)
                self.items.get_model().get_model().append([item.id, title, item])

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()
