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
#      Maros Barabas        <xbarry@gmail.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

"""Provides means to filter through XCCDF scan results
"""

from gi.repository import Gtk
from gi.repository import Gdk

import re
import sys
import os

from scap_workbench import paths
from scap_workbench import core
from scap_workbench.core import abstract
from scap_workbench.core.events import EventObject
from scap_workbench.core.logger import LOGGER

class Filter(object):
    """Abstract class for defining filters"""

    def __init__(self, name="", description="", params = dict(), istree=True, renderer=None, func=None):
        self.name = name
        self.description = description
        self.func = func
        self.params = params
        self.istree = istree
        self.renderer = renderer
        self.model = None
        self.active = False
        self.fg_color = "#000000"
        self.bg_color = "#FFFFFF"
        
        self.box = None
        self.button = None
        self.eb = None

    def render(self):
        self.box = Gtk.HBox()
        label = Gtk.Label(label=self.name)
        label.set_justify(Gtk.Justification.LEFT)
        label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse(self.fg_color))

        alig = Gtk.Alignment.new(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(label)
        self.box.pack_start(alig, True, True, 0)

        self.button = Gtk.Button("x")
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        self.button.set_tooltip_text("Remove this filter")
        self.button.connect("clicked", self.__cb_button)
        alig = Gtk.Alignment.new(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(0, 0, 10, 0)
        alig.add(self.button)
        eb = Gtk.EventBox()
        eb.add(alig)
        eb.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse(self.bg_color))
        self.box.pack_end(eb, False, False, 0)

        self.eb = Gtk.EventBox()
        self.eb.add(self.box)
        self.eb.set_border_width(2)
        self.eb.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse(self.bg_color))
        self.eb.set_tooltip_text(self.description)
        self.eb.show_all()

    def __cb_button(self, widget):
        if self.renderer: self.renderer.del_filter(self)
        self.active = False

    def get_widget(self):
        return self.eb

