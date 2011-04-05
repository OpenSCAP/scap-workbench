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
import gtk, gnome, gnome.ui
import gobject
import logging
import pango
import threading

import core
import abstract
import tailoring
import scan
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

        self.btn_new = self.builder.get_object("xccdf:btn_new")
        self.btn_new.connect("clicked", self.__cb_new)

        self.btn_import = self.builder.get_object("xccdf:btn_import")
        self.btn_import.connect("clicked", self.__cb_import)

        self.btn_validate = self.builder.get_object("xccdf:btn_validate")
        self.btn_validate.connect("clicked", self.__cb_validate)

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

        label_set_autowrap(self.label_title)
        label_set_autowrap(self.label_description)
        label_set_autowrap(self.label_warnings)
        label_set_autowrap(self.label_notices)

    def __add_file_info(self, name, file_info):

        # Add table of information to the expander with label name
        expander = gtk.Expander()
        label = gtk.Label("OVAL: %s" % (name,))
        pango_list = pango.AttrList()
        pango_list.insert(pango.AttrWeight(pango.WEIGHT_BOLD, start_index=0, end_index=-1))
        if not file_info:
            pango_list.insert(pango.AttrForeground(65535, 0, 0, start_index=0, end_index=-1))
        label.set_attributes(pango_list)
        expander.set_label_widget(label)
        expander.set_expanded(True)
        align = gtk.Alignment()
        align.set_padding(5, 10, 25, 0)

        if not file_info:
            label = gtk.Label("File not found: %s" % (name))
            label.set_attributes(pango_list)
            align.add(label)
        else:
            table = gtk.Table(rows=5, columns=2)
            table.set_col_spacings(spacing=5)
            align.add(table)

            # use table to add information
            label = gtk.Label("Product name:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label("Product version:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 1, 2, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label("Schema version:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 2, 3, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label("Timestamp:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 3, 4, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label("Valid:")
            label.set_alignment(0.0, 0.50)
            table.attach(label, 0, 1, 4, 5, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)

            label = gtk.Label(file_info["product_name"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 0, 1, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label(file_info["product_version"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 1, 2, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label(file_info["schema_version"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 2, 3, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label(file_info["timestamp"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 3, 4, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
            label = gtk.Label(file_info["valid"])
            label.set_alignment(0.0, 0.50)
            table.attach(label, 1, 2, 4, 5, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)

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
        self.label_status_current.set_text(abstract.ENUM_STATUS_CURRENT.map(details["status_current"])[1])
        self.label_resolved.set_text(["no", "yes"][details["resolved"]])
        self.label_warnings.set_text("\n".join(["%s: %s" % (warn[0], warn[1].text) for warn in details["warnings"]]) or "None")
        self.label_notices.set_text("\n".join(["%s: %s" % (notice[0], notice[1].text) for notice in details["notices"]]) or "None")
        self.label_language.set_text(lang or "")
        
        self.btn_close.set_sensitive(True)
        self.btn_validate.set_sensitive(True)
        self.btn_export.set_sensitive(True)
        self.__menu_sensitive(True)

        # References
        for child in self.box_references.get_children():
            child.destroy()

        for i, ref in enumerate(details["references"]):
            label = gtk.Label()
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
	    except AttributeError: pass
            label.set_line_wrap(True)
            label.set_line_wrap_mode(pango.WRAP_WORD) 
            label.set_alignment(0,0)
            label.connect("size-allocate", label_size_allocate)
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
        except KeyError: pass

        self.emit("load")

    def __cb_import(self, widget):
        file = self.data_model.file_browse("Load XCCDF file", action=gtk.FILE_CHOOSER_ACTION_OPEN)
        if file != "":
            self.__cb_close(None)
            logger.debug("Loading XCCDF file %s", file)
            if not self.core.init(file): return
            self.emit("load")

            try:
                self.__update()
            except KeyError: pass

    def __cb_validate(self, widget):
        validate = self.data_model.validate()
        message = [ "Document is not valid !",
                    "Document is valid.",
                    "Validation process failed, check for error in log file.",
                    "File not saved, use export first."][validate]
        lvl = [ core.Notification.WARNING,
                core.Notification.SUCCESS,
                core.Notification.ERROR,
                core.Notification.INFORMATION][validate]
        self.notifications.append(self.core.notify(message, lvl, msg_id="notify:xccdf:validate"))

    def __cb_export(self, widget):
        file_name = self.data_model.export()
        if file_name:
            self.core.notify_destroy("notify:xccdf:validate")
            self.notifications.append(self.core.notify("Benchmark has been exported to \"%s\"" % (file_name,),
                core.Notification.SUCCESS, msg_id="notify:xccdf:export"))
            self.core.xccdf_file = file_name

    def __menu_sensitive(self, active):
        self.core.get_item("gui:btn:menu:tailoring").set_sensitive(active)
        self.core.get_item("gui:btn:menu:scan").set_sensitive(active)

    def __cb_close(self, widget):
        self.btn_close.set_sensitive(False)
        self.btn_validate.set_sensitive(False)
        self.btn_export.set_sensitive(False)
        self.__menu_sensitive(False)
        self.core.destroy()
        self.__clear()
        self.core.notify_destroy("notify:xccdf:validate")
        self.core.notify_destroy("notify:xccdf:export")
        self.emit("load")
    
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
        self.core = core.SWBCore(self.builder, True)
        assert self.core != None, "Initialization failed, core is None"

        self.window = self.builder.get_object("main:window")
        self.core.main_window = self.window
        self.main_box = self.builder.get_object("main:box")

        # abstract the main menu
        self.menu = abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
        self.menu.add_item(MenuButtonXCCDF(self.builder, self.builder.get_object("main:toolbar:main"), self.core))
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:reports", self.builder.get_object("main:toolbar:reports"), self.core))
        self.menu.add_item(tailoring.MenuButtonTailoring(self.builder, self.builder.get_object("main:toolbar:tailoring"), self.core))
        self.menu.add_item(scan.MenuButtonScan(self.builder, self.builder.get_object("main:toolbar:scan"), self.core))
        
        self.window.show()
        self.builder.get_object("main:toolbar:main").set_active(True)

        self.core.get_item("gui:btn:main:xccdf").update()

    def __cb_info_close(self, widget):
        self.core.info_box.hide()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        gtk.gdk.threads_leave()
        gtk.main_quit()
        return False

    def run(self):
        gnome.init("SCAP Workbench", "0.2.3")
        gtk.main()
