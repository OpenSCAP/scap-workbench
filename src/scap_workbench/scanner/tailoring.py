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

""" Importing standard python libraries
"""
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Pango
from gi.repository import WebKit
import re               # Regular expressions 
import sre_constants    # For re.compile exception
import logging          # Logger for debug/info/error messages

""" Importing SCAP Workbench modules
"""
from scap_workbench import core
from scap_workbench.core import abstract
from scap_workbench.core import commands
from scap_workbench.core import filter
import scap_workbench.core.enum as ENUM
from scap_workbench.core.events import EventObject

from scap_workbench.core.threads import thread_free as threadFree

# Initializing Logger
logger = logging.getLogger("scap-workbench")

class ItemList(abstract.List):
    
    def __init__(self, builder, core, progress=None):
        self.builder = builder
        self.__progress = progress
        self.profiles = builder.get_object("tailoring:profile")
        self.data_model = commands.DHItemsTree("gui:tailoring:DHItemsTree", core, progress, self.profiles)
        super(ItemList, self).__init__("gui:tailoring:item_list", core, builder.get_object("tailoring:tw_items"))
        
        self.__has_model_changed = False
        self.filter_box = self.builder.get_object("tailoring:filter:box")
        self.filter_toggle = self.builder.get_object("tailoring:filter:toggle")
        self.filter_toggle.connect("toggled", self.__cb_filter_toggle)
        self.search = self.builder.get_object("tailoring:filter:search")
        self.search.connect("key-press-event", self.__cb_search, self.get_TreeView())
        
        selection = self.get_TreeView().get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)

        # actions
        self.add_receiver("gui:btn:menu:tailoring", "update", self.__update)
        
        builder.get_object("tailoring:items:toggled:cellrenderer").connect("toggled", self.data_model.cb_toggled)
        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.__cb_filter_toggle()
        
        # if True an idle worker that will perform the update (after selection changes) is already pending
        self.item_changed_worker_pending = False

    def __filter(self, model, path, iter, usr):
        
        pattern, columns = usr

        selection = self.get_TreeView().get_selection()
        if not iter: return False

        for col in columns:
            found = re.search(pattern or "", model[iter][col] or "")
            if found != None:
                self.get_TreeView().expand_to_path(path)
                selection.select_path(path)
                self.get_TreeView().scroll_to_cell(path)
                return True

        return False

    def __cb_search(self, widget, event, treeview):
        try:
            text = self.search.get_text() or ""
            pattern = re.compile(text, re.I)
        except sre_constants.error, err:
            self.core.notify("Regexp entry error: %s" % (err,), core.Notification.ERROR, msg_id="notify:profiles:filter")
            return True

        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval == Gdk.KEY_Return:
            """ User pressed the Enter button to search more
            """
            retval = self.recursive_search(pattern, [1,2])
            if retval: return True

        treeview.get_model().foreach(self.__filter, (pattern, [1,2]))

    def __cb_filter_toggle(self, widget=None):

        self.filter_box.set_property('visible', self.filter_toggle.get_active())
        self.filter_box.set_property('sensitive', self.filter_toggle.get_active())
        if self.filter_toggle.get_active():
            self.search.grab_focus()

    def __update(self):

        if not self.core.lib.loaded: self.data_model.model.clear()
        if "profile" not in self.__dict__ or self.profile != self.core.selected_profile or self.core.force_reload_items:
            self.profile = self.core.selected_profile
            self.profiles.set_sensitive(False)
            self.treeView.set_sensitive(False)
            self.data_model.fill()
            self.core.force_reload_items = False

        if self.core.selected_item and self.selected != self.core.selected_item:
            # Select the last one selected if there is one
            details = self.data_model.get_item_details(self.core.selected_item)
            if details and details["typetext"] != "Value":
                self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))
                self.selected = self.core.selected_item

    def __search(self):
        self.search(self.filter.get_search_text(),1)
        
    def __filter_add(self):
        self.data_model.map_filter = self.filter_add(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))

    def __filter_del(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))

    def __filter_refresh(self):
        #self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))

    def __cb_item_changed(self, widget, treeView):
        """Callback called whenever item selection changes. Performs updates of the property box.
        """

        def worker():
            selection = treeView.get_selection( )
            if selection != None: 
                (model, iter) = selection.get_selected( )
                if iter: 
                    self.core.selected_item = model.get_value(iter, commands.DHItemsTree.COLUMN_ID)
                    self.emit("update")
                    
            self.item_changed_worker_pending = False
        
        # The reason for the item_changed_worker_pending attribute is to avoid stacking up
        # many update requests that would all query the selection state again and do repeated
        # work. This way the update happens only once even though the selection changes many times.
        # TODO: This is more or less copied from edit.py, should be refactored for DRY
        if not self.item_changed_worker_pending:
            # we handle this in the idle function when no higher priority events are to be handled
            GLib.idle_add(worker)
            self.item_changed_worker_pending = True
        
