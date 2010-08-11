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

import abstract
import tailoring

class MenuButtonXCCDF(abstract.MenuButton):
    """
    GUI for operations with xccdf file.
    """
    def __init__(self, c_body=None, sensitivity=None):
        abstract.MenuButton.__init__(self,"menu:main:btn:xccdf", "XCCDF", c_body, sensitivity)
        self.c_body = c_body
        
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
        print "clicked = ", data

    def cb_changed(self, combobox):
        model = combobox.get_model()
        index = combobox.get_active()
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
        self.cBox_language.connect('changed', self.cb_changed)
        self.cBox_language.set_active(0)
        table.attach(self.cBox_language, 1, 2, 4, 5,gtk.FILL,gtk.FILL)

        self.set_language(["English", "Czech", "Russian"], 0)
        
        # generator for oval
        alig = self.add_frame(body, "<b>Generator for OVAL</b>")

        # operations
        alig = self.add_frame(body, "<b>Operations</b>", False)
        box = gtk.HButtonBox()
        box.set_layout(gtk.BUTTONBOX_START)
        
        btn = gtk.Button("Load File")
        btn.connect("clicked", self.cb_btn, "load")
        box.add(btn)
        
        btn = gtk.Button("Save Changes")
        btn.connect("clicked", self.cb_btn, "save")        
        box.add(btn)
        
        btn = gtk.Button("Validate")
        btn.connect("clicked", self.cb_btn, "valid")
        box.add(btn)
        alig.add(box)

        # add to conteiner
        body.show_all()
        body.hide()
        self.c_body.add(body)
        return body


class MenuButtonOVAL(abstract.MenuButton):

    def __init__(self, c_body=None, sensitivity=None):
        abstract.MenuButton.__init__(self,"menu:main:btn:oval", "Oval", c_body, sensitivity)
        self.c_body = c_body
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
        self.c_body.add(body)
        return body

class MainWindow:
    """TODO:
    """

    def __init__(self):
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Main window")
        self.window.set_size_request(900, 700)
        self.window.connect("delete_event", self.delete_event)
        self.vbox_main = gtk.VBox()
        self.vbox_main.show()
        self.window.add(self.vbox_main)
        
        # container for body
        vbox_body = gtk.VBox()
        vbox_body.show()
        
        #create menu

        # main menu
        vbox_menu = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_menu, expand=False, fill=True, padding=0)
        self.menu = abstract.Menu("menu:main", vbox_menu)
        menu1_but1 = abstract.MenuButton("menu:main:btn:main", "Main", vbox_body)
        self.menu.add_item(menu1_but1)
        menu1_but2 = abstract.MenuButton("menu:main:btn:tailoring", "Tailoring", vbox_body)
        self.menu.add_item(menu1_but2)
        menu1_but3 = abstract.MenuButton("menu:main:btn:edit", "Edit", vbox_body)
        self.menu.add_item(menu1_but3)
        menu1_but4 = abstract.MenuButton("menu:main:btn:scan", "Scan", vbox_body)
        self.menu.add_item(menu1_but4)
        menu1_but5 = abstract.MenuButton("menu:main:btn:reports", "Reports", vbox_body)
        self.menu.add_item(menu1_but5)
        
        
        # subMenu_but_main
        vbox_submenu = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_submenu, expand=False, fill=True, padding=0)
        self.submenu = abstract.Menu("menu:main", vbox_submenu)
        menu2_but1 = MenuButtonXCCDF(vbox_body)
        self.submenu.add_item(menu2_but1)
        menu2_but2 = MenuButtonOVAL(vbox_body)
        self.submenu.add_item(menu2_but2)
        menu1_but1.set_menu(self.submenu)

        # subMenu_but_tailoring
        vbox_submenu1 = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_submenu1, expand=False, fill=True, padding=0)
        self.submenu1 = abstract.Menu("menu:tailoring", vbox_submenu1)
        menu3_but1 = tailoring.MenuButtonProfiles(vbox_body)
        self.submenu1.add_item(menu3_but1)
        menu3_but2 = tailoring.MenuButtonRefines(vbox_body)
        self.submenu1.add_item(menu3_but2)
        menu1_but2.set_menu(self.submenu1)

        # subMenu_but_edit

        # subMenu_but_scan

        # subMenu_but_reports



        self.vbox_main.pack_start(vbox_body, expand=True, fill=True, padding=0)
        
        self.window.show()
        self.menu.show()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        gtk.main_quit()
        return False
