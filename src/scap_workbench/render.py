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
import logging
import pango
import threading

import core
import abstract
import tailoring
import profiles
import scan
import edit
import logging
import commands

logger = logging.getLogger("scap-workbench")

def label_set_autowrap(widget): 
    "Make labels automatically re-wrap if their containers are resized.  Accepts label or container widgets."
    # For this to work the label in the glade file must be set to wrap on words.
    if isinstance(widget, gtk.Container):
        children = widget.get_children()
        for i in xrange(len(children)):
            label_set_autowrap(children[i])
    elif isinstance(widget, gtk.Label) and widget.get_line_wrap():
        widget.connect_after("size-allocate", label_size_allocate)


def label_size_allocate(widget, allocation):
    "Callback which re-allocates the size of a label."
    layout = widget.get_layout()
    lw_old, lh_old = layout.get_size()
    # fixed width labels
    if lw_old / pango.SCALE == allocation.width:
        return
    # set wrap width to the pango.Layout of the labels
    layout.set_width(allocation.width * pango.SCALE)
    lw, lh = layout.get_size()  # lw is unused.
    if lh_old != lh:
        widget.set_size_request(-1, lh / pango.SCALE)

class MenuButtonXCCDF(abstract.MenuButton):
    """
    GUI for operations with xccdf file.
    """
    def __init__(self, builder, widget, core):
        self.builder = builder
        logger = logging.getLogger(self.__class__.__name__)
        self.data_model = commands.DHXccdf(core)
        abstract.MenuButton.__init__(self, "gui:btn:main:xccdf", widget, core)
        self.widget = widget
        self.core = core
        
        self.body = self.builder.get_object("xccdf:box")

        # info
        self.label_title = self.builder.get_object("xccdf:lbl_title")
        self.label_version = self.builder.get_object("xccdf:lbl_version")
        self.label_url = self.builder.get_object("xccdf:lbl_file")
        self.label_resolved = self.builder.get_object("xccdf:lbl_resolved")
        self.label_language = self.builder.get_object("xccdf:lbl_language")
        self.label_description = self.builder.get_object("xccdf:lbl_description")
        self.label_status_current = self.builder.get_object("xccdf:lbl_status_current")
        self.label_warnings = self.builder.get_object("xccdf:lbl_warnings")
        self.label_notices = self.builder.get_object("xccdf:lbl_notices")
        self.label_file_references = self.builder.get_object("xccdf:lbl_file_references")
        self.box_references = self.builder.get_object("xccdf:box_references")

        self.btn_import = self.builder.get_object("xccdf:btn_import")
        self.btn_import.connect("clicked", self.__cb_import)

        self.btn_validate = self.builder.get_object("xccdf:btn_validate")
        self.btn_validate.connect("clicked", self.__cb_validate)

        self.btn_export = self.builder.get_object("xccdf:btn_export")
        self.btn_export.connect("clicked", self.__cb_export)

        self.add_sender(self.id, "update")
        self.add_sender(self.id, "load")
        self.add_sender(self.id, "lang_changed")

        details = self.data_model.get_details()
        try:
            self.set_detail(details)
        except KeyError: pass

        label_set_autowrap(self.label_title)
        label_set_autowrap(self.label_description)
        label_set_autowrap(self.label_warnings)
        label_set_autowrap(self.label_notices)

    # set functions
    def set_detail(self, details):
        """
        Set information about file.
        """
        STATUS_CURRENT = ["not specified", "accepted", "deprecated", "draft", "incomplet", "interim"]
        lang = details["lang"]
        self.label_title.set_text(details["titles"][lang] or "")
        self.label_description.set_text(details["descs"][lang] or "")
        self.label_version.set_text(details["version"] or "")
        self.label_url.set_text(details["id"] or "")
        self.label_status_current.set_text(STATUS_CURRENT[details["status_current"]] or "")
        self.label_resolved.set_text(["no", "yes"][details["resolved"]])
        self.label_warnings.set_text("\n".join(["%s: %s" % (warn[0], warn[1].text) for warn in details["warnings"]]) or "None")
        self.label_notices.set_text("\n".join(["%s: %s" % (notice[0], notice[1].text) for notice in details["notices"]]) or "None")
        self.label_file_references.set_text("")
        self.label_file_references.set_text("\n".join(details["files"]) or "None")
        self.label_language.set_text(lang or "")
        
        # References
        for child in self.box_references.get_children():
            child.destroy()

        for i, ref in enumerate(details["references"]):
            text = "%d) %s [<a href='%s'>link</a>]" % (i+1, " ".join((ref["title"] or "").split()), ref["identifier"])
            label = gtk.Label(text)
            self.box_references.pack_start(label, True, True)
            label.set_tooltip_text(ref[1])
            label.set_use_markup(True)
	    try:
                label.set_track_visited_links(True)
	    except AttributeError: pass
            label.set_line_wrap(True)
            label.set_line_wrap_mode(pango.WRAP_WORD) 
            label.set_alignment(0,0)
            label.connect("size-allocate", label_size_allocate)
            label.show()

    # callBack functions
    def __cb_import(self, widget):
        file = self.data_model.file_browse("Load XCCDF file", action=gtk.FILE_CHOOSER_ACTION_OPEN)
        if file != "":
            logger.debug("Loading XCCDF file %s", file)
            self.core.init(file)
            self.emit("load")
            details = self.data_model.get_details()
            try:
                self.set_detail(details)
            except KeyError: pass

    def __cb_validate(self, widget):
        validate = self.data_model.validate()
        self.core.notify(["Document is not valid !", "Document is valid.", 
            "Validation process failed, check for error in log file."][validate], [1, 0, 2][validate])

    def __cb_export(self, widget):
        self.data_model.export()

    def cb_changed(self, combobox, core):
        
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return
        core.selected_lang = model[active][0]
        self.emit("lang_changed")
        return
        
    
