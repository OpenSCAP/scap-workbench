#!/usr/bin/env python
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
import logging
import pango
import threading

import core
import abstract
import tailoring
import scan
import logging
import commands

logger = logging.getLogger("OSCAPEditor")

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
    def __init__(self, box, widget, core):
        logger = logging.getLogger(self.__class__.__name__)
        self.data_model = commands.DataHandler(core)
        abstract.MenuButton.__init__(self, "gui:btn:main:xccdf", widget, core)
        self.box = box
        self.core = core
        
        self.add_sender(self.id, "load")
        self.add_sender(self.id, "lang_changed")

        # referencies
        self.label_title = None
        self.label_description = None
        self.label_version = None
        self.label_url = None
        self.cBox_language = None

        # draw body
        self.body = self.draw_body()
        
        
    # set functions
    def set_detail(self, tile, description, version, url):
        """
        Set information about file.
        """
        self.label_title.set_text(title)
        self.label_description.set_text(description)
        self.label_version.set_text(version)
        self.label_url.set_text(url)
        
    def set_language(self, languages, active):
        """
        Set list of languades for comboBox and set active.
        @param languages List of laguages name.
        @param active Number of active item in list
        """
        model = self.cBox_language.get_model()
        model.clear()
        for lan in languages:
            model.append([lan])
        self.cBox_language.set_active(active)
        
    # callBack functions
    def cb_btn(self, btn, data=None):
        if data == "load": 
            file = self.data_model.file_browse("Load XCCDF file", action=gtk.FILE_CHOOSER_ACTION_OPEN)
            if file != "":
                logger.debug("Loading XCCDF file %s", file)
                self.core.init(file)
                self.emit("load")
                self.set_language(self.data_model.get_languages(), 0)

    def cb_changed(self, combobox, core):
        
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return
        core.selected_lang = model[active][0]
        self.emit("lang_changed")
        return
        
    # draw functions
    def add_label(self,table, text, left, right, top, bottom, x=gtk.FILL, y=gtk.FILL):
        label = gtk.Label(text)
        table.attach(label, left, right, top, bottom, x, y)
        label.set_alignment(0, 0.5)
        return label
        
    def add_frame(self, body, text, expand = True):
        frame = gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)
        if expand: body.pack_start(frame, expand=True, fill=True, padding=0)
        else: body.pack_start(frame, expand=False, fill=True, padding=0)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return alig

    def draw_body(self):
        body = gtk.VBox()
        alig = self.add_frame(body, "<b>List</b>")
        table = gtk.Table(5 ,2)
        alig.add(table)

        self.add_label(table, "Name: ", 0, 1, 0, 1)
        self.add_label(table, "Description: ", 0, 1, 1, 2)
        self.add_label(table, "Version: ", 0, 1, 2, 3)
        self.add_label(table, "URL: ", 0, 1, 3, 4)
        self.add_label(table, "Prefered Language: ", 0, 1, 4, 5)

        self.label_title = self.add_label(table, "None ", 1, 2, 0, 1)
        self.label_description = self.add_label(table, "None ", 1, 2, 1, 2)
        self.label_version = self.add_label(table, "None", 1, 2, 2, 3)
        self.label_url = self.add_label(table, "None ", 1, 2, 3, 4)

        self.cBox_language = gtk.ComboBox()
        model = gtk.ListStore(str)
        cell = gtk.CellRendererText()
        self.cBox_language.pack_start(cell)
        self.cBox_language.add_attribute(cell, 'text', 0)
        self.cBox_language.set_model(model)
        self.cBox_language.connect('changed', self.cb_changed, self.core)
        self.cBox_language.set_active(0)
        table.attach(self.cBox_language, 1, 2, 4, 5,gtk.FILL,gtk.FILL)

        # operations
        alig = self.add_frame(body, "<b>Operations</b>", False)
        alig.set_padding(10,10,10,10)
        box = gtk.HButtonBox()
        box.set_layout(gtk.BUTTONBOX_START)
        
        btn = gtk.Button("Load File")
        btn.connect("clicked", self.cb_btn, "load")
        box.add(btn)
        
        btn = gtk.Button("Save Changes")
        btn.set_sensitive(False)
        btn.connect("clicked", self.cb_btn, "save")        
        box.add(btn)
        
        btn = gtk.Button("Validate")
        btn.set_sensitive(False)
        btn.connect("clicked", self.cb_btn, "valid")
        box.add(btn)
        alig.add(box)

        if self.core.lib != None: 
            self.set_language(self.data_model.get_languages(), 0)

        # add to conteiner
        body.show_all()
        body.hide()
        self.box.add(body)
        return body


    
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
        self.core = core.OECore()
        assert self.core != None, "Initialization failed, core is None"
        self.builder = gtk.Builder()
        self.builder.add_from_file("glade/main.glade")
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("main:window")
        self.main_box = self.builder.get_object("main:box")

        # abstract the main menu
        self.menu = abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:main", self.builder.get_object("main:toolbar:main"), self.core))
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:tailoring", self.builder.get_object("main:toolbar:tailoring"), self.core))
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:edit",  self.builder.get_object("main:toolbar:edit"), self.core))
        self.menu.add_item(scan.MenuButtonScan(self.main_box, self.builder.get_object("main:toolbar:scan"), self.core))
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:reports", self.builder.get_object("main:toolbar:reports"), self.core))
        
        # subMenu_but_main
        submenu = abstract.Menu("gui:menu:main", self.builder.get_object("main:sub:main"), self.core)
        submenu.add_item(MenuButtonXCCDF(self.main_box, self.builder.get_object("main:sub:main:xccdf"), self.core))
        submenu.add_item(MenuButtonOVAL(self.main_box, self.builder.get_object("main:sub:main:oval"), self.core))
        self.core.get_item("gui:btn:menu:main").set_menu(submenu)

        ## subMenu_but_tailoring
        submenu = abstract.Menu("gui:menu:tailoring", self.builder.get_object("main:sub:tailoring"), self.core)
        submenu.add_item(tailoring.MenuButtonProfiles(self.main_box, self.builder.get_object("main:sub:tailoring:profiles"), self.core))
        submenu.add_item(tailoring.MenuButtonRefines(self.main_box, self.builder.get_object("main:sub:tailoring:refines"), self.core))
        self.core.get_item("gui:btn:menu:tailoring").set_menu(submenu)

        self.core.main_window = self.window
        self.window.show()
        self.builder.get_object("main:toolbar:main").set_active(True)

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        gtk.main_quit()
        return False

    def run(self):
        gtk.main()
