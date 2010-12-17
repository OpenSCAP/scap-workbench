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
        self.__export_notify = None

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
        self.results_btn.set_sensitive(False)
        self.results_btn.connect("clicked", self.__cb_export_report)

        # set signals
        self.add_sender(self.id, "scan")
        self.add_sender(self.id, "cancel")
        self.add_sender(self.id, "export")
        self.add_receiver("gui:btn:menu:scan", "export", self.__export)

    def activate(self, active):
        if active:
            if self.core.selected_profile != None:
                self.notifications.append(self.core.notify("Selected profile: \"%s\"." % (self.core.selected_profile,), 0))
            else: self.notifications.append(self.core.notify("Selected default document profile.", 0))
        else:
            for notify in self.notifications:
                notify.destroy()

    #callback function
    def __cb_export_report(self, widget):
        self.data_model.export_report(self.exported_file)
        if self.__export_notify: self.__export_notify.destroy()

    def __export(self):
        self.exported_file = self.data_model.export()
        if self.exported_file: 
            self.__export_notify = self.core.notify("Results exported successfuly. You can see them by pushing the \"Results\" button.", 0)
            self.notifications.append(self.__export_notify)
            self.results_btn.set_sensitive(True)

    def __cb_profile(self, widget):
        for notify in self.notifications:
            notify.destroy()
        ProfileChooser(self.core)

    def __cb_start(self, widget):
        for notify in self.notifications:
            notify.destroy()
        self.emit("scan")

    def __cb_cancel(self, widget):
        self.emit("cancel")

    def __cb_export(self, widget):
        self.emit("export")

    def __cb_help(self, widget):
        window = HelpWindow(self.core)


class ProfileChooser(abstract.Window):
    """
    Modal window for choosing profile before scan
    """

    def __init__(self, core):
        self.core = core
        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/scap-workbench/profile_chooser.glade")
        self.draw_window()
        self.profile_model = commands.DHProfiles(core)
        self.profiles = self.builder.get_object("profile_chooser:tw")
        self.profile_model.render(self.profiles)
        self.profile_model.fill()
        self.builder.get_object("profile_chooser:btn_ok").connect("clicked", self.__cb_profile_changed, self.profiles)

    def __cb_profile_changed(self, widget, tw):
        selection = tw.get_selection()
        model, it = selection.get_selected()
        if it == None: 
            logger.error("Nothing selected or bug ??")
            return
        self.core.selected_profile = model.get_value(it, 0)
        self.window.destroy()
        return self.core.selected_profile

    def draw_window(self):
        self.window = self.builder.get_object("profile_chooser:window")
        self.window.set_transient_for(self.core.main_window)
        self.window.show_all()

class HelpWindow(abstract.Window):

    def __init__(self, core=None):
        self.core = core
        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/scap-workbench/scan_help.glade")
        self.draw_window()

    def delete_event(self, widget, event):
        self.window.destroy()
        
    def __notify(self, widget, event):
        if event.name == "width":
            for cell in widget.get_cell_renderers():
                cell.set_property('wrap-width', widget.get_width())

    def draw_window(self):
        # Create a new window
        self.window = self.builder.get_object("scan:help:window")
        self.treeView = self.builder.get_object("scan:help:treeview")
        self.help_model = self.builder.get_object("scan:help:treeview:model")
        self.builder.connect_signals(self)

        txtcell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Result", txtcell, text=0)
        column.add_attribute(txtcell, 'background', 1)
        self.treeView.append_column(column)

        txtcell = gtk.CellRendererText()
        txtcell.set_property('wrap-mode', pango.WRAP_WORD)
        txtcell.set_property('wrap-width', 500)
        column = gtk.TreeViewColumn("Description", txtcell, text=2)
        column.set_resizable(True)
        column.set_expand(True)
        column.connect("notify", self.__notify)
        self.treeView.append_column(column)

        selection = self.treeView.get_selection()
        selection.set_mode(gtk.SELECTION_NONE)

        self.help_model.append(["PASS", commands.DHScan.BG_GREEN, "The target system or system component satisfied all the conditions of the Rule. A pass result contributes to the weighted score and maximum possible score."])
        self.help_model.append(["FAIL", commands.DHScan.BG_RED, "The target system or system component did not satisfy all the conditions of the Rule. A fail result contributes to the maximum possible score."])
        self.help_model.append(["ERROR", commands.DHScan.BG_ERR, "The checking engine encountered a system error and could not complete the test, therefore the status of the target’s compliance with the Rule is not certain. This could happen, for example, if a Benchmark testing tool were run with insufficient privileges."])
        self.help_model.append(["UNKNOWN", commands.DHScan.BG_GRAY, "The testing tool encountered some problem and the result is unknown. For example, a result of ‘unknown’ might be given if the Benchmark testing tool were unable to interpret the output of the checking engine."])
        self.help_model.append(["NOT APPLICABLE", commands.DHScan.BG_GRAY, "The Rule was not applicable to the target of the test. For example, the Rule might have been specific to a different version of the target OS, or it might have been a test against a platform feature that was not installed. Results with this status do not contribute to the Benchmark score."])
        self.help_model.append(["NOT CHECKED", commands.DHScan.BG_GRAY, "The Rule was not evaluated by the checking engine. This status is designed for Rules that have no check properties. It may also correspond to a status returned by a checking engine. Results with this status do not contribute to the Benchmark score."])
        self.help_model.append(["NOT SELECTED", commands.DHScan.BG_GRAY, "The Rule was not selected in the Benchmark. Results with this status do not contribute to the Benchmark score."])
        self.help_model.append(["INFORMATIONAL", commands.DHScan.BG_LGREEN, "The Rule was checked, but the output from the checking engine is simply information for auditor or administrator; it is not a compliance category. This status value is designed for Rules whose main purpose is to extract information from the target rather than test compliance. Results with this status do not contribute to the Benchmark score."])
        self.help_model.append(["FIXED", commands.DHScan.BG_FIXED, "The Rule had failed, but was then fixed (possibly by a tool that can automatically apply remediation, or possibly by the human auditor). Results with this status should be scored the same as pass."])

        self.window.show_all()

    def destroy_window(self, widget):
        self.window.destroy()

