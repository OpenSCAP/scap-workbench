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

""" Importing standard python libraries
"""
import gtk              # GTK library
import gobject          # gobject.TYPE_PYOBJECT
import time             # Time functions in calendar data ::EditStatus
import re               # Regular expressions 
import sre_constants    # For re.compile exception
import os               # os Path join/basename, ..
import threading        # Main window is running in thread
import gnome, gnome.ui  # Gnome icons in HTML editor
import tempfile         # Temporary file for XCCDF preview

""" Importing SCAP Workbench modules
"""
import abstract                 # All abstract classes
import logging                  # Logger for debug/info/error messages
import core                     # Initializing of core in main window
import commands                 # Module for handling openscap
import filter                   # Module for handling filters
from core import Notification   # core.Notification levels for reference
from events import EventObject  # abstract module EventObject
import htmltextview             # Alternative of webkit

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

try:
    # 
    from BeautifulSoup import BeautifulSoup
    HAS_BEUTIFUL_SOUP = True
except ImportError:
    HAS_BEUTIFUL_SOUP = False

""" Import OpenSCAP library as backend.
If anything goes wrong just end with exception"""
try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None
    raise ex


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
        self.core = core
        self.builder = builder
        self.data_model = data_model
        abstract.List.__init__(self, "gui:edit:profile_list", core, widget)
        
        """ Register signals that can be emited by this class.
        All signals are registered in EventObject (abstract class) and
        are emited by other objects to trigger the async event.
        """
        self.add_sender(id, "update")
        self.add_receiver("gui:btn:menu:edit:profiles", "update", self.__update)
        self.add_receiver("gui:btn:menu:edit:XCCDF", "load", self.__clear_update)
        self.add_receiver("gui:edit:xccdf:profiles:finditem", "update", self.__update)

        """ Set objects from Glade files and connect signals
        """
        # Build the Popup Menu
        self.builder.get_object("profile_list:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("profile_list:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("profile_list:popup"))

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.__cb_changed, self.get_TreeView())
        self.section_list = self.builder.get_object("edit:section_list")
        self.profilesList = self.builder.get_object("edit:tw_profiles:sw")
        self.search = self.builder.get_object("xccdf:profiles:search")
        self.search.connect("changed", self.__cb_search, self.get_TreeView())

        """ Set the model of the list to support search
        """
        self.__stop_search = False
        modelfilter = self.data_model.model.filter_new()
        modelfilter.set_visible_func(self.__filter_func)
        self.get_TreeView().set_model(modelfilter)

        self.get_TreeView().connect("key-press-event", self.__cb_key_press)

    def __cb_search(self, widget, treeview):
        self.core.notify_destroy("notify:profiles:filter")
        self.__stop_search = False
        treeview.get_model().refilter()
        self.__update(False)

    def __filter_func(self, model, iter, data=None):
        if self.__stop_search: return True
        columns = [0,1,4]
        text = self.search.get_text()
        subcmd = re.findall("^([a-z]*:)?(.*)$", text)[0]

        group = subcmd[0]
        text = subcmd[1]
        if len(group) == 0 and len(text) == 0: return True

        if group != "profile:" and model[iter][0] == "profile":
            return True
        if len(group) > 0 and group != "all:" and model[iter][0] != group[:-1]:
            return False
        try:
            pattern = re.compile(text, re.I)
        except sre_constants.error, err:
            self.core.notify("Regexp entry error: %s" % (err,), Notification.ERROR, msg_id="notify:profiles:filter")
            self.__stop_search = True
            return True

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
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_profile, self.get_TreeView(), 1))
        self.get_TreeView().get_model().foreach(self.set_selected_profile_item, (self.core.selected_profile, self.core.selected_item, self.get_TreeView(), 1))

        # List is updated, trigger all events connected to this signal
        self.emit("update")

    def __cb_changed(self, widget, treeView):
        """ Changed the selected item of the list
        """
        selection = treeView.get_selection( )
        if selection != None: 
            (filter_model, filter_iter) = selection.get_selected( )
            if not filter_iter: 
                self.selected = None
                return
            model = filter_model.get_model()
            iter = filter_model.convert_iter_to_child_iter(filter_iter)

            if model.get_value(iter, 0) == "profile":
                # If a profile is selected, change the global value of selected profile
                # and clear the local value of item (to evade possible conflicts in selections)
                self.core.selected_profile = model.get_value(iter, 2).id
                self.selected = model[iter]
            else:
                # If a refine item is selected, change the global value of selected item
                # and fill the local value of selected item so details can be filled from it.
                self.core.selected_item = model.get_value(iter, 1)
                self.selected = model[iter]

        # Selection has changed, trigger all events connected to this signal
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
            if not iter: raise Exception("Iter validation failed")

            filter_iter_next = filter_model.iter_next(filter_iter)
            if filter_iter_next:
                iter_next = filter_model.convert_iter_to_child_iter(filter_iter_next)
            else: iter_next = None
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
        else: self.notifications.append(self.core.notify("Please select at least one item to delete",
                Notification.ERROR, msg_id="notify:edit:delete_item"))

    def __cb_item_add(self, widget=None):
        """ Add profile to the profile list (Item can 
        """
        AddProfileDialog(self.core, self.data_model, self.__update)


class ItemList(abstract.List):

    """ List of Rules, Groups and Values.

    This class represents TreeView in editor window which contains
    list of XCCDF Items as Rules, Groups and Values. Each Group contains
    its content.
    """

    def __init__(self, widget, core, builder=None, progress=None):
        """ Constructor of ProfileList.
        """
        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, None, True, no_checks=True)
        abstract.List.__init__(self, "gui:edit:item_list", core, widget)
        self.core = core
        self.loaded = False
        self.filter = filter
        self.builder = builder

        """ Register signals that can be emited by this class.
        All signals are registered in EventObject (abstract class) and
        are emited by other objects to trigger the async event.
        """
        self.add_sender(self.id, "update")
        self.add_receiver("gui:btn:menu:edit:items", "update", self.__update)
        self.add_receiver("gui:btn:menu:edit:XCCDF", "load", self.__clear_update)


        """ Set objects from Glade files and connect signals
        """
        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.section_list = self.builder.get_object("edit:section_list")
        self.itemsList = self.builder.get_object("edit:tw_items:sw")
        self.with_values = self.builder.get_object("edit:list:popup:show_values")
        self.with_values.connect("toggled", self.__update)
        # Popup Menu
        self.builder.get_object("edit:list:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("edit:list:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("edit:list:popup"))

        self.add_dialog = AddItem(self.core, self.data_model, self) # TODO
        self.get_TreeView().connect("key-press-event", self.__cb_key_press)

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
            self.notifications.append(self.core.notify("Delete operation is not supported yet.",
                Notification.INFORMATION, msg_id="notify:edit:delete_item"))

    def __cb_item_remove(self, widget=None):
        """ Remove selected item from the list and model.
        """
        selection = self.get_TreeView().get_selection()
        (model,iter) = selection.get_selected()
        if iter:
            self.data_model.remove_item(model[iter][1])
            model.remove(iter)
        else: raise AttributeError, "Removing non-selected item or nothing selected."

    def __cb_item_add(self, widget=None):
        """ Add item to the list and model
        """
        self.add_dialog.dialog()

    def __cb_item_changed(self, widget, treeView):
        """ Make all changes in application in separate threads: workaround for annoying
        blinking when redrawing treeView """
        details = self.data_model.get_item_details(self.core.selected_item)
        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: self.core.selected_item = model.get_value(iter, commands.DHItemsTree.COLUMN_ID)
            else: self.core.selected_item = None

        # Selection has changed, trigger all events connected to this signal
        self.emit("update")
        treeView.columns_autosize()


