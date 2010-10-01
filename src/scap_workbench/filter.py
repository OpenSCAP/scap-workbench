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

import gtk
import abstract
import logging
from events import EventObject

logger = logging.getLogger("scap-workbench")

class Filter:
    """Abstract class for defining filters"""

    def __init__(self, name):
        self.name = name
        self.active = False

        self.__render()

    def __render(self):
        self.box = gtk.HBox()
        label = gtk.Label(self.name)
        label.set_justify(gtk.JUSTIFY_LEFT)

        alig = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(label)
        self.box.pack_start(alig, True, True)

        self.button = gtk.Image()
        pic = self.button.render_icon(gtk.STOCK_CANCEL, size=gtk.ICON_SIZE_MENU, detail=None)
        self.button.set_from_pixbuf(pic)
        alig = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(self.button)
        eb = gtk.EventBox()
        eb.connect("button-press-event", self.__cb_button)
        eb.add(alig)
        self.box.pack_end(eb, False, False)

        self.eb = gtk.EventBox()
        self.eb.add(self.box)
        self.eb.set_border_width(2)
        """
        self.eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
        self.eb.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.color_parse("yellow"))
        self.eb.connect("enter-notify-event", self.__cb_enter)
        self.eb.connect("leave-notify-event", self.__cb_leave)
        self.eb.connect("button-press-event", self.__cb_btn_press)
        """
        self.eb.set_state(gtk.STATE_SELECTED)

        self.box.show()
        self.eb.show()
    
    """
    def __cb_enter(self, widget, event):
        if widget.get_state() == gtk.STATE_NORMAL: widget.set_state(gtk.STATE_ACTIVE)

    def __cb_leave(self, widget, event):
        if widget.get_state() == gtk.STATE_ACTIVE: widget.set_state(gtk.STATE_NORMAL)
    """

    def __cb_btn_press(self, widget, event):
        if event.button == 1:
            if  widget.get_state() == gtk.STATE_SELECTED: widget.set_state(gtk.STATE_ACTIVE)
            else: widget.set_state(gtk.STATE_SELECTED)

    def __cb_button(self, widget, event):
        self.active = not self.active
        if self.active: 
            self.eb.hide()
            stock = gtk.STOCK_APPLY
        else: 
            self.eb.show()
            stock = gtk.STOCK_CANCEL

        #pic = self.button.render_icon(stock, size=gtk.ICON_SIZE_MENU, detail=None)
        #self.button.set_from_pixbuf(pic)

    def get_widget(self):
        return self.eb

class Search(EventObject):

    def __init__(self, render):

        self.render = render
        self.render.add_sender(id, "search")
        self.__render()

    def __render(self):
        self.box = gtk.HBox()

        self.entry = gtk.Entry()
        alig = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(self.entry)
        self.box.pack_start(alig, True, True)

        self.button = gtk.Button()
        self.button.set_relief(gtk.RELIEF_NONE)
        self.button.set_label("Search")
        self.button.connect("clicked", self.cb_search)
        alig = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(self.button)
        self.box.pack_start(alig, True, True)
        

        self.box.show_all()

    def get_widget(self):
        return self.box

    def cb_search(self, widget):
        self.render.emit("search")

class Renderer(abstract.MenuButton,EventObject):

    def __init__(self,id, core, box):

        self.core = core
        self.filters = []
        self.id = id
        EventObject.__init__(self, self.core)
        self.core.register(id, self)
        self.render(box)

    def render(self, box):
        """Render Box for filters"""

        self.expander = ExpandBox(box, "Search / Filters", self.core)
        filter_box = self.expander.get_widget()
        alig_filters = self.add_frame(filter_box, "Search")
        self.search = Search(self)
        self.add_filter(self.search)
        alig_filters = self.add_frame(filter_box, "Active filters")
        self.add_filter(Filter("Filter 1"))
        self.add_filter(Filter("Filter 2"))
        box.show_all()
        
    def add_filter(self, filter):
        
        filter_box = self.expander.get_widget()
        self.expander.get_widget().pack_start(filter.get_widget(), True, True)
        self.filters.append(filter)

    def del_filter(self, filter):
        raise NotImplementedError

    def get_search_text(self):
        return self.search.entry.get_text()

class ExpandBox(abstract.EventObject):
    """
    Create expand box. Set only to conteiner.
    """
    
    def __init__(self, box, text, core=None):
        """
        @param box Container for this expandBox.
        @param text Button name for show or hide expandBox
        @param show If ExpanBox should be hidden/showed False/True
        """
        self.core = core
        
        # body for expandBox
        rollBox = gtk.HBox()
        box.pack_start(rollBox, True, True)

        alig = gtk.Alignment()
        alig.set_padding(5, 5, 5, 5) # top, bottom, left, right
        self.frameContent = gtk.VBox()
        alig.add(self.frameContent)
        rollBox.pack_start(alig, True, True)
        
        # create icons
        self.arrowTop = gtk.Image()
        self.arrowBottom = gtk.Image()
        self.pixbufShow = self.arrowTop.render_icon(gtk.STOCK_GO_FORWARD, size=gtk.ICON_SIZE_MENU, detail=None)
        self.pixbufHide = self.arrowBottom.render_icon(gtk.STOCK_GO_BACK, size=gtk.ICON_SIZE_MENU, detail=None)
        self.arrowTop.set_from_pixbuf(self.pixbufShow)
        self.arrowBottom.set_from_pixbuf(self.pixbufShow)
        
        # create label
        self.label = gtk.Label(text)
        self.label.set_angle(90)

        #create button
        hbox = gtk.VBox()
        hbox.pack_start(self.arrowTop, False, True)        
        hbox.pack_start(self.label, True, True)
        hbox.pack_start(self.arrowBottom, False, True)
        btn = gtk.Button()
        btn.add(hbox)
        rollBox.pack_start(btn, False, True)
        btn.connect("clicked", self.cb_changed)

    def cb_changed(self, widget=None):
        logger.debug("Expander switched to %s", self.frameContent.get_property("visible"))
        if self.frameContent.get_property("visible"):
            self.frameContent.hide_all()
            self.arrowTop.set_from_pixbuf(self.pixbufShow)
            self.arrowBottom.set_from_pixbuf(self.pixbufShow)
        else:
            self.frameContent.show_all()
            self.arrowTop.set_from_pixbuf(self.pixbufHide)
            self.arrowBottom.set_from_pixbuf(self.pixbufHide)

    def get_widget(self):
        return self.frameContent