class ValuesList(abstract.List):
    
    def __init__(self, widget, core, builder):
        self.builder = builder
        self.data_model = commands.DHValues(core)
        super(ValuesList, self).__init__("gui:tailoring:values_list", core, widget)
        
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)

        # actions
        self.add_receiver("gui:tailoring:item_list", "update", self.__update)
        self.builder.get_object("tailoring:tw_values:cell_values").connect("edited", self.__edited)

    def __update(self):
        self.data_model.fill()

    def __edited(self, cell, path, new_text):
        self.data_model.cellcombo_edited(cell, path, new_text)
        self.emit("update")


class ItemDetails(EventObject):

    def __init__(self, builder, core):
        super(ItemDetails, self).__init__(core)
        
        #create view
        self.builder = builder
        self.data_model = commands.DataHandler(self.core)

        self.add_receiver("gui:tailoring:item_list", "update", self.__update)
        self.add_receiver("gui:tailoring:item_list", "changed", self.__update)
        self.add_receiver("gui:tailoring:values_list", "update", self.__update)
        
        self.draw()

    def __update(self):
        details = self.data_model.get_item_details(self.core.selected_item)
        self.id.set_text(details["id"])
        self.type.set_text(details["typetext"])
        self.weight.set_text(str(details["weight"]))
        if "idents" in details: 
            self.idents.set_text(str("\n".join([ident[0] for ident in details["idents"]])))

        # clear
        self.description.load_html_string("", "file:///")
        self.fixes.load_html_string("", "file:///")
        self.title.set_text("")
        for child in self.refBox.get_children():
            child.destroy()
        fixes = []

        if self.core.selected_lang in details["titles"]: 
            self.title.set_text(details["titles"][self.core.selected_lang])
        else: 
            for lang in details["titles"]:
                self.title.set_text(details["titles"][lang])
                break

        description = ""
        if self.core.selected_lang in details["descriptions"]: 
            description = details["descriptions"][self.core.selected_lang].replace("xhtml:","")
            description = description.replace("xmlns:", "")
        else: 
            for lang in details["descriptions"]:
                description = details["descriptions"][lang].replace("xhtml:","")
                break
        description = self.data_model.substitute(description, with_policy=True)
        if description == "": description = "No description"
        description = "<body>"+description+"</body>"
        try:
            self.description.load_html_string(description, "file:///")
        except Exception as err:
            logger.exception("Exception: %s" % (err))
        
        for i, ref in enumerate(details["references"]):
            hbox = Gtk.HBox()
            counter = Gtk.Label(label="%d) " % (i+1,))
            counter.set_alignment(0,0)
            hbox.pack_start(counter, False, False, 0)
            text = "<a href='%s'>%s</a>" % (ref["identifier"], " ".join((ref["title"] or "").split()))
            label = Gtk.Label(label=text)
            hbox.pack_start(label, True, True, 0)
            label.set_tooltip_text(ref["title"])
            label.set_use_markup(True)
            
            try:
                label.set_track_visited_links(True)
            except AttributeError:
                pass
            
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD) 
            label.set_alignment(0,0)
            label.connect("size-allocate", core.label_size_allocate)
            hbox.show_all()
            self.refBox.pack_start(hbox, True, True, 0)

        if "fixtexts" in details: fixes.extend(details["fixtexts"])
        if "fixes" in details: fixes.extend(details["fixes"])
        text = None
        for i, fixtext in enumerate(fixes):
            if text == None: text = ""
            hbox = Gtk.HBox()
            text += "    "+self.data_model.substitute(fixtext["text"]).replace("xhtml:", "").replace("xmlns:", "")+"<br>"
        if text == None: text = "No fixes specified"
        text = "<body>"+text+"</body>"
        try:
            self.fixes.load_html_string(text, "file:///")
        except Exception as err:
            logger.exception("HTML display Exception: %s: (%s)", err, text)

    def draw(self):
        self.box_details = self.builder.get_object("tailoring:details:box")

        # TODO: Move to Glade

        #info (id, title, type)
        expander = Gtk.Expander(label = "<b>Info</b>")
        expander.set_expanded(True)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = Gtk.Alignment(xalign = 0.5, yalign = 0.5, xscale = 1, yscale = 1)
        alig.set_padding(0, 10, 12, 4)
        expander.add(alig)
        vbox = Gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(Gtk.HSeparator(), False, True, 1)
        self.box_details.pack_start(expander, False, True, 1)

        #id
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(label = "ID: "), False, True, 1)
        self.id = Gtk.Label(label="")
        self.id.set_alignment(0,0)
        hbox.pack_start(self.id, True, True, 1)
        vbox.pack_start(hbox, False, False, 1)

        #title
        hbox = Gtk.HBox()
        label = Gtk.Label(label = "Title: ")
        label.set_alignment(0,0)
        hbox.pack_start(label, False, True, 1)
        self.title = Gtk.Label(label="")
        self.title.set_line_wrap(True)
        self.title.set_line_wrap_mode(Pango.WrapMode.WORD)
        core.label_set_autowrap(self.title)
        self.title.set_alignment(0,0)
        hbox.pack_start(self.title, True, True, 1)
        vbox.pack_start(hbox, False, False, 1)

        #type
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(label = "Type: "), False, True, 1)
        self.type = Gtk.Label(label="")
        self.type.set_alignment(0,0)
        hbox.pack_start(self.type, True, True, 1)
        vbox.pack_start(hbox, False, False, 1)
        
        #weight
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(label = "Weight: "), False, True, 1)
        self.weight = Gtk.Label(label="")
        self.weight.set_alignment(0,0)
        hbox.pack_start(self.weight, True, True, 1)
        vbox.pack_start(hbox, False, False, 1)

        #CCE
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(label = "Idents: "), False, False, 1)
        self.idents = Gtk.Label(label="")
        self.idents.set_alignment(0,0)
        hbox.pack_start(self.idents, True, True, 1)
        vbox.pack_start(hbox, False, False, 1)
        
        #References
        expander = Gtk.Expander(label = "<b>References</b>")
        expander.set_expanded(False)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        expander.add(alig)
        vbox = Gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(Gtk.HSeparator(), False, True, 3)
        self.refBox = Gtk.VBox()
        vbox.pack_start(self.refBox, False, False, 0)
        self.box_details.pack_start(expander, False, False, 1)
        
        # Get the background color from window and destroy it
        window = Gtk.Window()
        nb = Gtk.Notebook()
        window.add(nb)
        window.realize()
        nb.realize()
        bg_color = nb.get_style().bg[Gtk.StateType.NORMAL]
        window.destroy()

        #fixes
        expander = Gtk.Expander(label = "<b>Fixes</b>")
        expander.set_expanded(False)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = Gtk.Alignment.new(0, 0, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        vbox = Gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(Gtk.HSeparator(), False, False, 3)
        self.fixes = WebKit.WebView()
        self.fixes.set_zoom_level(0.75)
        sw = Gtk.ScrolledWindow()
        sw.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        sw.set_property("vscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        sw.set_property("border-width", 0)
        sw.add(self.fixes)
        sw.show()
        expander.add(alig)
        vbox.pack_start(sw, False, False, 1)
        self.box_details.pack_start(expander, False, False, 1)

        #description
        expander = Gtk.Expander(label = "<b>Description</b>")
        expander.set_expanded(True)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = Gtk.Alignment.new(0, 0, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        vbox = Gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(Gtk.HSeparator(), False, False, 3)
        self.description = WebKit.WebView()
        self.description.set_zoom_level(0.75)
        sw = Gtk.ScrolledWindow()
        sw.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        sw.set_property("vscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
        sw.set_property("border-width", 0)
        sw.add(self.description)
        sw.show()
        expander.add(alig)
        vbox.pack_start(sw, True, True, 1)
        self.box_details.pack_start(expander, True, True, 1)
        self.box_details.show_all()

class RefineDetails(EventObject):
    
    def __init__(self, builder, core):
        super(RefineDetails, self).__init__(core)

        #create view
        self.builder = builder

        self.data_model = commands.DHProfiles(self.core)
        self.func = abstract.Func(core)
        self.add_receiver("gui:tailoring:item_list", "update", self.__update)
        self.add_receiver("gui:tailoring:item_list", "changed", self.__update)

        self.role = self.builder.get_object("tailoring:refines:role")
        self.role.set_model(ENUM.ROLE.get_model())
        self.role.connect('changed', self.__cb_edit)
        
        self.severity = self.builder.get_object("tailoring:refines:severity")
        self.severity.set_model(ENUM.LEVEL.get_model())
        self.severity.connect('changed', self.__cb_edit)
        
        self.weight = self.builder.get_object("tailoring:refines:weight")
        self.weight.connect("focus-out-event", self.__cb_edit)

    def __update(self):

        details = self.data_model.get_item_details(self.core.selected_item)
        if details is None:
            # in case the item details can't be acquired we still want the comboboxes
            # to be blank and insensitive
            details = {"typetext" : "unknown"}

        self.role.handler_block_by_func(self.__cb_edit)
        self.severity.handler_block_by_func(self.__cb_edit)
        self.weight.handler_block_by_func(self.__cb_edit)

        # role, severity and weight only apply to "Rule"
        if details["typetext"] == "Rule":
            self.role.set_sensitive(True)
            self.severity.set_sensitive(True)
            self.weight.set_sensitive(True)

            if "role" in details and details["role"] != 0:
                self.role.set_active(ENUM.ROLE.pos(details["role"]))
            else:
                self.role.set_active(0)

            if "severity" in details:
                self.severity.set_active(ENUM.LEVEL.pos(details["severity"]))
            else:
                self.severity.set_active(0)
            
            if "weight" in details:
                self.weight.set_text(str(details["weight"]))
            else:
                self.weight.set_text("")
        
        else:
            self.role.set_sensitive(False)
            self.severity.set_sensitive(False)
            self.weight.set_sensitive(False)
            
            # -1 means no combobox item is active, the combobox will appear blank
            self.role.set_active(-1)
            self.severity.set_active(-1)
            self.weight.set_text("")

        self.role.handler_unblock_by_func(self.__cb_edit)
        self.severity.handler_unblock_by_func(self.__cb_edit)
        self.weight.handler_unblock_by_func(self.__cb_edit)
            
    def add_widget(self, body, text, expand, widget):
                
        frame = Gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)        
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        
        if expand:
            body.pack_start(frame, True, True, 0)
        else:
            body.pack_start(frame, False, True, 0)
            
        alig = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        alig.add(widget)
        return widget
        
    def __cb_edit(self, widget, event=None):
        severity = role = None
        if self.severity.get_active() != -1: severity = ENUM.LEVEL[self.severity.get_active()][0]
        if self.role.get_active() != -1: role = ENUM.ROLE[self.role.get_active()][0]
        self.data_model.change_refines( severity=severity, role=role, weight=self.__cb_get_weight())
    
    def __cb_get_weight(self):
        weight = self.func.controlFloat(self.weight.get_text(), "Weight", self.core.main_window)
        if weight:
            return weight
        else: 
            details = self.data_model.get_item_details(self.core.selected_item)
            if details == None: return

            if "weight" in details:
                return str(details["weight"])
            else: return None
        
class MenuButtonTailoring(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        super(MenuButtonTailoring, self).__init__("gui:btn:menu:tailoring", widget, core)
        
        self.builder = builder

        # Profiles combo box
        self.profiles = self.builder.get_object("tailoring:profile")
        self.data_model = commands.DHProfiles(core)
        self.data_model.model = self.profiles.get_model()
        self.__profiles_update()
        self.profiles.connect("changed", self.__cb_profile_changed, self.profiles.get_model())

        self.add_receiver("gui:btn:main:xccdf", "load", self.__profiles_update)

        #draw body
        self.body = self.builder.get_object("tailoring:box")
        ItemDetails(self.builder, self.core)
        RefineDetails(self.builder, self.core)
        self.progress = self.builder.get_object("tailoring:progress")
        self.progress.hide()
        self.rules_list = ItemList(builder, self.core, self.progress)
        self.values = ValuesList(self.builder.get_object("tailoring:tw_values"), self.core, self.builder)

        # set signals
        self.add_sender(self.id, "update")

    def activate(self, active):
        abstract.MenuButton.activate(self, active)
        if active:
            # Let's change selected profile
            self.profiles.handler_block_by_func(self.__cb_profile_changed)
            for row in self.profiles.get_model():
                if row[0] == self.core.selected_profile:
                    self.profiles.set_active_iter(row.iter)
            self.profiles.handler_unblock_by_func(self.__cb_profile_changed)

    def __profiles_update(self):
        """ Fill profiles into the combobox above the tailoring
        item tree """

        if not self.data_model.check_library(): return None
        model = self.profiles.get_model()
        model.clear()

        """ Append the first "No Profile" item. This use to be the
        representation of the benchmark not altered by profiles """
        model.append(["", "(No profile)"])
        
        """ For each profile in the benchmark append the title of 
        current language or the title with ID of profile """
        for item in self.core.lib.benchmark.profiles:
            title = self.data_model.get_title(item.title) or "%s (ID)" % (item.id,)
            iter = model.append([item.id, ""+title])

        """ Set the current selected profile TODO: This would
        always be the 0-profile """
        if not self.core.selected_profile:
            self.profiles.set_active(0)
        else:
            for i, profile in enumerate(model):
                if self.core.selected_profile == profile[0]:
                    self.profiles.set_active(i)

    def __cb_profile_changed(self, widget, model):
        """ If user change the selected profile
        """
        if self.profiles.get_active() != -1:
            self.core.selected_profile = model[self.profiles.get_active()][0]
            self.emit("update")
