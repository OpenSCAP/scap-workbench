# -*- coding: utf-8 -*-
#
# Copyright 2011 Red Hat Inc., Durham, North Carolina.
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
#      Martin Preisler      <mpreisle@redhat.com>

from gi.repository import Gtk
from gi.repository import Gdk

from scap_workbench import core
from scap_workbench.core import paths
from scap_workbench.core import abstract
from scap_workbench.core.events import EventObject
from scap_workbench.editor.edit import *

import os.path
import re
import sre_constants
import logging

# Initializing Logger
logger = logging.getLogger("scap-workbench")

class AddProfileDialog(EventObject):

    def __init__(self, core, data_model, cb):
        super(AddProfileDialog, self).__init__(core)
        
        self.data_model = data_model
        self.__update = cb
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "profile_add.glade"))
        
        self.window = builder.get_object("dialog:profile_add")

        builder.get_object("profile_add:btn_ok").connect("clicked", self.__cb_do)
        builder.get_object("profile_add:btn_cancel").connect("clicked", self.__delete_event)
        self.pid = builder.get_object("profile_add:entry_id")
        self.title = builder.get_object("profile_add:entry_title")
        self.info_box = builder.get_object("profile_add:info_box")

        self.lang = builder.get_object("profile_add:entry_lang")
        self.lang.set_text(self.core.selected_lang or "")

        self.__entry_style = self.pid.get_style().base[Gtk.StateType.NORMAL]
        self.show()

    def __cb_do(self, widget):

        if len(self.pid.get_text()) == 0: 
            self.core.notify("Can't add profile with no ID !",
                    core.Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
            return
        profiles = self.data_model.get_profiles()
        for profile in profiles:
            if profile.id == self.pid.get_text():
                self.core.notify("Profile \"%s\" already exists." % (self.pid.get_text(),),
                        core.Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
                self.pid.grab_focus()
                self.pid.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#FFC1C2"))
                return
        self.pid.modify_base(Gtk.StateType.NORMAL, self.__entry_style)
        if len(self.title.get_text()) == 0: 
            self.core.notify("Please add title for this profile.",
                    core.Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
            self.title.grab_focus()
            self.title.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#FFC1C2"))
            return
        self.title.modify_base(Gtk.StateType.NORMAL, self.__entry_style)

        self.data_model.add(id=self.pid.get_text(), lang=self.lang.get_text(), title=self.title.get_text())
        self.core.selected_profile = self.pid.get_text()
        self.window.destroy()
        self.__update(force=True)

    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()

class ProfileList(abstract.List):

    """ List of Profiles and refine items.

    This class represents TreeView in editor window which contains
    list of profiles. Each profile contains list of selectors,
    refine-rules, refine-values and setvalues.
    
    Selectors and refine-rules are grouped into one item as well as
    refine-values and setvalues to contract the length of the list.
    """
    
    def __init__(self, widget, core, data_model, builder=None, progress=None, filter=None):
        """ Constructor of ProfileList.
        """
        
        self.data_model = data_model
        super(ProfileList, self).__init__("gui:edit:profile_list", core, widget)
        
        self.builder = builder
        
        """ Register signals that can be emited by this class.
        All signals are registered in EventObject (abstract class) and
        are emited by other objects to trigger the async event.
        """
        self.add_sender(id, "update")
        self.add_receiver("gui:btn:menu:edit:profiles", "update", self.__update)
        self.add_receiver("gui:btn:menu:edit:XCCDF", "load", self.__clear_update)
        self.add_receiver("gui:edit:xccdf:profiles:finditem", "update", self.__update)
        self.add_receiver("gui:edit:item_list", "delete", self.__clear_update)

        """ Set objects from Glade files and connect signals
        """
        # Build the Popup Menu
        self.builder.get_object("profile_list:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("profile_list:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("profile_list:popup"))

        selection = self.get_TreeView().get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self.__cb_changed, self.get_TreeView())
        self.section_list = self.builder.get_object("xccdf:section_list")
        self.profilesList = self.builder.get_object("xccdf:tw_profiles:sw")
        self.search = self.builder.get_object("xccdf:profiles:search")
        self.filter_none = self.builder.get_object("xccdf:profiles:filter:none")
        self.filter_none.connect("toggled", self.__set_filter, "")
        self.filter_profiles = self.builder.get_object("xccdf:profiles:filter:profiles")
        self.filter_profiles.connect("toggled", self.__set_filter, "profile:")
        self.filter_rules = self.builder.get_object("xccdf:profiles:filter:rules")
        self.filter_rules.connect("toggled", self.__set_filter, "rule:")
        self.filter_groups = self.builder.get_object("xccdf:profiles:filter:groups")
        self.filter_groups.connect("toggled", self.__set_filter, "group:")
        self.filter_values = self.builder.get_object("xccdf:profiles:filter:values")
        self.filter_values.connect("toggled", self.__set_filter, "value:")
        self.search.connect("changed", self.__cb_search, self.get_TreeView())

        """ Set the model of the list to support search
        """
        self.__stop_search = False
        modelfilter = self.data_model.model.filter_new(None)
        modelfilter.set_visible_func(self.__filter_func, None)
        self.get_TreeView().set_model(modelfilter)

        self.get_TreeView().connect("key-press-event", self.__cb_key_press)

    def __set_filter(self, widget, filter):
        """ This function is called when setting up some filter.

        There are 2 use cases:
        1) When user clicked on particular filter button, it will write
           unique string which correspond to the filter in the beginning
           of filter text entry.
        2) When user wrote to the filter text entry unique string which
           corresponds to some filter (see below) it will select this 
           filter explicitly.
        """
        filters = { "" : self.filter_none,
                    "profile:": self.filter_profiles,
                    "rule:": self.filter_rules,
                    "group:": self.filter_groups,
                    "value:": self.filter_values }
        if not widget and filter in filters.keys(): filters[filter].set_active(True)
        elif filter in filters.keys():
            sub = re.findall("^([a-z]*:)?(.*)$", self.search.get_text())[0]
            self.search.set_text(filter+sub[1])

    def __cb_search(self, widget, treeview):
        """ Callback when filter text entry was changed
        """
        self.core.notify_destroy("notify:profiles:filter")
        self.__stop_search = False
        sub = re.findall("^([a-z]*:)?(.*)$", self.search.get_text())[0]
        self.__set_filter(None, sub[0])
        treeview.get_model().refilter()
        self.__update(False)

    def __filter_func(self, model, iter, data=None):
        """ TreeModelFilter filter function which is called
        upon all model items. This function will decide if the
        item will be visible or not.
        """
        if self.__stop_search: return True
        columns = [0,1,4]                                   # In which columns we should look for regexp match ?
        text = self.search.get_text()                       # Regular expression text
        subcmd = re.findall("^([a-z]*:)?(.*)$", text)[0]    # Split to <filter>:text

        group = subcmd[0]                                   # Group is particular filter (see __set_filter func)
        text = subcmd[1]                                    # Text is regular expression string
        if len(group) == 0 and len(text) == 0: return True  # It is pointless to search nothing

        """ This is kind of tricky: When we are looking for anything
        within the tree but the profiles, when each profile does not
        match this search, it will be hidden - BUT it will also hide
        everything inside the node of every profile in the TreeView.
        Therefor we need to return True (it will be visible) for all
        profiles unless we explicitly say that we are looking just
        within profiles (by profile:text)
        """
        if group != "profile:" and model[iter][0] == "profile":
            return True

        """ If we have set up some filter and the filter rule does
        not match the current item requirement, just skip further
        search.
        """
        if len(group) > 0 and group != "all:" and model[iter][0] != group[:-1]:
            return False

        """ Everything matched so far, let's make a pattern from the
        regexp we have in "text" field. If compilation of this regexp
        fail for whatever reason, show notification and top search
        process.
        """
        try:
            pattern = re.compile(text, re.I)
        
        except sre_constants.error as err:
            self.core.notify("Regexp entry error: %s" % (err,), core.Notification.ERROR, msg_id="notify:profiles:filter")
            self.__stop_search = True
            logger.exception("Regexp entry error")
            
            return True

        """ Compilation of regexp is done. For each column specified
        in "columns" variable (each column should be a text field)
        look for pattern (compiled regular expression from "text").
        """
        for col in columns:
            found = re.search(pattern or "", model[iter][col] or "")
            if found != None: return True
        return False

    def __clear_update(self):
        """ Remove all items from the list and update model
        """
        self.data_model.model.clear()
        self.__update(force=True)

    def __update(self, force=False):
        """ Update items in the list. Parameter 'force' is used to force
        the fill function upon the list."""
        if "profile" not in self.__dict__ or force:
            self.data_model.model.clear()
            self.data_model.fill(no_default=True)
            self.profile = self.core.selected_profile

        if self.core.selected_profile and self.selected:
            """ We have a profile selected, let's find it and select """
            self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_profile, self.get_TreeView(), 1))
        if self.core.selected_item and self.selected:
            """ We have an item selected, let's find it and select """
            self.get_TreeView().get_model().foreach(self.set_selected_profile_item, (self.core.selected_profile, self.core.selected_item, self.get_TreeView(), 1))

        """List is updated, trigger all events 
        connected to this signal"""
        self.emit("update")

    def __cb_changed(self, widget, treeView):
        """Callback called when selection of the tree view (item and profile list) changes.
        """
        
        selection = treeView.get_selection( )
        if selection != None: 
            (filter_model, filter_iter) = selection.get_selected()
            
            if not filter_iter:
                # nothing selected
                self.core.selected_profile = None
                self.core.selected_item = None
                self.selected = None
                
            else:
                model = filter_model.get_model()
                iter = filter_model.convert_iter_to_child_iter(filter_iter)
    
                if model.get_value(iter, 0) == "profile":
                    # If a profile is selected, change the global value of selected profile
                    # and clear the local value of item (to evade possible conflicts in selections)
                    self.core.selected_profile = model.get_value(iter, 2).id
                    self.core.selected_item = None
                    self.selected = model[iter]
                
                else:
                    # If a refine item is selected, change the global value of selected item
                    # and fill the local value of selected item so details can be filled from it.
                    self.core.selected_profile = None
                    self.core.selected_item = model.get_value(iter, 1)
                    self.selected = model[iter]
        
        else:
            self.core.selected_profile = None
            self.core.selected_item = None
            self.selected = None

        # Selection has changed, trigger all events
        # connected to this signal
        self.emit("update")

    def __cb_key_press(self, widget, event):
        """ The key-press event has occured upon the list.
        If key == delete: Delete the selected item from the list and model"""
        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval == Gdk.KEY_Delete:
            selection = self.get_TreeView().get_selection()
            (model,iter) = selection.get_selected()
            if iter: self.__cb_item_remove()

    def __cb_button_pressed(self, treeview, event, menu):
        """ Mouse button has been pressed. If the button is 3rd: show
        popup menu"""
        if event.button == 3:
            menu.popup(None, None, None, None, event.button, event.time)

    def __cb_item_remove(self, widget=None):
        """ Remove selected item from the list and model.
        """
        selection = self.get_TreeView().get_selection()
        (filter_model, filter_iter) = selection.get_selected()
        if filter_iter:
            model = filter_model.get_model()
            iter = filter_model.convert_iter_to_child_iter(filter_iter)
            if not iter:
                raise RuntimeError("Iter validation failed")

            filter_iter_next = filter_model.iter_next(filter_iter)
            iter_next = filter_model.convert_iter_to_child_iter(filter_iter_next) if filter_iter_next else None

            if model.get_value(iter, 0) == "profile":
                # Profile selected
                self.data_model.remove_item(model[iter][2].id)
                model.remove(iter)
                
            else:
                # Refine item selected
                profile = model.get_value(model.iter_parent(iter), 1)
                self.data_model.remove_refine(profile, model[iter][2])
                model.remove(iter)

                # If the removed item has successor, let's select it so we can
                # continue in deleting or other actions without need to click the
                # list again to select next item
                if iter_next:
                    self.core.selected_item = model[iter_next][1]
                    self.__update(False)

        # Nothing selected
        else:
            self.notifications.append(self.core.notify("Please select at least one item to delete",
                core.Notification.ERROR, msg_id="notify:edit:delete_item"))

    def __cb_item_add(self, widget=None):
        """ Add profile to the profile list (Item can 
        """
        AddProfileDialog(self.core, self.data_model, self.__update)
        