class Search(object):
    """Deprecated search helper class. Creates it's own widget hierarchy.
    """
    
    def __init__(self, renderer):
        LOGGER.warning("Class Search is deprecated: Use search function of list instead")
        self.renderer = renderer
        self.renderer.add_sender(id, "search")
        self.__render()

    def __render(self):
        self.box = Gtk.HBox()

        self.entry = Gtk.Entry()
        self.entry.connect("key-press-event", self.__cb_entry_btn)
        alig = Gtk.Alignment.new(0.0, 0.0, 1.0, 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(self.entry)
        self.box.pack_start(alig, True, True, 0)

        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        self.button.set_label("Search")
        self.button.connect("clicked", self.__cb_search)
        alig = Gtk.Alignment(xalign = 0.0, yalign = 0.0, xscale = 1.0, yscale = 1.0)
        alig.set_padding(5, 5, 10, 5)
        alig.add(self.button)
        self.box.pack_start(alig, True, True, 0)

        self.box.show_all()

    def __cb_entry_btn(self, widget, event):
        if Gdk.keyval_name(event.keyval) == "Return":
            self.__cb_search()

    def __cb_search(self, widget=None):
        self.renderer.emit("search")

    def get_widget(self):
        return self.box

class Renderer(abstract.MenuButton,EventObject):
    # FIXME: This is not a MenuButton! MenuButton is just used as a mixin to get add_frame method
    #        into this class.

    def __init__(self,id, core, box):
        EventObject.__init__(self, core)

        self.filters = []
        self.id = id
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
        self.expander.focus_widget = self.search.entry
        self.expander.get_widget().pack_start(self.search.get_widget(), False, True, 0)

        #filter
        alig_filters = self.add_frame(filter_box, "Active filters")
        self.menu = Gtk.Menu()

        #btn choose filter
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_label("Add filter")
        button.connect_object("event", self.__cb_show_menu, self.menu)
        filter_box.pack_end(button, False, True, 0)
        box.show_all()

    def __cb_menu(self, widget, filter):
        
        # if filter is activated yet
        if filter.active == False:
            self.add_filter(filter)
        else:
            self.core.notify("Filter is already active.", core.Notification.INFORMATION)
        
    def __cb_show_menu(self, menu, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            # FIXME:
            # In my opinion and according to gtk3 docs the 5th parameter (excluding self) should be guint
            # of the mouse button that triggered the popup, however event.button is EventButton and the
            # bindings won't accept that
            menu.popup(None, None, None, None, 0, event.time)
            return True
        
        return False

    def get_search_text(self):
        return self.search.entry.get_text()

    def add_filter_to_menu(self, filter):
        """ Function add filter tu popup menu
        """
        assert filter != None, "Can't add None filter"
        menu_item = Gtk.MenuItem(filter.name)
        menu_item.set_tooltip_text(filter.description or "")
            
        menu_item.show()
        self.menu.append(menu_item)
        menu_item.connect("activate", self.__cb_menu, filter)
    
    def add_filter(self, filter):
        """ Add filter to list active filter and emit signal filter was added"""
        filter.active = True
        filter.render()
        self.expander.get_widget().pack_start(filter.get_widget(), True, True, 0)
        self.filters.append(filter)
        self.emit("filter_add")

    def del_filter(self, filter):
        """ remove filter from active filters and emit signal deleted"""
        if filter in self.filters: 
            self.filters.remove(filter)
            filter.get_widget().destroy()
            self.emit("filter_del")
        else: self.core.notify("Removing not existed filter !", core.Notification.ERROR)
        
    def init_filter(self):
        """ clean all acive filters"""
        return
        for filter in self.filters:
            filter.active = False
            filter.eb.destroy()
        self.filters = []
 

    def set_active(self, active):
        self.expander.get_widget().set_sensitive(active)
        self.expander.get_btn_widget().set_sensitive(active)
        self.expander.cb_changed(active=True)

class ExpandBox(abstract.EventObject):
    """
    Create expand box. Set only to conteiner.
    """
    
    def __init__(self, box, text, core=None):
        """
        @param box Container for this expandBox.
        @param text Button name for show or hide expandBox
        @param core SWBCore singleton
        """
        
        super(ExpandBox, self).__init__(core)
        
        self.focus_widget = None
        
        # body for expandBox
        rollBox = Gtk.HBox()
        box.pack_start(rollBox, True, True, 0)

        alig = Gtk.Alignment()
        alig.set_padding(5, 5, 5, 5) # top, bottom, left, right
        self.frameContent = Gtk.VBox()
        alig.add(self.frameContent)
        rollBox.pack_start(alig, True, True, 0)
        
        # create icons
        self.arrowTop = Gtk.Image()
        self.arrowBottom = Gtk.Image()
        self.pixbufShow = self.arrowTop.render_icon(Gtk.STOCK_GO_FORWARD, size=Gtk.IconSize.MENU, detail=None)
        self.pixbufHide = self.arrowBottom.render_icon(Gtk.STOCK_GO_BACK, size=Gtk.IconSize.MENU, detail=None)
        self.arrowTop.set_from_pixbuf(self.pixbufShow)
        self.arrowBottom.set_from_pixbuf(self.pixbufShow)
        
        # create label
        self.label = Gtk.Label(label=text)
        self.label.set_angle(90)

        #create button
        hbox = Gtk.VBox()
        hbox.pack_start(self.arrowTop, False, True, 0)
        hbox.pack_start(self.label, True, True, 0)
        hbox.pack_start(self.arrowBottom, False, True, 0)
        self.btn = Gtk.Button()
        self.btn.add(hbox)
        rollBox.pack_start(self.btn, False, True, 0)
        self.btn.connect("clicked", self.cb_changed)
        self.frameContent.show_all()

    def cb_changed(self, widget=None, active=None):
        LOGGER.debug("Expander switched to %s", not self.frameContent.get_property("visible"))
        if active == True or self.frameContent.get_property("visible"):
            self.frameContent.hide()
            self.arrowTop.set_from_pixbuf(self.pixbufShow)
            self.arrowBottom.set_from_pixbuf(self.pixbufShow)
        else:
            self.frameContent.show()
            self.arrowTop.set_from_pixbuf(self.pixbufHide)
            self.arrowBottom.set_from_pixbuf(self.pixbufHide)
            try:
                if self.focus_widget: self.focus_widget.grab_focus()
            except Exception as e:
                LOGGER.exception("Couldn't grab focus: %s" %(e))

    def get_widget(self):
        return self.frameContent

    def get_btn_widget(self):
        return self.btn

class ItemFilter(Renderer):
    """User filter used in scap-workbench-editor to filter through tailorings
    """
    
    def __init__(self, core, builder, widget, signal):
        self.builder = builder
        self.box_filter = self.builder.get_object(widget)
        super(ItemFilter, self).__init__(signal, core, self.box_filter)

        self.id_filter = 0
        self.user_filter_builder = Gtk.Builder()
        self.user_filter_builder.add_from_file(os.path.join(paths.glade_prefix, "filter_tailoring.glade"))
        self.user_filter_window = self.user_filter_builder.get_object("user_filter:dialog")
        self.user_filter_window.connect("delete-event", self.__cb_cancel)
        
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
        filters = self.importer.import_filters()
        for filter in filters:
            if filter.TYPE == self.id: self.add_filter_to_menu(filter(self))

        menu_item = Gtk.MenuItem("User filter ...")
        menu_item.set_tooltip_text("Specify new filter by list parameters")
        menu_item.show()
        self.menu.append(menu_item)
        menu_item.connect("activate", self.__user_filter_new)

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

class AdvancedFilterModel(Gtk.TreeStore):
    """Work in progress model class that will one day be able to hide parents in a tree without
    hiding their children at the same time.
    
    The main use for this is filtering through items (in the scanner).
    
    Currently unused code!
    """

    def __init__(self, *args):
        if not args:
            raise ValueError("AdvancedFilterModel constructor requires at least one argument")

        super(AdvancedFilterModel, self).__init__()
        self.__args = args
        self.__reference = self.TreeStore(args)

    def set_ref_model(self, model):
        """Set the reference model for the TreeView
        """
        if not model:
            raise ValueError("AdvancedFilterModel::set_ref_model requires TreeModel as argument")
        if model != Gtk.TreeModel:
            raise ValueError("AdvancedFilterModel::set_ref_model takes TreeModel as argument %s found" % (model.__class__))
        self.__reference = model

        # Let's build the filter model by creating nodes in the model that
        # refer to the reference mode
        # TODO

class ScanFilter(Renderer):
    """User filter used in scap-workbench (scanner) to filter through scan results
    """

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
        self.builder = builder
        self.box_filter = self. builder.get_object("scan:box_filter")
        super(ScanFilter, self).__init__("gui:btn:menu:scan:filter", core, self.box_filter)

        self.id_filter = 0
        self.user_filter_builder = Gtk.Builder()
        self.user_filter_builder.add_from_file(os.path.join(paths.glade_prefix, "filter_scan.glade"))
        self.user_filter_window = self.user_filter_builder.get_object("user_filter:dialog")
        self.user_filter_window.connect("delete-event", self.__cb_cancel)

        self.user_filter_id = self.user_filter_builder.get_object("entry_id")
        self.user_filter_description = self.user_filter_builder.get_object("entry_description")
        self.user_filter_column = self.user_filter_builder.get_object("search:cb_column")
        self.user_filter_text = self.user_filter_builder.get_object("search:entry_text")
        self.info_box = self.user_filter_builder.get_object("info_box")

        self.user_filter_results = [("PASS", self.user_filter_builder.get_object("ch_pass")),
                ("ERROR", self.user_filter_builder.get_object("ch_error")),
                ("FAIL", self.user_filter_builder.get_object("ch_fail")),
                ("UNKNOWN", self.user_filter_builder.get_object("ch_unknown")),
                ("NOT APPLICABLE", self.user_filter_builder.get_object("ch_not_applicable")),
                ("NOT CHECKED", self.user_filter_builder.get_object("ch_not_checked")),
                ("NOT SELECTED", self.user_filter_builder.get_object("ch_not_selected")),
                ("INFORMATIONAL", self.user_filter_builder.get_object("ch_informational")),
                ("FIXED", self.user_filter_builder.get_object("ch_fixed"))]

        self.user_filter_builder.get_object("btn_ok").connect("clicked", self.__cb_add)
        self.user_filter_builder.get_object("btn_cancel").connect("clicked", self.__cb_cancel)

        # import filters
        self.importer = Loader(self.core)
        filters = self.importer.import_filters()
        for filter in filters:
            if filter.TYPE == self.id: self.add_filter_to_menu(filter(self))

        menu_item = Gtk.MenuItem("User filter ...")
        menu_item.show()
        self.menu.append(menu_item)
        menu_item.connect("activate", self.__user_filter_new)

    #filter
    def __cb_add(self, widget):
        
        res = []
        for item in self.user_filter_results:
            if item[1].get_active(): res.append(item[0])

        params = {"searchData": self.user_filter_column.get_active(),
                  "text":       self.user_filter_text.get_text(),
                  "results":    res}

        filter = Filter(self.user_filter_id.get_text(), self.user_filter_description.get_text(), params, renderer=self)
        filter.func = self.__filter_func
        self.add_filter(filter)
        self.user_filter_window.hide()

    def __cb_cancel(self, widget, event=None):
        self.user_filter_window.hide()

    def __user_filter_new(self, widget):
        self.user_filter_window.set_transient_for(self.core.main_window)
        self.user_filter_window.show_all()

    def __filter_func(self, model, iter, params):

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
        
        # search text if is set
        if params["text"] != "":
            pattern = re.compile(params["text"], re.IGNORECASE)
            if pattern.search(model.get_value(iter, column[params["searchData"]])) == None:
                return False
        
        #type of result
        if len(params["results"]) > 0:
            if model.get_value(iter, COLUMN_RESULT) not in params["results"]:
                return False

        return True
  

class Loader(object):
    """Filter loader that loads all .py files in the filter directory
    """

    def __init__(self, core):

        self.core = core

    def import_filters(self):

        dpath = self.core.filter_directory

        if os.path.isdir(dpath):
            sys.path.append(dpath)
        else:
            LOGGER.error("%s is not a directory. Can't import filter modules !" % (dpath,))
            return []

        list = []

        for f in os.listdir(os.path.abspath(dpath)):
            name, ext = os.path.splitext(f)
            if ext == '.py':
                LOGGER.debug("Importing filter module: %s" % (name,))
                module = __import__(name)
                for obj in dir(module):
                    try:
                        if issubclass(module.__getattribute__(obj), Filter):
                            list.append(module.__getattribute__(obj))
                    except TypeError:
                        pass

        return list
