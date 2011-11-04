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

""" Importing standard python libraries
"""
import gtk              # GTK library
import threading        # Main window is running in thread
import pango            # Pango enumeration constants
import os.path
import logging          # Logger for debug/info/error messages

""" Importing SCAP Workbench modules
"""
from scap_workbench import core
from scap_workbench.core import abstract
from scap_workbench.core import commands
from scap_workbench.core import dialogs
from scap_workbench.core import paths
from scap_workbench.core import error
import scap_workbench.core.enum as ENUM

from scap_workbench.scanner import tailoring
from scap_workbench.scanner import scan

# Initializing Logger
logger = logging.getLogger("scap-workbench")

class MenuButtonXCCDF(abstract.MenuButton):
    """
    GUI for operations with xccdf file.
    """
    def __init__(self, builder, widget, _core):
        self.builder = builder
        self.data_model = commands.DHXccdf(_core)
        super(MenuButtonXCCDF, self).__init__("gui:btn:main:xccdf", widget, _core)
        
        self.widget = widget
        
        self.body = self.builder.get_object("xccdf:box")

        # info
        self.label_info = self.builder.get_object("xccdf:lbl_info")
        self.label_title = self.builder.get_object("xccdf:lbl_title")
        self.label_version = self.builder.get_object("xccdf:lbl_version")
        self.label_url = self.builder.get_object("xccdf:lbl_file")
        self.label_resolved = self.builder.get_object("xccdf:lbl_resolved")
        self.label_language = self.builder.get_object("xccdf:lbl_language")
        self.label_description = self.builder.get_object("xccdf:lbl_description")
        self.label_status_current = self.builder.get_object("xccdf:lbl_status_current")
        self.label_warnings = self.builder.get_object("xccdf:lbl_warnings")
        self.label_notices = self.builder.get_object("xccdf:lbl_notices")
        self.box_references = self.builder.get_object("xccdf:box_references")
        self.files_box = self.builder.get_object("xccdf:files:box")

        self.btn_import = self.builder.get_object("xccdf:btn_import")
        self.btn_import.connect("clicked", self.__cb_import)

        self.btn_export = self.builder.get_object("xccdf:btn_export")
        self.btn_export.connect("clicked", self.__cb_export)

        self.btn_close = self.builder.get_object("xccdf:btn_close")
        self.btn_close.connect("clicked", self.__cb_close)

        self.add_sender(self.id, "update")
        self.add_sender(self.id, "load")
        self.add_sender(self.id, "lang_changed")

        self.add_receiver("gui:btn:menu:edit:XCCDF", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:title", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:description", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:warning", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:notice", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:status", "update", self.__update)

        core.label_set_autowrap(self.label_title)
        core.label_set_autowrap(self.label_description)
        core.label_set_autowrap(self.label_warnings)
        core.label_set_autowrap(self.label_notices)

    def __add_file_info(self, name, file_info):

        # Add table of information to the expander with label name
        expander = Gtk.Expander()
        label = Gtk.Label("OVAL: %s" % (name,))
        pango_list = Pango.AttrList()
        pango_list.insert(Pango.AttrWeight(Pango.Weight.BOLD, start_index=0, end_index=-1))
        if not file_info:
            pango_list.insert(Pango.AttrForeground(65535, 0, 0, start_index=0, end_index=-1))
        label.set_attributes(pango_list)
        expander.set_label_widget(label)
        expander.set_expanded(True)
        align = Gtk.Alignment.new()
        align.set_padding(5, 10, 25, 0)

        if not file_info:
            label = Gtk.Label(label="File not found: %s" % (name))
            label.set_attributes(pango_list)
            align.add(label)
        else:
            table = Gtk.Table(rows=5, columns=2)
            table.set_col_spacings(spacing=5)
            align.add(table)

            # use table to add information
            label = Gtk.Label(label="Product name:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label="Product version:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label="Schema version:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 2, 3, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label="Timestamp:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 3, 4, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label="Valid:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 4, 5, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)

            label = Gtk.Label(label=file_info["product_name"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 0, 1, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label=file_info["product_version"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 1, 2, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label=file_info["schema_version"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 2, 3, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)
            label = Gtk.Label(label=file_info["timestamp"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 3, 4, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL, xpadding=0, ypadding=0)

        expander.add(align)
        self.files_box.pack_start(expander, False, False)
        expander.show_all()

    def __clear(self):
        self.label_info.set_text("")
        self.label_title.set_text("")
        self.label_description.set_text("")
        self.label_version.set_text("")
        self.label_url.set_text("")
        self.label_status_current.set_text("")
        self.label_resolved.set_text("")
        self.label_warnings.set_text("")
        self.label_notices.set_text("")
        self.label_language.set_text("")
        for child in self.files_box.get_children(): child.destroy()

    def update(self):
        self.__update()

    def __update(self):
        """
        Set information about file.
        """
        self.__clear()
        details = self.data_model.get_details()

        # SET
        if not details: return
        lang = details["lang"]
        self.label_info.set_text("XCCDF: %s" % (details["id"] or "",))
        if lang not in details["titles"]: self.label_title.set_text("No title in \"%s\" language" % (lang,))
        else: self.label_title.set_text(details["titles"][lang] or "")
        if lang not in details["descs"]: self.label_description.set_text("No description in \"%s\" language" % (lang,))
        else: self.label_description.set_text(details["descs"][lang] or "")
        self.label_version.set_text(details["version"] or "")
        self.label_url.set_text(details["id"] or "")
        self.label_status_current.set_text(ENUM.STATUS_CURRENT.map(details["status_current"])[1])
        self.label_resolved.set_text(["no", "yes"][details["resolved"]])
        self.label_warnings.set_text("\n".join(["%s: %s" % (warn[0], warn[1].text) for warn in details["warnings"]]) or "None")
        self.label_notices.set_text("\n".join(["%s: %s" % (notice[0], notice[1].text) for notice in details["notices"]]) or "None")
        self.label_language.set_text(lang or "")
        
        self.btn_close.set_sensitive(True)
        self.btn_export.set_sensitive(True)
        self.__menu_sensitive(True)

        # References
        for child in self.box_references.get_children():
            child.destroy()

        for i, ref in enumerate(details["references"]):
            label = Gtk.Label()
            if ref["isdc"] == True:
                text = "<span color='#AAA'>DoublinCore reference: NOT SUPPORTED</span>"
                label.set_use_markup(True)
            else: text = "%d) %s [<a href='%s'>link</a>]" % (i+1, " ".join((ref["title"] or "").split()), ref["identifier"])
            label.set_text(text)
            self.box_references.pack_start(label, True, True)
            #label.set_tooltip_text(ref[1])
            label.set_use_markup(True)
            
            try:
                label.set_track_visited_links(True)
            except AttributeError:
                pass
            
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD) 
            label.set_alignment(0,0)
            label.connect("size-allocate", core.label_size_allocate)
            label.show()

        # OVAL Files
        for child in self.files_box.get_children():
            child.destroy()

        files = self.data_model.get_oval_files_info()
        if len(details["files"]) ==  0:
            return
    
        for f in details["files"]:
            if f in files:
                self.__add_file_info(f, files[f])
            else: self.__add_file_info(f, None)


    # callBack functions
    def __cb_new(self, widget):
        if not self.core.init(None): return
        self.data_model.update(id="New_SCAP_Benchmark", version="0", lang="en")
        self.core.selected_lang = "en"
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
            if not self.core.init(file):
                return
            self.emit("load")

            try:
                self.__update()
            except KeyError:
                pass
            
            self.btn_import.set_sensitive(False)

    def __cb_import(self, widget):
        dialogs.ImportDialog(self.core, self.data_model, self.__import)

    def __cb_export(self, widget):
        file_name = self.data_model.export()
        if file_name:
            self.notifications.append(self.core.notify("Benchmark has been exported to \"%s\"" % (file_name,),
                core.Notification.SUCCESS, msg_id="notify:xccdf:export"))
            self.core.xccdf_file = file_name
            
        else:
            self.notifications.append(self.core.notify("Export canceled or unsuccessful.",
                core.Notification.INFORMATION, msg_id="notify:xccdf:export"))

    def __menu_sensitive(self, active):
        """This gets called as a reaction to a file being loaded or closed.
        
        If active is True this will make the latter 2 buttons in the top menu sensitive,
        otherwise it will make them insensitive.
        """
        
        self.core.get_item("gui:btn:menu:tailoring").set_sensitive(active)
        self.core.get_item("gui:btn:menu:scan").set_sensitive(active)

    def __cb_close(self, widget):
        self.__menu_sensitive(False)
        self.core.destroy()
        self.__clear()
        self.core.notify_destroy("notify:xccdf:export")
        self.emit("load")

        self.btn_close.set_sensitive(False)
        self.btn_export.set_sensitive(False)
        self.btn_import.set_sensitive(True)
