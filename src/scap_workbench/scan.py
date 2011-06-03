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
import gobject          # gobject.TYPE_PYOBJECT
import tempfile         # Temporary file for XCCDF preview
from threads import thread as threadSave

""" Importing SCAP Workbench modules
"""
import abstract                 # All abstract classes
import logging                  # Logger for debug/info/error messages
import core                     # Initializing of core in main window
import commands                 # Module for handling openscap
import filter                   # Module for handling filters
from core import Notification   # core.Notification levels for reference
from events import EventObject  # abstract module EventObject

# Initializing Logger
logger = logging.getLogger("scap-workbench")

class ScanList(abstract.List):
    
    def __init__(self, widget, core, filter, data_model):
        self.core = core
        self.filter = filter
        self.data_model = data_model
        abstract.List.__init__(self, "gui:scan:scan_list", core, widget=widget)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        self.get_TreeView().set_search_column(3)

        # actions
        self.add_receiver("gui:btn:menu:scan", "scan", self.__scan)
        self.add_receiver("gui:btn:menu:scan:filter", "search", self.__search)
        self.add_receiver("gui:btn:menu:scan:filter", "filter_add", self.__filter_add)
        self.add_receiver("gui:btn:menu:scan:filter", "filter_del", self.__filter_del)
        self.add_receiver("gui:scan:DHScan", "filled", self.__filter_refresh)
        
        self.init_filters(self.filter, self.data_model.model, self.data_model.new_model())
        
    def __scan(self):
        self.get_TreeView().set_model(self.data_model.model)

    def __search(self):
        self.search(self.filter.get_search_text(),3)

    def __filter_add(self):
        self.filter_add(self.filter.filters)

    def __filter_del(self):
        self.filter_del(self.filter.filters)

    def __filter_refresh(self):
        self.filter_del(self.filter.filters)
        
class MenuButtonScan(abstract.MenuButton, abstract.Func):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        self.builder = builder
        abstract.MenuButton.__init__(self, "gui:btn:menu:scan", widget, core)
        self.core = core
        self.exported_file = None
        self.__lock = False
        self.selected_profile = None

        self.progress = self.builder.get_object("scan:progress")
        self.data_model = commands.DHScan("gui:scan:DHScan", core, self.progress)

        #draw body
        self.body = self.builder.get_object("scan:box")
        self.filter = filter.ScanFilter(self.core, self.builder)
        self.scanlist = ScanList(self.builder.get_object("scan:treeview"), core=self.core, filter=self.filter, data_model=self.data_model)
        self.filter.expander.cb_changed()

        self.profile = self.builder.get_object("scan:btn_profile")
        self.profile.connect("clicked", self.__cb_profile)
        self.scan = self.builder.get_object("scan:btn_scan")
        self.scan.connect("clicked", self.__cb_scan)
        self.stop = self.builder.get_object("scan:btn_stop")
        self.stop.connect("clicked", self.__cb_cancel)
        self.export = self.builder.get_object("scan:btn_export")
        self.export.connect("clicked", self.__cb_export)
        self.help = self.builder.get_object("scan:btn_help")
        self.help.connect("clicked", self.__cb_help)
        self.results = self.builder.get_object("scan:btn_results")
        self.results.connect("clicked", self.__cb_export_report)

        # set signals
        self.add_sender(self.id, "scan")

    def __update_profile(self):
        self.core.notify_destroy("notify:scan:selected_profile")
        if self.core.selected_profile != None:
            profile = self.data_model.get_profile_details(self.core.selected_profile)
            if self.core.selected_lang in profile["titles"]: title = profile["titles"][self.core.selected_lang]
            else: title = "%s (ID)" % (profile["id"],)
            if self.selected_profile != self.core.selected_profile:
                self.notifications.append(self.core.notify("Selected profile: \"%s\"." % (title,), core.Notification.SUCCESS, msg_id="notify:scan:selected_profile"))
            self.selected_profile = self.core.selected_profile
        elif self.core.lib.loaded:
            if self.selected_profile != self.core.selected_profile:
                self.notifications.append(self.core.notify("Selected default document profile.", core.Notification.SUCCESS, msg_id="notify:scan:selected_profile"))
            self.selected_profile = None

    def activate(self, active):
        if active:
            self.__update_profile()
        else:
            for notify in self.notifications:
                notify.destroy()
            self.core.notify_destroy("notify:scan:cancel")

    def __cb_export_report(self, widget):
        if self.result:
            self.prepare_preview()
            gtk.gdk.flush()
            temp = tempfile.NamedTemporaryFile()
            retval = self.data_model.export(temp.name, self.result)
            if not retval:
                self.notifications.append(self.core.notify("Export failed.", core.Notification.ERROR, msg_id="notify:scan:export"))
                return
            expfile = self.data_model.export_report(retval)
            f = open(expfile)
            desc = f.read()
            f.close()
            self.preview(widget=None, desc=desc)
            temp.close()
        else:
            self.notifications.append(self.core.notify("Nothing to export.", core.Notification.ERROR, msg_id="notify:scan:export"))

    def __cb_profile(self, widget):
        for notify in self.notifications:
            notify.destroy()
        if self.core.lib.loaded == None:
            self.core.notify("Library not initialized or XCCDF file not specified",
                    core.Notification.INFORMATION, msg_id="notify:xccdf:not_loaded")
            return
        ProfileChooser(self.core, self.__update_profile)

    def __cb_scan(self, widget=None):
        self.exported_file = None
        for notify in self.notifications:
            notify.destroy()
        if self.__lock: 
            logger.error("Scan already running")
        else:
            self.emit("scan")
            self.data_model.prepare()
            self.__lock = True
            self.__set_sensitive(True)
            self.__th_scan()

    def __set_sensitive(self, active):
        self.stop.set_sensitive(active)
        self.scan.set_sensitive(not active)
        self.export.set_sensitive(not active)
        self.results.set_sensitive(not active)
        self.profile.set_sensitive(not active)

    @threadSave
    def __th_scan(self):
        if not self.data_model.check_library(): return None

        logger.debug("Scanning %s ..", self.data_model.policy.id)
        if self.progress != None:
            gtk.gdk.threads_enter()
            self.progress.set_fraction(0.0)
            self.progress.set_text("Prepairing ...")
            gtk.gdk.threads_leave()

        self.result = self.data_model.policy.evaluate()
        gtk.gdk.threads_enter()
        if self.progress: 
            self.progress.set_fraction(1.0)
            self.progress.set_text("Finished %s of %s rules" % (self.data_model.count_current, self.data_model.count_all))
            self.progress.set_has_tooltip(False)
        logger.debug("Finished scanning")
        self.core.notify("Scanning finished succesfully", core.Notification.SUCCESS, msg_id="notify:scan:complete")
        gtk.gdk.threads_leave()
        self.core.notify_destroy("notify:scan:cancel")
        self.__lock = False
        self.__set_sensitive(False)

    def __cb_cancel(self, widget):
        """ Called by user event when stop button pressed
        """
        if self.__lock:
            self.core.notify("Scanning canceled. Please wait for openscap to finish current task.", core.Notification.INFORMATION, msg_id="notify:scan:cancel")
            self.data_model.cancel()

    def __cb_export(self, widget):
        if self.result:
            retval = self.data_model.export(None, self.result)
            if not retval:
                self.notifications.append(self.core.notify("Export failed.", core.Notification.ERROR, msg_id="notify:scan:export"))
        else:
            self.notifications.append(self.core.notify("Nothing to export.", core.Notification.ERROR, msg_id="notify:scan:export"))

    def __cb_help(self, widget):
        window = HelpWindow(self.core)


