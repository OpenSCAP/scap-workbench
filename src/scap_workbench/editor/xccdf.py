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

from scap_workbench import core
from scap_workbench.core import dialogs
from scap_workbench.core import commands
from scap_workbench.core import abstract
from scap_workbench.editor.edit import *

import gtk
import glib

import logging

# Initializing Logger
logger = logging.getLogger("scap-workbench")


class MenuButtonEditXCCDF(abstract.MenuButton):

    def __init__(self, builder, widget, core):
        super(MenuButtonEditXCCDF, self).__init__("gui:btn:menu:edit:XCCDF", widget, core)
        
        self.builder = builder
        self.data_model = commands.DHXccdf(core)
        
        #draw body
        self.body = self.builder.get_object("xccdf:box")
        self.sub_menu = self.builder.get_object("edit:sub:main")
        self.add_sender(self.id, "update")
        self.add_sender(self.id, "load")

        # Get widgets from glade
        self.entry_id = self.builder.get_object("edit:xccdf:id")
        self.entry_id.connect( "changed", self.__change, "id")
        self.entry_version = self.builder.get_object("edit:xccdf:version")
        self.entry_version.connect( "changed", self.__change, "version")
        self.entry_resolved = self.builder.get_object("edit:xccdf:resolved")
        self.entry_resolved.connect( "changed", self.__change, "resolved")
        self.entry_lang = self.builder.get_object("edit:xccdf:lang")
        self.entry_lang.connect( "changed", self.__change, "lang")

        # -- TITLE --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:title", builder.get_object("edit:xccdf:titles"), self.data_model)
        builder.get_object("edit:xccdf:btn_titles_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:btn_titles_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:btn_titles_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:description", builder.get_object("edit:xccdf:descriptions"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_descriptions_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_descriptions_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_descriptions_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("edit:xccdf:btn_descriptions_preview").connect("clicked", self.descriptions.preview)

        # -- WARNING --
        self.warnings = EditWarning(self.core, "gui:edit:xccdf:warning", builder.get_object("edit:xccdf:warnings"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_warnings_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_warnings_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_warnings_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- NOTICE --
        self.notices = EditNotice(self.core, "gui:edit:xccdf:notice", builder.get_object("edit:xccdf:notices"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_notices_add").connect("clicked", self.notices.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_notices_edit").connect("clicked", self.notices.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_notices_del").connect("clicked", self.notices.dialog, self.data_model.CMD_OPER_DEL)

        # -- REFERENCE --
        # FIXME: Instantiating an abstract class?!
        self.tv_references = abstract.ListEditor("gui:edit:xccdf:references", self.core, widget=self.builder.get_object("edit:xccdf:references"), model=gtk.ListStore(str, str))
        self.tv_references.widget.append_column(gtk.TreeViewColumn("Reference", gtk.CellRendererText(), text=0))
        self.builder.get_object("edit:xccdf:btn_references_add").set_sensitive(False)
        self.builder.get_object("edit:xccdf:btn_references_edit").set_sensitive(False)
        self.builder.get_object("edit:xccdf:btn_references_del").set_sensitive(False)
        self.builder.get_object("edit:xccdf:references").set_sensitive(False)

        # -- STATUS --
        self.statuses = EditStatus(self.core, "gui:edit:xccdf:status", builder.get_object("edit:xccdf:statuses"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_statuses_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_statuses_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_statuses_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)
        # -------------

        self.btn_new = self.builder.get_object("edit:sub:new")
        self.btn_close = self.builder.get_object("edit:sub:close")
        self.btn_import = self.builder.get_object("edit:sub:import")
        self.btn_export = self.builder.get_object("edit:sub:export")
        self.btn_new.connect("clicked", self.__cb_new)
        self.btn_close.connect("clicked", self.__cb_close)
        self.btn_import.connect("clicked", self.__cb_import)
        self.btn_export.connect("clicked", self.__cb_export)

    def __cb_new(self, widget):
        """ Create new XCCDF Benchmark
        """
        if not self.core.init(None): return

        # Update neccessary attributes of Benchmark
        self.data_model.update(id="New_SCAP_Benchmark", version="0", lang="en")
        self.core.selected_lang = "en"
        self.core.notify_destroy("notify:xccdf:missing_lang")
        self.data_model.edit_status(self.data_model.CMD_OPER_ADD)
        try:
            self.__update()
        except KeyError:
            pass

        self.emit("load")

    def __import(self, file):
        if file != "":
            self.__cb_close(None)
            logger.debug("Loading XCCDF file %s", file)
            if not self.core.init(file): return
            self.emit("load")

            try:
                self.__update()
            except KeyError:
                pass

    def __cb_validate(self, widget):
        """ Deprecated: Validate button from main file is not visible
        anymore. This function is not reachable. Leting here for
        further reference """
        validate = self.data_model.validate()
        message = [ "Document is not valid !",
                    "Document is valid.",
                    "Validation process failed, check for error in log file."][validate]
        lvl = [ core.Notification.WARNING,
                core.Notification.SUCCESS,
                core.Notification.ERROR][validate]
        self.notifications.append(self.core.notify(message, lvl, msg_id="notify:xccdf:validate"))

    def __cb_import(self, widget):
        dialogs.ImportDialog(self.core, self.data_model, self.__import)

    def __cb_export(self, widget):
        dialogs.ExportDialog(self.core, self.data_model)

    def __menu_sensitive(self, active):
        self.btn_new.set_sensitive(not active)
        self.btn_import.set_sensitive(not active)
        self.btn_close.set_sensitive(active)
        self.btn_export.set_sensitive(active)
        self.core.get_item("gui:btn:menu:edit:profiles").set_sensitive(active)
        self.core.get_item("gui:btn:menu:edit:items").set_sensitive(active)

    def __cb_close(self, widget):
        self.__menu_sensitive(False)
        self.core.destroy()
        self.__clear()
        self.core.notify_destroy("notify:xccdf:validate")
        self.core.notify_destroy("notify:xccdf:export")
        self.__update()
        self.emit("load")

    def __change(self, widget, object=None):

        if object == "id":
            self.core.notify_destroy("notify:xccdf:id")
            # Replace all white spaces with '_' (space are not allowed in ID)
            text = re.sub("[\t ]+" , "_", widget.get_text())
            # Check if ID doesn't start with number
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                    core.Notification.ERROR, msg_id="notify:xccdf:id"))
            else: self.data_model.update(id=text)
        elif object == "version":
            self.data_model.update(version=widget.get_text())
        elif object == "resolved":
            self.data_model.update(resolved=(widget.get_active() == 1))
        elif object == "status":
            self.data_model.update(status=ENUM.STATUS_CURRENT[widget.get_active()][0])
        elif object == "lang":
            self.data_model.update(lang=widget.get_text())
        else: 
            logger.error("Change \"%s\" not supported object in \"%s\"" % (object, widget))
            return
        self.emit("update")

    def __clear(self):
        """Clear widgets
        """
        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.notices.clear()
        self.statuses.clear()
        self.tv_references.clear()
        self.entry_id.set_text("")
        self.entry_version.set_text("")
        self.entry_resolved.set_active(-1)
        self.entry_lang.set_text("")

    def activate(self, active):
        self.core.notify_destroy("notify:xccdf:export")
        super(MenuButtonEditXCCDF, self).activate(active)
        self.sub_menu.set_property("visible", active)

    def update(self):
        self.__update()

    def __update(self):

        # TODO: this blocks of handlers could be substitute ?        
        self.entry_id.handler_block_by_func(self.__change)
        self.entry_version.handler_block_by_func(self.__change)
        self.entry_resolved.handler_block_by_func(self.__change)
        self.entry_lang.handler_block_by_func(self.__change)

        self.__clear()
        details = self.data_model.get_details()
        self.__menu_sensitive(details != None)

        """Set sensitivity of widgets depended on availability of XCCDF details
        This is mainly supposed to control no-XCCDF or loaded XCCDF behavior
        """
        self.builder.get_object("edit:xccdf:notebook").set_sensitive(details != None)
        self.builder.get_object("edit:xccdf:entries").set_sensitive(details != None)

        """Update 
        """
        if details:
            self.entry_id.set_text(details["id"] or "")
            self.entry_version.set_text(details["version"] or "")
            self.entry_resolved.set_active(details["resolved"])
            self.entry_lang.set_text(details["lang"] or "")
            self.titles.fill()
            self.descriptions.fill()
            self.warnings.fill()
            self.notices.fill()
            #for ref in details["references"]:
                #self.tv_references.append([ref])
            self.statuses.fill()

        self.entry_id.handler_unblock_by_func(self.__change)
        self.entry_version.handler_unblock_by_func(self.__change)
        self.entry_resolved.handler_unblock_by_func(self.__change)
        self.entry_lang.handler_unblock_by_func(self.__change)
        