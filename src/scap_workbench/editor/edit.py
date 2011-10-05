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
import gtk              # GTK library
import glib
import gobject          # gobject.TYPE_PYOBJECT
import time             # Time functions in calendar data ::EditStatus
import re               # Regular expressions 
import sre_constants    # For re.compile exception
import os               # os Path join/basename, ..
import threading        # Main window is running in thread
import gnome, gnome.ui  # Gnome icons in HTML editor
import tempfile         # Temporary file for XCCDF preview
import datetime
import logging                  # Logger for debug/info/error messages

""" Importing SCAP Workbench modules
"""
import scap_workbench.core.abstract
import scap_workbench.core.core as core
import scap_workbench.core.commands
import scap_workbench.core.dialogs
from scap_workbench.core.core import Notification
from scap_workbench.core.events import EventObject
import scap_workbench.core.enum as ENUM
import scap_workbench.core.paths
import scap_workbench.core.error

# Initializing Logger
logger = logging.getLogger("scap-workbench")

""" Importing non-standard python libraries
These libraries are not required and should be always
checked by:
  if HAS_MODULE: do
  else: notify(..)"""
try:
    # Import WebKit module for HTML editing 
    # of descriptions
    import webkit as webkit
    HAS_WEBKIT = True
except ImportError:
    HAS_WEBKIT = False

""" Import OpenSCAP library as backend.
If anything goes wrong just end with exception"""
try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None
    raise ex


class ProfileList(scap_workbench.core.abstract.List):

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
        selection.set_mode(gtk.SELECTION_SINGLE)
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
        modelfilter = self.data_model.model.filter_new()
        modelfilter.set_visible_func(self.__filter_func)
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
            self.core.notify("Regexp entry error: %s" % (err,), Notification.ERROR, msg_id="notify:profiles:filter")
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
        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval == gtk.keysyms.Delete:
            selection = self.get_TreeView().get_selection()
            (model,iter) = selection.get_selected()
            if iter: self.__cb_item_remove()

    def __cb_button_pressed(self, treeview, event, menu):
        """ Mouse button has been pressed. If the button is 3rd: show
        popup menu"""
        if event.button == 3:
            menu.popup(None, None, None, event.button, event.time)

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
                Notification.ERROR, msg_id="notify:edit:delete_item"))

    def __cb_item_add(self, widget=None):
        """ Add profile to the profile list (Item can 
        """
        AddProfileDialog(self.core, self.data_model, self.__update)


class ItemList(scap_workbench.core.abstract.List):

    """ List of Rules, Groups and Values.

    This class represents TreeView in editor window which contains
    list of XCCDF Items as Rules, Groups and Values. Each Group contains
    its content.
    """

    def __init__(self, widget, core, builder=None, progress=None):
        """ Constructor of ProfileList.
        """
        self.data_model = scap_workbench.core.commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, None, True, no_checks=True)
        super(ItemList, self).__init__("gui:edit:item_list", core, widget)
        
        self.loaded = False
        self.filter = filter
        self.builder = builder

        """ Register signals that can be emited by this class.
        All signals are registered in EventObject (abstract class) and
        are emited by other objects to trigger the async event.
        """
        self.add_sender(self.id, "update")
        self.add_sender(self.id, "delete")
        self.add_receiver("gui:btn:menu:edit:items", "update", self.__update)
        self.add_receiver("gui:btn:menu:edit:XCCDF", "load", self.__clear_update)


        """ Set objects from Glade files and connect signals
        """
        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.section_list = self.builder.get_object("edit:section_list")
        self.itemsList = self.builder.get_object("edit:tw_items:sw")
        self.with_values = self.builder.get_object("xccdf:items:popup:show_values")
        self.with_values.connect("toggled", self.__update)
        # Popup Menu
        self.builder.get_object("xccdf:items:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("xccdf:items:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("xccdf:items:popup"))

        self.add_dialog = AddItem(self.core, self.data_model, self) # TODO
        self.get_TreeView().connect("key-press-event", self.__cb_key_press)
        
        # if True an idle worker that will perform the update (after selection changes) is already pending
        self.item_changed_worker_pending = False

    def __clear_update(self):
        """ Remove all items from the list and update model
        """
        self.data_model.model.clear()
        self.__update(force=True)

    def __update(self, force=False):
        """ Update items in the list. Parameter 'force' is used to force
        the fill function upon the list."""
        if not self.loaded or force:
            self.data_model.fill(with_values=self.with_values.get_active())
            self.loaded = True

        # Select the last one selected if there is one
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))

    def __cb_button_pressed(self, treeview, event, menu):
        """ Mouse button has been pressed. If the button is 3rd: show
        popup menu"""
        if event.button == 3:
            time = event.time
            menu.popup(None, None, None, event.button, event.time)

    def __cb_key_press(self, widget, event):
        """ The key-press event has occured upon the list.
        If key == delete: Delete the selected item from the list and model"""
        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval == gtk.keysyms.Delete:
            selection = self.get_TreeView().get_selection()
            (model,iter) = selection.get_selected()
            if iter: self.__cb_item_remove()

    def __cb_item_remove(self, widget=None):
        """ Remove selected item from the list and model.
        """
        selection = self.get_TreeView().get_selection()
        (model, iter) = selection.get_selected()
        if iter:
            iter_next = model.iter_next(iter)
            self.data_model.remove_item(model[iter][1])
            model.remove(iter)

            """ If the removed item has successor, let's select it so we can
            continue in deleting or other actions without need to click the
            list again to select next item """
            if iter_next:
                self.core.selected_item = model[iter_next][1]
                self.__update(False)
            self.emit("delete") 
        else: raise AttributeError, "Removing non-selected item or nothing selected."

    def __cb_item_add(self, widget=None):
        """ Add item to the list and model
        """
        self.add_dialog.dialog()

    def __cb_item_changed(self, widget, treeView):
        """Callback called whenever item selection changes. Performs updates of the property box.
        """
        
        def worker():
            details = self.data_model.get_item_details(self.core.selected_item)
            selection = treeView.get_selection( )
            if selection != None: 
                (model, iter) = selection.get_selected( )
                if iter: self.core.selected_item = model.get_value(iter, scap_workbench.core.commands.DHItemsTree.COLUMN_ID)
                else: self.core.selected_item = None
    
            # Selection has changed, trigger all events connected to this signal
            self.emit("update")
            treeView.columns_autosize()
            
            self.item_changed_worker_pending = False
        
        # The reason for the item_changed_worker_pending attribute is to avoid stacking up
        # many update requests that would all query the selection state again and do repeated
        # work. This way the update happens only once even though the selection changes many times.
        if not self.item_changed_worker_pending:
            # we handle this in the idle function when no higher priority events are to be handled
            glib.idle_add(worker)
            self.item_changed_worker_pending = True

