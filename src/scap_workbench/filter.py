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

import re
import gtk
import abstract
import logging
from events import EventObject

logger = logging.getLogger("scap-workbench")

class Filter:
    """Abstract class for defining filters"""

    def __init__(self, name, render):
        self.name = name
        self.active = False
        self.render = render

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
        self.eb.show_all()
    
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
            self.render.del_filter(self)
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
        self.add_sender(id, "filter_add")
        self.add_sender(id, "filter_del")

    def render(self, box):
        """Render Box for filters"""

        #search
        self.expander = ExpandBox(box, "Search / Filters", self.core)
        filter_box = self.expander.get_widget()
        alig_filters = self.add_frame(filter_box, "Search")
        self.search = Search(self)
        self.expander.get_widget().pack_start(self.search.get_widget(), True, True)

        #filter
        alig_filters = self.add_frame(filter_box, "Active filters")
        self.menu = gtk.Menu()

        #btn choose filter
        button = gtk.Button()
        button.set_relief(gtk.RELIEF_NONE)
        button.set_label("Add filter")
        button.connect_object("event", self.cb_chooseFilter, self.menu)
        filter_box.pack_end(button, False, True)
        box.show_all()

    def get_search_text(self):
        return self.search.entry.get_text()

    def add_filter_to_menu(self, filter_info):
        """ Function add filter tu popup menu
            If filter_info == None set own filter and callBack function is render_filter which
            create window for set own filter. Must def in child.
        """
        tooltips = gtk.Tooltips()
        if filter_info != None:
            menu_items = gtk.MenuItem(filter_info["name"])
            tooltips.set_tip(menu_items, filter_info["description"])
            filter_info.update({"active":False})     # if filter is active
        else:
            menu_items = gtk.MenuItem("User filter...")
            
        menu_items.show()
        self.menu.append(menu_items)
        menu_items.connect("activate", self.cb_menu, filter_info)
    
    def cb_menu(self, widget, filter_info):
        
        if filter_info != None:
            # if filter is activated yet
            if  filter_info["active"] == False:
                self.add_filter(filter_info)
            else:
                 msg = gtk.MessageDialog()
                 msg.set_markup("Filter is olready active.")
                 msg.show()
        else:
            self.render_filter()
        
    def render_filter(self):
        """abstract"""
        pass

    def cb_chooseFilter(self, menu, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            menu.popup(None, None, None, event.button, event.time)
            return True
        return False

    def add_filter(self, filtr_info):
        filtr_info["active"] = True
        filter = Filter(filtr_info["name"], self)
        self.expander.get_widget().pack_start(filter.get_widget(), True, True)
        self.filters.append({   "id":           filter,
                                "ref_model":    None,                       # model before filtering
                                "filtr_info":   filtr_info               # if is False filter will be remuved form active filter
                            })
        self.emit("filter_add")

    def del_filter(self, filter):

        filter.eb.destroy()
        for item in self.filters:
            if item["id"] == filter:
                item["filtr_info"]["active"] = False
                self.filters.remove(item)
        self.emit("filter_del")

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

class ItemFilter(Renderer):
    
    def __init__(self, core, builder):

        self.id_filter = 0
        objectBild = builder.get_object("tailoring:refines:box_filter")
        Renderer.__init__(self, "gui:btn:tailoring:refines:filter", core, objectBild)
        self.expander.cb_changed()
#-------------------------------------------------------------------------------
 
        filter = {"name":           "Select rule List",
                  "description":    "Select rule end get them to list.",
                  "func":           self.search_pokus,        # func for metch row in model func(model, iter)
                  "param":           [],                    # param tu function
                  "result_tree":    False,               # if result shoul be in tree or list
                  }
                  
        filter1 = {"name":           "Select rule/group with ensure",
                  "description":    "Select rule/group end get them to list.",
                  "func":           self.search_pokus1,        # func for metch row in model func(model, iter)
                  "param":           [],                    # param tu function
                  "result_tree":    False,               # if result shoul be in tree or list
                  }

        filter2 = {"name":          "Select rule Tree",
                  "description":    "Select rule end get them to tree.",
                  "func":           self.search_pokus,        # func for metch row in model func(model, iter)
                  "param":           [],                    # param tu function
                  "result_tree":    True,                       # if result shoul be in tree or list
                  }
                  
        self.add_filter_to_menu(filter)
        self.add_filter_to_menu(filter1)
        self.add_filter_to_menu(filter2) 
        self.add_filter_to_menu(None)

       #test filter
    def search_pokus(self, model, iter, params):
        pattern = re.compile("rule",re.IGNORECASE)
        if pattern.search(model.get_value(iter, 3),0,4) != None:
            return True
        else:
            return False
            
    def search_pokus1(self, model, iter, params):
        pattern = re.compile("ensure",re.IGNORECASE)
        if pattern.search(model.get_value(iter, 3)) != None:
            return True
        else:
            return False
#-------------------------------------------------------------------------------
            
    def render_filter(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Own filter")
        self.window.set_size_request(400, 400)
        self.window.connect("delete_event", self.delete_event)

        btn_filter = gtk.Button("test")
        btn_filter.connect("clicked", self.cb_setFilter)
        box = gtk.VBox()
        box.pack_start(btn_filter, False, False)
        self.window.add(box)
        self.window.show_all()
        return self.window

    def cb_setFilter(self, widget):
        
        filter = {"name": "pokus window",
                  "description": "popis",
                  "func": self.search,
                  "active": True}
        self.add_filter(filter)
        self.window.destroy()

    def delete_event(self, widget, event):
        self.window.destroy()