class MenuButtonEditXCCDF(abstract.MenuButton):

    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit:XCCDF", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DHXccdf(core)
        
        #draw body
        self.body = self.builder.get_object("edit_xccdf:box")
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
        self.tv_references = abstract.ListEditor("gui:edit:xccdf:references", self.core, widget=self.builder.get_object("edit:xccdf:references"), model=gtk.ListStore(str, str))
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
        self.btn_validate = self.builder.get_object("edit:sub:validate")
        self.btn_import = self.builder.get_object("edit:sub:import")
        self.btn_export = self.builder.get_object("edit:sub:export")
        self.btn_new.connect("clicked", self.__cb_new)
        self.btn_close.connect("clicked", self.__cb_close)
        self.btn_validate.connect("clicked", self.__cb_validate)
        self.btn_import.connect("clicked", self.__cb_import)
        self.btn_export.connect("clicked", self.__cb_export)

    def __cb_new(self, widget):
        """ Create new XCCDF Benchmark
        """
        if not self.core.init(None):return

        # Update neccessary attributes of Benchmark
        self.data_model.update(id="New_SCAP_Benchmark", version="0", lang="en")
        self.core.selected_lang = "en"
        self.data_model.edit_status(self.data_model.CMD_OPER_ADD)
        try:
            self.__update()
        except KeyError: pass

        self.emit("load")

    def __cb_import(self, widget):
        file = self.data_model.file_browse("Load XCCDF file", action=gtk.FILE_CHOOSER_ACTION_OPEN)
        if file != "":
            self.__cb_close(None)
            logger.debug("Loading XCCDF file %s", file)
            if not self.core.init(file): return
            self.emit("load")

            try:
                self.__update()
            except KeyError: pass

    def __cb_preview(self, widget):
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        preview_dialog = builder.get_object("dialog:description_preview")
        preview_scw = builder.get_object("dialog:description_preview:scw")
        builder.get_object("dialog:description_preview:btn_ok").connect("clicked", lambda w: preview_dialog.destroy())
        # Get the background color from window and destroy it

        desc = self.__model.get_value(iter, self.COLUMN_TEXT) or ""
        desc = desc.replace("xhtml:","")
        desc = desc.replace("xmlns:", "")
        desc = self.data_model.substitute(desc)
        if desc == "": desc = "No description"
        desc = "<body><div>"+desc+"</div></body>"

        if not HAS_WEBKIT:
            description = webkit.WebView()
            preview_scw.add(description)
            description.load_html_string(desc, "file:///")
            description.set_zoom_level(0.75)
        else:
            description = htmltextview.HtmlTextView()
            description.set_wrap_mode(gtk.WRAP_WORD)
            description.modify_base(gtk.STATE_NORMAL, bg_color)
            preview_scw.add(description)
            try:
                description.display_html(desc)
            except Exception as err:
                logger.error("Exception: %s", err)


        preview_dialog.set_transient_for(self.core.main_window)
        preview_dialog.show_all()
        

    def __cb_validate(self, widget):
        validate = self.data_model.validate()
        message = [ "Document is not valid !",
                    "Document is valid.",
                    "Validation process failed, check for error in log file.",
                    "File not saved, use export first."][validate]
        lvl = [ Notification.WARNING,
                Notification.SUCCESS,
                Notification.ERROR,
                Notification.INFORMATION][validate]
        self.notifications.append(self.core.notify(message, lvl, msg_id="notify:xccdf:validate"))

    def __cb_export(self, widget):
        self.core.notify_destroy("notify:xccdf:validate")
        ExportDialog(self.core, self.data_model)

    def __menu_sensitive(self, active):
        self.btn_close.set_sensitive(active)
        self.btn_validate.set_sensitive(active)
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
            # Replace all white spaces with '_' (space are not allowed in ID)
            text = re.sub("[\t ]+" , "_", widget.get_text())
            self.data_model.update(id=text)
        elif object == "version":
            self.data_model.update(version=widget.get_text())
        elif object == "resolved":
            self.data_model.update(resolved=(widget.get_active() == 1))
        elif object == "status":
            self.data_model.update(status=abstract.ENUM_STATUS_CURRENT[widget.get_active()][0])
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
        abstract.MenuButton.activate(self, active)
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

class ExportDialog(abstract.Window):

    def __init__(self, core, data_model):

        self.core = core
        self.data_model = data_model
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.wdialog = builder.get_object("dialog:export")
        self.info_box = builder.get_object("dialog:export:info_box")
        self.filechooser = builder.get_object("dialog:export:filechooser")
        self.filechooser.set_filename(self.core.lib.xccdf)
        self.filechooser.connect("confirm-overwrite", self.__confirm_overwrite)
        self.show = builder.get_object("dialog:export:show")
        self.profile = builder.get_object("dialog:export:profile")
        self.profile.connect("clicked", self.__cb_profile_clicked)
        self.profiles_cb = builder.get_object("dialog:export:profiles:cb")
        builder.get_object("dialog:export:btn_ok").connect("clicked", self.__do)
        builder.get_object("dialog:export:btn_cancel").connect("clicked", self.__dialog_destroy)

        self.file_rb = builder.get_object("dialog:export:file:rb")
        self.file_rb.connect("toggled", self.__cb_switch)
        self.guide_rb = builder.get_object("dialog:export:guide:rb")
        self.guide_rb.connect("toggled", self.__cb_switch)
        self.file_box = builder.get_object("dialog:export:file:box")
        self.guide_box = builder.get_object("dialog:export:guide:box")

        profiles_model = commands.DHProfiles(core)
        profiles_model.model = self.profiles_cb.get_model()
        profiles_model.fill(no_default=True)

        self.__paused_export = False
        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def __cb_profile_clicked(self, widget):
        self.profiles_cb.set_sensitive(widget.get_active())

    def __cb_switch(self, widget):
        self.guide_box.set_sensitive(widget == self.guide_rb)

    def __confirm_overwrite(self, widget, more=None):
        print widget, more

    def __do(self, widget=None):
        export_file = self.filechooser.get_filename()
        if export_file == None:
            self.core.notify("Choose a file to save to first.",
                Notification.INFORMATION, info_box=self.info_box, msg_id="dialog:export:notify")
            return
        if not self.__paused_export and export_file == self.core.lib.xccdf and self.guide_rb.get_active():
            # We are trying to export guide to the XCCDF file (common mistake)
            self.core.notify("You are trying to overwrite loaded XCCDF Benchmark by XCCDF Guide !\nPress OK again to proceed.", 
                    Notification.WARNING, info_box=self.info_box, msg_id="notify:xccdf:export:dialog")
            self.__paused_export = True
            return

        if self.file_rb.get_active():
            # we are exporting to file
            file_name = self.data_model.export(export_file)
            self.core.notify("Benchmark has been exported to \"%s\"" % (file_name,),
                    Notification.SUCCESS, msg_id="notify:xccdf:export")
            self.core.lib.xccdf = file_name
        else:
            # we are exporting as guide
            if not self.core.lib.xccdf:
                self.core.notify("Benchmark is not exported. Export benchmark first !",
                        Notification.INFORMATION, info_box=self.info_box, msg_id="notify:xccdf:export")
                return

            profile = None
            if self.profiles_cb.get_active() != -1:
                profile = self.profiles_cb.get_model()[self.profiles_cb.get_active()][0]
            self.data_model.export_guide(export_file, profile, not self.profile.get_active())
            self.core.notify("The guide has been exported to \"%s\"" % (export_file,), Notification.SUCCESS, msg_id="notify:xccdf:export")

            if self.show.get_active() == 1:
                browser_val = self.data_model.open_webbrowser(export_file)
            elif self.show.get_active() == 2:
                pass

        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

        
