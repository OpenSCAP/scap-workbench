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
import pango

import abstract
import logging
import core
from events import EventObject

import commands
import render


class ScanList(abstract.List):
    
    def __init__(self, core=None):
        self.core = core
        self.data_model = commands.DHScan(core)
        abstract.List.__init__(self, "gui:scan:scan_list", core)
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        #self.add_receiver()


    def __update(self):
        self.data_model.fill()

class MenuButtonScan(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, c_body=None, sensitivity=None, core=None):
        abstract.MenuButton.__init__(self, "gui:btn:menu:scan",  "Scan", gtk.STOCK_DIALOG_AUTHENTICATION, c_body, sensitivity)
        self.core = core
        self.c_body = c_body

        #draw body
        self.body = self.draw_body()

        # set signals
        self.add_sender(self.id, "update")

    #call back function
    def cb_btnScan(self, widget, data):
        pass
        #TODO
        
    #draw
    def draw_body(self):
        body = gtk.VBox()
        
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(10, 10, 10, 10)
        body.add(alig)
        
        vbox_main = gtk.VBox()
        alig.add(vbox_main)
        
        # Scan list
        self.scanList = ScanList(core=self.core)
        vbox_main.pack_start(self.scanList.get_widget(), True, True, 2)
        
        vbox_main.pack_start(gtk.HSeparator(), False, True, 2)
        
        #Progress Bar
        self.progress = gtk.ProgressBar()
        vbox_main.pack_start(self.progress, False, True, 2)
        
        #Buttons
        btnBox = gtk.HButtonBox()
        btnBox.set_layout(gtk.BUTTONBOX_START)
        vbox_main.pack_start(btnBox, False, True, 2)
        
        btn = gtk.Button("Scan")
        btn.connect("clicked", self.cb_btnScan, "scan")
        btnBox.add(btn)
        
        btn = gtk.Button("Pause")
        btn.connect("clicked", self.cb_btnScan, "stop")
        btnBox.add(btn)
        
        btn = gtk.Button("Cancel")
        btn.connect("clicked", self.cb_btnScan, "cancel")
        btnBox.add(btn)
        
        btn = gtk.Button("Export XCCDF")
        btn.connect("clicked", self.cb_btnScan, "exp_xccdf")
        btnBox.add(btn)
        
        btn = gtk.Button("Export OVAL")
        btn.connect("clicked", self.cb_btnScan, "exp_oval")
        btnBox.add(btn)
        
        body.show_all()
        body.hide()
        self.c_body.add(body)
        return body
        