class MenuButtonEditXCCDF(scap_workbench.core.abstract.MenuButton):

    def __init__(self, builder, widget, core):
        super(MenuButtonEditXCCDF, self).__init__("gui:btn:menu:edit:XCCDF", widget, core)
        
        self.builder = builder
        self.data_model = scap_workbench.core.commands.DHXccdf(core)
        
        #draw body
        self.body = self.builder.get_object("xccdf:box")
        self.sub_menu = self.builder.get_object("edit:sub:main")
        self.add_sender(self.id, "update")
        self.add_sender(self.id, "load")

        # Get widgets from glade
        self.entry_id = self.builder.get_object("edit:xccdf:id")
        self.entry_id.connect( "changed", self.__change, "id")
        self.entry_version = self.builder.get_object("edit:xccdf:version")
        self.entry_version.connect( "changed", self.__change, "version")
        self.entry_resolved = self.builder.get_object("edit:xccdf:resolved")
        self.entry_resolved.connect( "changed", self.__change, "resolved")
        self.entry_lang = self.builder.get_object("edit:xccdf:lang")
        self.entry_lang.connect( "changed", self.__change, "lang")

        # -- TITLE --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:title", builder.get_object("edit:xccdf:titles"), self.data_model)
        builder.get_object("edit:xccdf:btn_titles_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:btn_titles_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:btn_titles_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:description", builder.get_object("edit:xccdf:descriptions"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_descriptions_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_descriptions_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_descriptions_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("edit:xccdf:btn_descriptions_preview").connect("clicked", self.descriptions.preview)

        # -- WARNING --
        self.warnings = EditWarning(self.core, "gui:edit:xccdf:warning", builder.get_object("edit:xccdf:warnings"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_warnings_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_warnings_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_warnings_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- NOTICE --
        self.notices = EditNotice(self.core, "gui:edit:xccdf:notice", builder.get_object("edit:xccdf:notices"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_notices_add").connect("clicked", self.notices.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_notices_edit").connect("clicked", self.notices.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_notices_del").connect("clicked", self.notices.dialog, self.data_model.CMD_OPER_DEL)

        # -- REFERENCE --
        # FIXME: Instantiating an abstract class?!
        self.tv_references = scap_workbench.core.abstract.ListEditor("gui:edit:xccdf:references", self.core, widget=self.builder.get_object("edit:xccdf:references"), model=gtk.ListStore(str, str))
        self.tv_references.widget.append_column(gtk.TreeViewColumn("Reference", gtk.CellRendererText(), text=0))
        self.builder.get_object("edit:xccdf:btn_references_add").set_sensitive(False)
        self.builder.get_object("edit:xccdf:btn_references_edit").set_sensitive(False)
        self.builder.get_object("edit:xccdf:btn_references_del").set_sensitive(False)
        self.builder.get_object("edit:xccdf:references").set_sensitive(False)

        # -- STATUS --
        self.statuses = EditStatus(self.core, "gui:edit:xccdf:status", builder.get_object("edit:xccdf:statuses"), self.data_model)
        self.builder.get_object("edit:xccdf:btn_statuses_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:btn_statuses_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:btn_statuses_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)
        # -------------

        self.btn_new = self.builder.get_object("edit:sub:new")
        self.btn_close = self.builder.get_object("edit:sub:close")
        self.btn_import = self.builder.get_object("edit:sub:import")
        self.btn_export = self.builder.get_object("edit:sub:export")
        self.btn_new.connect("clicked", self.__cb_new)
        self.btn_close.connect("clicked", self.__cb_close)
        self.btn_import.connect("clicked", self.__cb_import)
        self.btn_export.connect("clicked", self.__cb_export)

    def __cb_new(self, widget):
        """ Create new XCCDF Benchmark
        """
        if not self.core.init(None): return

        # Update neccessary attributes of Benchmark
        self.data_model.update(id="New_SCAP_Benchmark", version="0", lang="en")
        self.core.selected_lang = "en"
        self.core.notify_destroy("notify:xccdf:missing_lang")
        self.data_model.edit_status(self.data_model.CMD_OPER_ADD)
        try:
            self.__update()
        except KeyError:
            pass

        self.emit("load")

    def __import(self, file):
        if file != "":
            self.__cb_close(None)
            logger.debug("Loading XCCDF file %s", file)
            if not self.core.init(file): return
            self.emit("load")

            try:
                self.__update()
            except KeyError:
                pass

    def __cb_validate(self, widget):
        """ Deprecated: Validate button from main file is not visible
        anymore. This function is not reachable. Leting here for
        further reference """
        validate = self.data_model.validate()
        message = [ "Document is not valid !",
                    "Document is valid.",
                    "Validation process failed, check for error in log file."][validate]
        lvl = [ Notification.WARNING,
                Notification.SUCCESS,
                Notification.ERROR][validate]
        self.notifications.append(self.core.notify(message, lvl, msg_id="notify:xccdf:validate"))

    def __cb_import(self, widget):
        scap_workbench.core.dialogs.ImportDialog(self.core, self.data_model, self.__import)

    def __cb_export(self, widget):
        scap_workbench.core.dialogs.ExportDialog(self.core, self.data_model)

    def __menu_sensitive(self, active):
        self.btn_new.set_sensitive(not active)
        self.btn_import.set_sensitive(not active)
        self.btn_close.set_sensitive(active)
        self.btn_export.set_sensitive(active)
        self.core.get_item("gui:btn:menu:edit:profiles").set_sensitive(active)
        self.core.get_item("gui:btn:menu:edit:items").set_sensitive(active)

    def __cb_close(self, widget):
        self.__menu_sensitive(False)
        self.core.destroy()
        self.__clear()
        self.core.notify_destroy("notify:xccdf:validate")
        self.core.notify_destroy("notify:xccdf:export")
        self.__update()
        self.emit("load")

    def __change(self, widget, object=None):

        if object == "id":
            self.core.notify_destroy("notify:xccdf:id")
            # Replace all white spaces with '_' (space are not allowed in ID)
            text = re.sub("[\t ]+" , "_", widget.get_text())
            # Check if ID doesn't start with number
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                    Notification.ERROR, msg_id="notify:xccdf:id"))
            else: self.data_model.update(id=text)
        elif object == "version":
            self.data_model.update(version=widget.get_text())
        elif object == "resolved":
            self.data_model.update(resolved=(widget.get_active() == 1))
        elif object == "status":
            self.data_model.update(status=ENUM.STATUS_CURRENT[widget.get_active()][0])
        elif object == "lang":
            self.data_model.update(lang=widget.get_text())
        else: 
            logger.error("Change \"%s\" not supported object in \"%s\"" % (object, widget))
            return
        self.emit("update")

    def __clear(self):
        """Clear widgets
        """
        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.notices.clear()
        self.statuses.clear()
        self.tv_references.clear()
        self.entry_id.set_text("")
        self.entry_version.set_text("")
        self.entry_resolved.set_active(-1)
        self.entry_lang.set_text("")

    def activate(self, active):
        self.core.notify_destroy("notify:xccdf:export")
        super(MenuButtonEditXCCDF, self).activate(active)
        self.sub_menu.set_property("visible", active)

    def update(self):
        self.__update()

    def __update(self):

        # TODO: this blocks of handlers could be substitute ?        
        self.entry_id.handler_block_by_func(self.__change)
        self.entry_version.handler_block_by_func(self.__change)
        self.entry_resolved.handler_block_by_func(self.__change)
        self.entry_lang.handler_block_by_func(self.__change)

        self.__clear()
        details = self.data_model.get_details()
        self.__menu_sensitive(details != None)

        """Set sensitivity of widgets depended on availability of XCCDF details
        This is mainly supposed to control no-XCCDF or loaded XCCDF behavior
        """
        self.builder.get_object("edit:xccdf:notebook").set_sensitive(details != None)
        self.builder.get_object("edit:xccdf:entries").set_sensitive(details != None)

        """Update 
        """
        if details:
            self.entry_id.set_text(details["id"] or "")
            self.entry_version.set_text(details["version"] or "")
            self.entry_resolved.set_active(details["resolved"])
            self.entry_lang.set_text(details["lang"] or "")
            self.titles.fill()
            self.descriptions.fill()
            self.warnings.fill()
            self.notices.fill()
            #for ref in details["references"]:
                #self.tv_references.append([ref])
            self.statuses.fill()

        self.entry_id.handler_unblock_by_func(self.__change)
        self.entry_version.handler_unblock_by_func(self.__change)
        self.entry_resolved.handler_unblock_by_func(self.__change)
        self.entry_lang.handler_unblock_by_func(self.__change)

class MenuButtonEditProfiles(scap_workbench.core.abstract.MenuButton, scap_workbench.core.abstract.Func):

    def __init__(self, builder, widget, core):
        scap_workbench.core.abstract.MenuButton.__init__(self, "gui:btn:menu:edit:profiles", widget, core)
        scap_workbench.core.abstract.Func.__init__(self, core)
        
        self.builder = builder
        self.data_model = scap_workbench.core.commands.DHProfiles(self.core)
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

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        item = self.list_profile.selected
        if not item: return
        if widget == self.pid:
            # Check if ID doesn't start with number
            self.core.notify_destroy("notify:xccdf:id")
            text = widget.get_text()
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                    Notification.ERROR, msg_id="notify:xccdf:id"))
                return
            else: retval = self.data_model.update(id=text)
            if not retval:
                self.notifications.append(self.core.notify("Setting ID failed: ID \"%s\" already exists." % (widget.get_text(),),
                    Notification.ERROR, msg_id="notify:not_selected"))
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
                Notification.INFORMATION, msg_id="notify:edit:find_item"))
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

            
class MenuButtonEditItems(scap_workbench.core.abstract.MenuButton, scap_workbench.core.abstract.Func):

    def __init__(self, builder, widget, core):
        scap_workbench.core.abstract.MenuButton.__init__(self, "gui:btn:menu:edit:items", widget, core)
        scap_workbench.core.abstract.Func.__init__(self, core)
        
        self.builder = builder
        self.data_model = scap_workbench.core.commands.DHEditItems(self.core)
        self.item = None
        # FIXME: Instantiating abstract class
        # FIXME: We inherit Func and we are composed of it
        self.func = scap_workbench.core.abstract.Func()
        self.current_page = 0

        #draw body
        self.body = self.builder.get_object("items:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        #self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        #self.filter.set_active(False)
        self.filter = None
        self.tw_items = self.builder.get_object("edit:tw_items")
        titles = self.data_model.get_benchmark_titles()
        self.list_item = ItemList(self.tw_items, self.core, builder, self.progress)
        self.ref_model = self.list_item.get_TreeView().get_model() # original model (not filtered)
        
        # set signals
        self.add_sender(self.id, "update")
        
        # remove just for now (missing implementations and so..)
        self.items = self.builder.get_object("edit:xccdf:items")
        self.items.remove_page(4)

        # Get widgets from GLADE
        self.item_id = self.builder.get_object("edit:general:entry_id")
        self.item_id.connect("focus-out-event", self.__change)
        self.item_id.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("edit:general:entry_version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.version_time = self.builder.get_object("edit:general:entry_version_time")
        self.version_time.connect("focus-out-event", self.__change)
        self.version_time.connect("key-press-event", self.__change)
        self.selected = self.builder.get_object("edit:general:chbox_selected")
        self.selected.connect("toggled", self.__change)
        self.hidden = self.builder.get_object("edit:general:chbox_hidden")
        self.hidden.connect("toggled", self.__change)
        self.prohibit = self.builder.get_object("edit:general:chbox_prohibit")
        self.prohibit.connect("toggled", self.__change)
        self.abstract = self.builder.get_object("edit:general:chbox_abstract")
        self.abstract.connect("toggled", self.__change)
        self.cluster_id = self.builder.get_object("edit:general:entry_cluster_id")
        self.cluster_id.connect("focus-out-event", self.__change)
        self.cluster_id.connect("key-press-event", self.__change)
        self.weight = self.builder.get_object("edit:general:entry_weight")
        self.weight.connect("focus-out-event", self.__change)
        self.weight.connect("key-press-event", self.__change)
        self.operations = self.builder.get_object("edit:xccdf:items:operations")
        self.extends = self.builder.get_object("edit:dependencies:lbl_extends")
        self.content_ref = self.builder.get_object("edit:xccdf:items:evaluation:content_ref")
        self.content_ref.connect("focus-out-event", self.__change)
        self.content_ref.connect("key-press-event", self.__change)
        self.content_ref_find = self.builder.get_object("edit:xccdf:items:evaluation:content_ref:find")
        self.href = self.builder.get_object("edit:xccdf:items:evaluation:href")
        self.href.connect("changed", self.__change)
        self.href_dialog = self.builder.get_object("edit:xccdf:items:evaluation:href:dialog")
        self.href_dialog.connect("file-set", self.__cb_href_file_set)
        self.item_values_main = self.builder.get_object("edit:values:sw_main")
        self.ident_box = self.builder.get_object("xccdf:items:ident:box")
        
        # -- TITLES --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:items:titles", builder.get_object("edit:general:lv_title"), self.data_model)
        builder.get_object("edit:general:btn_title_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_title_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_title_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTIONS --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:items:descriptions", builder.get_object("edit:general:lv_description"), self.data_model)
        builder.get_object("edit:general:btn_description_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_description_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_description_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("edit:general:btn_description_preview").connect("clicked", self.descriptions.preview)

        # -- WARNINGS --
        self.warnings = EditWarning(self.core, "gui:edit:items:general:warning", builder.get_object("edit:general:lv_warning"), self.data_model)
        builder.get_object("edit:general:btn_warning_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_warning_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_warning_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- STATUSES --
        self.statuses = EditStatus(self.core, "gui:edit:items:general:status", builder.get_object("edit:general:lv_status"), self.data_model)
        builder.get_object("edit:general:btn_status_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_status_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_status_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

        # -- QUESTIONS --
        self.questions = EditQuestion(self.core, "gui:edit:items:general:questions", builder.get_object("edit:items:questions"), self.data_model)
        builder.get_object("edit:items:questions:btn_add").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:items:questions:btn_edit").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:items:questions:btn_del").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_DEL)

        # -- RATIONALES --
        self.rationales = EditRationale(self.core, "gui:edit:items:general:rationales", builder.get_object("edit:items:rationales"), self.data_model)
        builder.get_object("edit:items:rationales:btn_add").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:items:rationales:btn_edit").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:items:rationales:btn_del").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_DEL)

        # -- VALUES --
        self.item_values = EditItemValues(self.core, "gui:edit:items:values", builder.get_object("edit:xccdf:items:values"), self.data_model)
        builder.get_object("edit:xccdf:items:values:btn_add").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:items:values:btn_edit").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:items:values:btn_del").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("edit:xccdf:items:values").connect("button-press-event", self.__cb_value_clicked) # Double-click makes the editor to look for the value in items

        # -- PLATFORMS --
        self.platforms = EditPlatform(self.core, "gui:edit:dependencies:platforms", builder.get_object("edit:xccdf:dependencies:platforms"), self.data_model)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_add").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_edit").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_del").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_DEL)

        # -- CONTENT REF --
        self.content_ref_dialog = FindOvalDef(self.core, "gui:edit:evaluation:content_ref:dialog", self.data_model)
        self.content_ref_find.connect("clicked", self.__cb_find_oval_definition)

        # -- FIXTEXTS --
        self.fixtext = EditFixtext(self.core, "id:edit:xccdf:items:fixtext", builder.get_object("xccdf:items:fixtext"), self.data_model, builder)
        builder.get_object("xccdf:items:fixtext:btn_add").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:fixtext:btn_edit").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:fixtext:btn_del").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("xccdf:items:fixtext:btn_preview").connect("clicked", self.fixtext.preview)

        # -- FIXES --
        self.fix = EditFix(self.core, "id:edit:xccdf:items:fix", builder.get_object("xccdf:items:fix"), self.data_model, builder)
        builder.get_object("xccdf:items:fix:btn_add").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:fix:btn_edit").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:fix:btn_del").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_DEL)

        # -- IDENTS --
        self.ident = EditIdent(self.core, "id:edit:xccdf:items:ident", builder.get_object("xccdf:items:ident"), self.data_model)
        builder.get_object("xccdf:items:ident:btn_add").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:ident:btn_edit").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:ident:btn_del").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_DEL)
        # -------------

        """Get widgets from Glade: Part editor.glade in edit
        """
        self.conflicts = EditConflicts(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.requires = EditRequires(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.values = EditValues(self.core, "gui:edit:xccdf:values", self.builder)
        
        self.severity = self.builder.get_object("edit:operations:combo_severity")
        self.severity.set_model(ENUM.LEVEL.get_model())
        self.severity.connect( "changed", self.__change)
        self.impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.impact_metric.connect("focus-out-event", self.cb_control_impact_metric)
        self.check = self.builder.get_object("edit:operations:lv_check")

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:evaluation:content_ref:dialog", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:values:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:items:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:values", "update_item", self.__update_item)

    def __cb_find_oval_definition(self, widget):

        model = self.href.get_model()
        if self.href.get_active() == -1:
            self.notifications.append(self.core.notify("No definition file available", Notification.WARNING, msg_id="notify:definition_available"))
            return
        self.content_ref_dialog.dialog(None, model[self.href.get_active()][0])

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        if widget == self.item_id:
            self.core.notify_destroy("notify:xccdf:id")
            text = widget.get_text()
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                    Notification.ERROR, msg_id="notify:xccdf:id"))
                return
            else: retval = self.data_model.update(id=text)
            if not retval:
                self.notifications.append(self.core.notify("Setting ID failed: ID \"%s\" already exists." % (widget.get_text(),),
                    Notification.ERROR, msg_id="notify:not_selected"))
                widget.set_text(self.core.selected_item)
                return
            self.__update_item()
        elif widget == self.version:
            self.data_model.update(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp > 0:
                self.data_model.update(version_time=timestamp)
        elif widget == self.selected:
            self.data_model.update(selected=widget.get_active())
        elif widget == self.hidden:
            self.data_model.update(hidden=widget.get_active())
        elif widget == self.prohibit:
            self.data_model.update(prohibit=widget.get_active())
        elif widget == self.abstract:
            self.data_model.update(abstract=widget.get_active())
        elif widget == self.cluster_id:
            self.data_model.update(cluster_id=widget.get_text())
        elif widget == self.weight:
            weight = self.controlFloat(widget.get_text(), "Weight")
            if weight:
                self.data_model.update(weight=weight)
        elif widget == self.content_ref:
            ret, err = self.data_model.set_item_content(name=widget.get_text())
            if not ret:
                self.notifications.append(self.core.notify(err, Notification.ERROR, msg_id="notify:edit:content_href"))
        elif widget == self.href:
            if self.href.get_active() == -1 or len(self.href.get_model()) == 0:
                return
            iter = self.href.get_model()[self.href.get_active()]
            if iter:
                href = iter[1]
                self.data_model.set_item_content(href=href)
                self.core.notify_destroy("notify:definition_available")
        elif widget == self.severity:
            self.data_model.update(severity=ENUM.LEVEL.value(widget.get_active()))
        else: 
            logger.error("Change of \"%s\" is not supported " % (widget,))
            return

    def __cb_href_file_set(self, widget):
        path = widget.get_filename()
        file = os.path.basename(widget.get_filename())

        self.data_model.add_oval_reference(path)
        retval, err = self.data_model.set_item_content(href=file)
        if not retval: self.notifications.append(self.core.notify(err, Notification.ERROR, msg_id="notify:set_content_ref"))
        self.__update()

    def __cb_value_clicked(self, widget, event):

        if event.type == gtk.gdk._2BUTTON_PRESS and event.button == 1:
            selection = widget.get_selection()
            if selection:
                (model, iter) = selection.get_selected()
                if not iter: return
                id = model[iter][0]# Should be ID of value
                if not id: return
            else: return
            self.list_item.search(id, 1)

    def __section_list_load(self):
        self.section_list.get_model().clear()
        titles = self.data_model.get_benchmark_titles()
        if len(titles.keys()) != 0:
            if self.core.selected_lang in titles: 
                title = self.data_model.get_benchmark_titles()[self.core.selected_lang]
            else: 
                self.data_model.get_benchmark_titles()[0]
            self.section_list.get_model().append(["XCCDF", "XCCDF: "+title])
            self.section_list.get_model().append(["PROFILES", "XCCDF: "+title+" (Profiles)"])
            self.section_list.set_active(0)

    def cb_control_impact_metric(self, widget, event):
        text = widget.get_text()
        if text != "" and self.controlImpactMetric(text, self.core):
            self.data_model.DHEditImpactMetric(self.item, text)

    def show(self, sensitive):
        self.items.set_sensitive(sensitive)
        self.items.set_property("visible", sensitive)

    def __set_profile_description(self, description):
        """
        Set description to the textView.
        @param text Text with description
        """
        self.profile_description.get_buffer().set_text("")
        if description == "": description = "No description"
        description = "<body>"+description+"</body>"
        self.profile_description.display_html(description)

    def __update_item(self):
        selection = self.tw_items.get_selection()
        (model, iter) = selection.get_selected()
        if iter:
            item = self.data_model.get_item(model[iter][1])
            if item == None:
                item = self.data_model.get_item(self.core.selected_item)
            if item == None:
                logger.error("Can't find item with ID: \"%s\"" % (model[iter][1],))
                return
            model[iter][1] = item.id

            # Get the title of item
            title = self.data_model.get_title(item.title) or "%s (ID)" % (item.id,)

            model[iter][2] = title
            model[iter][4] = ""+title

    def __block_signals(self):
        self.hidden.handler_block_by_func(self.__change)
        self.selected.handler_block_by_func(self.__change)
        self.prohibit.handler_block_by_func(self.__change)
        self.abstract.handler_block_by_func(self.__change)
        self.severity.handler_block_by_func(self.__change)
        self.content_ref.handler_block_by_func(self.__change)
        self.href.handler_block_by_func(self.__change)
        #self.multiple.handler_block_by_func(self.__change)
        #self.role.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.hidden.handler_unblock_by_func(self.__change)
        self.selected.handler_unblock_by_func(self.__change)
        self.prohibit.handler_unblock_by_func(self.__change)
        self.abstract.handler_unblock_by_func(self.__change)
        self.severity.handler_unblock_by_func(self.__change)
        self.content_ref.handler_unblock_by_func(self.__change)
        self.href.handler_unblock_by_func(self.__change)
        #self.chbox_multiple.handler_unblock_by_func(self.__change)
        #self.cBox_role.handler_unblock_by_func(self.__change)

    def __clear(self):
        self.__block_signals()
        self.item_id.set_text("")
        self.hidden.set_active(False)
        self.selected.set_active(False)
        self.prohibit.set_active(False)
        self.abstract.set_active(False)
        self.version.set_text("")
        self.version_time.set_text("")
        self.cluster_id.set_text("")
        #self.extends.set_text("None")
        self.content_ref.set_text("")
        self.href.get_model().clear()
        self.severity.set_active(-1)

        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.statuses.clear()
        self.questions.clear()
        self.rationales.clear()
        self.item_values.clear()
        self.conflicts.fill(None)
        self.requires.fill(None)
        self.platforms.fill()
        self.fix.fill()
        self.fixtext.fill()
        self.__unblock_signals()

    def __update(self):
 
        if self.core.selected_item != None:
            details = self.data_model.get_item_details(self.core.selected_item)
        else:
            details = None
            #self.item = None
        
        self.__clear()
        if details == None:
            self.items.set_sensitive(False)
            return

        # Check if the item is value and change widgets
        if details["type"] == openscap.OSCAP.XCCDF_VALUE:
            self.show(False)
            self.values.show(True)
            self.values.update()
            return
        else: 
            self.show(True)
            self.values.show(False)

        # Item is not value, continue
        self.__block_signals()
        self.item_id.set_text(details["id"] or "")
        self.weight.set_text(str(details["weight"] or ""))
        self.version.set_text(details["version"] or "")
        self.version_time.set_text("" if details["version_time"] <= 0 else str(datetime.date.fromtimestamp(details["version_time"])))
        self.cluster_id.set_text(details["cluster_id"] or "")
        self.extends.set_text(details["extends"] or "")
        self.titles.fill()
        self.descriptions.fill()
        self.warnings.fill()
        self.statuses.fill()
        self.questions.fill()
        self.rationales.fill()
        self.conflicts.fill(details)
        self.requires.fill(details["item"])
        self.platforms.fill()

        self.abstract.set_active(details["abstract"])
        self.selected.set_active(details["selected"])
        self.hidden.set_active(details["hidden"])
        self.prohibit.set_active(details["prohibit_changes"])

        self.items.set_sensitive(True)

        # Set sensitivity for rule / group
        self.ident_box.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.item_values_main.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.operations.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.severity.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)

        if details["type"] == openscap.OSCAP.XCCDF_RULE: # Item is Rule
            self.severity.set_active(ENUM.LEVEL.pos(details["severity"]))
            self.impact_metric.set_text(details["imapct_metric"] or "")
            self.fixtext.fill()
            self.fix.fill()
            self.ident.fill()
            content = self.data_model.get_item_content()
 
            if len(self.core.lib.files) > 0:
                self.href.get_model().clear()
                for name in self.core.lib.files.keys():
                    self.href.get_model().append([name, name])
            if content != None and len(content) > 0:
                self.content_ref.set_text(content[0][0] or "")
                for i, item in enumerate(self.href.get_model()):
                    if item[0] == content[0][1]: self.href.set_active(i)
            self.item_values.fill()
            
        else: # Item is GROUP
            self.severity.set_active(-1)
            self.impact_metric.set_text("")
            self.fixtext.fill()
            self.fix.fill()
            self.ident.fill()

        self.__unblock_signals()
                
            
