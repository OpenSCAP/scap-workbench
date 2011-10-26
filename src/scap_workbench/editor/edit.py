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
        super(EditTitle, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, bool, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_TEXT))

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
        builder = gtk.Builder()
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
        super(EditDescription, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, bool, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=self.COLUMN_TEXT))

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
        builder = gtk.Builder()
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
        super(EditWarning, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, bool, str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Category", gtk.CellRendererText(), text=self.COLUMN_CATEGORY))
        self.widget.append_column(gtk.TreeViewColumn("Warning", gtk.CellRendererText(), text=self.COLUMN_TEXT))

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
        builder = gtk.Builder()
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

class EditNotice(abstract.ListEditor):

    COLUMN_ID = 0
    COLUMN_LANG = -1

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditNotice, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.widget.append_column(gtk.TreeViewColumn("Notice", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        # Check input data
        if self.wid.get_text() == "":
            self.core.notify("ID of the notice is mandatory.",
                    core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            self.wid.grab_focus()
            return
        for iter in self.get_model():
            if iter[self.COLUMN_ID] == self.wid.get_text():
                self.core.notify("ID of the notice has to be unique !",
                        core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                self.wid.grab_focus()
                return

        item = None
        buffer = self.notice.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_notice(self.operation, item, self.wid.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_notice")
        self.info_box = builder.get_object("dialog:edit_notice:info_box")
        self.wid = builder.get_object("dialog:edit_notice:id")
        self.notice = builder.get_object("dialog:edit_notice:notice")
        builder.get_object("dialog:edit_notice:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_notice:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.wid.set_text(model[self.iter][self.COLUMN_ID] or "")
                self.notice.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
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

        self.get_model().clear()
        for data in self.data_model.get_notices() or []:
            self.append([data.id, re.sub("[\t ]+" , " ", data.text.text or "").strip(), data])

class EditStatus(abstract.ListEditor):

    COLUMN_DATE = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditStatus, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Date", gtk.CellRendererText(), text=self.COLUMN_DATE))
        self.widget.append_column(gtk.TreeViewColumn("Status", gtk.CellRendererText(), text=self.COLUMN_TEXT))

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
        builder = gtk.Builder()
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

class EditIdent(abstract.ListEditor):

    COLUMN_ID = 0
    COLUMN_LANG = -1

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditIdent, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.widget.append_column(gtk.TreeViewColumn("System", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        item = None
        buffer = self.system.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            self.data_model.edit_ident(self.operation, item, None, None, None)
        else:
            # Check input data
            if self.wid.get_text() == "":
                self.core.notify("ID of the ident is mandatory.",
                        core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                self.wid.grab_focus()
                return
            if self.operation == self.data_model.CMD_OPER_ADD:
                for iter in self.get_model():
                    if iter[self.COLUMN_ID] == self.wid.get_text():
                        self.core.notify("ID of the ident has to be unique !",
                                core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                        self.wid.grab_focus()
                        return

            retval = self.data_model.edit_ident(self.operation, item, self.wid.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))

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
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_ident.glade"))
        self.wdialog = builder.get_object("dialog:edit_ident")
        self.info_box = builder.get_object("dialog:edit_ident:info_box")
        self.wid = builder.get_object("dialog:edit_ident:id")
        self.system = builder.get_object("dialog:edit_ident:system")
        builder.get_object("dialog:edit_ident:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_ident:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.wid.set_text(model[self.iter][self.COLUMN_ID] or "")
                self.system.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
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

        self.get_model().clear()
        for data in self.data_model.get_idents() or []:
            self.append([data.id, re.sub("[\t ]+" , " ", data.system or "").strip(), data])

class EditQuestion(abstract.ListEditor):

    COLUMN_OVERRIDES = 3
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditQuestion, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Question", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.question.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_question(self.operation, item, self.lang.get_text(),
                self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_question.glade"))
        self.wdialog = builder.get_object("dialog:edit_question")
        self.info_box = builder.get_object("dialog:edit_question:info_box")
        self.lang = builder.get_object("dialog:edit_question:lang")
        self.question = builder.get_object("dialog:edit_question:question")
        self.override = builder.get_object("dialog:edit_question:override")
        builder.get_object("dialog:edit_question:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_question:btn_ok").connect("clicked", self.__do)

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
                self.override.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.question.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
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
            logger.error("Unknown operation for question dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for data in self.data_model.get_questions() or []:
            self.append([data.lang, re.sub("[\t ]+" , " ", data.text).strip(), data, data.overrides])


class EditRationale(abstract.ListEditor):

    COLUMN_OVERRIDES = 3
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditRationale, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Rationale", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        buffer = self.rationale.get_buffer()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_rationale(self.operation, item, self.lang.get_text(),
                self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_rationale")
        self.info_box = builder.get_object("dialog:edit_rationale:info_box")
        self.lang = builder.get_object("dialog:edit_rationale:lang")
        self.rationale = builder.get_object("dialog:edit_rationale:rationale")
        self.override = builder.get_object("dialog:edit_rationale:override")
        builder.get_object("dialog:edit_rationale:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_rationale:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                self.override.set_active(model[iter][self.COLUMN_OVERRIDES])
                self.rationale.get_buffer().set_text(model[iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for rationale dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for data in self.data_model.get_rationales() or []:
            self.append([data.lang, re.sub("[\t ]+" , " ", data.text).strip(), data, data.overrides])


class EditPlatform(abstract.ListEditor):

    COLUMN_TEXT = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model
        super(EditPlatform, self).__init__(id, core, widget=widget, model=gtk.ListStore(str))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("CPE Name", gtk.CellRendererText(), text=self.COLUMN_LANG))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:edit")
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_TEXT]

        if self.operation != self.data_model.CMD_OPER_DEL:
            text = self.cpe.get_text()
            if len(text) < 6 or text[5] not in ["a", "o", "h"]:
                self.core.notify("The part section can be \"a\", \"o\" or \"h\"",
                        core.Notification.ERROR, self.info_box, msg_id="notify:edit")
                return
            if len(text[7:].split(":")) != 6:
                self.core.notify("Invalid number of sections: should be cpe:/part:vendor:product:version:update:edition:lang",
                        core.Notification.ERROR, self.info_box, msg_id="notify:edit")
                return

        retval = self.data_model.edit_platform(self.operation, item, self.cpe.get_text())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def __cb_build(self, widget):
        self.cpe.handler_block_by_func(self.__cb_parse)
        if self.part.get_active() == -1:
            active = ""
        else: active = ["a", "h", "o"][self.part.get_active()]
        self.cpe.set_text("cpe:/%s:%s:%s:%s:%s:%s:%s" % (active, 
            self.vendor.get_text().replace(" ", "_"),
            self.product.get_text().replace(" ", "_"),
            self.version.get_text().replace(" ", "_"),
            self.update.get_text().replace(" ", "_"),
            self.edition.get_text().replace(" ", "_"),
            self.language.get_text().replace(" ", "_")))
        self.cpe.handler_unblock_by_func(self.__cb_parse)

    def __cb_parse(self, widget):
        
        text = widget.get_text()

        # cpe:/
        if text[:5] != "cpe:/": widget.set_text("cpe:/")

        # cpe:/[a,o,h]
        if len(text) > 5:
            if text[5] not in ["a", "o", "h"]: 
                self.core.notify("The part section can be \"a\", \"o\" or \"h\"",
                        core.Notification.ERROR, self.info_box, msg_id="notify:edit")
                widget.set_text("cpe:/")
                return
            else:
                self.core.notify_destroy("notify:edit")
                self.part.set_active(["a", "h", "o"].index(text[5]))

        # cpe:/[a,o,h]:
        if len(text) > 7 and text[6] != ":":
            widget.set_text(text[:6]+":")

        if len(text) > 8:
            parts = text[7:].split(":")
        else: parts = []

        # cpe:/[a,o,h]:vendor:product:version:update:edition:language
        if len(parts) > 0: self.vendor.set_text(parts[0])
        else: self.vendor.set_text("")
        if len(parts) > 1: self.product.set_text(parts[1])
        else: self.product.set_text("")
        if len(parts) > 2: self.version.set_text(parts[2])
        else: self.version.set_text("")
        if len(parts) > 3: self.update.set_text(parts[3])
        else: self.update.set_text("")
        if len(parts) > 4: self.edition.set_text(parts[4])
        else: self.edition.set_text("")
        if len(parts) > 5: self.language.set_text(parts[5])
        else: self.language.set_text("")

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_platform.glade"))
        self.wdialog = builder.get_object("dialog:edit_platform")
        self.info_box = builder.get_object("dialog:edit_platform:info_box")
        self.cpe = builder.get_object("dialog:edit_platform:cpe")
        self.part = builder.get_object("dialog:edit_platform:cpe_part")
        self.vendor = builder.get_object("dialog:edit_platform:cpe_vendor")
        self.product = builder.get_object("dialog:edit_platform:cpe_product")
        self.version = builder.get_object("dialog:edit_platform:cpe_version")
        self.update = builder.get_object("dialog:edit_platform:cpe_update")
        self.edition = builder.get_object("dialog:edit_platform:cpe_edition")
        self.language = builder.get_object("dialog:edit_platform:cpe_language")
        builder.get_object("dialog:edit_platform:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_platform:btn_ok").connect("clicked", self.__do)

        self.cpe.set_text("cpe:/")
        self.cpe.connect("changed", self.__cb_parse)
        self.part.connect("changed", self.__cb_build)
        self.vendor.connect("changed", self.__cb_build)
        self.product.connect("changed", self.__cb_build)
        self.version.connect("changed", self.__cb_build)
        self.update.connect("changed", self.__cb_build)
        self.edition.connect("changed", self.__cb_build)
        self.language.connect("changed", self.__cb_build)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.cpe.set_text(model[iter][self.COLUMN_TEXT])
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for rationale dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):
        self.clear()
        for item in self.data_model.get_platforms() or []:
            self.get_model().append([item])

class EditValues(abstract.MenuButton, abstract.Func):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_TYPE_ITER = 2
    COLUMN_TYPE_TEXT = 3
    COLUMN_OBJECT = 4
    COLUMN_CHECK = 5
    COLUMN_CHECK_EXPORT = 6
    
    def __init__(self, core, id, builder):
        # FIXME: We are not calling constructor of abstract.MenuButton, this could backfire sometime in the future!
        abstract.Func.__init__(self, core)

        self.data_model = commands.DHValues(core) 
        self.builder = builder
        self.id = id

        # FIXME: Calling constructors of classes that are not direct ancestors!
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(id, "update_item")
        
        #edit data of values
        # -- VALUES --
        self.values = builder.get_object("edit:values")

        # -- TITLE --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:values:titles", builder.get_object("edit:values:titles"), self.data_model)
        self.builder.get_object("edit:values:titles:btn_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:values:titles:btn_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:values:titles:btn_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:values:descriptions", builder.get_object("edit:values:descriptions"), self.data_model)
        self.builder.get_object("edit:values:descriptions:btn_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:values:descriptions:btn_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:values:descriptions:btn_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("edit:values:descriptions:btn_preview").connect("clicked", self.descriptions.preview)

        # -- WARNING --
        self.warnings = EditWarning(self.core, "gui:edit:xccdf:values:warnings", builder.get_object("edit:values:warnings"), self.data_model)
        builder.get_object("edit:values:warnings:btn_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:warnings:btn_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:warnings:btn_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- STATUS --
        self.statuses = EditStatus(self.core, "gui:edit:xccdf:values:statuses", builder.get_object("edit:values:statuses"), self.data_model)
        builder.get_object("edit:values:statuses:btn_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:statuses:btn_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:statuses:btn_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

        # -- QUESTIONS --
        self.questions = EditQuestion(self.core, "gui:edit:xccdf:values:questions", builder.get_object("edit:values:questions"), self.data_model)
        builder.get_object("edit:values:questions:btn_add").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:questions:btn_edit").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:questions:btn_del").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_DEL)

        # -- VALUES --
        self.values_values = EditValuesValues(self.core, "gui:edit:xccdf:values:values", builder.get_object("edit:values:values"), self.data_model)
        builder.get_object("edit:values:values:btn_add").connect("clicked", self.values_values.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:values:btn_edit").connect("clicked", self.values_values.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:values:btn_del").connect("clicked", self.values_values.dialog, self.data_model.CMD_OPER_DEL)
        # -------------
        
        self.vid = self.builder.get_object("edit:values:id")
        self.vid.connect("focus-out-event", self.__change)
        self.vid.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("edit:values:version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.version_time = self.builder.get_object("edit:values:version_time")
        self.version_time.connect("focus-out-event", self.__change)
        self.version_time.connect("key-press-event", self.__change)
        self.cluster_id = self.builder.get_object("edit:values:cluster_id")
        self.cluster_id.connect("focus-out-event", self.__change)
        self.cluster_id.connect("key-press-event", self.__change)
        self.vtype = self.builder.get_object("edit:values:type")
        self.operator = self.builder.get_object("edit:values:operator")
        self.operator.connect("changed", self.__change)
        self.abstract = self.builder.get_object("edit:values:abstract")
        self.abstract.connect("toggled", self.__change)
        self.prohibit_changes = self.builder.get_object("edit:values:prohibit_changes")
        self.prohibit_changes.connect("toggled", self.__change)
        self.interactive = self.builder.get_object("edit:values:interactive")
        self.interactive.connect("toggled", self.__change)

        self.operator.set_model(ENUM.OPERATOR.get_model())
        
    def show(self, active):
        self.values.set_sensitive(active)
        self.values.set_property("visible", active)

    def update(self):
        self.__update()

    def __change(self, widget, event=None):

        item = self.data_model.get_item(self.core.selected_item)
        if item.type != openscap.OSCAP.XCCDF_VALUE: return

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        if widget == self.vid:
            retval = self.data_model.edit_value(id=widget.get_text())
            if not retval:
                self.notifications.append(self.core.notify("Setting ID failed: ID \"%s\" already exists." % (widget.get_text(),),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                widget.set_text(self.core.selected_item)
                return
            self.emit("update_item")
        elif widget == self.version:
            self.data_model.edit_value(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp > 0:
                self.data_model.edit_value(version_time=timestamp)
        elif widget == self.cluster_id:
            self.data_model.edit_value(cluster_id=widget.get_text())
        elif widget == self.operator:
            self.data_model.edit_value(operator=ENUM.OPERATOR[widget.get_active()][0])
        elif widget == self.abstract:
            self.data_model.edit_value(abstract=widget.get_active())
        elif widget == self.prohibit_changes:
            self.data_model.edit_value(prohibit_changes=widget.get_active())
        elif widget == self.interactive:
            self.data_model.edit_value(interactive=widget.get_active())
        else: 
            logger.error("Change: not supported object in \"%s\"" % (widget,))
            return

    def __block_signals(self):

        self.operator.handler_block_by_func(self.__change)
        self.interactive.handler_block_by_func(self.__change)
        self.version.handler_block_by_func(self.__change)
        self.version_time.handler_block_by_func(self.__change)
        self.vid.handler_block_by_func(self.__change)
        self.cluster_id.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.operator.handler_unblock_by_func(self.__change)
        self.interactive.handler_unblock_by_func(self.__change)
        self.version.handler_unblock_by_func(self.__change)
        self.version_time.handler_unblock_by_func(self.__change)
        self.cluster_id.handler_unblock_by_func(self.__change)

    def __clear(self):
        self.__block_signals()
        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.statuses.clear()
        self.questions.clear()
        self.values_values.clear()
        self.__unblock_signals()

    def __update(self):

        self.__block_signals()
        details = self.data_model.get_item_details(self.core.selected_item)

        self.values.set_sensitive(details != None)

        if details:

            """It depends on value type what details should
            be filled and sensitive to user actions"""
            # TODO

            self.vid.set_text(details["id"] or "")
            self.version.set_text(details["version"] or "")
            self.version_time.set_text("" if details["version_time"] <= 0 else str(datetime.date.fromtimestamp(details["version_time"])))
            self.cluster_id.set_text(details["cluster_id"] or "")
            self.vtype.set_text(ENUM.TYPE.map(details["vtype"])[1])
            self.abstract.set_active(details["abstract"])
            self.prohibit_changes.set_active(details["prohibit_changes"])
            self.interactive.set_active(details["interactive"])
            self.operator.set_active(ENUM.OPERATOR.pos(details["oper"]))
            self.titles.fill()
            self.descriptions.fill()
            self.warnings.fill()
            self.statuses.fill()
            self.questions.fill()
            self.values_values.fill()
        self.__unblock_signals()

            
class EditValuesValues(abstract.ListEditor):

    COLUMN_SELECTOR     = 0
    COLUMN_VALUE        = 1
    COLUMN_DEFAULT      = 2
    COLUMN_LOWER_BOUND  = 3
    COLUMN_UPPER_BOUND  = 4
    COLUMN_MUST_MATCH   = 5
    COLUMN_MATCH        = 6
    COLUMN_OBJ          = 7
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditValuesValues, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, str, str, str, bool, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Selector", gtk.CellRendererText(), text=self.COLUMN_SELECTOR))
        self.widget.append_column(gtk.TreeViewColumn("Value", gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.widget.append_column(gtk.TreeViewColumn("Default", gtk.CellRendererText(), text=self.COLUMN_DEFAULT))
        self.widget.append_column(gtk.TreeViewColumn("Lower bound", gtk.CellRendererText(), text=self.COLUMN_LOWER_BOUND))
        self.widget.append_column(gtk.TreeViewColumn("Upper bound", gtk.CellRendererText(), text=self.COLUMN_UPPER_BOUND))
        self.widget.append_column(gtk.TreeViewColumn("Must match", gtk.CellRendererText(), text=self.COLUMN_MUST_MATCH))
        self.widget.append_column(gtk.TreeViewColumn("Match", gtk.CellRendererText(), text=self.COLUMN_MATCH))

    def __do(self, widget=None):
        """
        """
        # Check input data
        (model, iter) = self.get_selection().get_selected()
        item = None
        if iter:
            item = model[iter][self.COLUMN_OBJ]

        for inst in model:
            if self.selector.get_text() == inst[0] and model[iter][self.COLUMN_SELECTOR] != self.selector.get_text():
                self.core.notify("Selector \"%s\" is already used !" % (inst[0],),
                        core.Notification.ERROR, self.info_box, msg_id="dialog:add_value")
                self.selector.grab_focus()
                self.selector.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
                return
        self.selector.modify_base(gtk.STATE_NORMAL, self.__entry_style)
        
        if self.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
            retval = self.data_model.edit_value_of_value(self.operation, item, self.selector.get_text(),
                    self.value_bool.get_active(), self.default_bool.get_active(),
                    self.match.get_text(), None, None, self.must_match.get_active())
        
        elif self.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            def safe_float(x, fallback = None):
                try:
                    return float(x)
                
                except ValueError:
                    return fallback
            
            retval = self.data_model.edit_value_of_value(self.operation, item, self.selector.get_text(),
                    safe_float(self.value.get_text(), 0), safe_float(self.default.get_text(), 0), self.match.get_text(),
                    safe_float(self.upper_bound.get_text()), safe_float(self.lower_bound.get_text()),
                    self.must_match.get_active())
        
        elif self.type == openscap.OSCAP.XCCDF_TYPE_STRING:
            retval = self.data_model.edit_value_of_value(self.operation, item, self.selector.get_text(),
                    self.value.get_text(), self.default.get_text(), self.match.get_text(), None,
                    None, self.must_match.get_active())
        
        else:
            raise NotImplementedError("Unknown value type '%i'" % (self.type))
        
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
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_value.glade"))
        self.wdialog = builder.get_object("dialog:edit_value")
        self.info_box = builder.get_object("dialog:edit_value:info_box")
        self.selector = builder.get_object("dialog:edit_value:selector")
        self.value = builder.get_object("dialog:edit_value:value")
        self.value_bool = builder.get_object("dialog:edit_value:value:bool")
        self.default = builder.get_object("dialog:edit_value:default")
        self.default_bool = builder.get_object("dialog:edit_value:default:bool")
        self.match = builder.get_object("dialog:edit_value:match")
        self.upper_bound = builder.get_object("dialog:edit_value:upper_bound")
        self.lower_bound = builder.get_object("dialog:edit_value:lower_bound")
        self.must_match = builder.get_object("dialog:edit_value:must_match")
        self.choices = builder.get_object("dialog:edit_value:choices")
        builder.get_object("dialog:edit_value:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_value:btn_ok").connect("clicked", self.__do)

        self.__entry_style = self.selector.get_style().base[gtk.STATE_NORMAL]

        # Upper and lower bound should be disabled if value is not a number
        item = self.data_model.get_item_details(self.core.selected_item)
        self.type = item["vtype"]
        if self.type != openscap.OSCAP.XCCDF_TYPE_NUMBER:
            self.upper_bound.set_sensitive(False)
            self.lower_bound.set_sensitive(False)

        # Different widgets for different type boolean or other
        boolean = (self.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN)
        self.value.set_property('visible', not boolean)
        self.default.set_property('visible', not boolean)
        self.value_bool.set_property('visible', boolean)
        self.default_bool.set_property('visible', boolean)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.selector.set_text(model[iter][self.COLUMN_SELECTOR] or "")
                self.value.set_text(model[iter][self.COLUMN_VALUE] or "")
                self.default.set_text(model[iter][self.COLUMN_DEFAULT] or "")
                self.match.set_text(model[iter][self.COLUMN_MATCH] or "")
                self.upper_bound.set_text(model[iter][self.COLUMN_UPPER_BOUND] or "")
                self.lower_bound.set_text(model[iter][self.COLUMN_LOWER_BOUND] or "")
                self.must_match.set_active(model[iter][self.COLUMN_MUST_MATCH])
                for choice in model[iter][self.COLUMN_OBJ].choices:
                    self.choices.get_model().append([choice])
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for values dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def fill(self):

        self.clear()
        for instance in self.data_model.get_value_instances() or []:
            self.append([instance["selector"], 
                         instance["value"], 
                         instance["defval"], 
                         instance["lower_bound"], 
                         instance["upper_bound"], 
                         instance["must_match"], 
                         instance["match"], 
                         instance["item"]])

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
        
        builder = gtk.Builder()
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
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:find_definition")
        self.info_box = builder.get_object("dialog:find_definition:info_box")
        self.definitions = builder.get_object("dialog:find_definition:definitions")
        self.search = builder.get_object("dialog:find_definition:search")
        self.search.connect("changed", self.search_treeview, self.definitions)
        builder.get_object("dialog:find_definition:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_definition:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        self.definitions.append_column(gtk.TreeViewColumn("ID of Definition", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.definitions.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.definitions.set_model(gtk.ListStore(str, str))
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
        builder = gtk.Builder()
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
        self.items.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.items.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))

        if type == "rule":
            items = self.data_model.get_all_item_ids()
        elif type == "value":
            items = [value.to_item() for value in self.data_model.get_all_values()]
        else:
            raise NotImplementedError("Type \"%s\" not supported!" % (type))

        self.items.set_model(gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
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
