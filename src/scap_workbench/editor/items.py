# -*- coding: utf-8 -*-
#
# Copyright 2011 Red Hat Inc., Durham, North Carolina.
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
#      Martin Preisler      <mpreisle@redhat.com>

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

from datetime import datetime

from scap_workbench import core
from scap_workbench import paths
from scap_workbench import l10n
from scap_workbench.core import enum as ENUM
from scap_workbench.core import abstract
from scap_workbench.core import commands
from scap_workbench.core.events import EventObject
from scap_workbench.editor import edit
from scap_workbench.core.logger import LOGGER

import os.path
import re

import openscap_api as openscap

class AddItem(EventObject):

    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2

    def __init__(self, core, data_model, list_item):
        super(AddItem, self).__init__(core)

        self.data_model = data_model
        self.list_item = list_item
        self.view = list_item.get_TreeView()

    def dialog(self):
        builder = Gtk.Builder()
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "add_item.glade"))

        self.window = builder.get_object("dialog:add_item")
        self.window.connect("delete-event", self.__delete_event)

        btn_ok = builder.get_object("dialog:add_item:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("dialog:add_item:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)

        self.itype = builder.get_object("dialog:add_item:type")
        self.itype.connect("changed", self.__cb_changed_type)
        self.vtype_lbl = builder.get_object("dialog:add_item:value_type:lbl")
        self.vtype = builder.get_object("dialog:add_item:value_type")
        self.iid = builder.get_object("dialog:add_item:id")
        self.lang = builder.get_object("dialog:add_item:lang")
        self.lang.set_text(self.core.selected_lang)
        self.lang.set_sensitive(False)
        self.title = builder.get_object("dialog:add_item:title")
        self.relation = builder.get_object("dialog:add_item:relation")
        self.relation.connect("changed", self.__cb_changed_relation)
        self.info_box = builder.get_object("dialog:add_item:info_box")

        self.__entry_style = self.iid.get_style().base[Gtk.StateType.NORMAL]

        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __cb_changed_relation(self, widget):

        self.core.notify_destroy("notify:relation")
        (model, iterator) = self.view.get_selection().get_selected()
        if not iterator:
            if widget.get_active() in [self.data_model.RELATION_PARENT, self.data_model.RELATION_SIBLING]:
                self.core.notify(_("Item can't be a parent or sibling of benchmark!"),
                        core.Notification.ERROR, self.info_box, msg_id="notify:relation")
                widget.grab_focus()
                return False
        else:
            self.core.notify_destroy("dialog:add_item")
            if model[iterator][self.data_model.COLUMN_TYPE] in ["value", "rule"] and widget.get_active() == self.data_model.RELATION_CHILD:
                self.core.notify(_("Item types VALUE and RULE can't be a parent!"),
                        core.Notification.ERROR, self.info_box, msg_id="notify:relation")
                widget.grab_focus()
                return False

        return True

    def __cb_changed_type(self, widget):

        self.core.notify_destroy("dialog:add_item")
        self.vtype_lbl.set_property("visible", widget.get_active() == self.data_model.TYPE_VALUE)
        self.vtype.set_property('visible', widget.get_active() == self.data_model.TYPE_VALUE)

    def __cb_do(self, widget):

        self.core.notify_destroy("dialog:add_item")
        tagOK = True
        itype = self.itype.get_active()
        vtype = self.vtype.get_active()
        relation = self.relation.get_active()
        if not self.__cb_changed_relation(self.relation):
            return

        if itype == -1:
            self.core.notify(_("Relation has to be chosen"),
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.itype.grab_focus()
            return

        if itype == self.data_model.TYPE_VALUE:
            if vtype == -1:
                self.core.notify(_("Type of value has to be chosen"),
                        core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
                self.vtype.grab_focus()
                return

        if relation == -1:
            self.core.notify(_("Relation has to be chosen"),
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.relation.grab_focus()
            return

        if self.iid.get_text() == "":
            self.core.notify(_("The ID of item is mandatory!"),
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.iid.grab_focus()
            self.iid.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#FFC1C2"))
            return
        elif self.data_model.get_item_details(self.iid.get_text()):
            self.core.notify(_("ID already exists"),
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.iid.grab_focus()
            self.iid.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#FFC1C2"))
            return
        else:
            self.iid.modify_base(Gtk.StateType.NORMAL, self.__entry_style)

        if self.title.get_text() == "":
            self.core.notify(_("The title of item is mandatory!"),
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.title.grab_focus()
            self.title.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#FFC1C2"))
            return
        else:
            self.title.modify_base(Gtk.StateType.NORMAL, self.__entry_style)

        if relation == self.data_model.RELATION_PARENT:
            self.core.notify(_("Relation PARENT is not implemented yet"),
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.relation.grab_focus()
            return

        item = {"id": self.iid.get_text(),
                "lang": self.lang.get_text(),
                "title": self.title.get_text()}
        retval = self.data_model.add_item(item, itype, relation, vtype)
        if retval: self.list_item.emit("update") # TODO: HACK
        self.window.destroy()

    def __delete_event(self, widget, event=None):
        self.core.notify_destroy("dialog:add_item")
        self.window.destroy()

class EditConflicts(commands.DHEditItems, abstract.ControlEditWindow):

    COLUMN_ID = 0

    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_conflict")
        model = Gtk.ListStore(str)
        lv.set_model(model)

        commands.DHEditItems.__init__(self, core)
        abstract.ControlEditWindow.__init__(self, core, lv, None)

        btn_add = builder.get_object("edit:dependencies:btn_conflict_add")
        btn_del = builder.get_object("edit:dependencies:btn_conflict_del")

        # set callBack to btn
        btn_add.connect("clicked", self.__cb_add)
        btn_del.connect("clicked", self.__cb_del_row)

        self.addColumn("ID Item",self.COLUMN_ID)

    def fill(self, details):
        if details == None:
            return
        self.item = details["item"]
        self.model.clear()
        for data in details["conflicts"]:
            self.model.append([data])

    def __cb_add(self, widget):
        # unimplemented
        dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, _("Not implemented!"))
        dialog.format_secondary_text(
            _("Sorry, manipulating conflicts is not implemented yet!"))
        dialog.run()
        dialog.destroy()

        #edit.EditSelectIdDialogWindow(self.item, self.core, self.model, self.model_item, self.DHEditConflicts)

    def __cb_del_row(self, widget):
        pass

class EditRequires(commands.DHEditItems, abstract.ControlEditWindow):

    COLUMN_ID = 0

    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_requires")
        model = Gtk.ListStore(str)
        lv.set_model(model)

        commands.DHEditItems.__init__(self, core)
        abstract.ControlEditWindow.__init__(self, core, lv, None)

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
        # unimplemented
        dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, _("Not implemented!"))
        dialog.format_secondary_text(
            _("Sorry, manipulating requires is not implemented yet!"))
        dialog.run()
        dialog.destroy()

        #edit.EditSelectIdDialogWindow(self.item, self.core, self.model, self.model_item, self.DHEditRequires)

    def __cb_del_row(self, widget):
        pass

class EditItemValues(abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1
    COLUMN_EXPORT   = 2
    COLUMN_OBJ      = 3
    COLUMN_COLOR    = 4

    def __init__(self, core, id, widget, data_model):
        super(EditItemValues, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, str, GObject.TYPE_PYOBJECT, str, str))

        self.data_model = data_model

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        item = None
        (model, iterator) = self.values.get_selection().get_selected()
        if iterator:
            item = model[iterator][self.COLUMN_ID]
        elif self.operation != self.data_model.CMD_OPER_EDIT:
            self.core.notify(_("Value has to be chosen."), core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            return

        if self.operation == self.data_model.CMD_OPER_EDIT:
            self.data_model.item_edit_value(self.operation, self.search.get_text(), self.export_name.get_text())
        else:
            self.data_model.item_edit_value(self.operation, item, self.export_name.get_text())
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
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))

        self.wdialog = builder.get_object("dialog:find_value")
        self.info_box = builder.get_object("dialog:find_value:info_box")
        self.values = builder.get_object("dialog:find_value:values")
        self.export_name = builder.get_object("dialog:find_value:export_name")
        self.search = builder.get_object("dialog:find_value:search")
        self.search.connect("changed", self.search_treeview, self.values)
        builder.get_object("dialog:find_value:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_value:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iterator) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            self.values.append_column(Gtk.TreeViewColumn(_("ID of Value"), Gtk.CellRendererText(), text=self.COLUMN_ID))
            self.values.append_column(Gtk.TreeViewColumn(_("Title"), Gtk.CellRendererText(), text=self.COLUMN_VALUE))
            values = self.data_model.get_all_values()
            self.values.set_model(Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
            modelfilter = self.values.get_model().filter_new()
            modelfilter.set_visible_func(self.filter_listview, (self.search, (0,1)))
            self.values.set_model(modelfilter)
            for value in values:
                item = self.data_model.parse_value(value)
                if len(item["titles"]) > 0:
                    if self.core.selected_lang in item["titles"].keys(): title = item["titles"][self.core.selected_lang]
                    else: title = item["titles"][item["titles"].keys()[0]]+" ["+item["titles"].keys()[0]+"]"
                self.values.get_model().get_model().append([value.id, title, value])

            self.wdialog.set_transient_for(self.core.main_window)
            self.wdialog.show_all()
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            self.values.append_column(Gtk.TreeViewColumn(_("ID of Value"), Gtk.CellRendererText(), text=self.COLUMN_ID))
            self.values.append_column(Gtk.TreeViewColumn(_("Title"), Gtk.CellRendererText(), text=self.COLUMN_VALUE))
            values = self.data_model.get_all_values()
            self.values.set_model(Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
            modelfilter = self.values.get_model().filter_new()
            modelfilter.set_visible_func(self.filter_listview, (self.search, (0,1)))
            self.values.set_model(modelfilter)
            for value in values:
                item = self.data_model.parse_value(value)
                if len(item["titles"]) > 0:
                    if self.core.selected_lang in item["titles"].keys(): title = item["titles"][self.core.selected_lang]
                    else: title = item["titles"][item["titles"].keys()[0]]+" ["+item["titles"].keys()[0]+"]"
                self.values.get_model().get_model().append([value.id, title, value])

            self.search.set_text(model[iterator][self.COLUMN_ID])
            self.values.get_model().refilter()
            self.values.set_sensitive(False)
            self.search.set_sensitive(False)
            self.export_name.set_text(model[iterator][self.COLUMN_EXPORT])
            self.wdialog.set_transient_for(self.core.main_window)
            self.wdialog.show_all()

        elif operation == self.data_model.CMD_OPER_BIND:
            self.values.append_column(Gtk.TreeViewColumn(_("ID of Value"), Gtk.CellRendererText(), text=self.COLUMN_ID))
            self.values.append_column(Gtk.TreeViewColumn(_("Title"), Gtk.CellRendererText(), text=self.COLUMN_VALUE))
            self.values.set_sensitive(False)

            self.wdialog.set_transient_for(self.core.main_window)
            self.wdialog.show_all()

        elif operation == self.data_model.CMD_OPER_DEL:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                iterator = self.dialogDel(self.core.main_window, self.get_selection())
                if iterator is not None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for title dialog: \"%s\"" % (operation,))
            return

    def fill(self):
        """
        """
        self.clear()
        ref = ""
        for check in self.data_model.get_item_check_exports() or []:
            item = self.data_model.get_item(check[0])
            if item:
                title = self.data_model.get_title(item.title) or ""
                self.append([check[0], (" ".join(title.split())), check[1], item, None, None])
            else:
                self.append([check[0], _("(Missing item)"), check[1], None, "red", "white"])


class EditFixtext(abstract.HTMLEditor):

    COLUMN_LANG = 0
    COLUMN_TEXT = 1
    COLUMN_OBJ  = 2

    def __init__(self, core, id, widget, data_model, builder):

        self.data_model = data_model
        self.builder = builder
        super(EditFixtext, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("Language"), Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn(_("Description"), Gtk.CellRendererText(), text=self.COLUMN_TEXT))

        # Here are all attributes of fixtext
        self.__attr_frame = self.builder.get_object("items:fixtext")
        self.__attr_frame.set_sensitive(False)
        self.__attr_fixref = self.builder.get_object("items:fixtext:fixref")
        self.__attr_fixref.connect("focus-out-event", self.__change)
        self.__attr_fixref.connect("key-press-event", self.__change)
        self.__attr_strategy = self.builder.get_object("items:fixtext:strategy")
        self.__attr_strategy.set_model(ENUM.STRATEGY.get_model())
        self.__attr_strategy.connect( "changed", self.__change)
        self.__attr_complexity = self.builder.get_object("items:fixtext:complexity")
        self.__attr_complexity.set_model(ENUM.COMPLEXITY.get_model())
        self.__attr_complexity.connect( "changed", self.__change)
        self.__attr_disruption = self.builder.get_object("items:fixtext:disruption")
        self.__attr_disruption.set_model(ENUM.DISRUPTION.get_model())
        self.__attr_disruption.connect( "changed", self.__change)
        self.__attr_reboot = self.builder.get_object("items:fixtext:reboot")
        self.__attr_reboot.connect("toggled", self.__change)
        self.__attr_overrides = self.builder.get_object("items:fixtext:overrides")
        self.__attr_overrides.connect("toggled", self.__change)

        self.widget.get_selection().connect("changed", self.__attr_fill)

    def __change(self, widget, event=None):

        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval != Gdk.KEY_Return:
            return

        (model, iterator) = self.get_selection().get_selected()
        if not iterator:
            LOGGER.debug("Changing attribute of fixtext failed. HINT: Use enter to save your changes")
            return
        data = model[iterator][self.COLUMN_OBJ]

        if widget == self.__attr_fixref:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, fixref=widget.get_text())
        elif widget == self.__attr_strategy:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, strategy=ENUM.STRATEGY.value(widget.get_active()))
        elif widget == self.__attr_complexity:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, complexity=ENUM.COMPLEXITY.value(widget.get_active()))
        elif widget == self.__attr_disruption:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, disruption=ENUM.DISRUPTION.value(widget.get_active()))
        elif widget == self.__attr_reboot:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, reboot=widget.get_active())
        elif widget == self.__attr_overrides:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, overrides=widget.get_active())
        else:
            LOGGER.error("Change of \"%s\" is not supported " % (widget,))
            return


    def __do(self, widget=None):
        """
        """
        item = None
        (model, iterator) = self.get_selection().get_selected()
        if iterator and model is not None:
            item = model[iterator][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_fixtext(self.operation, item, None, None)
        else:
            desc = self.get_text()
            retval = self.data_model.edit_fixtext(self.operation, item, self.lang.get_text(), desc)

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
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "edit_description.glade"))

        self.wdialog = builder.get_object("dialog:edit_description")
        self.info_box = builder.get_object("dialog:edit_description:info_box")
        self.lang = builder.get_object("dialog:edit_description:lang")
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
        (model, iterator) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
            self.load_html("", "file:///")
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iterator][self.COLUMN_LANG] or "")
                desc = model[iterator][self.COLUMN_TEXT]
                desc = desc.replace("xhtml:","")
                self.load_html(desc or "", "file:///")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                retval = self.dialogDel(self.core.main_window, self.get_selection())
                if retval != None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def __block_signals(self):
        self.__attr_fixref.handler_block_by_func(self.__change)
        self.__attr_strategy.handler_block_by_func(self.__change)
        self.__attr_complexity.handler_block_by_func(self.__change)
        self.__attr_disruption.handler_block_by_func(self.__change)
        self.__attr_reboot.handler_block_by_func(self.__change)
        self.__attr_overrides.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.__attr_fixref.handler_unblock_by_func(self.__change)
        self.__attr_strategy.handler_unblock_by_func(self.__change)
        self.__attr_complexity.handler_unblock_by_func(self.__change)
        self.__attr_disruption.handler_unblock_by_func(self.__change)
        self.__attr_reboot.handler_unblock_by_func(self.__change)
        self.__attr_overrides.handler_unblock_by_func(self.__change)

    def __attrs_clear(self):
        self.__block_signals()
        self.__attr_frame.set_sensitive(False)
        self.__attr_fixref.set_text("")
        self.__attr_strategy.set_active(-1)
        self.__attr_complexity.set_active(-1)
        self.__attr_disruption.set_active(-1)
        self.__attr_reboot.set_active(False)
        self.__attr_overrides.set_active(False)
        self.__unblock_signals()

    def __attr_fill(self, widget=None):

        (model, iterator) = self.get_selection().get_selected()

        self.__attr_frame.set_sensitive(iterator is not None)
        if not iterator:
            return

        data = model[iterator][self.COLUMN_OBJ]

        self.__block_signals()
        self.__attr_fixref.set_text(data.fixref or "")
        self.__attr_strategy.set_active(ENUM.STRATEGY.pos(data.strategy))
        self.__attr_complexity.set_active(ENUM.COMPLEXITY.pos(data.complexity))
        self.__attr_disruption.set_active(ENUM.DISRUPTION.pos(data.disruption))
        self.__attr_reboot.set_active(data.reboot)
        self.__attr_overrides.set_active(data.text.overrides)
        self.__unblock_signals()

    def fill(self):
        self.clear()
        self.__attrs_clear()

        for data in self.data_model.get_fixtexts() or []:
            self.append([data.text.lang, re.sub("[\t ]+" , " ", data.text.text or "").strip(), data])