class EditConflicts(scap_workbench.core.commands.DHEditItems, scap_workbench.core.abstract.ControlEditWindow):
    
    COLUMN_ID = 0
    
    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_conflict")
        model = gtk.ListStore(str)
        lv.set_model(model)
        
        scap_workbench.core.commands.DHEditItems.__init__(self, core)
        scap_workbench.core.abstract.ControlEditWindow.__init__(self, core, lv, None)
        
        btn_add = builder.get_object("edit:dependencies:btn_conflict_add")
        btn_del = builder.get_object("edit:dependencies:btn_conflict_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.__cb_add)
        btn_del.connect("clicked", self.__cb_del_row)

        self.addColumn("ID Item",self.COLUMN_ID)

    def fill(self, details):
        if details == None:
            return
        self.item = details["item"]
        self.model.clear()
        for data in details["conflicts"]:
            self.model.append([data])
    
    def __cb_add(self, widget):
        EditSelectIdDialogWindow(self.item, self.core, self.model, self.model_item, self.DHEditConflicts)
    
    
    def __cb_del_row(self, widget):
        pass

class EditRequires(scap_workbench.core.commands.DHEditItems, scap_workbench.core.abstract.ControlEditWindow):
    
    COLUMN_ID = 0
    
    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_requires")
        model = gtk.ListStore(str)
        lv.set_model(model)

        scap_workbench.core.commands.DHEditItems.__init__(self, core)
        scap_workbench.core.abstract.ControlEditWindow.__init__(self, core, lv, None)
        
        btn_add = builder.get_object("edit:dependencies:btn_requires_add")
        btn_del = builder.get_object("edit:dependencies:btn_requires_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.__cb_add)
        btn_del.connect("clicked", self.__cb_del_row)

        self.addColumn("ID Item", self.COLUMN_ID)

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            for data in item.requires:
                self.model.append([data])
    
    def __cb_add(self, widget):
        EditSelectIdDialogWindow(self.item, self.core, self.model, self.model_item, self.DHEditRequires)
    
    def __cb_del_row(self, widget):
        pass

class EditItemValues(scap_workbench.core.abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1
    COLUMN_EXPORT   = 2
    COLUMN_OBJ      = 3
    COLUMN_COLOR    = 4

    def __init__(self, core, id, widget, data_model):
        super(EditItemValues, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, str, gobject.TYPE_PYOBJECT, str, str))

        self.data_model = data_model

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        item = None
        (model, iter) = self.values.get_selection().get_selected()
        if iter:
            item = model[iter][self.COLUMN_ID]
        elif self.operation != self.data_model.CMD_OPER_EDIT:
            self.core.notify("Value has to be choosen.", Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            return

        if self.operation == self.data_model.CMD_OPER_EDIT:
            self.data_model.item_edit_value(self.operation, self.search.get_text(), self.export_name.get_text())
        else:
            self.data_model.item_edit_value(self.operation, item, self.export_name.get_text())
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:find_value")
        self.info_box = builder.get_object("dialog:find_value:info_box")
        self.values = builder.get_object("dialog:find_value:values")
        self.export_name = builder.get_object("dialog:find_value:export_name")
        self.search = builder.get_object("dialog:find_value:search")
        self.search.connect("changed", self.search_treeview, self.values)
        builder.get_object("dialog:find_value:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_value:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            self.values.append_column(gtk.TreeViewColumn("ID of Value", gtk.CellRendererText(), text=self.COLUMN_ID))
            self.values.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))
            values = self.data_model.get_all_values()
            self.values.set_model(gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
            modelfilter = self.values.get_model().filter_new()
            modelfilter.set_visible_func(self.filter_listview, data=(self.search, (0,1)))
            self.values.set_model(modelfilter)
            for value in values: 
                item = self.data_model.parse_value(value)
                if len(item["titles"]) > 0:
                    if self.core.selected_lang in item["titles"].keys(): title = item["titles"][self.core.selected_lang]
                    else: title = item["titles"][item["titles"].keys()[0]]+" ["+item["titles"].keys()[0]+"]"
                self.values.get_model().get_model().append([value.id, title, value])

            self.wdialog.set_transient_for(self.core.main_window)
            self.wdialog.show_all()
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            self.values.append_column(gtk.TreeViewColumn("ID of Value", gtk.CellRendererText(), text=self.COLUMN_ID))
            self.values.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))
            values = self.data_model.get_all_values()
            self.values.set_model(gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
            modelfilter = self.values.get_model().filter_new()
            modelfilter.set_visible_func(self.filter_listview, data=(self.search, (0,1)))
            self.values.set_model(modelfilter)
            for value in values: 
                item = self.data_model.parse_value(value)
                if len(item["titles"]) > 0:
                    if self.core.selected_lang in item["titles"].keys(): title = item["titles"][self.core.selected_lang]
                    else: title = item["titles"][item["titles"].keys()[0]]+" ["+item["titles"].keys()[0]+"]"
                self.values.get_model().get_model().append([value.id, title, value])

            self.search.set_text(model[iter][self.COLUMN_ID])
            self.values.get_model().refilter()
            self.values.set_sensitive(False)
            self.search.set_sensitive(False)
            self.export_name.set_text(model[iter][self.COLUMN_EXPORT])
            self.wdialog.set_transient_for(self.core.main_window)
            self.wdialog.show_all()

        elif operation == self.data_model.CMD_OPER_BIND:
            self.values.append_column(gtk.TreeViewColumn("ID of Value", gtk.CellRendererText(), text=self.COLUMN_ID))
            self.values.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))
            self.values.set_sensitive(False)

            self.wdialog.set_transient_for(self.core.main_window)
            self.wdialog.show_all()

        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for title dialog: \"%s\"" % (operation,))
            return

    def fill(self):
        """
        """
        self.clear()
        ref = ""
        for check in self.data_model.get_item_check_exports() or []:
            item = self.data_model.get_item(check[0])
            if item:
                title = self.data_model.get_title(item.title) or ""
                self.append([check[0], (" ".join(title.split())), check[1], item, None, None])
            else:
                self.append([check[0], "(Missing item)", check[1], None, "red", "white"])