class MenuButtonEditProfiles(abstract.MenuButton, abstract.Func):

    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit:profiles", widget, core)
        abstract.Func.__init__(self, core)
        
        self.builder = builder
        self.data_model = commands.DHProfiles(self.core)
        self.__item_finder = FindItem(self.core, "gui:edit:xccdf:profiles:finditem", self.data_model)

        #draw body
        self.body = self.builder.get_object("profiles:box")
        self.profiles = self.builder.get_object("xccdf:profiles")
        self.list_profile = ProfileList(self.profiles, self.core, self.data_model, builder, None, None)

        # set signals
        self.add_receiver("gui:edit:profile_list", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:profile:titles", "update", self.__update_item)
        self.add_sender(self.id, "update")
        
        self.__refines_box = self.builder.get_object("xccdf:refines:box")
        self.__profile_box = self.builder.get_object("xccdf:profiles:details")

        # PROFILES
        self.info_box_lbl = self.builder.get_object("xccdf:profile:info_box:lbl")
        self.pid = self.builder.get_object("xccdf:profile:id")
        self.pid.connect("focus-out-event", self.__change)
        self.pid.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("xccdf:profile:version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.extends = self.builder.get_object("xccdf:profile:extends")
        self.extends.connect("changed", self.__change)
        self.abstract = self.builder.get_object("xccdf:profile:abstract")
        self.abstract.connect("toggled", self.__change)
        self.prohibit_changes = self.builder.get_object("xccdf:profile:prohibit_changes")
        self.prohibit_changes.connect("toggled", self.__change)

        # -- TITLE --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:profile:titles", builder.get_object("xccdf:profile:titles"), self.data_model)
        builder.get_object("xccdf:profile:titles:btn_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:profile:titles:btn_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:profile:titles:btn_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:profile:descriptions", builder.get_object("xccdf:profile:descriptions"), self.data_model)
        self.builder.get_object("xccdf:profile:descriptions:btn_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("xccdf:profile:descriptions:btn_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("xccdf:profile:descriptions:btn_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("xccdf:profile:descriptions:btn_preview").connect("clicked", self.descriptions.preview)

        # -- STATUS --
        self.statuses = EditStatus(self.core, "gui:edit:xccdf:profile:statuses", builder.get_object("xccdf:profile:statuses"), self.data_model)
        self.builder.get_object("xccdf:profile:statuses:btn_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("xccdf:profile:statuses:btn_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("xccdf:profile:statuses:btn_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

        # -- REFINES --

        self.refines_idref = self.builder.get_object("xccdf:refines:idref")
        self.refines_selected = self.builder.get_object("xccdf:refines:selected")
        self.refines_selected.connect("toggled", self.__change)
        self.refines_weight = self.builder.get_object("xccdf:refines:weight")
        self.refines_weight.connect("focus-out-event", self.__change)
        self.refines_weight.connect("key-press-event", self.__change)
        self.refines_value = self.builder.get_object("xccdf:refines:value")
        self.refines_value.connect("focus-out-event", self.__change)
        self.refines_value.connect("key-press-event", self.__change)
        self.refines_selector = self.builder.get_object("xccdf:refines:selector")
        self.refines_selector_value = self.builder.get_object("xccdf:refines:selector:cb")
        self.refines_selector.connect("focus-out-event", self.__change)
        self.refines_selector.connect("key-press-event", self.__change)
        self.refines_selector_value.connect("changed", self.__change)
        self.refines_operator = self.builder.get_object("xccdf:refines:operator")
        self.refines_operator.connect("changed", self.__change)
        self.refines_severity = self.builder.get_object("xccdf:refines:severity")
        self.refines_severity.connect("changed", self.__change)

        self.refines_operator.set_model(ENUM.OPERATOR.get_model())
        self.refines_severity.set_model(ENUM.LEVEL.get_model())
        # -------------

        self.builder.get_object("profile_list:popup:sub:select").connect("activate", self.__find_item, "rule")
        self.builder.get_object("profile_list:popup:sub:set-value").connect("activate", self.__find_item, "value")

    def __change(self, widget, event=None):

        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval != Gdk.KEY_Return:
            return

        item = self.list_profile.selected
        if not item: return
        if widget == self.pid:
            # Check if ID doesn't start with number
            self.core.notify_destroy("notify:xccdf:id")
            text = widget.get_text()
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                    core.Notification.ERROR, msg_id="notify:xccdf:id"))
                return
            else: retval = self.data_model.update(id=text)
            if not retval:
                self.notifications.append(self.core.notify("Setting ID failed: ID \"%s\" already exists." % (widget.get_text(),),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                widget.set_text(self.core.selected_profile)
        elif widget == self.version:
            self.data_model.update(version=widget.get_text())
        elif widget == self.extends:
            active = widget.get_active()
            if active != -1:
                self.data_model.update(extends=widget.get_model()[active][0])
        elif widget == self.abstract:
            self.data_model.update(abstract=widget.get_active())
        elif widget == self.prohibit_changes:
            self.data_model.update(prohibit_changes=widget.get_active())
        elif widget == self.refines_idref:
            self.data_model.update_refines(item[0], item[1], item[2], idref=widget.get_text())
        elif widget == self.refines_selected:
            self.data_model.update_refines(item[0], item[1], item[2], selected=widget.get_active())
        elif widget == self.refines_weight:
            weight = self.controlFloat(widget.get_text(), "Weight")
            if weight:
                self.data_model.update_refines(item[0], item[1], item[2], weight=weight)
        elif widget == self.refines_value:
            self.data_model.update_refines(item[0], item[1], item[2], value=widget.get_text())
        elif widget == self.refines_selector:
            self.data_model.update_refines(item[0], item[1], item[2], selector=widget.get_text())
        elif widget == self.refines_selector_value:
            active = widget.get_active()
            if active != -1:
                self.data_model.update_refines(item[0], item[1], item[2], selector=widget.get_model()[active][0])
        elif widget == self.refines_operator:
            self.data_model.update_refines(item[0], item[1], item[2], operator=ENUM.OPERATOR[widget.get_active()][0])
        elif widget == self.refines_severity:
            self.data_model.update_refines(item[0], item[1], item[2], severity=ENUM.LEVEL[widget.get_active()][0])
        else: 
            logger.error("Change not supported object in \"%s\"" % (widget,))
            return
        self.__update_item()
        self.__update()

    def __find_item(self, widget, type):
        if not self.core.selected_profile:
            self.notifications.append(self.core.notify("Please select profile first.",
                core.Notification.INFORMATION, msg_id="notify:edit:find_item"))
            return

        self.__item_finder.dialog(type)

    def __block_signals(self):
        self.pid.handler_block_by_func(self.__change)
        self.version.handler_block_by_func(self.__change)
        self.extends.handler_block_by_func(self.__change)
        self.abstract.handler_block_by_func(self.__change)
        self.prohibit_changes.handler_block_by_func(self.__change)
        #self.refines_idref.handler_block_by_func(self.__change)
        self.refines_selected.handler_block_by_func(self.__change)
        self.refines_weight.handler_block_by_func(self.__change)
        self.refines_value.handler_block_by_func(self.__change)
        self.refines_selector.handler_block_by_func(self.__change)
        self.refines_selector_value.handler_block_by_func(self.__change)
        self.refines_operator.handler_block_by_func(self.__change)
        self.refines_severity.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.pid.handler_unblock_by_func(self.__change)
        self.version.handler_unblock_by_func(self.__change)
        self.extends.handler_unblock_by_func(self.__change)
        self.abstract.handler_unblock_by_func(self.__change)
        self.prohibit_changes.handler_unblock_by_func(self.__change)
        #self.refines_idref.handler_unblock_by_func(self.__change)
        self.refines_selected.handler_unblock_by_func(self.__change)
        self.refines_weight.handler_unblock_by_func(self.__change)
        self.refines_value.handler_unblock_by_func(self.__change)
        self.refines_selector.handler_unblock_by_func(self.__change)
        self.refines_selector_value.handler_unblock_by_func(self.__change)
        self.refines_operator.handler_unblock_by_func(self.__change)
        self.refines_severity.handler_unblock_by_func(self.__change)

    def __clear(self):

        self.pid.set_text("")
        self.version.set_text("")
        self.abstract.set_active(False)
        self.prohibit_changes.set_active(False)
        self.titles.clear()
        self.descriptions.clear()
        self.statuses.clear()
        self.refines_selected.set_active(False)
        self.refines_weight.set_text("")
        self.refines_value.set_text("")
        self.refines_selector.set_text("")
        self.refines_operator.set_active(-1)
        self.refines_severity.set_active(-1)
        self.extends.get_model().clear()

    def __update(self):
        if not self.core.selected_profile or not self.list_profile.selected:
            # this will make sure that the box that was previously visible gets disabled
            
            # NOTE: we could also just hide it but that makes the interface jump around.
            #       in my opinion disabling it surprises the user much less
            self.__profile_box.set_sensitive(False)
            self.__refines_box.set_sensitive(False)
            
            return
        
        self.__block_signals()
        self.__clear()
        
        if self.list_profile.selected[0] == "profile":
            # a profile is selected, make sure the profile box is visible and enabled
            self.__profile_box.set_visible(True)
            self.__profile_box.set_sensitive(True)
            
            # and hide the refine box
            self.__refines_box.set_visible(False)
            
            details = self.data_model.get_profile_details(self.core.selected_profile)
            if not details:
                self.__unblock_signals()
                return

            self.pid.set_text(details["id"] or "")
            self.version.set_text(details["version"] or "")

            # Set extend profile
            self.extends.get_model().append(["", ""])
            for profile in self.data_model.get_profiles():
                if profile.id != details["id"]:
                    title = self.data_model.get_title(profile.title) or "%s (ID)" % (profile.id,)
                    iter = self.extends.get_model().append([profile.id, title])
                    if details["extends"] == profile.id: self.extends.set_active_iter(iter)

            self.abstract.set_active(details["abstract"])
            self.prohibit_changes.set_active(details["prohibit_changes"])
            self.titles.fill()
            self.descriptions.fill()
            self.statuses.fill()
            
        else:
            # at this point we assume a refine of a profile is selected, so lets show
            # the refine box
            self.__refines_box.set_visible(True)
            self.__refines_box.set_sensitive(True)
            
            # and hide the profile box
            self.__profile_box.set_visible(False)

            itype   = self.list_profile.selected[0]
            refid   = self.list_profile.selected[1]
            objs    = self.list_profile.selected[2]

            details = self.data_model.get_item_details(refid)
            self.__refines_box.set_sensitive(details != None)
            if not details:
                self.__unblock_signals()
                return

            self.refines_selected.set_sensitive(itype in ["rule", "group"])
            self.refines_weight.set_sensitive(itype in ["rule", "group"])
            self.refines_selector.set_sensitive(itype in ["rule", "value"])
            self.refines_selector.set_property('visible', itype != "value")
            self.refines_selector_value.set_property('visible', itype == "value")
            self.refines_severity.set_sensitive(itype == "rule")
            self.refines_value.set_sensitive(itype == "value")
            self.refines_operator.set_sensitive(itype == "value")

            self.refines_idref.set_text(refid)
            if itype in ["rule", "group"]:
                for rule in objs:
                    if rule.object == "xccdf_select":
                        self.refines_selected.set_active(rule.selected)
                    elif rule.object == "xccdf_refine_rule":
                        self.refines_selector.set_text(rule.selector or "")
                        self.refines_weight.set_text(`rule.weight`)
                        self.refines_severity.set_active(ENUM.LEVEL.pos(rule.severity))
                    else: raise AttributeError("Unknown type of rule refine: %s" % (rule.object,))
            elif itype == "value":
                model = self.refines_selector_value.get_model()
                model.clear()
                for inst in details["instances"]:
                    model.append([inst.selector])

                has_value = False
                for value in objs:
                    if value.object == "xccdf_setvalue":
                        self.refines_value.set_text(value.value or "")
                        has_value = True
                        self.refines_selector_value.set_active(-1)
                    elif value.object == "xccdf_refine_value":
                        for row in model:
                            if not has_value and row[0] == value.selector: self.refines_selector_value.set_active_iter(row.iter)
                        self.refines_operator.set_active(ENUM.OPERATOR.pos(value.oper))
                    else: raise AttributeError("Unknown type of value refine: %s" % (value.object,))
                
            else: raise AttributeError("Unknown type of refines in profile: %s" % (itype,))
            
        self.__unblock_signals()

    def __update_item(self):
        selection = self.profiles.get_selection()
        (filter_model, filter_iter) = selection.get_selected()
        if filter_iter:
            model = filter_model.get_model()
            iter = filter_model.convert_iter_to_child_iter(filter_iter)
            if model[iter][0] == "profile":
                profile = model[iter][2]
                # Get the title of item
                model[iter][4]= self.data_model.get_title(profile.title) or "%s (ID)" % (profile.id,)
            else: # refine
                if len(model[iter][2]) == 0:
                    #TODO: remove ?
                    logger.error("No objects in refines for %s" % (model[iter][1],))
                    return
                else:
                    for obj in model[iter][2]:
                        model[iter][1] = obj.item
                        item = self.data_model.get_item(obj.item)
                        if obj.object == "xccdf_select":
                            model[iter][5] = ["gray", None][obj.selected]
                        if not item:
                            model[iter][3] = "dialog-error"
                            model[iter][4] = "Broken reference: %s" % (obj.item,)
                            model[iter][5] = "red"
                        else:
                            model[iter][4] = self.data_model.get_title(item.title) or "%s (ID)" % (item.id,)