class MenuButtonOVAL(abstract.MenuButton):

    def __init__(self, box, widget, core):
        logger = logging.getLogger(self.__class__.__name__)
        abstract.MenuButton.__init__(self, "gui:btn:main:oval", widget, core)
        self.box = box
        self.title = None
        self.description = None
        self.version = None
        self.url = None
        self.language = None
        self.body = self.draw_body()


    def draw_body(self):
        body = gtk.VBox()

        body.show_all()
        body.hide()
        self.box.add(body)
        return body

class MainWindow(abstract.Window, threading.Thread):
    """TODO:
    """

    def __init__(self):

        threading.Thread.__init__(self)
        logger = logging.getLogger(self.__class__.__name__)
        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/scap-workbench/main.glade")
        self.builder.connect_signals(self)
        self.core = core.SWBCore(self.builder)
        assert self.core != None, "Initialization failed, core is None"

        self.window = self.builder.get_object("main:window")
        self.main_box = self.builder.get_object("main:box")

        # abstract the main menu
        self.menu = abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:main", self.builder.get_object("main:toolbar:main"), self.core))
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:edit", self.builder.get_object("main:toolbar:edit"), self.core))
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:reports", self.builder.get_object("main:toolbar:reports"), self.core))
        self.menu.add_item(tailoring.MenuButtonTailoring(self.builder, self.builder.get_object("main:toolbar:tailoring"), self.core))
        self.menu.add_item(scan.MenuButtonScan(self.builder, self.builder.get_object("main:toolbar:scan"), self.core))
        
        # subMenu_but_main
        submenu = abstract.Menu("gui:menu:main", self.builder.get_object("main:sub:main"), self.core)
        submenu.add_item(MenuButtonXCCDF(self.builder, self.builder.get_object("main:sub:main:xccdf"), self.core))
        submenu.add_item(MenuButtonOVAL(self.main_box, self.builder.get_object("main:sub:main:oval"), self.core))
        self.core.get_item("gui:btn:menu:main").set_menu(submenu)

        submenu = abstract.Menu("gui:menu:edit", self.builder.get_object("edit:sub:main"), self.core)
        submenu.add_item(edit.MenuButtonEditXCCDF(self.builder, self.builder.get_object("edit:sub:xccdf"), self.core))
        submenu.add_item(edit.MenuButtonEditProfiles(self.builder, self.builder.get_object("edit:sub:profiles"), self.core))
        submenu.add_item(edit.MenuButtonEditItems(self.builder, self.builder.get_object("edit:sub:items"), self.core))
        self.core.get_item("gui:btn:menu:edit").set_menu(submenu)

        self.core.register("main:button_forward", self.builder.get_object("main:button_forward"))
        self.core.register("main:button_back", self.builder.get_object("main:button_back"))
        #self.builder.get_object("main:button_back").set_sensitive(False)

        self.core.main_window = self.window
        self.window.show()
        self.builder.get_object("main:toolbar:main").set_active(True)

    def __cb_info_close(self, widget):
        self.core.info_box.hide()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        gtk.gdk.threads_leave()
        gtk.main_quit()
        return False

    def run(self):
        gtk.main()