class EditTitle(scap_workbench.core.abstract.ListEditor):

    COLUMN_LANG         = 0
    COLUMN_OVERRIDES    = 1
    COLUMN_TEXT         = 2
    COLUMN_OBJ          = 3

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model
        super(EditTitle, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, bool, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.title.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_title(self.operation, item, self.lang.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()), 
                                            self.overrides.get_active())
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_title")
        self.info_box = builder.get_object("dialog:edit_title:info_box")
        self.lang = builder.get_object("dialog:edit_title:lang")
        self.title = builder.get_object("dialog:edit_title:title")
        self.overrides = builder.get_object("dialog:edit_title:overrides")
        builder.get_object("dialog:edit_title:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_title:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.overrides.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.title.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for title dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):
        """
        """
        self.clear()
        for data in self.data_model.get_titles() or []:
            self.append([data.lang, data.overrides, (" ".join(data.text.split())), data])

class EditDescription(scap_workbench.core.abstract.HTMLEditor):

    COLUMN_LANG         = 0
    COLUMN_OVERRIDES    = 1
    COLUMN_TEXT         = 2
    COLUMN_OBJ          = 3

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditDescription, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, bool, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_description(self.operation, item, None, None, None)
        else:
            desc = self.get_text().strip()
            retval = self.data_model.edit_description(self.operation, item, self.lang.get_text(), desc, self.overrides.get_active())

        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_description")
        self.info_box = builder.get_object("dialog:edit_description:info_box")
        self.lang = builder.get_object("dialog:edit_description:lang")
        self.overrides = builder.get_object("dialog:edit_description:overrides")
        self.toolbar = builder.get_object("dialog:edit_description:toolbar")
        self.html_box = builder.get_object("dialog:edit_description:html:box")
        builder.get_object("dialog:edit_description:action:bold").connect("activate", self.on_action, "bold")
        builder.get_object("dialog:edit_description:action:italic").connect("activate", self.on_action, "italic")
        builder.get_object("dialog:edit_description:action:underline").connect("activate", self.on_action, "underline")
        builder.get_object("dialog:edit_description:action:code").connect("activate", self.on_code_set, "code")
        builder.get_object("dialog:edit_description:action:num_list").connect("activate", self.on_action, "InsertOrderedList")
        builder.get_object("dialog:edit_description:action:bul_list").connect("activate", self.on_action, "InsertUnorderedList")
        builder.get_object("dialog:edit_description:action:outdent").connect("activate", self.on_action, "Outdent")
        builder.get_object("dialog:edit_description:action:indent").connect("activate", self.on_action, "Indent")
        builder.get_object("dialog:edit_description:action:link").connect("activate", self.on_link_set)
        builder.get_object("dialog:edit_description:action:zoomin").connect("activate", self.on_zoom)
        builder.get_object("dialog:edit_description:action:zoomout").connect("activate", self.on_zoom)
        builder.get_object("dialog:edit_description:tb:color").connect("clicked", self.on_color_set)
        builder.get_object("dialog:edit_description:tb:font").connect("clicked", self.on_font_set)
        builder.get_object("dialog:edit_description:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_description:btn_ok").connect("clicked", self.__do)
        self.switcher = builder.get_object("dialog:edit_description:switcher")

        self.render(self.html_box, self.toolbar, self.switcher)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
            self.load_html("", "file:///")
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                self.overrides.set_active(model[iter][self.COLUMN_OVERRIDES])
                desc = model[iter][self.COLUMN_TEXT]
                desc = desc.replace("xhtml:","")
                self.load_html(desc or "", "file:///")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                retval = self.dialogDel(self.core.main_window, self.get_selection())
                if retval != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def fill(self):

        self.clear()
        for data in self.data_model.get_descriptions() or []:
            self.append([data.lang, data.overrides, re.sub("[\t ]+" , " ", data.text or "").strip(), data])

class EditFixtext(scap_workbench.core.abstract.HTMLEditor):
    
    COLUMN_LANG = 0
    COLUMN_TEXT = 1
    COLUMN_OBJ  = 2

    def __init__(self, core, id, widget, data_model, builder):

        self.data_model = data_model
        self.builder = builder
        super(EditFixtext, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=self.COLUMN_TEXT))

        """ Here are all attributes of fixtext
        """
        self.__attr_frame = self.builder.get_object("items:fixtext")
        self.__attr_frame.set_sensitive(False)
        self.__attr_fixref = self.builder.get_object("items:fixtext:fixref")
        self.__attr_fixref.connect("focus-out-event", self.__change)
        self.__attr_fixref.connect("key-press-event", self.__change)
        self.__attr_strategy = self.builder.get_object("items:fixtext:strategy")
        self.__attr_strategy.set_model(ENUM.STRATEGY.get_model())
        self.__attr_strategy.connect( "changed", self.__change)
        self.__attr_complexity = self.builder.get_object("items:fixtext:complexity")
        self.__attr_complexity.set_model(ENUM.COMPLEXITY.get_model())
        self.__attr_complexity.connect( "changed", self.__change)
        self.__attr_disruption = self.builder.get_object("items:fixtext:disruption")
        self.__attr_disruption.set_model(ENUM.DISRUPTION.get_model())
        self.__attr_disruption.connect( "changed", self.__change)
        self.__attr_reboot = self.builder.get_object("items:fixtext:reboot")
        self.__attr_reboot.connect("toggled", self.__change)
        self.__attr_overrides = self.builder.get_object("items:fixtext:overrides")
        self.__attr_overrides.connect("toggled", self.__change)
 
        self.widget.get_selection().connect("changed", self.__attr_fill)

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        (model, iter) = self.get_selection().get_selected()
        if not iter:
            logger.debug("Changing attribute of fixtext failed. HINT: Use enter to save your changes")
            return
        data = model[iter][self.COLUMN_OBJ]

        if widget == self.__attr_fixref:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, fixref=widget.get_text())
        elif widget == self.__attr_strategy:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, strategy=ENUM.STRATEGY.value(widget.get_active()))
        elif widget == self.__attr_complexity:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, complexity=ENUM.COMPLEXITY.value(widget.get_active()))
        elif widget == self.__attr_disruption:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, disruption=ENUM.DISRUPTION.value(widget.get_active()))
        elif widget == self.__attr_reboot:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, reboot=widget.get_active())
        elif widget == self.__attr_overrides:
            retval = self.data_model.edit_fixtext(self.data_model.CMD_OPER_EDIT, fixtext=data, overrides=widget.get_active())
        else: 
            logger.error("Change of \"%s\" is not supported " % (widget,))
            return


    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_fixtext(self.operation, item, None, None)
        else:
            desc = self.get_text()
            retval = self.data_model.edit_fixtext(self.operation, item, self.lang.get_text(), desc)

        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_description")
        self.info_box = builder.get_object("dialog:edit_description:info_box")
        self.lang = builder.get_object("dialog:edit_description:lang")
        self.toolbar = builder.get_object("dialog:edit_description:toolbar")
        self.html_box = builder.get_object("dialog:edit_description:html:box")
        builder.get_object("dialog:edit_description:action:bold").connect("activate", self.on_action, "bold")
        builder.get_object("dialog:edit_description:action:italic").connect("activate", self.on_action, "italic")
        builder.get_object("dialog:edit_description:action:underline").connect("activate", self.on_action, "underline")
        builder.get_object("dialog:edit_description:action:code").connect("activate", self.on_code_set, "code")
        builder.get_object("dialog:edit_description:action:num_list").connect("activate", self.on_action, "InsertOrderedList")
        builder.get_object("dialog:edit_description:action:bul_list").connect("activate", self.on_action, "InsertUnorderedList")
        builder.get_object("dialog:edit_description:action:outdent").connect("activate", self.on_action, "Outdent")
        builder.get_object("dialog:edit_description:action:indent").connect("activate", self.on_action, "Indent")
        builder.get_object("dialog:edit_description:action:link").connect("activate", self.on_link_set)
        builder.get_object("dialog:edit_description:action:zoomin").connect("activate", self.on_zoom)
        builder.get_object("dialog:edit_description:action:zoomout").connect("activate", self.on_zoom)
        builder.get_object("dialog:edit_description:tb:color").connect("clicked", self.on_color_set)
        builder.get_object("dialog:edit_description:tb:font").connect("clicked", self.on_font_set)
        builder.get_object("dialog:edit_description:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_description:btn_ok").connect("clicked", self.__do)
        self.switcher = builder.get_object("dialog:edit_description:switcher")

        self.render(self.html_box, self.toolbar, self.switcher)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
            self.load_html("", "file:///")
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                desc = model[iter][self.COLUMN_TEXT]
                desc = desc.replace("xhtml:","")
                self.load_html(desc or "", "file:///")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                retval = self.dialogDel(self.core.main_window, self.get_selection())
                if retval != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def __block_signals(self):
        self.__attr_fixref.handler_block_by_func(self.__change)
        self.__attr_strategy.handler_block_by_func(self.__change)
        self.__attr_complexity.handler_block_by_func(self.__change)
        self.__attr_disruption.handler_block_by_func(self.__change)
        self.__attr_reboot.handler_block_by_func(self.__change)
        self.__attr_overrides.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.__attr_fixref.handler_unblock_by_func(self.__change)
        self.__attr_strategy.handler_unblock_by_func(self.__change)
        self.__attr_complexity.handler_unblock_by_func(self.__change)
        self.__attr_disruption.handler_unblock_by_func(self.__change)
        self.__attr_reboot.handler_unblock_by_func(self.__change)
        self.__attr_overrides.handler_unblock_by_func(self.__change)

    def __attrs_clear(self):
        self.__block_signals()
        self.__attr_frame.set_sensitive(False)
        self.__attr_fixref.set_text("")
        self.__attr_strategy.set_active(-1)
        self.__attr_complexity.set_active(-1)
        self.__attr_disruption.set_active(-1)
        self.__attr_reboot.set_active(False)
        self.__attr_overrides.set_active(False)
        self.__unblock_signals()

    def __attr_fill(self, widget=None):
        
        (model, iter) = self.get_selection().get_selected()

        self.__attr_frame.set_sensitive(iter is not None)
        if not iter: return

        data = model[iter][self.COLUMN_OBJ]
        
        self.__block_signals()
        self.__attr_fixref.set_text(data.fixref or "")
        self.__attr_strategy.set_active(ENUM.STRATEGY.pos(data.strategy))
        self.__attr_complexity.set_active(ENUM.COMPLEXITY.pos(data.complexity))
        self.__attr_disruption.set_active(ENUM.DISRUPTION.pos(data.disruption))
        self.__attr_reboot.set_active(data.reboot)
        self.__attr_overrides.set_active(data.text.overrides)
        self.__unblock_signals()

    def fill(self):
        self.clear()
        self.__attrs_clear()

        for data in self.data_model.get_fixtexts() or []:
            self.append([data.text.lang, re.sub("[\t ]+" , " ", data.text.text or "").strip(), data])