class EditFix(abstract.ListEditor):

    COLUMN_ID   = 0
    COLUMN_TEXT = 1
    COLUMN_OBJ  = 2

    def __init__(self, core, id, widget, data_model, builder):

        self.data_model = data_model
        self.builder = builder
        super(EditFix, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("ID"), Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn(_("Content"), Gtk.CellRendererText(), text=self.COLUMN_TEXT))

        """ Here are all attributes of fix
        """
        self.__attr_frame = self.builder.get_object("items:fix")
        self.__attr_frame.set_sensitive(False)
        self.__attr_system = self.builder.get_object("items:fix:system")
        self.__attr_system.connect("focus-out-event", self.__change)
        self.__attr_system.connect("key-press-event", self.__change)
        self.__attr_platform = self.builder.get_object("items:fix:platform")
        self.__attr_platform.connect("focus-out-event", self.__change)
        self.__attr_platform.connect("key-press-event", self.__change)
        self.__attr_strategy = self.builder.get_object("items:fix:strategy")
        self.__attr_strategy.set_model(ENUM.STRATEGY.get_model())
        self.__attr_strategy.connect( "changed", self.__change)
        self.__attr_complexity = self.builder.get_object("items:fix:complexity")
        self.__attr_complexity.set_model(ENUM.LEVEL.get_model())
        self.__attr_complexity.connect( "changed", self.__change)
        self.__attr_disruption = self.builder.get_object("items:fix:disruption")
        self.__attr_disruption.set_model(ENUM.LEVEL.get_model())
        self.__attr_disruption.connect( "changed", self.__change)
        self.__attr_reboot = self.builder.get_object("items:fix:reboot")
        self.__attr_reboot.connect("toggled", self.__change)

        self.widget.get_selection().connect("changed", self.__attr_fill)

    def __change(self, widget, event=None):

        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval != Gdk.KEY_Return:
            return

        (model, iterator) = self.get_selection().get_selected()
        if not iterator:
            LOGGER.debug("Changing attribute of fix failed. HINT: Use enter to save your changes")
            return
        data = model[iterator][self.COLUMN_OBJ]

        if widget == self.__attr_system:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, system=widget.get_text())
        elif widget == self.__attr_platform:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, platform=widget.get_text())
        elif widget == self.__attr_strategy:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, strategy=ENUM.STRATEGY.value(widget.get_active()))
        elif widget == self.__attr_complexity:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, complexity=ENUM.LEVEL.value(widget.get_active()))
        elif widget == self.__attr_disruption:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, disruption=ENUM.LEVEL.value(widget.get_active()))
        elif widget == self.__attr_reboot:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, reboot=widget.get_active())
        else:
            LOGGER.error("Change of \"%s\" is not supported " % (widget,))
            return


    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:xccdf:id")
        item = None
        (model, iterator) = self.get_selection().get_selected()
        if iterator and model is not None:
            item = model[iterator][self.COLUMN_OBJ]

        text_id = self.fid.get_text()
        if len(text_id) != 0 and re.search("[A-Za-z_]", text_id[0]) == None:
            self.core.notify(_("First character of ID has to be from A-Z (case insensitive) or \"_\""),
                core.Notification.ERROR, msg_id="notify:xccdf:id")
            return

        buffer = self.content.get_buffer()
        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_fix(self.operation, fix=item)
        else:
            retval = self.data_model.edit_fix(self.operation, fix=item, id=text_id, content=buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))

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
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))

        self.wdialog = builder.get_object("dialog:edit_fix")
        self.info_box = builder.get_object("dialog:edit_fix:info_box")
        self.fid = builder.get_object("dialog:edit_fix:id")
        self.content = builder.get_object("dialog:edit_fix:content")
        builder.get_object("dialog:edit_fix:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_fix:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iterator) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.fid.set_text(model[iterator][self.COLUMN_ID] or "")
                self.content.get_buffer().set_text(model[iterator][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                retval = self.dialogDel(self.core.main_window, self.get_selection())
                if retval != None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for fix content dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def __block_signals(self):
        self.__attr_system.handler_block_by_func(self.__change)
        self.__attr_platform.handler_block_by_func(self.__change)
        self.__attr_strategy.handler_block_by_func(self.__change)
        self.__attr_complexity.handler_block_by_func(self.__change)
        self.__attr_disruption.handler_block_by_func(self.__change)
        self.__attr_reboot.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.__attr_system.handler_unblock_by_func(self.__change)
        self.__attr_platform.handler_unblock_by_func(self.__change)
        self.__attr_strategy.handler_unblock_by_func(self.__change)
        self.__attr_complexity.handler_unblock_by_func(self.__change)
        self.__attr_disruption.handler_unblock_by_func(self.__change)
        self.__attr_reboot.handler_unblock_by_func(self.__change)

    def __attrs_clear(self):
        self.__block_signals()
        self.__attr_frame.set_sensitive(False)
        self.__attr_system.set_text("")
        self.__attr_platform.set_text("")
        self.__attr_strategy.set_active(-1)
        self.__attr_complexity.set_active(-1)
        self.__attr_disruption.set_active(-1)
        self.__attr_reboot.set_active(False)
        self.__unblock_signals()

    def __attr_fill(self, widget=None):

        (model, iterator) = self.get_selection().get_selected()

        self.__attr_frame.set_sensitive(iterator is not None)
        if not iterator:
            return

        data = model[iterator][self.COLUMN_OBJ]

        self.__block_signals()
        self.__attr_system.set_text(data.system or "")
        self.__attr_platform.set_text(data.platform or "")
        self.__attr_strategy.set_active(ENUM.STRATEGY.pos(data.strategy))
        self.__attr_complexity.set_active(ENUM.LEVEL.pos(data.complexity))
        self.__attr_disruption.set_active(ENUM.LEVEL.pos(data.disruption))
        self.__attr_reboot.set_active(data.reboot)
        self.__unblock_signals()

    def fill(self):
        self.clear()
        self.__attrs_clear()

        for data in self.data_model.get_fixes() or []:
            self.append([data.id,  (data.content or "").strip(), data])

class EditIdent(abstract.ListEditor):

    COLUMN_ID = 0
    COLUMN_LANG = -1

    def __init__(self, core, id, widget, data_model):
        self.data_model = data_model
        self.iter = None

        super(EditIdent, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("ID"), Gtk.CellRendererText(), text=self.COLUMN_ID))
        self.widget.append_column(Gtk.TreeViewColumn(_("System"), Gtk.CellRendererText(), text=self.COLUMN_TEXT))

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
                self.core.notify(_("ID of the ident is mandatory."),
                        core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                self.wid.grab_focus()
                return
            if self.operation == self.data_model.CMD_OPER_ADD:
                for iterator in self.get_model():
                    if iterator[self.COLUMN_ID] == self.wid.get_text():
                        self.core.notify(_("ID of the ident has to be unique!"),
                                core.Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                        self.wid.grab_focus()
                        return

            retval = self.data_model.edit_ident(self.operation, item, self.wid.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))

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
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
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
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.wid.set_text(model[self.iter][self.COLUMN_ID] or "")
                self.system.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                iterator = self.dialogDel(self.core.main_window, self.get_selection())
                if iterator is not None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for description dialog: \"%s\"" % (operation,))
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
        self.iter = None

        super(EditQuestion, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("Language"), Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn(_("Overrides"), Gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(Gtk.TreeViewColumn(_("Question"), Gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.question.get_buffer()
        if self.iter and self.get_model() != None:
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_question(self.operation, item, self.lang.get_text(),
                self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
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
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
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
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.override.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.question.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                iterator = self.dialogDel(self.core.main_window, self.get_selection())
                if iter is not None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for question dialog: \"%s\"" % (operation,))
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
        super(EditRationale, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("Language"), Gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(Gtk.TreeViewColumn(_("Overrides"), Gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(Gtk.TreeViewColumn(_("Rationale"), Gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        item = None
        (model, iterator) = self.get_selection().get_selected()
        buffer = self.rationale.get_buffer()
        if iterator and model is not None:
            item = model[iterator][self.COLUMN_OBJ]

        retval = self.data_model.edit_rationale(self.operation, item, self.lang.get_text(),
                self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        if self.wdialog:
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        self.operation = operation

        builder = Gtk.Builder()
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        builder.add_from_file(os.path.join(paths.glade_prefix, "dialogs.glade"))

        self.wdialog = builder.get_object("dialog:edit_rationale")
        self.info_box = builder.get_object("dialog:edit_rationale:info_box")
        self.lang = builder.get_object("dialog:edit_rationale:lang")
        self.rationale = builder.get_object("dialog:edit_rationale:rationale")
        self.override = builder.get_object("dialog:edit_rationale:override")
        builder.get_object("dialog:edit_rationale:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_rationale:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iterator) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iterator][self.COLUMN_LANG] or "")
                self.override.set_active(model[iterator][self.COLUMN_OVERRIDES])
                self.rationale.get_buffer().set_text(model[iterator][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                iterator = self.dialogDel(self.core.main_window, self.get_selection())
                if iterator is not None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for rationale dialog: \"%s\"" % (operation,))
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
        super(EditPlatform, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("CPE Name"), Gtk.CellRendererText(), text=self.COLUMN_LANG))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:edit")
        item = None
        (model, iterator) = self.get_selection().get_selected()
        if iterator and model != None:
            item = model[iterator][self.COLUMN_TEXT]

        if self.operation != self.data_model.CMD_OPER_DEL:
            text = self.cpe.get_text()
            if len(text) < 6 or text[5] not in ["a", "o", "h"]:
                self.core.notify(_("The part section can be \"a\", \"o\" or \"h\""),
                        core.Notification.ERROR, self.info_box, msg_id="notify:edit")
                return
            if len(text[7:].split(":")) != 6:
                self.core.notify(_("Invalid number of sections: should be cpe:/part:vendor:product:version:update:edition:lang"),
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
                self.core.notify(_("The part section can be \"a\", \"o\" or \"h\""),
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

        builder = Gtk.Builder()
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
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
        (model, iterator) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.cpe.set_text(model[iterator][self.COLUMN_TEXT])
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                iterator = self.dialogDel(self.core.main_window, self.get_selection())
                if iterator is not None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for rationale dialog: \"%s\"" % (operation,))
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
        self.titles = edit.EditTitle(self.core, "gui:edit:xccdf:values:titles", builder.get_object("edit:values:titles"), self.data_model)
        self.builder.get_object("edit:values:titles:btn_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:values:titles:btn_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:values:titles:btn_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = edit.EditDescription(self.core, "gui:edit:xccdf:values:descriptions", builder.get_object("edit:values:descriptions"), self.data_model)
        self.builder.get_object("edit:values:descriptions:btn_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:values:descriptions:btn_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:values:descriptions:btn_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("edit:values:descriptions:btn_preview").connect("clicked", self.descriptions.preview)

        # -- WARNING --
        self.warnings = edit.EditWarning(self.core, "gui:edit:xccdf:values:warnings", builder.get_object("edit:values:warnings"), self.data_model)
        builder.get_object("edit:values:warnings:btn_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:warnings:btn_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:warnings:btn_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- STATUS --
        self.statuses = edit.EditStatus(self.core, "gui:edit:xccdf:values:statuses", builder.get_object("edit:values:statuses"), self.data_model)
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

        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval != Gdk.KEY_Return:
            return

        if widget == self.vid:
            retval = self.data_model.edit_value(id=widget.get_text())
            if not retval:
                self.notifications.append(self.core.notify(_("Setting ID failed: ID \"%s\" already exists.") % (widget.get_text(),),
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
            LOGGER.error("Change: not supported object in \"%s\"" % (widget,))
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
        super(EditValuesValues, self).__init__(id, core, widget=widget, model=Gtk.ListStore(str, str, str, str, str, bool, str, GObject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(Gtk.TreeViewColumn(_("Selector"), Gtk.CellRendererText(), text=self.COLUMN_SELECTOR))
        self.widget.append_column(Gtk.TreeViewColumn(_("Value"), Gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.widget.append_column(Gtk.TreeViewColumn(_("Default"), Gtk.CellRendererText(), text=self.COLUMN_DEFAULT))
        self.widget.append_column(Gtk.TreeViewColumn(_("Lower bound"), Gtk.CellRendererText(), text=self.COLUMN_LOWER_BOUND))
        self.widget.append_column(Gtk.TreeViewColumn(_("Upper bound"), Gtk.CellRendererText(), text=self.COLUMN_UPPER_BOUND))
        self.widget.append_column(Gtk.TreeViewColumn(_("Must match"), Gtk.CellRendererText(), text=self.COLUMN_MUST_MATCH))
        self.widget.append_column(Gtk.TreeViewColumn(_("Match"), Gtk.CellRendererText(), text=self.COLUMN_MATCH))

    def __do(self, widget=None):
        """
        """
        # Check input data
        (model, iterator) = self.get_selection().get_selected()
        item = None
        if iterator:
            item = model[iterator][self.COLUMN_OBJ]

        for inst in model:
            if self.selector.get_text() == inst[0] and model[iterator][self.COLUMN_SELECTOR] != self.selector.get_text():
                self.core.notify(_("Selector \"%s\" is already used!") % (inst[0],),
                        core.Notification.ERROR, self.info_box, msg_id="dialog:add_value")
                self.selector.grab_focus()
                self.selector.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#FFC1C2"))
                return
        self.selector.modify_base(Gtk.StateType.NORMAL, self.__entry_style)

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

        builder = Gtk.Builder()
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
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

        self.__entry_style = self.selector.get_style().base[Gtk.StateType.NORMAL]

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
        (model, iterator) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to edit"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.selector.set_text(model[iterator][self.COLUMN_SELECTOR] or "")
                self.value.set_text(model[iterator][self.COLUMN_VALUE] or "")
                self.default.set_text(model[iterator][self.COLUMN_DEFAULT] or "")
                self.match.set_text(model[iterator][self.COLUMN_MATCH] or "")
                self.upper_bound.set_text(model[iterator][self.COLUMN_UPPER_BOUND] or "")
                self.lower_bound.set_text(model[iterator][self.COLUMN_LOWER_BOUND] or "")
                self.must_match.set_active(model[iterator][self.COLUMN_MUST_MATCH])
                for choice in model[iterator][self.COLUMN_OBJ].choices:
                    self.choices.get_model().append([choice])
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iterator:
                self.notifications.append(self.core.notify(_("Please select at least one item to delete"),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                iterator = self.dialogDel(self.core.main_window, self.get_selection())
                if iterator is not None:
                    self.__do()
                return
        else:
            LOGGER.error("Unknown operation for values dialog: \"%s\"" % (operation,))
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

class ItemList(abstract.List):

    """ List of Rules, Groups and Values.

    This class represents TreeView in editor window which contains
    list of XCCDF Items as Rules, Groups and Values. Each Group contains
    its content.
    """

    def __init__(self, widget, core, builder=None, progress=None):
        """ Constructor of ProfileList.
        """
        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, None, True, no_checks=True)
        super(ItemList, self).__init__("gui:edit:item_list", core, widget)

        self.loaded = False
        self.filter = filter
        self.builder = builder

        """ Register signals that can be emited by this class.
        All signals are registered in EventObject (abstract class) and
        are emited by other objects to trigger the async event.
        """
        self.add_sender(self.id, "update")
        self.add_sender(self.id, "delete")
        self.add_receiver("gui:btn:menu:edit:items", "update", self.__update)
        self.add_receiver("gui:btn:menu:edit:XCCDF", "load", self.__clear_update)


        """ Set objects from Glade files and connect signals
        """
        selection = self.get_TreeView().get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.section_list = self.builder.get_object("edit:section_list")
        self.itemsList = self.builder.get_object("edit:tw_items:sw")
        self.with_values = self.builder.get_object("xccdf:items:popup:show_values")
        self.with_values.connect("toggled", self.__update)
        # Popup Menu
        self.builder.get_object("xccdf:items:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("xccdf:items:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("xccdf:items:popup"))

        self.add_dialog = AddItem(self.core, self.data_model, self) # TODO
        self.get_TreeView().connect("key-press-event", self.__cb_key_press)

        # if True an idle worker that will perform the update (after selection changes) is already pending
        self.item_changed_worker_pending = False

    def __clear_update(self):
        """ Remove all items from the list and update model
        """
        self.data_model.model.clear()
        self.__update(force=True)

    def __update(self, force=False):
        """ Update items in the list. Parameter 'force' is used to force
        the fill function upon the list."""
        if not self.loaded or force:
            self.data_model.fill(with_values=self.with_values.get_active())
            self.loaded = True

        # Select the last one selected if there is one
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))

    def __cb_button_pressed(self, treeview, event, menu):
        """ Mouse button has been pressed. If the button is 3rd: show
        popup menu"""
        if event.button == 3:
            menu.popup(None, None, None, None, event.button, event.time)

    def __cb_key_press(self, widget, event):
        """ The key-press event has occured upon the list.
        If key == delete: Delete the selected item from the list and model"""
        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval == Gdk.KEY_Delete:
            selection = self.get_TreeView().get_selection()
            (model, iterator) = selection.get_selected()
            if iterator:
                self.__cb_item_remove()

    def __cb_item_remove(self, widget=None):
        """ Remove selected item from the list and model.
        """
        selection = self.get_TreeView().get_selection()
        (model, iterator) = selection.get_selected()
        if iterator:
            iter_next = model.iter_next(iterator)
            self.data_model.remove_item(model[iterator][1])
            model.remove(iterator)

            """ If the removed item has successor, let's select it so we can
            continue in deleting or other actions without need to click the
            list again to select next item """
            if iter_next:
                self.core.selected_item = model[iter_next][1]
                self.__update(False)
            self.emit("delete")
        else: raise AttributeError, "Removing non-selected item or nothing selected."

    def __cb_item_add(self, widget=None):
        """ Add item to the list and model
        """
        self.add_dialog.dialog()

    def __cb_item_changed(self, widget, treeView):
        """Callback called whenever item selection changes. Performs updates of the property box.
        """

        def worker():
            details = self.data_model.get_item_details(self.core.selected_item)
            selection = treeView.get_selection( )
            if selection != None:
                (model, iterator) = selection.get_selected( )
                if iter:
                    self.core.selected_item = model.get_value(iterator, commands.DHItemsTree.COLUMN_ID)
                else:
                    self.core.selected_item = None

            # Selection has changed, trigger all events connected to this signal
            self.emit("update")
            treeView.columns_autosize()

            self.item_changed_worker_pending = False

        # The reason for the item_changed_worker_pending attribute is to avoid stacking up
        # many update requests that would all query the selection state again and do repeated
        # work. This way the update happens only once even though the selection changes many times.
        if not self.item_changed_worker_pending:
            # we handle this in the idle function when no higher priority events are to be handled
            GLib.idle_add(worker)
            self.item_changed_worker_pending = True


class MenuButtonEditItems(abstract.MenuButton, abstract.Func):

    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit:items", widget, core)
        abstract.Func.__init__(self, core)

        self.builder = builder
        self.data_model = commands.DHEditItems(self.core)
        self.item = None
        # FIXME: Instantiating abstract class
        # FIXME: We inherit Func and we are composed of it
        self.func = abstract.Func()
        self.current_page = 0

        #draw body
        self.body = self.builder.get_object("items:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        #self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        #self.filter.set_active(False)
        self.filter = None
        self.tw_items = self.builder.get_object("edit:tw_items")
        titles = self.data_model.get_benchmark_titles()
        self.list_item = ItemList(self.tw_items, self.core, builder, self.progress)
        self.ref_model = self.list_item.get_TreeView().get_model() # original model (not filtered)

        # set signals
        self.add_sender(self.id, "update")

        # remove just for now (missing implementations and so..)
        self.items = self.builder.get_object("edit:xccdf:items")
        self.items.remove_page(4)

        # Get widgets from GLADE
        self.item_id = self.builder.get_object("edit:general:entry_id")
        self.item_id.connect("focus-out-event", self.__change)
        self.item_id.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("edit:general:entry_version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.version_time = self.builder.get_object("edit:general:entry_version_time")
        self.version_time.connect("focus-out-event", self.__change)
        self.version_time.connect("key-press-event", self.__change)
        self.selected = self.builder.get_object("edit:general:chbox_selected")
        self.selected.connect("toggled", self.__change)
        self.hidden = self.builder.get_object("edit:general:chbox_hidden")
        self.hidden.connect("toggled", self.__change)
        self.prohibit = self.builder.get_object("edit:general:chbox_prohibit")
        self.prohibit.connect("toggled", self.__change)
        self.abstract = self.builder.get_object("edit:general:chbox_abstract")
        self.abstract.connect("toggled", self.__change)
        self.cluster_id = self.builder.get_object("edit:general:entry_cluster_id")
        self.cluster_id.connect("focus-out-event", self.__change)
        self.cluster_id.connect("key-press-event", self.__change)
        self.weight = self.builder.get_object("edit:general:entry_weight")
        self.weight.connect("focus-out-event", self.__change)
        self.weight.connect("key-press-event", self.__change)
        self.operations = self.builder.get_object("edit:xccdf:items:operations")
        self.extends = self.builder.get_object("edit:dependencies:lbl_extends")
        self.content_ref = self.builder.get_object("edit:xccdf:items:evaluation:content_ref")
        self.content_ref.connect("focus-out-event", self.__change)
        self.content_ref.connect("key-press-event", self.__change)
        self.content_ref_find = self.builder.get_object("edit:xccdf:items:evaluation:content_ref:find")
        self.system = self.builder.get_object("edit:xccdf:items:evaluation:system")
        self.href = self.builder.get_object("edit:xccdf:items:evaluation:href")
        self.href.connect("changed", self.__change)
        self.href_dialog = self.builder.get_object("edit:xccdf:items:evaluation:href:dialog")
        self.href_dialog.connect("file-set", self.__cb_href_file_set)
        self.item_values_main = self.builder.get_object("edit:values:sw_main")
        self.ident_box = self.builder.get_object("xccdf:items:ident:box")

        # -- TITLES --
        self.titles = edit.EditTitle(self.core, "gui:edit:xccdf:items:titles", builder.get_object("edit:general:lv_title"), self.data_model)
        builder.get_object("edit:general:btn_title_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_title_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_title_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTIONS --
        self.descriptions = edit.EditDescription(self.core, "gui:edit:xccdf:items:descriptions", builder.get_object("edit:general:lv_description"), self.data_model)
        builder.get_object("edit:general:btn_description_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_description_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_description_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("edit:general:btn_description_preview").connect("clicked", self.descriptions.preview)

        # -- WARNINGS --
        self.warnings = edit.EditWarning(self.core, "gui:edit:items:general:warning", builder.get_object("edit:general:lv_warning"), self.data_model)
        builder.get_object("edit:general:btn_warning_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_warning_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_warning_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- STATUSES --
        self.statuses = edit.EditStatus(self.core, "gui:edit:items:general:status", builder.get_object("edit:general:lv_status"), self.data_model)
        builder.get_object("edit:general:btn_status_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_status_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_status_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

        # -- QUESTIONS --
        self.questions = EditQuestion(self.core, "gui:edit:items:general:questions", builder.get_object("edit:items:questions"), self.data_model)
        builder.get_object("edit:items:questions:btn_add").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:items:questions:btn_edit").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:items:questions:btn_del").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_DEL)

        # -- RATIONALES --
        self.rationales = EditRationale(self.core, "gui:edit:items:general:rationales", builder.get_object("edit:items:rationales"), self.data_model)
        builder.get_object("edit:items:rationales:btn_add").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:items:rationales:btn_edit").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:items:rationales:btn_del").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_DEL)

        # -- VALUES --
        self.item_values = EditItemValues(self.core, "gui:edit:items:values", builder.get_object("edit:xccdf:items:values"), self.data_model)
        builder.get_object("edit:xccdf:items:values:btn_add").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:items:values:btn_edit").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:items:values:btn_del").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("edit:xccdf:items:values").connect("button-press-event", self.__cb_value_clicked) # Double-click makes the editor to look for the value in items

        # -- PLATFORMS --
        self.platforms = EditPlatform(self.core, "gui:edit:dependencies:platforms", builder.get_object("edit:xccdf:dependencies:platforms"), self.data_model)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_add").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_edit").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_del").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_DEL)

        # -- CONTENT REF --
        self.content_ref_dialog = edit.FindOvalDef(self.core, "gui:edit:evaluation:content_ref:dialog", self.data_model)
        self.content_ref_find.connect("clicked", self.__cb_find_oval_definition)

        # -- FIXTEXTS --
        self.fixtext = EditFixtext(self.core, "id:edit:xccdf:items:fixtext", builder.get_object("xccdf:items:fixtext"), self.data_model, builder)
        builder.get_object("xccdf:items:fixtext:btn_add").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:fixtext:btn_edit").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:fixtext:btn_del").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("xccdf:items:fixtext:btn_preview").connect("clicked", self.fixtext.preview)

        # -- FIXES --
        self.fix = EditFix(self.core, "id:edit:xccdf:items:fix", builder.get_object("xccdf:items:fix"), self.data_model, builder)
        builder.get_object("xccdf:items:fix:btn_add").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:fix:btn_edit").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:fix:btn_del").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_DEL)

        # -- IDENTS --
        self.ident = EditIdent(self.core, "id:edit:xccdf:items:ident", builder.get_object("xccdf:items:ident"), self.data_model)
        builder.get_object("xccdf:items:ident:btn_add").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:ident:btn_edit").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:ident:btn_del").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_DEL)
        # -------------

        """Get widgets from Glade: Part editor.glade in edit
        """
        self.conflicts = EditConflicts(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.requires = EditRequires(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.values = EditValues(self.core, "gui:edit:xccdf:values", self.builder)

        self.severity = self.builder.get_object("edit:operations:combo_severity")
        self.severity.set_model(ENUM.LEVEL.get_model())
        self.severity.connect( "changed", self.__change)
        self.impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.impact_metric.connect("focus-out-event", self.cb_control_impact_metric)
        self.check = self.builder.get_object("edit:operations:lv_check")

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:evaluation:content_ref:dialog", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:values:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:items:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:values", "update_item", self.__update_item)

    def __cb_find_oval_definition(self, widget):

        model = self.href.get_model()
        if self.href.get_active() == -1:
            self.notifications.append(self.core.notify("No definition file available", core.Notification.WARNING, msg_id="notify:definition_available"))
            return
        self.content_ref_dialog.dialog(None, model[self.href.get_active()][0])

    def __change(self, widget, event=None):

        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval != Gdk.KEY_Return:
            return

        if widget == self.item_id:
            self.core.notify_destroy("notify:xccdf:id")
            text = widget.get_text()
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify(_("First character of ID has to be from A-Z (case insensitive) or \"_\""),
                    core.Notification.ERROR, msg_id="notify:xccdf:id"))
                return
            else: retval = self.data_model.update(id=text)
            if not retval:
                self.notifications.append(self.core.notify(_("Setting ID failed: ID \"%s\" already exists.") % (widget.get_text(),),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                widget.set_text(self.core.selected_item)
                return
            self.__update_item()
        elif widget == self.version:
            self.data_model.update(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp > 0:
                self.data_model.update(version_time=timestamp)
        elif widget == self.selected:
            self.data_model.update(selected=widget.get_active())
        elif widget == self.hidden:
            self.data_model.update(hidden=widget.get_active())
        elif widget == self.prohibit:
            self.data_model.update(prohibit=widget.get_active())
        elif widget == self.abstract:
            self.data_model.update(abstract=widget.get_active())
        elif widget == self.cluster_id:
            self.data_model.update(cluster_id=widget.get_text())
        elif widget == self.weight:
            weight = self.controlFloat(widget.get_text(), _("Weight"))
            if weight:
                self.data_model.update(weight=weight)
        elif widget == self.content_ref:
            ret, err = self.data_model.set_item_content(name=widget.get_text())
            if not ret:
                self.notifications.append(self.core.notify(err, core.Notification.ERROR, msg_id="notify:edit:content_href"))
        elif widget == self.href:
            if self.href.get_active() == -1 or len(self.href.get_model()) == 0:
                return
            iterator = self.href.get_model()[self.href.get_active()]
            if iterator:
                href = iterator[1]
                self.data_model.set_item_content(href=href)
                self.core.notify_destroy("notify:definition_available")
        elif widget == self.severity:
            self.data_model.update(severity=ENUM.LEVEL.value(widget.get_active()))
        else:
            LOGGER.error("Change of \"%s\" is not supported " % (widget,))
            return

    def __cb_href_file_set(self, widget):
        path = widget.get_filename()
        file = os.path.basename(widget.get_filename())

        self.data_model.add_oval_reference(path)
        retval, err = self.data_model.set_item_content(href=file)
        if not retval: self.notifications.append(self.core.notify(err, core.Notification.ERROR, msg_id="notify:set_content_ref"))
        self.__update()

    def __cb_value_clicked(self, widget, event):

        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            selection = widget.get_selection()
            if selection:
                (model, iterator) = selection.get_selected()
                if not iterator:
                    return
                id = model[iterator][0] # Should be ID of value
                if not id:
                    return
            else: return
            self.list_item.search(id, 1)

    def cb_control_impact_metric(self, widget, event):
        text = widget.get_text()
        if text != "" and self.controlImpactMetric(text, self.core):
            self.data_model.DHEditImpactMetric(self.item, text)

    def show(self, sensitive):
        self.items.set_sensitive(sensitive)
        self.items.set_property("visible", sensitive)

    def __set_profile_description(self, description):
        """
        Set description to the textView.
        @param text Text with description
        """
        self.profile_description.get_buffer().set_text("")
        if description == "": description = _("No description")
        description = "<body>"+description+"</body>"
        self.profile_description.display_html(description)

    def __update_item(self):
        selection = self.tw_items.get_selection()
        (model, iterator) = selection.get_selected()
        if iterator:
            item = self.data_model.get_item(model[iterator][1])
            if item == None:
                item = self.data_model.get_item(self.core.selected_item)

            if item == None:
                LOGGER.error("Can't find item with ID: \"%s\"" % (model[iterator][1],))
                return

            model[iterator][1] = item.id

            # Get the title of item
            title = self.data_model.get_title(item.title) or "%s (ID)" % (item.id,)

            model[iterator][2] = title
            model[iterator][4] = ""+title

    def __block_signals(self):
        self.hidden.handler_block_by_func(self.__change)
        self.selected.handler_block_by_func(self.__change)
        self.prohibit.handler_block_by_func(self.__change)
        self.abstract.handler_block_by_func(self.__change)
        self.severity.handler_block_by_func(self.__change)
        self.content_ref.handler_block_by_func(self.__change)
        self.href.handler_block_by_func(self.__change)
        #self.multiple.handler_block_by_func(self.__change)
        #self.role.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.hidden.handler_unblock_by_func(self.__change)
        self.selected.handler_unblock_by_func(self.__change)
        self.prohibit.handler_unblock_by_func(self.__change)
        self.abstract.handler_unblock_by_func(self.__change)
        self.severity.handler_unblock_by_func(self.__change)
        self.content_ref.handler_unblock_by_func(self.__change)
        self.href.handler_unblock_by_func(self.__change)
        #self.chbox_multiple.handler_unblock_by_func(self.__change)
        #self.cBox_role.handler_unblock_by_func(self.__change)

    def __clear(self):
        self.__block_signals()
        self.item_id.set_text("")
        self.hidden.set_active(False)
        self.selected.set_active(False)
        self.prohibit.set_active(False)
        self.abstract.set_active(False)
        self.version.set_text("")
        self.version_time.set_text("")
        self.cluster_id.set_text("")
        #self.extends.set_text("None")
        self.content_ref.set_text("")
        self.system.set_text("")
        self.href.get_model().clear()
        self.severity.set_active(-1)

        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.statuses.clear()
        self.questions.clear()
        self.rationales.clear()
        self.item_values.clear()
        self.conflicts.fill(None)
        self.requires.fill(None)
        self.platforms.fill()
        self.fix.fill()
        self.fixtext.fill()
        self.__unblock_signals()

    def __update(self):

        if self.core.selected_item != None:
            details = self.data_model.get_item_details(self.core.selected_item)
        else:
            details = None
            #self.item = None

        self.__clear()
        if details == None:
            self.items.set_sensitive(False)
            return

        # Check if the item is value and change widgets
        if details["type"] == openscap.OSCAP.XCCDF_VALUE:
            self.show(False)
            self.values.show(True)
            self.values.update()
            return
        else:
            self.show(True)
            self.values.show(False)

        # Item is not value, continue
        self.__block_signals()
        self.item_id.set_text(details["id"] or "")
        self.weight.set_text(str(details["weight"] or ""))
        self.version.set_text(details["version"] or "")
        self.version_time.set_text("" if details["version_time"] <= 0 else str(datetime.date.fromtimestamp(details["version_time"])))
        self.cluster_id.set_text(details["cluster_id"] or "")
        self.extends.set_text(details["extends"] or "")
        self.titles.fill()
        self.descriptions.fill()
        self.warnings.fill()
        self.statuses.fill()
        self.questions.fill()
        self.rationales.fill()
        self.conflicts.fill(details)
        self.requires.fill(details["item"])
        self.platforms.fill()

        self.abstract.set_active(details["abstract"])
        self.selected.set_active(details["selected"])
        self.hidden.set_active(details["hidden"])
        self.prohibit.set_active(details["prohibit_changes"])

        self.items.set_sensitive(True)

        # Set sensitivity for rule / group
        self.ident_box.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.item_values_main.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.operations.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.severity.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)

        if details["type"] == openscap.OSCAP.XCCDF_RULE: # Item is Rule
            self.severity.set_active(ENUM.LEVEL.pos(details["severity"]))
            self.impact_metric.set_text(details["imapct_metric"] or "")
            self.fixtext.fill()
            self.fix.fill()
            self.ident.fill()
            content = self.data_model.get_item_content()

            item = self.core.lib.benchmark.get_item(self.core.selected_item)
            rule = item.to_rule()
            self.system.set_text(rule.checks[0].system if len(rule.checks) > 0 else "")

            self.href.get_model().clear()
            for name in self.core.lib.oval_files.keys():
                self.href.get_model().append([name, name])
            for name in self.core.lib.sce_files:
                self.href.get_model().append([name, name])

            if content != None and len(content) > 0:
                self.content_ref.set_text(content[0][0] or "")
                for i, item in enumerate(self.href.get_model()):
                    if item[0] == content[0][1]:
                        self.href.set_active(i)

            self.item_values.fill()

        else: # Item is GROUP
            self.severity.set_active(-1)
            self.impact_metric.set_text("")
            self.fixtext.fill()
            self.fix.fill()
            self.ident.fill()

        self.__unblock_signals()
