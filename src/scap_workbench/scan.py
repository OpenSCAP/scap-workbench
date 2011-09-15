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
import os               # For path basedir
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
        self.data_model = data_model
        super(ScanList, self).__init__("gui:scan:scan_list", core, widget=widget)

        self.filter = filter

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
    """Button and GUI for scanning, contains results and various buttons to control
    the scanning process.
    """
    
    def __init__(self, builder, widget, core):
        self.builder = builder
        
        abstract.MenuButton.__init__(self, "gui:btn:menu:scan", widget, core)
        abstract.Func.__init__(self, core)
        
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
        self.export.connect("clicked", lambda widget: self.__cb_save_report(append_notifications = True))
        self.help = self.builder.get_object("scan:btn_help")
        self.help.connect("clicked", self.__cb_help)
        self.results = self.builder.get_object("scan:btn_results")
        self.results.connect("clicked", self.__cb_preview_report)

        # set signals
        self.add_sender(self.id, "scan")
        self.add_receiver("gui:main", "quit", self.__cb_cancel)

    def __update_profile(self):
        """Called whenever current profile changes (for example by the profile chooser dialog - see scan.ProfileChooser)
        
        Practically sets self.selected_profile to self.core.selected_profile
        (this duplication appears to be used mainly to test whether a change actually happened or not)
        """
        
        self.core.notify_destroy("notify:scan:selected_profile")
        
        if not self.core.lib.loaded:
            return
        
        if self.core.selected_profile is not None:
            profile = self.data_model.get_profile_details(self.core.selected_profile)
            
            if self.core.selected_lang in profile["titles"]:
                title = profile["titles"][self.core.selected_lang]
            else:
                title = "%s (ID)" % (profile["id"],)
                
            if self.selected_profile != self.core.selected_profile:
                self.notifications.append(self.core.notify("Selected profile: \"%s\"." % (title,), core.Notification.SUCCESS, msg_id="notify:scan:selected_profile"))
            self.selected_profile = self.core.selected_profile
            
            self.profile.set_tooltip_text("Current profile: %s" % (title))
            
        else:
            # if self.core.selected_profile is None the current profile is "No profile"
            if self.selected_profile != self.core.selected_profile:
                self.notifications.append(self.core.notify("Selected default document profile.", core.Notification.SUCCESS, msg_id="notify:scan:selected_profile"))
            self.selected_profile = None
            
            self.profile.set_tooltip_text("Current profile: (No profile)")

    def activate(self, active):
        if active:
            self.__update_profile()
        else:
            for notify in self.notifications:
                notify.destroy()
            self.core.notify_destroy("notify:scan:cancel")

    def __cb_preview_report(self, widget):
        """Creates a preview of the exported report. Allows user to save it using the Save button.
        
        See MenuButtonScan.__cb_save_report
        """

        if self.result:
            self.prepare_preview()
            gtk.gdk.flush()
            
            raw_temp = tempfile.NamedTemporaryFile()
            transformed_temp = tempfile.NamedTemporaryFile()
            
            if not self.data_model.export(raw_temp.name, self.result):
                self.notifications.append(self.core.notify("Export failed.", core.Notification.ERROR, msg_id="notify:scan:export"))
                return
            
            self.data_model.perform_xslt_transformation(file = raw_temp.name,
                                                        expfile = transformed_temp.name,
                                                        result_id = self.result.id,
                                                        oval_path = os.path.dirname(raw_temp.name))
            
            desc = transformed_temp.read()
            
            self.preview(widget = None, desc = desc, save = self.__cb_save_report)
            
            raw_temp.close()
            transformed_temp.close()
            
        else:
            self.notifications.append(self.core.notify("Nothing to export.", core.Notification.ERROR, msg_id="notify:scan:export"))

    def __cb_save_report(self, append_notifications = False):
        """ This method is used as callback to preview dialog window. When user press "save" button
        this function will be called and saved the report to the file.
        
        append_notifications - if True this method will immediately append notifications as necessary,
                               otherwise it will return a notification 2-tuple 
        """
        
        chooser = gtk.FileChooserDialog(title="Save report", action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        chooser.set_current_name("report.xhtml")
        response = chooser.run()
        
        if response == gtk.RESPONSE_OK:
            file_name = chooser.get_filename()
        elif response == gtk.RESPONSE_CANCEL:
            chooser.destroy()
            return None, None
        
        chooser.destroy()

        if not os.access(file_name, os.W_OK):
            ret = (Notification.ERROR, "Export failed - chosen file path isn't accessible for writing")
            if append_notifications:
                self.notifications.append(self.core.notify(ret[1], ret[0], msg_id="notify:scan:export"))
            else:
                return ret
            
        else:
            retval = self.data_model.export(file_name, self.result)
            # TODO: More info about the error
            ret = (Notification.ERROR, "Export failed") if not retval else (Notification.SUCCESS, "Report file saved successfully")
            
            # TODO: We should be more robust and do more error checking here
            self.data_model.perform_xslt_transformation(retval, result_id = self.result.id, oval_path = os.path.dirname(retval))
            
            if append_notifications:
                self.notifications.append(self.core.notify(ret[1], ret[0], msg_id="notify:scan:export"))
            else:
                return ret

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
            self.__th_scan()

    def set_scan_in_progress(self, active):
        """This method manages sensitivity of various buttons according to whether scanning
        is in progress or not. Also manages self.__lock
        """
        
        self.__lock = active
        
        self.stop.set_sensitive(active)
        self.scan.set_sensitive(not active)
        self.export.set_sensitive(not active)
        self.results.set_sensitive(not active)
        self.profile.set_sensitive(not active)

    @threadSave
    def __th_scan(self):
        """Starts scanning in a separate thread (via the @threadSave decorator, see threads.py)
        """
        
        if not self.data_model.check_library():
            return None

        self.set_scan_in_progress(True)
        
        gtk.gdk.threads_enter()
        self.core.notify_destroy("notify:scan:complete")
        gtk.gdk.threads_leave()
        
        logger.debug("Scanning %s ..", self.data_model.policy.id)
        if self.progress != None:
            gtk.gdk.threads_enter()
            self.progress.set_fraction(0.0)
            self.progress.set_text("Preparing ...")
            gtk.gdk.threads_leave()

        # at this point evaluation will keep working in this thread,
        # DHScan.__callback_start and DHScan.__callback_end will get called when each
        # of the tests will run and that is what is filling the scan results table
        self.result = self.data_model.policy.evaluate()
        
        # the scan finished (successfully or maybe it was canceled)
        gtk.gdk.threads_enter()
        if self.progress:
            # set the progress to 100% regardless of how many tests were actually run
            self.progress.set_fraction(1.0)
            self.progress.set_text("Finished %i of %i rules" % (self.data_model.count_current, self.data_model.count_all))
            self.progress.set_has_tooltip(False)
            
        logger.debug("Finished scanning")
        if self.data_model.count_current == self.data_model.count_all:
            self.core.notify("Scanning finished successfully", core.Notification.SUCCESS, msg_id="notify:scan:complete")
        else:
            self.core.notify("Scanning prematurely interrupted by user", core.Notification.INFORMATION, msg_id="notify:scan:complete")
        
        self.core.notify_destroy("notify:scan:cancel")
        gtk.gdk.threads_leave()

        self.set_scan_in_progress(False)

    def __cb_cancel(self, widget=None):
        """ Called by user event when stop button pressed
        """
        if self.__lock:
            self.core.notify("Scanning canceled. Please wait for openscap to finish current task.", core.Notification.INFORMATION, msg_id="notify:scan:cancel")
            self.data_model.cancel()

    def __cb_help(self, widget):
        window = HelpWindow(self.core)


class ProfileChooser(object):
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
    """Window that opens up when user clicks the "Help" button in the "Scan" section of scap-workbench.
    
    For now it only displays rule result legend.
    """

    def __init__(self, core=None):
        # we don't want to register this window with SWBCore since we will be creating and destroying it
        # regularly (each time user clicks the help button)
        super(HelpWindow, self).__init__("scan:help:window", core, skip_registration = True)
        
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

