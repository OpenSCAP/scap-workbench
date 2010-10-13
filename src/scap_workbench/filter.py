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

import re
import gtk
import abstract
import logging
from events import EventObject

import sys, os

logger = logging.getLogger("scap-workbench")

class Filter:
    """Abstract class for defining filters"""

    def __init__(self, name, description="", params={}, istree=True, renderer=None, func=None):

        self.name = name
        self.description = ""
        self.func = func
        self.params = params
        self.istree = istree
        self.renderer = renderer
        self.model = None
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
        self.eb.set_state(gtk.STATE_SELECTED)

    def __cb_btn_press(self, widget, event):
        if event.button == 1:
            if  widget.get_state() == gtk.STATE_SELECTED: widget.set_state(gtk.STATE_ACTIVE)
            else: widget.set_state(gtk.STATE_SELECTED)

    def __cb_button(self, widget, event):
        if self.renderer: self.renderer.del_filter(self)
        self.eb.hide()
        self.active = False

    def get_widget(self):
        return self.eb

class Search(EventObject):

    def __init__(self, renderer):

        self.renderer = renderer
        self.renderer.add_sender(id, "search")
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
        self.renderer.emit("search")

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

    def add_filter_to_menu(self, filter):
        """ Function add filter tu popup menu
        """
        assert filter != None, "Can't add None filter"
        tooltips = gtk.Tooltips()
        menu_item = gtk.MenuItem(filter.name)
        tooltips.set_tip(menu_item, filter.description)
            
        menu_item.show()
        self.menu.append(menu_item)
        menu_item.connect("activate", self.__cb_menu, filter)
    
    def __cb_menu(self, widget, filter):
        
        # if filter is activated yet
        if filter.active == False:
            self.add_filter(filter)
        else:
            self.core.notify("Filter is already active.", 1)
        
    def cb_chooseFilter(self, menu, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            menu.popup(None, None, None, event.button, event.time)
            return True
        return False

    def add_filter(self, filter):
        """ Add filter to list active filter and emit signal filter was added"""
        filter.active = True
        self.expander.get_widget().pack_start(filter.get_widget(), True, True)
        filter.get_widget().show_all()
        self.filters.append(filter)
        self.emit("filter_add")

    def del_filter(self, filter):
        """ remove filter from active filters and emit signal deleted"""
        if filter in self.filters: 
            self.filters.remove(filter)
            self.emit("filter_del")
        else: self.core.notify("Removing not existed filter !", 2)
        
    def init_filter(self):
        """ clean all acive filters"""
        for filter in self.filters:
            filter.active = False
            filter.eb.destroy()
        self.filters = []
        

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
        self.frameContent.show_all()

    def cb_changed(self, widget=None):
        logger.debug("Expander switched to %s", not self.frameContent.get_property("visible"))
        if self.frameContent.get_property("visible"):
            self.frameContent.hide()
            self.arrowTop.set_from_pixbuf(self.pixbufShow)
            self.arrowBottom.set_from_pixbuf(self.pixbufShow)
        else:
            self.frameContent.show()
            self.arrowTop.set_from_pixbuf(self.pixbufHide)
            self.arrowBottom.set_from_pixbuf(self.pixbufHide)

    def get_widget(self):
        return self.frameContent

class ItemFilter(Renderer):
    
    def __init__(self, core, builder):

        self.core = core
        self.id_filter = 0
        self.builder = builder
        self.box_filter = self.builder.get_object("tailoring:refines:box_filter")
        self.user_filter_builder = gtk.Builder()
        self.user_filter_builder.add_from_file("/usr/share/scap-workbench/filter_tailoring.glade")
        self.user_filter_window = self.user_filter_builder.get_object("user_filter:dialog")
        self.user_filter_window.connect("delete-event", self.__cb_cancel)
        Renderer.__init__(self, "gui:btn:tailoring:refines:filter", core, self.box_filter)

        # get objects from glade
        self.user_filter_id = self.user_filter_builder.get_object("entry_id")
        self.user_filter_description = self.user_filter_builder.get_object("entry_description")
        self.user_filter_selected = self.user_filter_builder.get_object("cb_selected")
        self.user_filter_structure = self.user_filter_builder.get_object("cb_structure")
        self.user_filter_rule_group = self.user_filter_builder.get_object("search:cb_rule_group")
        self.user_filter_column = self.user_filter_builder.get_object("search:cb_column")
        self.user_filter_text = self.user_filter_builder.get_object("search:entry_text")
        self.info_box = self.user_filter_builder.get_object("info_box")

        self.user_filter_builder.get_object("btn_ok").connect("clicked", self.__cb_add)
        self.user_filter_builder.get_object("btn_cancel").connect("clicked", self.__cb_cancel)

        # import filters
        self.importer = Loader(self.core)
        self.importer.import_filters()

        # fill example filters
        filter = Filter("Hide groups", "Show all rules in list, hide groups.", istree=False, renderer=self, func=self.__search_func)
        filter1 = Filter("Show only groups with rules", "Hide all groups that has no rules.", istree=True, renderer=self, func=self.__search_func)
        filter2 = Filter("Show only selected rules/groups", "Hide all groups and rules that are not selected.", params={"selected": True}, istree=True, renderer=self, func=self.__search_func)

        self.add_filter_to_menu(filter)
        self.add_filter_to_menu(filter1)
        self.add_filter_to_menu(filter2)

        menu_item = gtk.MenuItem("User filter ...")
        menu_item.show()
        self.menu.append(menu_item)
        menu_item.connect("activate", self.__user_filter_new)

    def __search_func(self, model, iter, params):
        pattern = re.compile("rule", re.IGNORECASE)
        if pattern.search(model.get_value(iter, 3), 0, 4) != None:
            return True
        else:
            return False

    def __user_filter_new(self, widget):
        self.user_filter_window.set_transient_for(self.core.main_window)
        self.user_filter_window.show_all()

    def __cb_cancel(self, widget, event=None):
        self.user_filter_window.hide()

    def __cb_add(self, widget):
        
        params = {"searchIn": self.user_filter_rule_group.get_active(),
                  "searchData": self.user_filter_column.get_active(),
                  "selected": self.user_filter_selected.get_active(),
                  "text":      self.user_filter_text.get_text()}
        print params
        filter = Filter(self.user_filter_id.get_text(), self.user_filter_description.get_text(), params, istree=self.user_filter_structure.get_active() is 0, renderer=self)
        filter.func = self.__filter_func
        self.add_filter(filter)
        self.user_filter_window.hide()

    def __filter_func(self, model, iter, params):

        #search in
        RULE_GROUP = 0
        RULE = 1
        GROUP = 2
        #search data
        TEXT = 0
        ID = 1
        #selected
        TRUE_FALSE = 0
        TRUE = 1
        FALSE = 2
        #data in model
        COLUMN_ID       = 0
        COLUMN_NAME     = 1
        COLUMN_PICTURE  = 2
        COLUMN_TEXT     = 3
        COLUMN_COLOR    = 4
        COLUMN_SELECTED = 5
        COLUMN_PARENT   = 6
        column = [COLUMN_NAME, COLUMN_ID]
        
        res = True
        # if is rule or group
        if params["searchIn"] != RULE_GROUP:
            pattern = re.compile("rule",re.IGNORECASE)
            type = [GROUP, RULE] [pattern.search(model.get_value(iter, COLUMN_TEXT), 0, 4) != None]

            if params["searchIn"] != type:
                return False
        
        # search text if is set
        if params["text"] != "":
            pattern = re.compile(params["text"],re.IGNORECASE)
            if pattern.search(model.get_value(iter, column[params["searchData"]])) == None: 
                return False
        
        # if is selected, not selected or both
        if params["selected"] == TRUE_FALSE:
            return True
        else: return (model.get_value(iter, COLUMN_SELECTED) == [0,1,0][params["selected"]])


class ScanFilter(Renderer):

    #data in model
    COLUMN_ID = 0               # id of rule
    COLUMN_RESULT = 1           # Result of scan
    COLUMN_FIX = 2              # fix
    COLUMN_TITLE = 3            # Description of rule
    COLUMN_DESC = 4             # Description of rule
    COLUMN_COLOR_TEXT_TITLE = 5 # Color of text description
    COLUMN_COLOR_BACKG = 6      # Color of cell
    COLUMN_COLOR_TEXT_ID = 7    # Color of text ID
        
    def __init__(self, core, builder):
        self.id_filter = 0
        self.builder = builder
        self.box_filter = self. builder.get_object("scan:box_filter")
        self.user_filter_builder = gtk.Builder()
        self.user_filter_builder.add_from_file("/usr/share/scap-workbench/filter_scan.glade")
        self.user_filter_window = self.user_filter_builder.get_object("user_filter:dialog")
        self.user_filter_window.connect("delete-event", self.__cb_cancel)
        Renderer.__init__(self, "gui:btn:menu:scan:filter", core, self.box_filter)

        filter = Filter("Only tests with result PASS", "Show tests that has result PASS", params=["Pass"], istree=False, renderer=self, func=self.__filter_func)
        filter1 = Filter("Only tests with result ERROR", "Show tests that has result ERROR", params=["error"], istree=False, renderer=self, func=self.__filter_func)
        filter2 = Filter("Only tests with result FAIL", "Show tests that has result FAIL", params=["fail"], istree=False, renderer=self, func=self.__filter_func)

        self.add_filter_to_menu(filter)
        self.add_filter_to_menu(filter1)
        self.add_filter_to_menu(filter2)

        menu_item = gtk.MenuItem("User filter ...")
        menu_item.show()
        self.menu.append(menu_item)
        menu_item.connect("activate", self.render_filter)

    #filter
    def __filter_func(self, model, iter, params):
        pattern = re.compile(params[0],re.IGNORECASE)
        if pattern.search(model.get_value(iter, ScanFilter.COLUMN_RESULT)) != None:
            return True
        else:
            return False

    def __cb_cancel(self, widget, event=None):
        self.user_filter_window.hide()
            
    def render_filter(self, widget=None):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("User filter")
        #self.window.set_size_request(325, 240)
        self.window.connect("delete_event", self.delete_event)
        self.window.set_modal(True)
        self.window.set_property("resizable", False)
        
        alig = gtk.Alignment()
        alig.set_padding(10, 0, 10, 10)

        box_main = gtk.VBox()
        alig.add(box_main)

        #information for filter
        table = gtk.Table()
       
        self.label_to_table("Name filter:", table,  0, 1, 0, 1)
        self.label_to_table("Search text in:", table,  0, 1, 1, 2)
        self.label_to_table("Serch text:", table,  0, 1, 2, 3)

        box = gtk.VBox()
        label = gtk.Label("Result:")
        box.pack_start(label, True, True)
        but = gtk.Button("changed")
        but.connect("clicked", self.cb_changed)
        box.pack_start(but, True, False)
        self.add_to_label(box, table, 0, 1, 3, 12)
        
        self.name = gtk.Entry()
        self.name.set_text("None")
        self.add_to_label(self.name, table, 1, 2, 0, 1)
        
        self.searchColumn = gtk.combo_box_new_text()
        self.fill_comoBox(self.searchColumn, ["Title", "ID", "Decription"] )
        self.add_to_label(self.searchColumn, table, 1, 2, 1, 2)
        
        self.text = gtk.Entry()
        self.add_to_label(self.text, table, 1, 2, 2, 3)

        self.res_pass = gtk.CheckButton("PASS")
        self.res_pass.set_active(True)
        self.add_to_label(self.res_pass, table, 1, 2, 3, 4)
        
        self.res_error = gtk.CheckButton("ERROR")
        self.res_error.set_active(True)
        self.add_to_label(self.res_error, table, 1, 2, 4, 5)
        
        self.res_fail = gtk.CheckButton("FAIL")
        self.res_fail.set_active(True)
        self.add_to_label(self.res_fail, table, 1, 2, 5, 6)
        
        self.res_unknown = gtk.CheckButton("UNKNOWN")
        self.res_unknown.set_active(True)
        self.add_to_label(self.res_unknown, table, 1, 2, 6, 7)

        self.res_not_app = gtk.CheckButton("NOT APPLICABLE")
        self.res_not_app.set_active(True)
        self.add_to_label(self.res_not_app, table, 1, 2, 7, 8)
        
        self.res_not_check = gtk.CheckButton("NOT CHECKED")
        self.res_not_check.set_active(True)
        self.add_to_label(self.res_not_check, table, 1, 2, 8, 9)
        
        self.res_not_select = gtk.CheckButton("NOT SELECTED")
        self.res_not_select.set_active(True)
        self.add_to_label(self.res_not_select, table, 1, 2, 9, 10)
        
        self.res_info = gtk.CheckButton("INFORMATIONAL")
        self.res_info.set_active(True)
        self.add_to_label(self.res_info, table, 1, 2, 10, 11)
        
        self.res_fix = gtk.CheckButton("FIXED")
        self.res_fix.set_active(True)
        self.add_to_label(self.res_fix, table, 1, 2, 11, 12)
        
        
        box_main.pack_start(table,True,True)
        #buttons
        box_btn = gtk.HButtonBox()
        box_btn.set_layout(gtk.BUTTONBOX_END)
        btn_filter = gtk.Button("Add filter")
        btn_filter.connect("clicked", self.cb_setFilter)
        box_btn.pack_start(btn_filter)
        btn_filter = gtk.Button("Cancel")
        btn_filter.connect("clicked", self.cb_cancel)
        box_btn.pack_start(btn_filter)
        box_main.pack_start(box_btn, True, True, 20)
        
        self.window.add(alig)
        self.window.show_all()
        return self.window

    def cb_changed(self, widget):
        
        self.res_pass.set_active(not self.res_pass.get_active())
        self.res_error.set_active(not self.res_error.get_active())
        self.res_fail.set_active(not self.res_fail.get_active())
        self.res_unknown.set_active(not self.res_unknown.get_active())
        self.res_not_app.set_active(not self.res_not_app.get_active())
        self.res_not_check.set_active(not self.res_not_check.get_active())
        self.res_not_select.set_active(not self.res_not_select.get_active())
        self.res_info.set_active(not self.res_info.get_active())
        self.res_fix.set_active(not self.res_fix.get_active())
        
    def cb_setFilter(self, widget):
        
        filter = {"name":          self.name.get_text(),
                  "description":   "",
                  "func":           self.filter_func,        # func for metch row in model func(model, iter)
                  "param":           {},                    # param tu function
                  "result_tree":    False   # if result shoul be in tree or list
                  }
        
        res = []
        if not self.res_pass.get_active():
            res.append("PASS")
        if not self.res_error.get_active():
            res.append("ERROR")
        if not self.res_fail.get_active():
            res.append("FAIL")
        if not self.res_unknown.get_active():
            res.append("UNKNOWN")
        if not self.res_not_app.get_active():
            res.append("NOT APPLICABLE")
        if not self.res_not_check.get_active():
            res.append("NOT CHECKED")
        if not self.res_not_select.get_active():
            res.append("NOT SELECTED")
        if not self.res_info.get_active():
            res.append("INFORMATIONAL")
        if not self.res_fix.get_active():
            res.append("FIXED")

        params = {"searchData": self.searchColumn.get_active(),
                  "text":       self.text.get_text(),
                  "res":        res}

        filter["param"] = params
        self.add_filter(filter)
        self.window.destroy()



    def filter_func(self, model, iter, params):

        #search data
        TITLE = 0
        ID = 1
        DESC = 3

        #data in model
        COLUMN_ID = 0               # id of rule
        COLUMN_RESULT = 1           # Result of scan
        COLUMN_FIX = 2              # fix
        COLUMN_TITLE = 3            # Description of rule
        COLUMN_DESC = 4             # Description of rule
        COLUMN_COLOR_TEXT_TITLE = 5 # Color of text description
        COLUMN_COLOR_BACKG = 6      # Color of cell
        COLUMN_COLOR_TEXT_ID = 7    # Color of text ID
        
        column = [COLUMN_TITLE, COLUMN_ID, COLUMN_DESC]
        
        vys = True
        # search text if is set
        if params["text"] <> "":
            pattern = re.compile(params["text"],re.IGNORECASE)
            if pattern.search(model.get_value(iter, column[params["searchData"]])) != None:
                vys = vys and True 
            else:
                vys = vys and False
            if not vys:
                return vys
        
        #type of result
        if len(params["res"]) > 0:
            if model.get_value(iter, COLUMN_RESULT) in params["res"]:
                vys = vys and False
        return vys
  
    def cb_cancel(self, widget):
        self.window.destroy()
        
    def delete_event(self, widget, event):
        self.window.destroy()


class Loader:

    def __init__(self, core):

        self.core = core

    def import_filters(self):

        dpath = self.core.filter_directory

        if os.path.isdir(dpath):
            sys.path.append(dpath)
        else:
            logger.error("%s is not a directory. Can't import filter modules !" % (dpath,))
            return []

        list = []

        for f in os.listdir(os.path.abspath(dpath)):
            name, ext = os.path.splitext(f)
            if ext == '.py':
                 logger.info("Imported filter module: %s" % (name,))
                 module = __import__(name)
                 for obj in dir(module):
                     try:
                         if issubclass(module.__getattribute__(obj), Filter):
                             list.append(module.__getattribute__(obj))
                     except TypeError:
                         pass

        return list
