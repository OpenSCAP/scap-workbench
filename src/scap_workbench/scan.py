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

import pygtk
import gtk
import gobject
import pango

import abstract
import logging
import core
import filter
import commands
import render

import logging
from events import EventObject

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
        self.add_receiver("gui:btn:menu:scan", "cancel", self.__cancel)
        self.add_receiver("gui:btn:menu:scan:filter", "search", self.__search)
        self.add_receiver("gui:btn:menu:scan:filter", "filter_add", self.__filter_add)
        self.add_receiver("gui:btn:menu:scan:filter", "filter_del", self.__filter_del)
        self.add_receiver("gui:scan:DHScan", "filled", self.__filter_refresh)
        
        self.init_filters(self.filter, self.data_model.model, self.data_model.new_model())
        
    def __cancel(self):
        self.data_model.cancel()

    def __scan(self):
        self.get_TreeView().set_model(self.data_model.model)
        self.data_model.scan()

    def __search(self):
        self.search(self.filter.get_search_text(),3)

    def __filter_add(self):
        self.filter_add(self.filter.filters)

    def __filter_del(self):
        self.filter_del(self.filter.filters)

    def __filter_refresh(self):
        self.filter_del(self.filter.filters)
        
class MenuButtonScan(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        self.builder = builder
        abstract.MenuButton.__init__(self, "gui:btn:menu:scan", widget, core)
        self.core = core
        self.exported_file = None

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
        self.scan.connect("clicked", self.__cb_start)
        self.stop = self.builder.get_object("scan:btn_stop")
        self.stop.connect("clicked", self.__cb_cancel)
        self.export = self.builder.get_object("scan:btn_export")
        self.export.connect("clicked", self.__cb_export)
        self.help = self.builder.get_object("scan:btn_help")
        self.help.connect("clicked", self.__cb_help)
        self.results_btn = self.builder.get_object("scan:btn_results")
        self.results_btn.connect("clicked", self.__cb_export_report)

        # set signals
        self.add_sender(self.id, "scan")
        self.add_sender(self.id, "cancel")
        self.add_sender(self.id, "export")
        self.add_receiver("gui:btn:menu:scan", "export", self.__export)

    def __update_profile(self):
        if self.core.selected_profile != None:
            profile = self.data_model.get_profile_details(self.core.selected_profile)
            if self.core.selected_lang in profile["titles"]: title = profile["titles"][self.core.selected_lang]
            else: title = "%s (ID)" % (profile["id"],)
            self.notifications.append(self.core.notify("Selected profile: \"%s\"." % (title,), core.Notification.SUCCESS))
        elif self.core.lib.loaded: self.notifications.append(self.core.notify("Selected default document profile.", core.Notification.SUCCESS))

    def activate(self, active):
        if active:
            self.__update_profile()
        else:
            for notify in self.notifications:
                notify.destroy()
            self.core.notify_destroy("notify:scan:cancel")

    #callback function
    def __cb_export_report(self, widget):
        if self.exported_file:
            self.core.notify_destroy("notify:scan:no_results")
            self.data_model.export_report(self.exported_file)
        else: self.notifications.append(self.core.notify("Please export results first.",
            core.Notification.ERROR, msg_id="notify:scan:no_results"))
        self.core.notify_destroy("notify:scan:export_notify")

    def __export(self):
        self.exported_file = self.data_model.export()
        if self.exported_file: 
            self.notifications.append(self.core.notify("Results exported successfuly. You can see them by pushing the \"Results\" button.",
                core.Notification.SUCCESS, msg_id="notify:scan:export_notify"))
            self.results_btn.set_sensitive(True)

    def __cb_profile(self, widget):
        for notify in self.notifications:
            notify.destroy()
        if self.core.lib.loaded == None:
            self.core.notify("Library not initialized or XCCDF file not specified",
                    core.Notification.INFORMATION, msg_id="notify:xccdf:not_loaded")
            return
        ProfileChooser(self.core, self.__update_profile)

    def __cb_start(self, widget):
        self.exported_file = None
        for notify in self.notifications:
            notify.destroy()
        self.emit("scan")

    def __cb_cancel(self, widget):
        self.emit("cancel")

    def __cb_export(self, widget):
        self.emit("export")

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