class ProfileChooser:
    """
    Modal window for choosing profile before scan
    """

    def __init__(self, core, callback=None):
        self.callback = callback
        self.core = core
        self.data_model = commands.DHProfiles(core)

        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/dialogs.glade")
        self.dialog = builder.get_object("dialog:profile_change")
        self.info_box = builder.get_object("dialog:profile_change:info_box")
        self.profiles = builder.get_object("dialog:profile_change:profiles")
        self.profiles.connect("key-press-event", self.__do)
        builder.get_object("dialog:profile_change:btn_ok").connect("clicked", self.__do)
        builder.get_object("dialog:profile_change:btn_cancel").connect("clicked", self.__dialog_destroy)

        self.data_model.treeView = self.profiles

        self.data_model.model = self.profiles.get_model()
        self.data_model.fill()
        self.dialog.set_transient_for(self.core.main_window)
        self.dialog.show_all()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.dialog: 
            self.dialog.destroy()

    def __do(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        selection = self.profiles.get_selection()
        model, it = selection.get_selected()
        if it == None: 
            logger.debug("Nothing selected, skipping")
            self.window.destroy()
            return
        self.core.selected_profile = model.get_value(it, 0)
        if self.callback:
            self.callback()
        self.__dialog_destroy()
        return self.core.selected_profile

class HelpWindow(abstract.Window):

    def __init__(self, core=None):
        self.core = core
        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/scap-workbench/scan_help.glade")
        self.draw_window()

    def delete_event(self, widget, event):
        self.window.destroy()
        
    def draw_window(self):
        # Create a new window
        self.window = self.builder.get_object("scan:help:window")
        self.treeView = self.builder.get_object("scan:help:treeview")
        self.help_model = self.treeView.get_model()
        self.builder.connect_signals(self)

        selection = self.treeView.get_selection()
        selection.set_mode(gtk.SELECTION_NONE)

        self.help_model[0][1] = commands.DHScan.BG_GREEN
        self.help_model[1][1] = commands.DHScan.BG_RED
        self.help_model[2][1] = commands.DHScan.BG_ERR
        self.help_model[3][1] = commands.DHScan.BG_GRAY
        self.help_model[4][1] = commands.DHScan.BG_GRAY
        self.help_model[5][1] = commands.DHScan.BG_GRAY
        self.help_model[6][1] = commands.DHScan.BG_GRAY
        self.help_model[7][1] = commands.DHScan.BG_LGREEN
        self.help_model[8][1] = commands.DHScan.BG_FIXED

        self.window.set_transient_for(self.core.main_window)
        self.window.show_all()

    def destroy_window(self, widget):
        self.window.destroy()