class EditFix(scap_workbench.core.abstract.ListEditor):
    
    COLUMN_ID   = 0
    COLUMN_TEXT = 1
    COLUMN_OBJ  = 2

    def __init__(self, core, id, widget, data_model, builder):

        self.data_model = data_model
        self.builder = builder
        super(EditFix, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Content", gtk.CellRendererText(), text=self.COLUMN_TEXT))

        """ Here are all attributes of fix
        """
        self.__attr_frame = self.builder.get_object("items:fix")
        self.__attr_frame.set_sensitive(False)
        self.__attr_system = self.builder.get_object("items:fix:system")
        self.__attr_system.connect("focus-out-event", self.__change)
        self.__attr_system.connect("key-press-event", self.__change)
        self.__attr_platform = self.builder.get_object("items:fix:platform")
        self.__attr_platform.connect("focus-out-event", self.__change)
        self.__attr_platform.connect("key-press-event", self.__change)
        self.__attr_strategy = self.builder.get_object("items:fix:strategy")
        self.__attr_strategy.set_model(ENUM.STRATEGY.get_model())
        self.__attr_strategy.connect( "changed", self.__change)
        self.__attr_complexity = self.builder.get_object("items:fix:complexity")
        self.__attr_complexity.set_model(ENUM.LEVEL.get_model())
        self.__attr_complexity.connect( "changed", self.__change)
        self.__attr_disruption = self.builder.get_object("items:fix:disruption")
        self.__attr_disruption.set_model(ENUM.LEVEL.get_model())
        self.__attr_disruption.connect( "changed", self.__change)
        self.__attr_reboot = self.builder.get_object("items:fix:reboot")
        self.__attr_reboot.connect("toggled", self.__change)
 
        self.widget.get_selection().connect("changed", self.__attr_fill)

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        (model, iter) = self.get_selection().get_selected()
        if not iter:
            logger.debug("Changing attribute of fix failed. HINT: Use enter to save your changes")
            return
        data = model[iter][self.COLUMN_OBJ]

        if widget == self.__attr_system:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, system=widget.get_text())
        elif widget == self.__attr_platform:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, platform=widget.get_text())
        elif widget == self.__attr_strategy:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, strategy=ENUM.STRATEGY.value(widget.get_active()))
        elif widget == self.__attr_complexity:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, complexity=ENUM.LEVEL.value(widget.get_active()))
        elif widget == self.__attr_disruption:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, disruption=ENUM.LEVEL.value(widget.get_active()))
        elif widget == self.__attr_reboot:
            retval = self.data_model.edit_fix(self.data_model.CMD_OPER_EDIT, fix=data, reboot=widget.get_active())
        else: 
            logger.error("Change of \"%s\" is not supported " % (widget,))
            return


    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:xccdf:id")
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        text_id = self.fid.get_text()
        if len(text_id) != 0 and re.search("[A-Za-z_]", text_id[0]) == None:
            self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                Notification.ERROR, msg_id="notify:xccdf:id")
            return

        buffer = self.content.get_buffer()
        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_fix(self.operation, fix=item)
        else:
            retval = self.data_model.edit_fix(self.operation, fix=item, id=text_id, content=buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))

        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_fix")
        self.info_box = builder.get_object("dialog:edit_fix:info_box")
        self.fid = builder.get_object("dialog:edit_fix:id")
        self.content = builder.get_object("dialog:edit_fix:content")
        builder.get_object("dialog:edit_fix:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_fix:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.fid.set_text(model[iter][self.COLUMN_ID] or "")
                self.content.get_buffer().set_text(model[iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                retval = self.dialogDel(self.core.main_window, self.get_selection())
                if retval != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for fix content dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def __block_signals(self):
        self.__attr_system.handler_block_by_func(self.__change)
        self.__attr_platform.handler_block_by_func(self.__change)
        self.__attr_strategy.handler_block_by_func(self.__change)
        self.__attr_complexity.handler_block_by_func(self.__change)
        self.__attr_disruption.handler_block_by_func(self.__change)
        self.__attr_reboot.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.__attr_system.handler_unblock_by_func(self.__change)
        self.__attr_platform.handler_unblock_by_func(self.__change)
        self.__attr_strategy.handler_unblock_by_func(self.__change)
        self.__attr_complexity.handler_unblock_by_func(self.__change)
        self.__attr_disruption.handler_unblock_by_func(self.__change)
        self.__attr_reboot.handler_unblock_by_func(self.__change)

    def __attrs_clear(self):
        self.__block_signals()
        self.__attr_frame.set_sensitive(False)
        self.__attr_system.set_text("")
        self.__attr_platform.set_text("")
        self.__attr_strategy.set_active(-1)
        self.__attr_complexity.set_active(-1)
        self.__attr_disruption.set_active(-1)
        self.__attr_reboot.set_active(False)
        self.__unblock_signals()

    def __attr_fill(self, widget=None):
        
        (model, iter) = self.get_selection().get_selected()

        self.__attr_frame.set_sensitive(iter is not None)
        if not iter: return

        data = model[iter][self.COLUMN_OBJ]
        
        self.__block_signals()
        self.__attr_system.set_text(data.system or "")
        self.__attr_platform.set_text(data.platform or "")
        self.__attr_strategy.set_active(ENUM.STRATEGY.pos(data.strategy))
        self.__attr_complexity.set_active(ENUM.LEVEL.pos(data.complexity))
        self.__attr_disruption.set_active(ENUM.LEVEL.pos(data.disruption))
        self.__attr_reboot.set_active(data.reboot)
        self.__unblock_signals()

    def fill(self):
        self.clear()
        self.__attrs_clear()

        for data in self.data_model.get_fixes() or []:
            self.append([data.id,  (data.content or "").strip(), data])

class EditWarning(scap_workbench.core.abstract.ListEditor):

    COLUMN_LANG         = 0
    COLUMN_OVERRIDES    = 1
    COLUMN_CATEGORY     = 2
    COLUMN_TEXT         = 3
    COLUMN_OBJ          = 4

    def __init__(self, core, id, widget, data_model):
        
        self.data_model = data_model
        super(EditWarning, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, bool, str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Category", gtk.CellRendererText(), text=self.COLUMN_CATEGORY))
        self.widget.append_column(gtk.TreeViewColumn("Warning", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        category = None
        buffer = self.warning.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]
        if self.category.get_active() != -1:
            category = self.category.get_model()[self.category.get_active()][0]

        retval = self.data_model.edit_warning(self.operation, item, category, self.lang.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()),
                                              self.overrides.get_active())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_warning")
        self.info_box = builder.get_object("dialog:edit_warning:info_box")
        self.lang = builder.get_object("dialog:edit_warning:lang")
        self.overrides = builder.get_object("dialog:edit_warning:overrides")
        self.warning = builder.get_object("dialog:edit_warning:warning")
        self.category = builder.get_object("dialog:edit_warning:category")
        self.category.set_model(ENUM.WARNING.get_model())
        builder.get_object("dialog:edit_warning:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_warning:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.category.set_active(ENUM.WARNING.pos(model[self.iter][self.COLUMN_OBJ].category) or -1)
                self.overrides.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.warning.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for item in self.data_model.get_warnings() or []:
            category = ENUM.WARNING.map(item.category)
            index = ENUM.WARNING.pos(item.category)
            self.append([item.text.lang, item.text.overrides, category[1], re.sub("[\t ]+" , " ", item.text.text).strip(), item])

class EditNotice(scap_workbench.core.abstract.ListEditor):

    COLUMN_ID = 0
    COLUMN_LANG = -1

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditNotice, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.widget.append_column(gtk.TreeViewColumn("Notice", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        # Check input data
        if self.wid.get_text() == "":
            self.core.notify("ID of the notice is mandatory.",
                    Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            self.wid.grab_focus()
            return
        for iter in self.get_model():
            if iter[self.COLUMN_ID] == self.wid.get_text():
                self.core.notify("ID of the notice has to be unique !",
                        Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                self.wid.grab_focus()
                return

        item = None
        buffer = self.notice.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_notice(self.operation, item, self.wid.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_notice")
        self.info_box = builder.get_object("dialog:edit_notice:info_box")
        self.wid = builder.get_object("dialog:edit_notice:id")
        self.notice = builder.get_object("dialog:edit_notice:notice")
        builder.get_object("dialog:edit_notice:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_notice:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.wid.set_text(model[self.iter][self.COLUMN_ID] or "")
                self.notice.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.get_model().clear()
        for data in self.data_model.get_notices() or []:
            self.append([data.id, re.sub("[\t ]+" , " ", data.text.text or "").strip(), data])

class EditStatus(scap_workbench.core.abstract.ListEditor):

    COLUMN_DATE = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditStatus, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Date", gtk.CellRendererText(), text=self.COLUMN_DATE))
        self.widget.append_column(gtk.TreeViewColumn("Status", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        # Check input data
        if self.operation != self.data_model.CMD_OPER_DEL and self.status.get_active() == -1:
            self.core.notify("Status has to be choosen.",
                    Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            self.status.grab_focus()
            return

        item = None
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        year, month, day = self.calendar.get_date()
        retval = self.data_model.edit_status(self.operation, item, "%s-%s-%s" % (year, month, day), self.status.get_active())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_status")
        self.info_box = builder.get_object("dialog:edit_status:info_box")
        self.calendar = builder.get_object("dialog:edit_status:calendar")
        self.status = builder.get_object("dialog:edit_status:status")
        self.status.set_model(ENUM.STATUS_CURRENT.get_model())
        builder.get_object("dialog:edit_status:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_status:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            day, month, year = time.strftime("%d %m %Y", time.gmtime()).split()
            self.calendar.select_month(int(month), int(year))
            self.calendar.select_day(int(day))
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                day, month, year = time.strftime("%d %m %Y", time.localtime(model[self.iter][self.COLUMN_OBJ].date)).split()
                self.calendar.select_month(int(month), int(year))
                self.calendar.select_day(int(day))
                self.status.set_active(ENUM.STATUS_CURRENT.pos(model[self.iter][self.COLUMN_OBJ].status) or -1)
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for item in self.data_model.get_statuses() or []:
            status = ENUM.STATUS_CURRENT.map(item.status)
            index = ENUM.STATUS_CURRENT.pos(item.status)
            self.append([time.strftime("%d-%m-%Y", time.localtime(item.date)), status[1], item])

class EditIdent(scap_workbench.core.abstract.ListEditor):

    COLUMN_ID = 0
    COLUMN_LANG = -1

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditIdent, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.widget.append_column(gtk.TreeViewColumn("System", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        item = None
        buffer = self.system.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            self.data_model.edit_ident(self.operation, item, None, None, None)
        else:
            # Check input data
            if self.wid.get_text() == "":
                self.core.notify("ID of the ident is mandatory.",
                        Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                self.wid.grab_focus()
                return
            if self.operation == self.data_model.CMD_OPER_ADD:
                for iter in self.get_model():
                    if iter[self.COLUMN_ID] == self.wid.get_text():
                        self.core.notify("ID of the ident has to be unique !",
                                Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
                        self.wid.grab_focus()
                        return

            retval = self.data_model.edit_ident(self.operation, item, self.wid.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))

        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_ident")
        self.info_box = builder.get_object("dialog:edit_ident:info_box")
        self.wid = builder.get_object("dialog:edit_ident:id")
        self.system = builder.get_object("dialog:edit_ident:system")
        builder.get_object("dialog:edit_ident:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_ident:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.wid.set_text(model[self.iter][self.COLUMN_ID] or "")
                self.system.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for description dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.get_model().clear()
        for data in self.data_model.get_idents() or []:
            self.append([data.id, re.sub("[\t ]+" , " ", data.system or "").strip(), data])

class EditQuestion(scap_workbench.core.abstract.ListEditor):

    COLUMN_OVERRIDES = 3
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditQuestion, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Question", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.question.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_question(self.operation, item, self.lang.get_text(),
                self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_question")
        self.info_box = builder.get_object("dialog:edit_question:info_box")
        self.lang = builder.get_object("dialog:edit_question:lang")
        self.question = builder.get_object("dialog:edit_question:question")
        self.override = builder.get_object("dialog:edit_question:override")
        builder.get_object("dialog:edit_question:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_question:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, self.iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.override.set_active(model[self.iter][self.COLUMN_OVERRIDES])
                self.question.get_buffer().set_text(model[self.iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for question dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for data in self.data_model.get_questions() or []:
            self.append([data.lang, re.sub("[\t ]+" , " ", data.text).strip(), data, data.overrides])


class EditRationale(scap_workbench.core.abstract.ListEditor):

    COLUMN_OVERRIDES = 3
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditRationale, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Overrides", gtk.CellRendererText(), text=self.COLUMN_OVERRIDES))
        self.widget.append_column(gtk.TreeViewColumn("Rationale", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        buffer = self.rationale.get_buffer()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_rationale(self.operation, item, self.lang.get_text(),
                self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_rationale")
        self.info_box = builder.get_object("dialog:edit_rationale:info_box")
        self.lang = builder.get_object("dialog:edit_rationale:lang")
        self.rationale = builder.get_object("dialog:edit_rationale:rationale")
        self.override = builder.get_object("dialog:edit_rationale:override")
        builder.get_object("dialog:edit_rationale:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_rationale:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            if self.core.selected_lang: self.lang.set_text(self.core.selected_lang)
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                self.override.set_active(model[iter][self.COLUMN_OVERRIDES])
                self.rationale.get_buffer().set_text(model[iter][self.COLUMN_TEXT] or "")
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for rationale dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):

        self.clear()
        for data in self.data_model.get_rationales() or []:
            self.append([data.lang, re.sub("[\t ]+" , " ", data.text).strip(), data, data.overrides])


class EditPlatform(scap_workbench.core.abstract.ListEditor):

    COLUMN_TEXT = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model
        super(EditPlatform, self).__init__(id, core, widget=widget, model=gtk.ListStore(str))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("CPE Name", gtk.CellRendererText(), text=self.COLUMN_LANG))

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:edit")
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_TEXT]

        if self.operation != self.data_model.CMD_OPER_DEL:
            text = self.cpe.get_text()
            if len(text) < 6 or text[5] not in ["a", "o", "h"]:
                self.core.notify("The part section can be \"a\", \"o\" or \"h\"",
                        Notification.ERROR, self.info_box, msg_id="notify:edit")
                return
            if len(text[7:].split(":")) != 6:
                self.core.notify("Invalid number of sections: should be cpe:/part:vendor:product:version:update:edition:lang",
                        Notification.ERROR, self.info_box, msg_id="notify:edit")
                return

        retval = self.data_model.edit_platform(self.operation, item, self.cpe.get_text())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def __cb_build(self, widget):
        self.cpe.handler_block_by_func(self.__cb_parse)
        if self.part.get_active() == -1:
            active = ""
        else: active = ["a", "h", "o"][self.part.get_active()]
        self.cpe.set_text("cpe:/%s:%s:%s:%s:%s:%s:%s" % (active, 
            self.vendor.get_text().replace(" ", "_"),
            self.product.get_text().replace(" ", "_"),
            self.version.get_text().replace(" ", "_"),
            self.update.get_text().replace(" ", "_"),
            self.edition.get_text().replace(" ", "_"),
            self.language.get_text().replace(" ", "_")))
        self.cpe.handler_unblock_by_func(self.__cb_parse)

    def __cb_parse(self, widget):
        
        text = widget.get_text()

        # cpe:/
        if text[:5] != "cpe:/": widget.set_text("cpe:/")

        # cpe:/[a,o,h]
        if len(text) > 5:
            if text[5] not in ["a", "o", "h"]: 
                self.core.notify("The part section can be \"a\", \"o\" or \"h\"",
                        Notification.ERROR, self.info_box, msg_id="notify:edit")
                widget.set_text("cpe:/")
                return
            else:
                self.core.notify_destroy("notify:edit")
                self.part.set_active(["a", "h", "o"].index(text[5]))

        # cpe:/[a,o,h]:
        if len(text) > 7 and text[6] != ":":
            widget.set_text(text[:6]+":")

        if len(text) > 8:
            parts = text[7:].split(":")
        else: parts = []

        # cpe:/[a,o,h]:vendor:product:version:update:edition:language
        if len(parts) > 0: self.vendor.set_text(parts[0])
        else: self.vendor.set_text("")
        if len(parts) > 1: self.product.set_text(parts[1])
        else: self.product.set_text("")
        if len(parts) > 2: self.version.set_text(parts[2])
        else: self.version.set_text("")
        if len(parts) > 3: self.update.set_text(parts[3])
        else: self.update.set_text("")
        if len(parts) > 4: self.edition.set_text(parts[4])
        else: self.edition.set_text("")
        if len(parts) > 5: self.language.set_text(parts[5])
        else: self.language.set_text("")

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_platform")
        self.info_box = builder.get_object("dialog:edit_platform:info_box")
        self.cpe = builder.get_object("dialog:edit_platform:cpe")
        self.part = builder.get_object("dialog:edit_platform:cpe_part")
        self.vendor = builder.get_object("dialog:edit_platform:cpe_vendor")
        self.product = builder.get_object("dialog:edit_platform:cpe_product")
        self.version = builder.get_object("dialog:edit_platform:cpe_version")
        self.update = builder.get_object("dialog:edit_platform:cpe_update")
        self.edition = builder.get_object("dialog:edit_platform:cpe_edition")
        self.language = builder.get_object("dialog:edit_platform:cpe_language")
        builder.get_object("dialog:edit_platform:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_platform:btn_ok").connect("clicked", self.__do)

        self.cpe.set_text("cpe:/")
        self.cpe.connect("changed", self.__cb_parse)
        self.part.connect("changed", self.__cb_build)
        self.vendor.connect("changed", self.__cb_build)
        self.product.connect("changed", self.__cb_build)
        self.version.connect("changed", self.__cb_build)
        self.update.connect("changed", self.__cb_build)
        self.edition.connect("changed", self.__cb_build)
        self.language.connect("changed", self.__cb_build)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.cpe.set_text(model[iter][self.COLUMN_TEXT])
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for rationale dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()

    def fill(self):
        self.clear()
        for item in self.data_model.get_platforms() or []:
            self.get_model().append([item])

class EditValues(scap_workbench.core.abstract.MenuButton, scap_workbench.core.abstract.Func):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_TYPE_ITER = 2
    COLUMN_TYPE_TEXT = 3
    COLUMN_OBJECT = 4
    COLUMN_CHECK = 5
    COLUMN_CHECK_EXPORT = 6
    
    def __init__(self, core, id, builder):
        # FIXME: We are not calling constructor of abstract.MenuButton, this could backfire sometime in the future!
        scap_workbench.core.abstract.Func.__init__(self, core)

        self.data_model = scap_workbench.core.commands.DHValues(core) 
        self.builder = builder
        self.id = id

        # FIXME: Calling constructors of classes that are not direct ancestors!
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(id, "update_item")
        
        #edit data of values
        # -- VALUES --
        self.values = builder.get_object("edit:values")

        # -- TITLE --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:values:titles", builder.get_object("edit:values:titles"), self.data_model)
        self.builder.get_object("edit:values:titles:btn_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:values:titles:btn_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:values:titles:btn_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:values:descriptions", builder.get_object("edit:values:descriptions"), self.data_model)
        self.builder.get_object("edit:values:descriptions:btn_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:values:descriptions:btn_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:values:descriptions:btn_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("edit:values:descriptions:btn_preview").connect("clicked", self.descriptions.preview)

        # -- WARNING --
        self.warnings = EditWarning(self.core, "gui:edit:xccdf:values:warnings", builder.get_object("edit:values:warnings"), self.data_model)
        builder.get_object("edit:values:warnings:btn_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:warnings:btn_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:warnings:btn_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- STATUS --
        self.statuses = EditStatus(self.core, "gui:edit:xccdf:values:statuses", builder.get_object("edit:values:statuses"), self.data_model)
        builder.get_object("edit:values:statuses:btn_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:statuses:btn_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:statuses:btn_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

        # -- QUESTIONS --
        self.questions = EditQuestion(self.core, "gui:edit:xccdf:values:questions", builder.get_object("edit:values:questions"), self.data_model)
        builder.get_object("edit:values:questions:btn_add").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:questions:btn_edit").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:questions:btn_del").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_DEL)

        # -- VALUES --
        self.values_values = EditValuesValues(self.core, "gui:edit:xccdf:values:values", builder.get_object("edit:values:values"), self.data_model)
        builder.get_object("edit:values:values:btn_add").connect("clicked", self.values_values.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:values:values:btn_edit").connect("clicked", self.values_values.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:values:values:btn_del").connect("clicked", self.values_values.dialog, self.data_model.CMD_OPER_DEL)
        # -------------
        
        self.vid = self.builder.get_object("edit:values:id")
        self.vid.connect("focus-out-event", self.__change)
        self.vid.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("edit:values:version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.version_time = self.builder.get_object("edit:values:version_time")
        self.version_time.connect("focus-out-event", self.__change)
        self.version_time.connect("key-press-event", self.__change)
        self.cluster_id = self.builder.get_object("edit:values:cluster_id")
        self.cluster_id.connect("focus-out-event", self.__change)
        self.cluster_id.connect("key-press-event", self.__change)
        self.vtype = self.builder.get_object("edit:values:type")
        self.operator = self.builder.get_object("edit:values:operator")
        self.operator.connect("changed", self.__change)
        self.abstract = self.builder.get_object("edit:values:abstract")
        self.abstract.connect("toggled", self.__change)
        self.prohibit_changes = self.builder.get_object("edit:values:prohibit_changes")
        self.prohibit_changes.connect("toggled", self.__change)
        self.interactive = self.builder.get_object("edit:values:interactive")
        self.interactive.connect("toggled", self.__change)

        self.operator.set_model(ENUM.OPERATOR.get_model())
        
    def show(self, active):
        self.values.set_sensitive(active)
        self.values.set_property("visible", active)

    def update(self):
        self.__update()

    def __change(self, widget, event=None):

        item = self.data_model.get_item(self.core.selected_item)
        if item.type != openscap.OSCAP.XCCDF_VALUE: return

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        if widget == self.vid:
            retval = self.data_model.edit_value(id=widget.get_text())
            if not retval:
                self.notifications.append(self.core.notify("Setting ID failed: ID \"%s\" already exists." % (widget.get_text(),),
                    Notification.ERROR, msg_id="notify:not_selected"))
                widget.set_text(self.core.selected_item)
                return
            self.emit("update_item")
        elif widget == self.version:
            self.data_model.edit_value(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp > 0:
                self.data_model.edit_value(version_time=timestamp)
        elif widget == self.cluster_id:
            self.data_model.edit_value(cluster_id=widget.get_text())
        elif widget == self.operator:
            self.data_model.edit_value(operator=ENUM.OPERATOR[widget.get_active()][0])
        elif widget == self.abstract:
            self.data_model.edit_value(abstract=widget.get_active())
        elif widget == self.prohibit_changes:
            self.data_model.edit_value(prohibit_changes=widget.get_active())
        elif widget == self.interactive:
            self.data_model.edit_value(interactive=widget.get_active())
        else: 
            logger.error("Change: not supported object in \"%s\"" % (widget,))
            return

    def __block_signals(self):

        self.operator.handler_block_by_func(self.__change)
        self.interactive.handler_block_by_func(self.__change)
        self.version.handler_block_by_func(self.__change)
        self.version_time.handler_block_by_func(self.__change)
        self.vid.handler_block_by_func(self.__change)
        self.cluster_id.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.operator.handler_unblock_by_func(self.__change)
        self.interactive.handler_unblock_by_func(self.__change)
        self.version.handler_unblock_by_func(self.__change)
        self.version_time.handler_unblock_by_func(self.__change)
        self.cluster_id.handler_unblock_by_func(self.__change)

    def __clear(self):
        self.__block_signals()
        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.statuses.clear()
        self.questions.clear()
        self.values_values.clear()
        self.__unblock_signals()

    def __update(self):

        self.__block_signals()
        details = self.data_model.get_item_details(self.core.selected_item)

        self.values.set_sensitive(details != None)

        if details:

            """It depends on value type what details should
            be filled and sensitive to user actions"""
            # TODO

            self.vid.set_text(details["id"] or "")
            self.version.set_text(details["version"] or "")
            self.version_time.set_text("" if details["version_time"] <= 0 else str(datetime.date.fromtimestamp(details["version_time"])))
            self.cluster_id.set_text(details["cluster_id"] or "")
            self.vtype.set_text(ENUM.TYPE.map(details["vtype"])[1])
            self.abstract.set_active(details["abstract"])
            self.prohibit_changes.set_active(details["prohibit_changes"])
            self.interactive.set_active(details["interactive"])
            self.operator.set_active(ENUM.OPERATOR.pos(details["oper"]))
            self.titles.fill()
            self.descriptions.fill()
            self.warnings.fill()
            self.statuses.fill()
            self.questions.fill()
            self.values_values.fill()
        self.__unblock_signals()

            
class EditValuesValues(scap_workbench.core.abstract.ListEditor):

    COLUMN_SELECTOR     = 0
    COLUMN_VALUE        = 1
    COLUMN_DEFAULT      = 2
    COLUMN_LOWER_BOUND  = 3
    COLUMN_UPPER_BOUND  = 4
    COLUMN_MUST_MATCH   = 5
    COLUMN_MATCH        = 6
    COLUMN_OBJ          = 7
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        super(EditValuesValues, self).__init__(id, core, widget=widget, model=gtk.ListStore(str, str, str, str, str, bool, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Selector", gtk.CellRendererText(), text=self.COLUMN_SELECTOR))
        self.widget.append_column(gtk.TreeViewColumn("Value", gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.widget.append_column(gtk.TreeViewColumn("Default", gtk.CellRendererText(), text=self.COLUMN_DEFAULT))
        self.widget.append_column(gtk.TreeViewColumn("Lower bound", gtk.CellRendererText(), text=self.COLUMN_LOWER_BOUND))
        self.widget.append_column(gtk.TreeViewColumn("Upper bound", gtk.CellRendererText(), text=self.COLUMN_UPPER_BOUND))
        self.widget.append_column(gtk.TreeViewColumn("Must match", gtk.CellRendererText(), text=self.COLUMN_MUST_MATCH))
        self.widget.append_column(gtk.TreeViewColumn("Match", gtk.CellRendererText(), text=self.COLUMN_MATCH))

    def __do(self, widget=None):
        """
        """
        # Check input data
        (model, iter) = self.get_selection().get_selected()
        item = None
        if iter:
            item = model[iter][self.COLUMN_OBJ]

        for inst in model:
            if self.selector.get_text() == inst[0] and model[iter][self.COLUMN_SELECTOR] != self.selector.get_text():
                self.core.notify("Selector \"%s\" is already used !" % (inst[0],),
                        Notification.ERROR, self.info_box, msg_id="dialog:add_value")
                self.selector.grab_focus()
                self.selector.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
                return
        self.selector.modify_base(gtk.STATE_NORMAL, self.__entry_style)
        
        if self.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN:
            retval = self.data_model.edit_value_of_value(self.operation, item, self.selector.get_text(),
                    self.value_bool.get_active(), self.default_bool.get_active(),
                    self.match.get_text(), None, None, self.must_match.get_active())
        if self.type == openscap.OSCAP.XCCDF_TYPE_NUMBER:
            retval = self.data_model.edit_value_of_value(self.operation, item, self.selector.get_text(),
                    self.value.get_text(), self.default.get_text(), self.match.get_text(), self.upper_bound.get_text(),
                    self.lower_bound.get_value_as_int(), self.must_match.get_value_as_int())
        else:
            retval = self.data_model.edit_value_of_value(self.operation, item, self.selector.get_text(),
                    self.value.get_text(), self.default.get_text(), self.match.get_text(), None,
                    None, self.must_match.get_active())
        # TODO if not retval
        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:edit_value")
        self.info_box = builder.get_object("dialog:edit_value:info_box")
        self.selector = builder.get_object("dialog:edit_value:selector")
        self.value = builder.get_object("dialog:edit_value:value")
        self.value_bool = builder.get_object("dialog:edit_value:value:bool")
        self.default = builder.get_object("dialog:edit_value:default")
        self.default_bool = builder.get_object("dialog:edit_value:default:bool")
        self.match = builder.get_object("dialog:edit_value:match")
        self.upper_bound = builder.get_object("dialog:edit_value:upper_bound")
        self.lower_bound = builder.get_object("dialog:edit_value:lower_bound")
        self.must_match = builder.get_object("dialog:edit_value:must_match")
        self.choices = builder.get_object("dialog:edit_value:choices")
        builder.get_object("dialog:edit_value:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_value:btn_ok").connect("clicked", self.__do)

        self.__entry_style = self.selector.get_style().base[gtk.STATE_NORMAL]

        # Upper and lower bound should be disabled if value is not a number
        item = self.data_model.get_item_details(self.core.selected_item)
        self.type = item["vtype"]
        if self.type != openscap.OSCAP.XCCDF_TYPE_NUMBER:
            self.upper_bound.set_sensitive(False)
            self.lower_bound.set_sensitive(False)

        # Different widgets for different type boolean or other
        boolean = (self.type == openscap.OSCAP.XCCDF_TYPE_BOOLEAN)
        self.value.set_property('visible', not boolean)
        self.default.set_property('visible', not boolean)
        self.value_bool.set_property('visible', boolean)
        self.default_bool.set_property('visible', boolean)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.selector.set_text(model[iter][self.COLUMN_SELECTOR] or "")
                self.value.set_text(model[iter][self.COLUMN_VALUE] or "")
                self.default.set_text(model[iter][self.COLUMN_DEFAULT] or "")
                self.match.set_text(model[iter][self.COLUMN_MATCH] or "")
                self.upper_bound.set_text(model[iter][self.COLUMN_UPPER_BOUND] or "")
                self.lower_bound.set_text(model[iter][self.COLUMN_LOWER_BOUND] or "")
                self.must_match.set_active(model[iter][self.COLUMN_MUST_MATCH])
                for choice in model[iter][self.COLUMN_OBJ].choices:
                    self.choices.get_model().append([choice])
        elif operation == self.data_model.CMD_OPER_DEL:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to delete",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else: 
                iter = self.dialogDel(self.core.main_window, self.get_selection())
                if iter != None:
                    self.__do()
                return
        else: 
            logger.error("Unknown operation for values dialog: \"%s\"" % (operation,))
            return

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def fill(self):

        self.clear()
        for instance in self.data_model.get_value_instances() or []:
            self.append([instance["selector"], 
                         instance["value"], 
                         instance["defval"], 
                         instance["lower_bound"], 
                         instance["upper_bound"], 
                         instance["must_match"], 
                         instance["match"], 
                         instance["item"]])

class AddProfileDialog(EventObject):

    def __init__(self, core, data_model, cb):
        super(AddProfileDialog, self).__init__(core)
        
        self.data_model = data_model
        self.__update = cb
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.window = builder.get_object("dialog:profile_add")

        builder.get_object("profile_add:btn_ok").connect("clicked", self.__cb_do)
        builder.get_object("profile_add:btn_cancel").connect("clicked", self.__delete_event)
        self.pid = builder.get_object("profile_add:entry_id")
        self.title = builder.get_object("profile_add:entry_title")
        self.info_box = builder.get_object("profile_add:info_box")

        self.lang = builder.get_object("profile_add:entry_lang")
        self.lang.set_text(self.core.selected_lang or "")

        self.__entry_style = self.pid.get_style().base[gtk.STATE_NORMAL]
        self.show()

    def __cb_do(self, widget):

        if len(self.pid.get_text()) == 0: 
            self.core.notify("Can't add profile with no ID !",
                    Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
            return
        profiles = self.data_model.get_profiles()
        for profile in profiles:
            if profile.id == self.pid.get_text():
                self.core.notify("Profile \"%s\" already exists." % (self.pid.get_text(),),
                        Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
                self.pid.grab_focus()
                self.pid.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
                return
        self.pid.modify_base(gtk.STATE_NORMAL, self.__entry_style)
        if len(self.title.get_text()) == 0: 
            self.core.notify("Please add title for this profile.",
                    Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
            self.title.grab_focus()
            self.title.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        self.title.modify_base(gtk.STATE_NORMAL, self.__entry_style)

        self.data_model.add(id=self.pid.get_text(), lang=self.lang.get_text(), title=self.title.get_text())
        self.core.selected_profile = self.pid.get_text()
        self.window.destroy()
        self.__update(force=True)

    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()
        

class AddItem(EventObject):
    
    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2
    
    def __init__(self, core, data_model, list_item):
        super(AddItem, self).__init__(core)
        
        self.data_model = data_model
        self.list_item = list_item
        self.view = list_item.get_TreeView()
        
    def dialog(self):

        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.window = builder.get_object("dialog:add_item")
        self.window.connect("delete-event", self.__delete_event)
        
        btn_ok = builder.get_object("dialog:add_item:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("dialog:add_item:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)

        self.itype = builder.get_object("dialog:add_item:type")
        self.itype.connect("changed", self.__cb_changed_type)
        self.vtype_lbl = builder.get_object("dialog:add_item:value_type:lbl")
        self.vtype = builder.get_object("dialog:add_item:value_type")
        self.iid = builder.get_object("dialog:add_item:id")
        self.lang = builder.get_object("dialog:add_item:lang")
        self.lang.set_text(self.core.selected_lang)
        self.lang.set_sensitive(False)
        self.title = builder.get_object("dialog:add_item:title")
        self.relation = builder.get_object("dialog:add_item:relation")
        self.relation.connect("changed", self.__cb_changed_relation)
        self.info_box = builder.get_object("dialog:add_item:info_box")

        self.__entry_style = self.iid.get_style().base[gtk.STATE_NORMAL]

        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __cb_changed_relation(self, widget):

        self.core.notify_destroy("notify:relation")
        (model, iter) = self.view.get_selection().get_selected()
        if not iter:
            if widget.get_active() in [self.data_model.RELATION_PARENT, self.data_model.RELATION_SIBLING]:
                self.core.notify("Item can't be a parent or sibling of benchmark !",
                        Notification.ERROR, self.info_box, msg_id="notify:relation")
                widget.grab_focus()
                return False
        else:
            self.core.notify_destroy("dialog:add_item")
            if model[iter][self.data_model.COLUMN_TYPE] in ["value", "rule"] and widget.get_active() == self.data_model.RELATION_CHILD:
                self.core.notify("Item types VALUE and RULE can't be a parent !",
                        Notification.ERROR, self.info_box, msg_id="notify:relation")
                widget.grab_focus()
                return False

        return True

    def __cb_changed_type(self, widget):

        self.core.notify_destroy("dialog:add_item")
        self.vtype_lbl.set_property("visible", widget.get_active() == self.data_model.TYPE_VALUE)
        self.vtype.set_property('visible', widget.get_active() == self.data_model.TYPE_VALUE)

    def __cb_do(self, widget):

        self.core.notify_destroy("dialog:add_item")
        tagOK = True
        itype = self.itype.get_active()
        vtype = self.vtype.get_active()
        relation = self.relation.get_active()
        if not self.__cb_changed_relation(self.relation):
            return

        if itype == -1:
            self.core.notify("Relation has to be chosen",
                    Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.itype.grab_focus()
            return

        if itype == self.data_model.TYPE_VALUE:
            if vtype == -1:
                self.core.notify("Type of value has to be choosen",
                        Notification.ERROR, self.info_box, msg_id="dialog:add_item")
                self.vtype.grab_focus()
                return

        if relation == -1:
            self.core.notify("Relation has to be chosen",
                    Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.relation.grab_focus()
            return

        if self.iid.get_text() == "":
            self.core.notify("The ID of item is mandatory !",
                    Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.iid.grab_focus()
            self.iid.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        elif self.data_model.get_item_details(self.iid.get_text()):
            self.core.notify("ID already exists",
                    Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.iid.grab_focus()
            self.iid.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        else: 
            self.iid.modify_base(gtk.STATE_NORMAL, self.__entry_style)

        if self.title.get_text() == "":
            self.core.notify("The title of item is mandatory !",
                    Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.title.grab_focus()
            self.title.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        else: 
            self.title.modify_base(gtk.STATE_NORMAL, self.__entry_style)

        if relation == self.data_model.RELATION_PARENT:
            self.core.notify("Relation PARENT is not implemented yet",
                    Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.relation.grab_focus()
            return

        item = {"id": self.iid.get_text(),
                "lang": self.lang.get_text(),
                "title": self.title.get_text()}
        retval = self.data_model.add_item(item, itype, relation, vtype)
        if retval: self.list_item.emit("update") # TODO: HACK
        self.window.destroy()

    def __delete_event(self, widget, event=None):
        self.core.notify_destroy("dialog:add_item")
        self.window.destroy()

class EditSelectIdDialogWindow(object):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_SELECTED = 2
    
    def __init__(self, item, core, model_conflict, model_item, cb):
        self.core = core
        self.item = item
        self.cb = cb
        self.model_conflict = model_conflict
        self.model_item = model_item
        
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))

        self.window = builder.get_object("dialog:add_id")
        self.window.connect("delete-event", self.__delete_event)
        self.window.resize(800, 600)
        
        btn_ok = builder.get_object("add_id:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("add_id:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)

        btn_add = builder.get_object("add_id:btn_add")
        btn_add.connect("clicked", self.cb_btn_add)
        btn_remove = builder.get_object("add_id:btn_remove")
        btn_remove.connect("clicked", self.__cb_del_row)
        
        self.btn_search = builder.get_object("add_id:btn_search")
        self.btn_search.connect("clicked",self.__cb_search)
        self.btn_search_reset = builder.get_object("add_id:btn_search_reset")
        self.btn_search_reset.connect("clicked",self.__cb_search_reset)
        
        self.text_search_id = builder.get_object("add_id:text_search_id")
        self.text_search_title = builder.get_object("add_id:text_search_title")
        
        #treeView for search item for select to add
        self.model_search = gtk.TreeStore(str, str, bool)
        self.tw_search = builder.get_object("add_id:tw_search")
        
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ID Item", cell, text=self.COLUMN_ID)
        column.set_resizable(True)
        self.tw_search.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", cell, text=self.COLUMN_TITLE)
        column.set_expand(True)
        column.set_resizable(True)
        self.tw_search.append_column(column)
        
        self.tw_search.set_model(self.model_search)
        
        #treeView for item, which will be add
        self.model_to_add = gtk.ListStore(str, str)
        self.tw_add = builder.get_object("add_id:tw_add")
        
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ID Item", cell, text=self.COLUMN_ID)
        column.set_resizable(True)
        self.tw_add.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", cell, text=self.COLUMN_TITLE)
        column.set_expand(True)
        column.set_resizable(True)
        self.tw_add.append_column(column)

        self.tw_add.set_model(self.model_to_add)
        
        menu = gtk.Menu()
        menu_item = gtk.MenuItem("Remove from add")
        menu_item.show()
        menu.append(menu_item)
        menu_item.connect("activate", self.__cb_del_row)
        self.tw_add.connect ("button_press_event",self.cb_popupMenu_to_add, menu)
        self.tw_add.connect("key-press-event", self.__cb_del_row1,)

        menu_search = gtk.Menu()
        menu_item = gtk.MenuItem("Copy to add")
        menu_item.show()
        menu_search.append(menu_item)
        menu_item.connect("activate", self.cb_btn_add)
        self.tw_search.connect ("button_press_event",self.cb_popupMenu_to_add, menu_search)

        
        self.model_search.clear()
        self.copy_model(model_item, model_item.get_iter_first(), self.model_search, None)
        self.show()

    def __cb_do(self, widget):
        
        iter_add =  self.model_to_add.get_iter_first()
        while iter_add:
            #add row, which not added before
            exist = False
            iter = self.model_conflict.get_iter_first()
            id_add = self.model_to_add.get_value(iter_add,self.COLUMN_ID)
            while iter:
                if id_add == self.model_conflict.get_value(iter,self.COLUMN_ID):
                    exist = True
                iter = self.model_conflict.iter_next(iter)
            if not exist:
                self.cb(self.item, id_add, True)
                self.model_conflict.append([id_add])
            iter_add = self.model_to_add.iter_next(iter_add)
        self.window.destroy()
            
    def __cb_del_row1(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Delete":
            selection = self.tw_add.get_selection( )
            if selection != None: 
                (model, iter) = selection.get_selected( )
                if  iter != None:
                    model.remove(iter)

                        
    def __cb_del_row(self, widget):
        selection = self.tw_add.get_selection()
        (model, iter) = selection.get_selected()
        if iter != None:
            model.remove(iter)
    
    def cb_popupMenu_to_add (self, treeview, event, menu):
        if event.button == 3:
            time = event.time
            menu.popup(None,None,None,event.button,event.time)
            
    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()
            
    def __cb_toggled(self, cell, path ):
        
        self.model_search[path][self.COLUMN_SELECTED] = not self.model_search[path][self.COLUMN_SELECTED]
        id_item = self.model_search[path][self.COLUMN_ID]
        if not self.model_search[path][self.COLUMN_SELECTED]:
            # remve from model to add
            iter = self.model_to_add.get_iter_first()
            while iter:
                if self.model_to_add.get_value(iter,self.COLUMN_ID) == id_item:
                    self.model_to_add.remove(iter)
                    break
                iter = self.model_to_add.iter_next(iter)
        else:
            # move from serch model to model for add, if not there
            iter = self.model_to_add.get_iter_first()
            while iter:
                if self.model_to_add.get_value(iter,self.COLUMN_ID) == id_item:
                    return
                iter = self.model_to_add.iter_next(iter)
            self.model_to_add.append([id_item,self.model_search[path][self.COLUMN_TITLE]])
        # change state check box

    def cb_btn_add(self, widget):
        selection = self.tw_search.get_selection( )
        if selection != None: 
            (model, iter_add) = selection.get_selected( )
            if  iter_add != None:
                id_item = self.model_search.get_value(iter_add, self.COLUMN_ID)
                iter = self.model_to_add.get_iter_first()
                while iter:
                    if self.model_to_add.get_value(iter,self.COLUMN_ID) == id_item:
                        return
                    iter = self.model_to_add.iter_next(iter)
                self.model_to_add.append([id_item,self.model_search.get_value(iter_add, self.COLUMN_TITLE)])
            
    def copy_model(self, model_item, iter, model_search, iter_parent):
        """
        copy_model to search model
        """
        while iter:
            row = []
            row.append(model_item.get_value(iter,0))
            row.append(model_item.get_value(iter,3))
            row.append(False)
            iter_self = model_search.append(iter_parent, row)
            self.copy_model(model_item, model_item.iter_children(iter), model_search, iter_self)
            iter = model_item.iter_next(iter)
        return
    
    def __cb_search(self, widget):
        self.model_search.clear()
        self.search(self.model_item, self.model_item.get_iter_first(), self.model_search, 
                                self.text_search_id.get_text(), self.text_search_title.get_text())

    def __cb_search_reset(self, widget):
        self.model_search.clear()
        self.copy_model(self.model_item, self.model_item.get_iter_first(), self.model_search, None)
                                
    def search(self, model_item, iter, model_search, id, title):
        """ 
        Filter data to list
        """
        while iter:
            if self.match_fiter(id, title,  model_item, iter):
                row = []
                row.append(model_item.get_value(iter,0))
                row.append(model_item.get_value(iter,3))
                row.append(False)
                iter_to = model_search.append(None, row)
            self.search(model_item, model_item.iter_children(iter), model_search, id, title)
            iter = model_item.iter_next(iter)
    
    
    def match_fiter(self, id, title,  model_item, iter):
        try:
            pattern = re.compile(id,re.IGNORECASE)
            res_id = pattern.search(model_item.get_value(iter,0)) 
            pattern = re.compile(title,re.IGNORECASE)
            res_title = pattern.search(model_item.get_value(iter,3)) 
            
            if res_id == None or res_title == None:
                return False
            return True
        except Exception as e:
            #self.core.notify("Can't filter items: %s" % (e,), 3)
            logger.exception("Can't filter items: %s" % (e))
            return False

class FindOvalDef(scap_workbench.core.abstract.Window, scap_workbench.core.abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1

    def __init__(self, core, id, data_model):

        self.data_model = data_model
        self.core = core
        scap_workbench.core.abstract.Window.__init__(self, id, core)
        # FIXME: We can't call the constructor of abstract.ListEditor here because it would register our id
        #        and instance again (Window's constructor has already done that)
        self.add_sender(id, "update")

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        (model, iter) = self.definitions.get_selection().get_selected()
        if not iter:
            self.core.notify("You have to choose the definition !",
                    Notification.ERROR, self.info_box, msg_id="notify:dialog_notify")
            return
        ret, err = self.data_model.set_item_content(name=model[iter][self.COLUMN_ID])
        self.emit("update")
        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, widget, href):
        """
        """
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:find_definition")
        self.info_box = builder.get_object("dialog:find_definition:info_box")
        self.definitions = builder.get_object("dialog:find_definition:definitions")
        self.search = builder.get_object("dialog:find_definition:search")
        self.search.connect("changed", self.search_treeview, self.definitions)
        builder.get_object("dialog:find_definition:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_definition:btn_ok").connect("clicked", self.__do)

        self.core.notify_destroy("notify:not_selected")
        self.definitions.append_column(gtk.TreeViewColumn("ID of Definition", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.definitions.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.definitions.set_model(gtk.ListStore(str, str))
        modelfilter = self.definitions.get_model().filter_new()
        modelfilter.set_visible_func(self.filter_listview, data=(self.search, (0,1)))
        self.definitions.set_model(modelfilter)

        definitions = self.data_model.get_oval_definitions(href)
        for definition in definitions: 
            self.definitions.get_model().get_model().append([definition.id, definition.title])

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show_all()


class FindItem(scap_workbench.core.abstract.Window, scap_workbench.core.abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1
    COLUMN_OBJ      = 2

    def __init__(self, core, id, data_model):

        self.data_model = data_model
        self.core = core
        scap_workbench.core.abstract.Window.__init__(self, id, core)
        # FIXME: We can't call the constructor of abstract.ListEditor here because it would register our id
        #        and instance again (Window's constructor has already done that)
        self.add_sender(id, "update")

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        (model, iter) = self.items.get_selection().get_selected()
        if not iter:
            self.core.notify("You have to chose the item !",
                    Notification.ERROR, self.info_box, msg_id="notify:dialog_notify")
            return
        retval = self.data_model.add_refine(model[iter][self.COLUMN_ID], model[iter][self.COLUMN_VALUE], model[iter][self.COLUMN_OBJ])
        if not retval:
            self.core.notify("Item already exists in selected profile.", Notification.ERROR, info_box=self.info_box, msg_id="notify:dialog_notify")
            return
        self.core.selected_item = model[iter][self.COLUMN_ID]
        self.emit("update")
        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def dialog(self, type):
        """
        """
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "dialogs.glade"))
        self.wdialog = builder.get_object("dialog:find_value")
        self.info_box = builder.get_object("dialog:find_value:info_box")
        self.items = builder.get_object("dialog:find_value:values")
        self.search = builder.get_object("dialog:find_value:search")
        self.search.connect("changed", self.search_treeview, self.items)
        builder.get_object("dialog:find_value:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:find_value:btn_ok").connect("clicked", self.__do)
        builder.get_object("dialog:find_value:export_name:box").set_property('visible', False)
        builder.get_object("dialog:find_value:export_name:separator").set_property('visible', False)

        self.core.notify_destroy("notify:not_selected")
        self.items.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.items.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))

        if type == "rule":
            items = self.data_model.get_all_item_ids()
        elif type == "value":
            items = [value.to_item() for value in self.data_model.get_all_values()]
        else:
            raise NotImplementedError("Type \"%s\" not supported!" % (type))

        self.items.set_model(gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        modelfilter = self.items.get_model().filter_new()
        modelfilter.set_visible_func(self.filter_listview, data=(self.search, (0,1)))
        self.items.set_model(modelfilter)

        refines = self.data_model.get_refine_ids(self.data_model.get_profile(self.core.selected_profile))
        for item in items:
            if item.id not in refines:
                title = self.data_model.get_title(item.title)
                self.items.get_model().get_model().append([item.id, title, item])

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

class Editor(scap_workbench.core.abstract.Window):
    """The central window of scap-workbench-editor
    """
    
    def __init__(self):
        scap_workbench.core.error.ErrorHandler.install_exception_hook()
        
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(scap_workbench.core.paths.glade_prefix, "editor.glade"))
        self.builder.connect_signals(self)
        scap_workbench.core.abstract.Window.__init__(self, "main:window", core.SWBCore(self.builder))

        logger = logging.getLogger(self.__class__.__name__)

        self.window = self.builder.get_object("main:window")
        self.core.main_window = self.window
        self.main_box = self.builder.get_object("main:box")

        # abstract the main menu
        # FIXME: Instantiating abstract class
        self.menu = scap_workbench.core.abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
        self.menu.add_item(MenuButtonEditXCCDF(self.builder, self.builder.get_object("main:toolbar:main"), self.core))
        self.menu.add_item(MenuButtonEditProfiles(self.builder, self.builder.get_object("main:toolbar:profiles"), self.core))
        self.menu.add_item(MenuButtonEditItems(self.builder, self.builder.get_object("main:toolbar:items"), self.core))

        self.window.show()
        self.builder.get_object("main:toolbar:main").set_active(True)

        self.core.get_item("gui:btn:menu:edit:XCCDF").update()
        if self.core.lib.loaded:
            self.core.get_item("gui:btn:menu:edit:profiles").set_sensitive(True)
            self.core.get_item("gui:btn:menu:edit:items").set_sensitive(True)

    def __cb_info_close(self, widget):
        self.core.info_box.hide()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        # since we are quitting gtk we can't be popping a dialog when exception happens anymore
        scap_workbench.core.error.ErrorHandler.uninstall_exception_hook()
 
        gtk.main_quit()
        return False

    def run(self):
        from scap_workbench.core import version
        
        gnome.init("SCAP Workbench Editor", version.as_string)
        gtk.main()

if __name__ == '__main__':
    editor = Editor()
    editor.start()