class MenuButtonEditProfiles(abstract.MenuButton, abstract.Func):

    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit:profiles", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DHProfiles(self.core)
        self.__item_finder = FindItem(self.core, "gui:edit:xccdf:profiles:finditem", self.data_model)

        #draw body
        self.body = self.builder.get_object("edit:xccdf:profiles:box")
        self.profiles = self.builder.get_object("edit:xccdf:profiles")
        self.list_profile = ProfileList(self.profiles, self.core, self.data_model, builder, None, None)

        # set signals
        self.add_receiver("gui:edit:profile_list", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:profile:titles", "update", self.__update_item)
        self.add_sender(self.id, "update")
        
        self.__refines_box = self.builder.get_object("xccdf:refines:box")
        self.__profile_box = self.builder.get_object("edit:xccdf:profiles:details")

        # PROFILES
        self.info_box_lbl = self.builder.get_object("edit:xccdf:profile:info_box:lbl")
        self.pid = self.builder.get_object("edit:xccdf:profile:id")
        self.pid.connect("focus-out-event", self.__change)
        self.pid.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("edit:xccdf:profile:version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.extends = self.builder.get_object("edit:xccdf:profile:extends")
        self.abstract = self.builder.get_object("edit:xccdf:profile:abstract")
        self.abstract.connect("toggled", self.__change)
        self.prohibit_changes = self.builder.get_object("edit:xccdf:profile:prohibit_changes")
        self.prohibit_changes.connect("toggled", self.__change)

        # -- TITLE --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:profile:titles", builder.get_object("edit:xccdf:profile:titles"), self.data_model)
        builder.get_object("edit:xccdf:profile:titles:btn_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:profile:titles:btn_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:profile:titles:btn_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTION --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:profile:descriptions", builder.get_object("edit:xccdf:profile:descriptions"), self.data_model)
        self.builder.get_object("edit:xccdf:profile:descriptions:btn_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:profile:descriptions:btn_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:profile:descriptions:btn_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        self.builder.get_object("edit:xccdf:profile:descriptions:btn_preview").connect("clicked", self.descriptions.preview)

        # -- STATUS --
        self.statuses = EditStatus(self.core, "gui:edit:xccdf:profile:statuses", builder.get_object("edit:xccdf:profile:statuses"), self.data_model)
        self.builder.get_object("edit:xccdf:profile:statuses:btn_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        self.builder.get_object("edit:xccdf:profile:statuses:btn_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        self.builder.get_object("edit:xccdf:profile:statuses:btn_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

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
        self.refines_idref_find = self.builder.get_object("xccdf:refines:idref:find")
        self.refines_idref_find.set_sensitive(False)# TODO
        self.refines_idref.set_sensitive(False)# TODO

        self.refines_operator.set_model(abstract.Enum_type.combo_model_operator_number)
        self.refines_severity.set_model(abstract.Enum_type.combo_model_level)
        # -------------

        self.builder.get_object("profile_list:popup:sub:select").connect("activate", self.__find_item, "rule")
        self.builder.get_object("profile_list:popup:sub:set-value").connect("activate", self.__find_item, "value")

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        item = self.list_profile.selected
        if not item: return
        if widget == self.pid:
            self.data_model.update(id=widget.get_text())
        elif widget == self.version:
            self.data_model.update(version=widget.get_text())
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
            self.data_model.update_refines(item[0], item[1], item[2], operator=abstract.ENUM_OPERATOR[widget.get_active()][0])
        elif widget == self.refines_severity:
            self.data_model.update_refines(item[0], item[1], item[2], severity=abstract.ENUM_LEVEL[widget.get_active()][0])
        else: 
            logger.error("Change \"%s\" not supported object in \"%s\"" % (object, widget))
            return
        self.__update_item()

    def __find_item(self, widget, type):
        if not self.core.selected_profile:
            self.notifications.append(self.core.notify("Please select profile first.",
                Notification.INFORMATION, msg_id="notify:edit:find_item"))
            return

        self.__item_finder.dialog(type)

    def __block_signals(self):
        self.pid.handler_block_by_func(self.__change)
        self.version.handler_block_by_func(self.__change)
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

    def __update(self):

        if not self.core.selected_profile or not self.list_profile.selected: return
        self.__block_signals()
        self.__clear()
        self.__profile_box.set_property('visible', self.list_profile.selected[0] == "profile")
        self.__refines_box.set_property('visible', self.list_profile.selected[0] != "profile")

        if self.list_profile.selected[0] == "profile":
            details = self.data_model.get_profile_details(self.core.selected_profile)
            if not details:
                self.__unblock_signals()
                return

            self.pid.set_text(details["id"] or "")
            self.version.set_text(details["version"] or "")
            #self.profile_extend.set_text(str(details["extends"] or ""))
            self.abstract.set_active(details["abstract"])
            self.prohibit_changes.set_active(details["prohibit_changes"])
            self.titles.fill()
            self.descriptions.fill()
            self.statuses.fill()
        else:
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
                        self.refines_severity.set_active(abstract.ENUM_LEVEL.pos(rule.severity))
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
                        self.refines_operator.set_active(abstract.ENUM_OPERATOR.pos(value.oper))
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

            
class MenuButtonEditItems(abstract.MenuButton, abstract.Func):

    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit:items", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DHEditItems(self.core)
        self.item = None
        self.func = abstract.Func()
        self.current_page = 0

        #draw body
        self.body = self.builder.get_object("edit_item:box")
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

        # -------------

        """Get widgets from Glade: Part main.glade in edit
        """
        self.conflicts = EditConflicts(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.requires = EditRequires(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.ident = EditIdent(self.core, self.builder)
        self.values = EditValues(self.core, "gui:edit:xccdf:values", self.builder)
        self.fixtext = EditFixtext(self.core, self.builder)
        self.fix = EditFix(self.core, self.builder)
        
        self.severity = self.builder.get_object("edit:operations:combo_severity")
        self.severity.set_model(abstract.Enum_type.combo_model_level)
        self.severity.connect( "changed", self.__change)
        self.impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.impact_metric.connect("focus-out-event", self.cb_control_impact_metrix)
        self.check = self.builder.get_object("edit:operations:lv_check")

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:evaluation:content_ref:dialog", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:values:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:items:titles", "update", self.__update_item)

    def __cb_find_oval_definition(self, widget):

        model = self.href.get_model()
        if self.href.get_active() == -1:
            self.notifications.append(self.core.notify("No definition file available", Notification.WARNING, msg_id="notify:definition_available"))
            return
        self.content_ref_dialog.dialog(None, model[self.href.get_active()][0])

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        if widget == self.version:
            self.data_model.update(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp:
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
        else: 
            logger.error("Change \"%s\" not supported object in \"%s\"" % (object, widget))
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

    def cb_control_impact_metrix(self, widget, event):
        text = widget.get_text()
        if text != "" and self.controlImpactMetric(text):
            self.data_model.DHEditImpactMetrix(self.item, text)

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
        self.fix.fill(None)
        self.fixtext.fill(None)
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
        #self.version_time.set_text(str(datetime.date.fromtimestamp(details["version_time"]) or "")) TODO: Add version_time
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

        if details["type"] == openscap.OSCAP.XCCDF_RULE: # Item is Rule
            self.ident.set_sensitive(True)
            self.item_values_main.set_sensitive(True)
            self.operations.set_sensitive(True)

            self.severity.set_active(abstract.ENUM_LEVEL.pos(details["severity"]) or -1)
            self.impact_metric.set_text(details["imapct_metric"] or "")
            self.fixtext.fill(details["item"])
            self.fix.fill(details["item"])
            self.ident.fill(details["item"])
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
            # clean data only for rule and set insensitive
            self.ident.set_sensitive(False)
            self.item_values_main.set_sensitive(False)
            self.operations.set_sensitive(False)

            self.severity.set_active(-1)
            self.impact_metric.set_text("")
            self.fixtext.fill(None)
            self.fix.fill(None)
            self.ident.fill(None)

        self.__unblock_signals()
                
            
class EditConflicts(commands.DHEditItems, abstract.ControlEditWindow):
    
    COLUMN_ID = 0
    
    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_conflict")
        model = gtk.ListStore(str)
        lv.set_model(model)
        
        abstract.ControlEditWindow.__init__(self, core, lv, None)
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

class EditRequires(commands.DHEditItems,abstract.ControlEditWindow):
    
    COLUMN_ID = 0
    
    def __init__(self, core, builder, model_item):
        self.model_item = model_item
        lv = builder.get_object("edit:dependencies:lv_requires")
        model = gtk.ListStore(str)
        lv.set_model(model)

        abstract.ControlEditWindow.__init__(self, core, lv, None)
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

class EditItemValues(abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1
    COLUMN_EXPORT   = 2
    COLUMN_OBJ      = 3

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, str, gobject.TYPE_PYOBJECT))

        self.widget.append_column(gtk.TreeViewColumn("ID", gtk.CellRendererText(), text=self.COLUMN_ID))
        self.widget.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_VALUE))
        self.widget.append_column(gtk.TreeViewColumn("Export value", gtk.CellRendererText(), text=self.COLUMN_EXPORT))

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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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
        checks = self.data_model.get_item_check_exports()
        for item in self.data_model.get_item_values(self.core.selected_item):
            if len(item["titles"]) > 0:
                if self.core.selected_lang in item["titles"].keys(): title = item["titles"][self.core.selected_lang]
                else: title = item["titles"][item["titles"].keys()[0]]+" ["+item["titles"].keys()[0]+"]"
            ref = ""
            for check in checks or []:
                if check[0] == item["id"]: ref = check[1]
            self.append([item["id"], (" ".join(title.split())), ref, self.data_model.get_item(item["id"])])

class EditTitle(abstract.ListEditor):

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.title.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_title(self.operation, item, self.lang.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.wdialog = builder.get_object("dialog:edit_title")
        self.info_box = builder.get_object("dialog:edit_title:info_box")
        self.lang = builder.get_object("dialog:edit_title:lang")
        self.title = builder.get_object("dialog:edit_title:title")
        builder.get_object("dialog:edit_title:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_title:btn_ok").connect("clicked", self.__do)

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
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
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
            self.append([data.lang, (" ".join(data.text.split())), data])

class EditDescription(abstract.ListEditor):

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def regexp(self, regexp):
        match = regexp.groups()
        if match[1][:6] == "xhtml:": TAG = ""
        else: TAG = "xhtml:"

        if match[1] in ["head", "body"]:
            return ""
        elif match[1] in ["br", "hr"]: return match[0]+TAG+" ".join(match[1:3])+"/>" # unpaired tags
        elif match[1] in ["sub"]: 
            if match[2].find("idref") != -1: return match[0]+" ".join(match[1:3])+"/>" # <sub>
            else: return "" # </sub>
        else: return match[0]+TAG+" ".join(match[1:3]).strip()+">" # paired tags

    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        if self.operation == self.data_model.CMD_OPER_DEL:
            retval = self.data_model.edit_description(self.operation, item, None, None)
        else:
            if self.switcher.get_active() == 1:
                desc = self.description_html.get_buffer().get_text(self.description_html.get_buffer().get_start_iter(), self.description_html.get_buffer().get_end_iter())
            else:
                self.description.execute_script("document.title=document.documentElement.innerHTML;")
                desc = self.description.get_main_frame().get_title()
                if HAS_BEUTIFUL_SOUP:
                    # Use Beutiful soup to prettify the HTML
                    soup = BeautifulSoup(desc)
                    desc = soup.prettify()
            desc = re.sub("(< */* *)([^>/ ]*) *([^>]*)/*>", self.regexp, desc)
            retval = self.data_model.edit_description(self.operation, item, self.lang.get_text(), desc)

        self.fill()
        self.__dialog_destroy()
        self.emit("update")

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

    def __on_color_set(self, widget):
        dialog = gtk.ColorSelectionDialog("Select Color")
        if dialog.run() == gtk.RESPONSE_OK:
            gc = str(dialog.colorsel.get_current_color())
            color = "#" + "".join([gc[1:3], gc[5:7], gc[9:11]])
            self.description.execute_script("document.execCommand('forecolor', null, '%s');" % color)
        dialog.destroy()

    def __on_font_set(self, widget):
        dialog = gtk.FontSelectionDialog("Select a font")
        if dialog.run() == gtk.RESPONSE_OK:
            fname, fsize = dialog.fontsel.get_family().get_name(), dialog.fontsel.get_size()
            self.description.execute_script("document.execCommand('fontname', null, '%s');" % fname)
            self.description.execute_script("document.execCommand('fontsize', null, '%s');" % fsize)
        dialog.destroy()

    def __on_link_set(self, widget):
        dialog = gtk.Dialog("Enter a URL:", self.core.main_window, 0,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))

        entry = gtk.Entry()
        dialog.vbox.pack_start(entry)
        dialog.show_all()

        if dialog.run() == gtk.RESPONSE_OK:
            text = entry.get_text()
            text = "<sub xmlns=\"http://checklists.nist.gov/xccdf/1.1\" idref=\""+text+"\"/>"
            self.description.execute_script("document.execCommand('InsertHTML', true, '%s');" % text)
        dialog.destroy()

    def __on_code_set(self, action):
        self.description.execute_script("document.execCommand('SetMark', null, 'code');")

    def __on_action(self, action):
        """
        """
        MAP = { "dialog:edit_description:action:bold":      "bold",
                "dialog:edit_description:action:italic":    "italic",
                "dialog:edit_description:action:underline": "underline",
                "dialog:edit_description:action:outdent":   "Outdent",
                "dialog:edit_description:action:indent":    "Indent",
                "dialog:edit_description:action:bul_list":  "InsertUnorderedList",
                "dialog:edit_description:action:num_list":  "InsertOrderedList"}
        self.description.execute_script("document.execCommand('%s', false, false);" % MAP[action.get_name()])

    def __on_zoom(self, action):
        """
        """
        if action.get_name().split(":")[-1] == "zoomin":
            self.description.zoom_in()
        else: self.description.zoom_out()

    def __propagate(self, widget=None):
        
        if self.switcher.get_active() == 0: # TEXT -> HTML
            for child in self.description_tb.get_children():
                child.set_sensitive(True)
            self.description_sw.set_property("visible", True)
            self.description_html_sw.set_property("visible", False)
            desc = self.description_html.get_buffer().get_text(self.description_html.get_buffer().get_start_iter(), self.description_html.get_buffer().get_end_iter())
            self.description.load_html_string(desc or "", "file:///")
        elif self.switcher.get_active() == 1: # HTML -> TEXT
            for child in self.description_tb.get_children():
                child.set_sensitive(False)
            self.description_sw.set_property("visible", False)
            self.description_html_sw.set_property("visible", True)
            self.description.execute_script("document.title=document.documentElement.innerHTML;")
            desc = self.description.get_main_frame().get_title()
            desc = desc.replace("<head></head>", "")
            desc = desc.replace("<body>", "").replace("</body>", "")

            if HAS_BEUTIFUL_SOUP:
                # Use Beutiful soup to prettify the HTML
                soup = BeautifulSoup(desc)
                desc = soup.prettify()
            else: 
                self.core.notify("Missing BeautifulSoup python module, HTML processing disabled.",
                    Notification.INFORMATION, info_box=self.info_box, msg_id="")
            self.description_html.get_buffer().set_text(desc)
        self.switcher.parent.set_sensitive(True)

    def dialog(self, widget, operation):
        """
        """
        self.operation = operation
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.wdialog = builder.get_object("dialog:edit_description")
        self.info_box = builder.get_object("dialog:edit_description:info_box")
        self.lang = builder.get_object("dialog:edit_description:lang")
        self.description_sw = builder.get_object("dialog:edit_description:description:sw")
        self.description_tb = builder.get_object("dialog:edit_description:toolbar")
        self.description_html = builder.get_object("dialog:edit_description:html")
        self.description_html_sw = builder.get_object("dialog:edit_description:html:sw")
        builder.get_object("dialog:edit_description:action:bold").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:italic").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:underline").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:code").connect("activate", self.__on_code_set)
        builder.get_object("dialog:edit_description:action:num_list").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:bul_list").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:outdent").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:indent").connect("activate", self.__on_action)
        builder.get_object("dialog:edit_description:action:link").connect("activate", self.__on_link_set)
        builder.get_object("dialog:edit_description:action:zoomin").connect("activate", self.__on_zoom)
        builder.get_object("dialog:edit_description:action:zoomout").connect("activate", self.__on_zoom)
        builder.get_object("dialog:edit_description:tb:color").connect("clicked", self.__on_color_set)
        builder.get_object("dialog:edit_description:tb:font").connect("clicked", self.__on_font_set)
        builder.get_object("dialog:edit_description:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_description:btn_ok").connect("clicked", self.__do)
        self.switcher = builder.get_object("dialog:edit_description:switcher")
        self.switcher.set_active(1)
        self.switcher.connect("changed", self.__propagate)
        self.description = None

        if not HAS_WEBKIT:
            label = gtk.Label("Missing WebKit python module")
            label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color("red"))
            self.description_sw.add_with_viewport(label)
            builder.get_object("dialog:edit_description:btn_ok").set_sensitive(False)
            self.description_tb.set_sensitive(False)
            self.description_sw.show_all()
            self.core.notify("Missing WebKit python module, HTML editing disabled.",
                    Notification.INFORMATION, info_box=self.info_box, msg_id="")
        else:
            self.description = webkit.WebView()
            self.description.set_editable(True)
            self.description_sw.add(self.description)
            self.description.set_zoom_level(0.75)
            self.description_sw.show_all()
        self.description_html_sw.show_all()
        self.description_sw.set_property("visible", False)
        for child in self.description_tb.get_children():
            child.set_sensitive(False)
        self.switcher.parent.set_sensitive(True)

        self.core.notify_destroy("notify:not_selected")
        (model, iter) = self.get_selection().get_selected()
        if operation == self.data_model.CMD_OPER_ADD:
            self.description.load_html_string("", "file:///")
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                desc = model[iter][self.COLUMN_TEXT]
                desc = desc.replace("xhtml:","")
                #if self.description: self.description.load_html_string(desc or "", "file:///")
                self.description_html.get_buffer().set_text(desc or "")
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
            self.append([data.lang, re.sub("[\t ]+" , " ", data.text).strip(), data])


class EditWarning(abstract.ListEditor):

    COLUMN_CATEGORY = 3

    def __init__(self, core, id, widget, data_model):
        
        self.data_model = data_model
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, str))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
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

        retval = self.data_model.edit_warning(self.operation, item, category, self.lang.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.wdialog = builder.get_object("dialog:edit_warning")
        self.info_box = builder.get_object("dialog:edit_warning:info_box")
        self.lang = builder.get_object("dialog:edit_warning:lang")
        self.warning = builder.get_object("dialog:edit_warning:warning")
        self.category = builder.get_object("dialog:edit_warning:category")
        self.category.set_model(self.combo_model_warning)
        builder.get_object("dialog:edit_warning:btn_cancel").connect("clicked", self.__dialog_destroy)
        builder.get_object("dialog:edit_warning:btn_ok").connect("clicked", self.__do)

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
                self.category.set_active(abstract.ENUM_WARNING.pos(model[self.iter][self.COLUMN_OBJ].category) or -1)
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
            category = abstract.ENUM_WARNING.map(item.category)
            index = abstract.ENUM_WARNING.pos(item.category)
            self.append([item.text.lang, re.sub("[\t ]+" , " ", item.text.text).strip(), item, category[1]])

class EditNotice(abstract.ListEditor):

    COLUMN_ID = 0
    COLUMN_LANG = -1

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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

class EditStatus(abstract.ListEditor):

    COLUMN_DATE = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.wdialog = builder.get_object("dialog:edit_status")
        self.info_box = builder.get_object("dialog:edit_status:info_box")
        self.calendar = builder.get_object("dialog:edit_status:calendar")
        self.status = builder.get_object("dialog:edit_status:status")
        self.status.set_model(self.combo_model_status)
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
                self.status.set_active(abstract.ENUM_STATUS_CURRENT.pos(model[self.iter][self.COLUMN_OBJ].status) or -1)
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
            status = abstract.ENUM_STATUS_CURRENT.map(item.status)
            index = abstract.ENUM_STATUS_CURRENT.pos(item.status)
            self.append([time.strftime("%d-%m-%Y", time.localtime(item.date)), status[1], item])

class EditIdent(commands.DHEditItems,abstract.ControlEditWindow):

    COLUMN_ID = 0
    COLUMN_SYSTEM = 1
    COLUMN_OBJECTS = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:dependencies:lv_ident")
        self.box_ident = builder.get_object("edit:dependencies:box_ident")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit Question",
                        "view":         lv,
                        "cb":           self.DHEditIdent,
                        "textEntry":    {"name":    "ID",
                                        "column":   self.COLUMN_ID,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "System",
                                        "column":   self.COLUMN_SYSTEM,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        abstract.ControlEditWindow.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:dependencies:btn_ident_add")
        btn_edit = builder.get_object("edit:dependencies:btn_ident_edit")
        btn_del = builder.get_object("edit:dependencies:btn_ident_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("ID",self.COLUMN_ID)
        self.addColumn("System",self.COLUMN_SYSTEM)

    def fill(self, item):
        self.item = item
        self.model.clear()
        if item:
            self.item = item.to_rule()
            for data in self.item.idents:
                self.model.append([data.id, data.system, data])
                
    def set_sensitive(self, sensitive):
        self.box_ident.set_sensitive(sensitive)

class EditQuestion(abstract.ListEditor):

    COLUMN_OVERRIDE = 3
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Override", gtk.CellRendererText(), text=self.COLUMN_OVERRIDE))
        self.widget.append_column(gtk.TreeViewColumn("Question", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        buffer = self.question.get_buffer()
        if self.iter and self.get_model() != None: 
            item = self.get_model()[self.iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_question(self.operation, item, self.lang.get_text(), self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not self.iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[self.iter][self.COLUMN_LANG] or "")
                self.override.set_active(model[self.iter][self.COLUMN_OVERRIDE])
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


class EditRationale(abstract.ListEditor):

    COLUMN_OVERRIDE = 3
    
    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, gobject.TYPE_PYOBJECT, bool))
        self.add_sender(id, "update")

        self.widget.append_column(gtk.TreeViewColumn("Language", gtk.CellRendererText(), text=self.COLUMN_LANG))
        self.widget.append_column(gtk.TreeViewColumn("Override", gtk.CellRendererText(), text=self.COLUMN_OVERRIDE))
        self.widget.append_column(gtk.TreeViewColumn("Rationale", gtk.CellRendererText(), text=self.COLUMN_TEXT))

    def __do(self, widget=None):
        """
        """
        item = None
        (model, iter) = self.get_selection().get_selected()
        buffer = self.rationale.get_buffer()
        if iter and model != None: 
            item = model[iter][self.COLUMN_OBJ]

        retval = self.data_model.edit_rationale(self.operation, item, self.lang.get_text(), self.override.get_active(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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
            pass
        elif operation == self.data_model.CMD_OPER_EDIT:
            if not iter:
                self.notifications.append(self.core.notify("Please select at least one item to edit",
                    Notification.ERROR, msg_id="notify:not_selected"))
                return
            else:
                self.lang.set_text(model[iter][self.COLUMN_LANG] or "")
                self.override.set_active(model[iter][self.COLUMN_OVERRIDE])
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


class EditPlatform(abstract.ListEditor):

    COLUMN_TEXT = 0

    def __init__(self, core, id, widget, data_model):

        self.data_model = data_model 
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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

class EditValues(abstract.MenuButton):
    
    COLUMN_ID = 0
    COLUMN_TITLE = 1
    COLUMN_TYPE_ITER = 2
    COLUMN_TYPE_TEXT = 3
    COLUMN_OBJECT = 4
    COLUMN_CHECK = 5
    COLUMN_CHECK_EXPORT = 6
    
    def __init__(self, core, id, builder):

        self.data_model = commands.DHValues(core) 
        self.core = core
        self.builder = builder
        self.id = id

        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        
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

        self.operator.set_model(abstract.Enum_type.combo_model_operator_number)
        
    def show(self, active):
        self.values.set_sensitive(active)
        self.values.set_property("visible", active)

    def update(self):
        self.__update()

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        if widget == self.version:
            self.data_model.edit_value(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp:
                self.data_model.update(version_time=timestamp)
        elif widget == self.cluster_id:
            self.data_model.edit_value(cluster_id=widget.get_text())
        elif widget == self.operator:
            self.data_model.edit_value(operator=abstract.ENUM_OPERATOR[widget.get_active()][0])
        elif widget == self.abstract:
            self.data_model.edit_value(abstract=widget.get_active())
        elif widget == self.prohibit_changes:
            self.data_model.edit_value(prohibit_changes=widget.get_active())
        elif widget == self.interactive:
            self.data_model.edit_value(interactive=widget.get_active())
        else: 
            logger.error("Change: not supported object in \"%s\"" % (widget,))
            return

    def __clear(self):
        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.statuses.clear()
        self.questions.clear()
        self.values_values.clear()
        self.operator.set_active(-1)
        self.interactive.set_active(False)
        self.vtype.set_text("")

    def __update(self):

        details = self.data_model.get_item_details(self.core.selected_item)

        self.values.set_sensitive(details != None)

        if details:

            """It depends on value type what details should
            be filled and sensitive to user actions"""
            # TODO

            self.vid.set_text(details["id"] or "")
            self.version.set_text(details["version"] or "")
            self.version_time.set_text(details["version_time"] or "")
            self.cluster_id.set_text(details["cluster_id"] or "")
            self.vtype.set_text(abstract.ENUM_TYPE.map(details["vtype"])[1])
            self.abstract.set_active(details["abstract"])
            self.prohibit_changes.set_active(details["prohibit_changes"])
            self.interactive.set_active(details["interactive"])
            self.operator.set_active(abstract.ENUM_OPERATOR.pos(details["oper"]))
            self.titles.fill()
            self.descriptions.fill()
            self.warnings.fill()
            self.statuses.fill()
            self.questions.fill()
            self.values_values.fill()

            
class EditValuesValues(abstract.ListEditor):

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
        abstract.ListEditor.__init__(self, id, core, widget=widget, model=gtk.ListStore(str, str, str, str, str, bool, str, gobject.TYPE_PYOBJECT))
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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

#======================================= EDIT FIXTEXT ==========================================

class EditFixtext(abstract.ListEditor):
    
    COLUMN_TEXT = 0

    def __init__(self, core, builder):
        
        self.core = core
        self.builder = builder
        self.data_model = commands.DHEditItems(core)
        abstract.ListEditor.__init__(self, "gui:edit:items:operations:fixtext", self.core, widget=self.builder.get_object("edit:operations:lv_fixtext"), model=gtk.ListStore(str, gobject.TYPE_PYOBJECT))
        self.builder.get_object("edit:operations:btn_fixtext_preview").connect("clicked", self.preview)
        
        # Register Event Object
        self.add_sender(self.id, "item_changed")
        self.edit_fixtext_option = EditFixtextOption(core, builder)
        self.add_receiver("gui:edit:items:operations:fixtext", "item_changed", self.__update)
        
        #information for new/edit dialog
        values = {
                    "name_dialog":  "Fixtext",
                    "view":         self,
                    "cb":           self.data_model.DHEditFixtextText,
                    "textView":     {"name":    "Value",
                                    "column":   0,
                                    "empty":    False, 
                                    "unique":   False}
                        }
        btn_add = builder.get_object("edit:operations:btn_fixtext_add")
        btn_edit = builder.get_object("edit:operations:btn_fixtext_edit")
        btn_del = builder.get_object("edit:operations:btn_fixtext_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row, values)
        btn_edit.connect("clicked", self.cb_edit_row, values)
        btn_del.connect("clicked", self.cb_del_row, values)
        
        self.widget.get_selection().connect("changed", self.__cb_item_changed, self.widget)
        
        self.box_main = self.builder.get_object("edit:operations:fixtext:box")
        
        self.widget.append_column(gtk.TreeViewColumn("Text", gtk.CellRendererText(), text=0))
        
    def fill(self, item):
        self.clear()
        self.emit("item_changed")
        if item:
            self.item = item
            rule = item.to_rule()
            if rule.fixtexts:
                for obj in rule.fixtexts:
                    self.append([re.sub("[\t ]+" , " ", obj.text.text).strip(), obj])
        else:
            self.item = None
    
    def set_sensitive(self, sensitive):
        self.box_main.set_sensitive(sensitive)
        
    def __cb_item_changed(self, widget, treeView):
        self.emit("item_changed")
        treeView.columns_autosize()
    
    def __update(self):
        (model,iter) = self.get_selection().get_selected()
 
        if iter:
            self.edit_fixtext_option.fill(model.get_value(iter, 1))
        else:
            self.edit_fixtext_option.fill(None)

            
class EditFixtextOption(commands.DHEditItems,abstract.ControlEditWindow):
    
    def __init__(self, core, builder):
    
        # set  models
        self.core = core
        self.builder = builder
        abstract.ControlEditWindow.__init__(self, core, None, None)
        
        #edit data of fictext
        self.entry_reference = self.builder.get_object("edit:operations:fixtext:entry_reference1")
        self.entry_reference.connect("focus-out-event",self.cb_entry_fixtext_reference)
        
        self.combo_strategy = self.builder.get_object("edit:operations:fixtext:combo_strategy1")
        self.combo_strategy.set_model(abstract.Enum_type.combo_model_strategy)
        self.combo_strategy.connect( "changed", self.cb_combo_fixtext_strategy)
        
        self.combo_complexity = self.builder.get_object("edit:operations:fixtext:combo_complexity1")
        self.combo_complexity.set_model(abstract.Enum_type.combo_model_level)
        self.combo_complexity.connect( "changed", self.cb_combo_fixtext_complexity)
    
        self.combo_disruption = self.builder.get_object("edit:operations:fixtext:combo_disruption1")
        self.combo_disruption.set_model(abstract.Enum_type.combo_model_level)
        self.combo_disruption.connect( "changed", self.cb_combo_fixtext_disruption)
    
        self.chbox_reboot = self.builder.get_object("edit:operations:fixtext:chbox_reboot1")
        self.chbox_reboot.connect("toggled",self.cb_chbox_fixtext_reboot)

        self.box_detail= self.builder.get_object("edit:operations:fixtext:frame")
        
    def fill(self, fixtext):
        self.item = fixtext
        self.combo_strategy.handler_block_by_func(self.cb_combo_fixtext_strategy)
        self.combo_complexity.handler_block_by_func(self.cb_combo_fixtext_complexity)
        self.combo_disruption.handler_block_by_func(self.cb_combo_fixtext_disruption)
        self.chbox_reboot.handler_block_by_func(self.cb_chbox_fixtext_reboot)
        if fixtext:

            self.box_detail.set_sensitive(True)

            if fixtext.fixref:
                self.entry_reference.set_text(fixtext.fixref)
            else:
                self.entry_reference.set_text("")
            
            self.chbox_reboot.set_active(fixtext.reboot)
            self.set_active_comboBox(self.combo_strategy, fixtext.strategy, self.COMBO_COLUMN_DATA, "fixtext strategy")
            self.set_active_comboBox(self.combo_complexity, fixtext.complexity, self.COMBO_COLUMN_DATA, "fixtext complexity")
            self.set_active_comboBox(self.combo_disruption, fixtext.disruption, self.COMBO_COLUMN_DATA, "fixtext disruption")
        else:
            self.item = None
            self.box_detail.set_sensitive(False)
            self.entry_reference.set_text("")
            self.chbox_reboot.set_active(False)
            self.combo_strategy.set_active(-1)
            self.combo_complexity.set_active(-1)
            self.combo_disruption.set_active(-1)
            
        self.combo_strategy.handler_unblock_by_func(self.cb_combo_fixtext_strategy)
        self.combo_complexity.handler_unblock_by_func(self.cb_combo_fixtext_complexity)
        self.combo_disruption.handler_unblock_by_func(self.cb_combo_fixtext_disruption)
        self.chbox_reboot.handler_unblock_by_func(self.cb_chbox_fixtext_reboot)
            
            

#======================================= EDIT FIX ==========================================

class EditFix(commands.DHEditItems, abstract.ControlEditWindow, EventObject):
    
    COLUMN_ID = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2
    
    def __init__(self, core, builder):
        
        self.id = "gui:btn:menu:edit:fix"
        self.builder = builder
        self.core = core
        
        EventObject.__init__(self, core)
        self.core.register(self.id, self)
        self.add_sender(self.id, "item_changed")
        
        self.edit_fix_option = EditFixOption(core, builder)
        self.add_receiver("gui:btn:menu:edit:fix", "item_changed", self.__update)
        
        self.model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv = self.builder.get_object("edit:operations:lv_fix")
        lv.set_model(self.model)
        
                #information for new/edit dialog
        values = {
                    "name_dialog":  "Fix",
                    "view":         lv,
                    "cb":           self.DHEditFix,
                    "textEntry":    {"name":    "ID",
                                    "column":   self.COLUMN_ID,
                                    "empty":    False, 
                                    "unique":   True},
                    "textView":     {"name":    "Content",
                                    "column":   self.COLUMN_TEXT,
                                    "empty":    False, 
                                    "unique":   False}
                        }
        abstract.ControlEditWindow.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:operations:btn_fix_add")
        btn_edit = builder.get_object("edit:operations:btn_fix_edit")
        btn_del = builder.get_object("edit:operations:btn_fix_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        abstract.ControlEditWindow.__init__(self, core, lv, values)
        self.selection.connect("changed", self.__cb_item_changed, lv)
        
        self.box_main = self.builder.get_object("edit:operations:fix:box")
        
        self.addColumn("ID",self.COLUMN_ID)
        self.addColumn("Content",self.COLUMN_TEXT)
        
    def fill(self, item):
        self.model.clear()
        self.emit("item_changed")
        if item:
            self.item = item
            rule = item.to_rule()
            for object in rule.fixes:
                self.model.append([object.id, object.content, object])
        else:
            self.item = None
    
    def set_sensitive(self, sensitive):
        self.box_main.set_sensitive(sensitive)
        
    def __cb_item_changed(self, widget, treeView):
        self.emit("item_changed")
        treeView.columns_autosize()
    
    def __update(self):
        (model,iter) = self.selection.get_selected()
 
        if iter:
            self.edit_fix_option.fill(model.get_value(iter,self.COLUMN_OBJECT))
        else:
            self.edit_fix_option.fill(None)

            
class EditFixOption(commands.DHEditItems,abstract.ControlEditWindow):
    
    def __init__(self, core, builder):
    
        # set  models
        self.core = core
        self.builder = builder

        #edit data of fictext
        self.entry_system = self.builder.get_object("edit:operations:fix:entry_system")
        self.entry_system.connect("focus-out-event",self.cb_entry_fix_system)
        
        self.entry_platform = self.builder.get_object("edit:operations:fix:entry_platform")
        self.entry_platform.connect("focus-out-event",self.cb_entry_fix_platform)
        
        self.combo_strategy = self.builder.get_object("edit:operations:fix:combo_strategy")
        self.combo_strategy.set_model(abstract.Enum_type.combo_model_strategy)
        self.combo_strategy.connect( "changed", self.cb_combo_fix_strategy)
        
        self.combo_complexity = self.builder.get_object("edit:operations:fix:combo_complexity")
        self.combo_complexity.set_model(abstract.Enum_type.combo_model_level)
        self.combo_complexity.connect( "changed", self.cb_combo_fix_complexity)
    
        self.combo_disruption = self.builder.get_object("edit:operations:fix:combo_disruption")
        self.combo_disruption.set_model(abstract.Enum_type.combo_model_level)
        self.combo_disruption.connect( "changed", self.cb_combo_fix_disruption)
    
        self.chbox_reboot = self.builder.get_object("edit:operations:fix:chbox_reboot")
        self.chbox_reboot.connect("toggled",self.cb_chbox_fix_reboot)

        self.box_detail= self.builder.get_object("edit:operations:fix:frame")
        
    def fill(self, fix):
        self.item = fix
        self.combo_strategy.handler_block_by_func(self.cb_combo_fix_strategy)
        self.combo_complexity.handler_block_by_func(self.cb_combo_fix_complexity)
        self.combo_disruption.handler_block_by_func(self.cb_combo_fix_disruption)
        self.chbox_reboot.handler_block_by_func(self.cb_chbox_fix_reboot)
        if fix:

            self.box_detail.set_sensitive(True)

            if fix.system:
                self.entry_system.set_text(fix.system)
            else:
                self.entry_system.set_text("")

            if fix.platform:
                self.entry_platform.set_text(fix.platform)
            else:
                self.entry_platform.set_text("")
                
            self.chbox_reboot.set_active(fix.reboot)
            self.set_active_comboBox(self.combo_strategy, fix.strategy, self.COMBO_COLUMN_DATA,  "fix strategy")
            self.set_active_comboBox(self.combo_complexity, fix.complexity, self.COMBO_COLUMN_DATA, "fix complexity")
            self.set_active_comboBox(self.combo_disruption, fix.disruption, self.COMBO_COLUMN_DATA, "fix disruption")
        else:
            self.item = None
            self.box_detail.set_sensitive(False)
            self.entry_system.set_text("")
            self.entry_platform.set_text("")
            self.chbox_reboot.set_active(False)
            self.combo_strategy.set_active(-1)
            self.combo_complexity.set_active(-1)
            self.combo_disruption.set_active(-1)
            
        self.combo_strategy.handler_unblock_by_func(self.cb_combo_fix_strategy)
        self.combo_complexity.handler_unblock_by_func(self.cb_combo_fix_complexity)
        self.combo_disruption.handler_unblock_by_func(self.cb_combo_fix_disruption)
        self.chbox_reboot.handler_unblock_by_func(self.cb_chbox_fix_reboot)

class AddProfileDialog(EventObject, abstract.ControlEditWindow):

    def __init__(self, core, data_model, cb):
        self.core = core
        self.data_model = data_model
        self.__update = cb
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.window = builder.get_object("dialog:profile_add")

        builder.get_object("profile_add:btn_ok").connect("clicked", self.__cb_do)
        builder.get_object("profile_add:btn_cancel").connect("clicked", self.__delete_event)
        self.pid = builder.get_object("profile_add:entry_id")
        self.title = builder.get_object("profile_add:entry_title")
        self.info_box = builder.get_object("profile_add:info_box")

        self.lang = builder.get_object("profile_add:entry_lang")
        self.lang.set_text(self.core.selected_lang or "")

        self.show()

    def __cb_do(self, widget):

        if len(self.pid.get_text()) == 0: 
            self.core.notify("Can't add profile with no ID !",
                    Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
            return
        profiles = self.data_model.get_profiles()
        for profile in profiles:
            if profile[0] == self.pid.get_text():
                self.core.notify("Profile \"%s\" already exists." % (self.pid.get_text(),),
                        Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
                self.pid.grab_focus()
                return
        if len(self.title.get_text()) == 0: 
            self.core.notify("Please add title for this profile.",
                    Notification.ERROR, self.info_box, msg_id="notify:edit:profile:new")
            self.title.grab_focus()
            return

        self.data_model.add(id=self.pid.get_text(), lang=self.lang.get_text(), title=self.title.get_text())
        self.core.selected_profile = self.pid.get_text()
        self.window.destroy()
        self.__update(force=True)

    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __delete_event(self, widget, event=None):
        self.window.destroy()
        

class AddItem(EventObject, abstract.ControlEditWindow):
    
    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2
    
    def __init__(self, core, data_model, list_item):
        
        self.core = core
        self.data_model = data_model
        self.list_item = list_item
        self.view = list_item.get_TreeView()
        
    def dialog(self):

        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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

class EditSelectIdDialogWindow():
    
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")

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
        except Exception, e:
            #self.core.notify("Can't filter items: %s" % (e,), 3)
            logger.error("Can't filter items: %s" % (e,))
            return False

class FindOvalDef(abstract.Window, abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1

    def __init__(self, core, id, data_model):

        self.data_model = data_model
        self.core = core
        abstract.Window.__init__(self, id, core)
        self.add_sender(id, "update")

    def __do(self, widget=None):
        """
        """
        self.core.notify_destroy("notify:dialog_notify")
        (model, iter) = self.definitions.get_selection().get_selected()
        if not iter:
            self.core.notify("You have to chose the definition !",
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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


class FindItem(abstract.Window, abstract.ListEditor):

    COLUMN_ID       = 0
    COLUMN_VALUE    = 1
    COLUMN_OBJ      = 2

    def __init__(self, core, id, data_model):

        self.data_model = data_model
        self.core = core
        abstract.Window.__init__(self, id, core)
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
        self.data_model.add_refine(model[iter][self.COLUMN_ID], model[iter][self.COLUMN_VALUE], model[iter][self.COLUMN_OBJ])
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
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
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
        else: raise Exception("Type \"%s\" not supported !" % (type,))

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

class Editor(abstract.Window, threading.Thread):

    def __init__(self):

        threading.Thread.__init__(self)
        logger = logging.getLogger(self.__class__.__name__)
        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/scap-workbench/editor.glade")
        self.builder.connect_signals(self)
        self.core = core.SWBCore(self.builder)
        assert self.core != None, "Initialization failed, core is None"

        self.window = self.builder.get_object("main:window")
        self.core.main_window = self.window
        self.main_box = self.builder.get_object("main:box")

        # abstract the main menu
        self.menu = abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
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
        #gtk.gdk.threads_leave()
        gtk.main_quit()
        return False

    def run(self):
        gnome.init("SCAP Workbench", "0.2.3")
        gtk.main()

if __name__ == '__main__':
    editor = Editor()
    editor.start()
