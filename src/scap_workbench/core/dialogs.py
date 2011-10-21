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

""" Importing standard python libraries
"""
import gtk              # GTK library
import os               # os Path join/basename, ..
import tempfile         # Temporary file for XCCDF preview
import logging          # Logger for debug/info/error messages

""" Importing SCAP Workbench modules
"""
from scap_workbench.core import abstract                 # All abstract classes
from scap_workbench.core import commands                 # Module for handling openscap
from scap_workbench.core import Notification   # core.Notification levels for reference
from scap_workbench.core import paths

# Initializing Logger
logger = logging.getLogger("scap-workbench")

class ImportDialog(abstract.Window, abstract.ListEditor):

    """ ImportDialog class for importing XCCDF documents from main
    page of editor.
    """

    def __init__(self, core, data_model, cb):
        """Constructor
        
        core - the SWBCore singleton instance
        data_model - commands.DXccdf instance (actually it's a DataHandler, not model!)
        cb - the import callback, if the import dialog succeeds in choosing a file this
             will be called to import the file
        """
        
        # FIXME: constructors of both base classes are not called here!
        
        self.core = core
        
        self.__import = cb
        self.data_model = data_model
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "import.glade"))
        self.wdialog = builder.get_object("dialog:import")
        self.info_box = builder.get_object("dialog:import:info_box")
        self.filechooser = builder.get_object("dialog:import:filechooser")
        self.filechooser.set_filename(self.core.lib.xccdf or "")
        self.valid = builder.get_object("dialog:import:valid")
        builder.get_object("dialog:import:btn_ok").connect("clicked", self.__do)
        builder.get_object("dialog:import:btn_cancel").connect("clicked", self.__dialog_destroy)

        # TODO: Shouldn't this rather just raise an exception? Is there a use case
        #       where user can choose a callback?
        if not callable(self.__import):
            logger.critical("FATAL: Function for import is not callable")
            self.core.notify("<b>FATAL !</b> Function for import is not callable ! <a href='#bug'>Report</a>", 
                    Notification.FATAL, msg_id="notify:xccdf:import:dialog", link_cb=self.__action_link)
            return
        
        if os.access(paths.stock_data_prefix, os.X_OK):
            self.filechooser.set_current_folder(paths.stock_data_prefix)
        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()
        self.log = []

    def __cb_report(self, msg, plugin):
        self.log.append(msg.string)
        return True

    def __action_link(self, widget, action):
        """ This function is called when user clicked on hyperlink
        in the text of notification message.
        """
        if action == "#overvalid":
            self.core.notify_destroy("notify:xccdf:import:dialog")
            self.__do(overvalid=True)
        elif action == "#log":
            builder = gtk.Builder()
            builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "preview.glade"))
            preview_dialog = builder.get_object("dialog:preview")
            box = gtk.VBox()
            box.set_spacing(2)
            box.show()
            builder.get_object("dialog:preview:scw").add_with_viewport(box)
            builder.get_object("dialog:preview:btn_ok").connect("clicked", lambda w: preview_dialog.destroy())
            builder.get_object("dialog:preview:btn_save").set_property("visible", False)
            for entry in self.log:
                self.core.notify("%s" % (entry,), Notification.WARNING, info_box=box)
            preview_dialog.set_transient_for(self.wdialog)
            preview_dialog.show()

        elif action == "#bug":
            browser_val = self.data_model.open_webbrowser("http://bugzilla.redhat.com")
        else: return False

        # return True to stop handling this event by builtin mechanism
        return True

    def __do(self, widget=None, overvalid=False):
        """Performs the import.
        
        widget - the widget (usually the OK button) that caused this to happen
        overvalid - if True the validation step will be skipped
        """
        
        import_file = self.filechooser.get_filename()
        if import_file == None:
            self.core.notify("Choose a file to first.",
                Notification.INFORMATION, info_box=self.info_box, msg_id="notify:xccdf:import:dialog")
            return
        
        if not overvalid and self.valid.get_active():
            # Test the validity of exported model
            self.log = []
            retval = self.data_model.validate_file(import_file, reporter=self.__cb_report)
            if retval != True:
                self.core.notify("You are trying to import non-valid XCCDF Benchmark ! <a href='#overvalid'>Proceed</a> <a href='#log'>More</a>", 
                        Notification.WARNING, info_box=self.info_box, msg_id="notify:xccdf:import:dialog", link_cb=self.__action_link)
                #self.progress.destroy()
                return

        self.__import(import_file)
        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """Destroy the dialog window, usually as a reponse to Cancel being clicked.
        
        widget - the widget that caused this to happen
        """
        if self.wdialog: 
            self.wdialog.destroy()

class ExportDialog(abstract.Window, abstract.ListEditor):

    """ ExportDialog class for exporting XCCDF documents from main
    page of editor.
    """

    def __init__(self, core, data_model):
        # FIXME: Constructors of both base classes are not called here!
        
        self.core = core
        
        self.data_model = data_model
        builder = gtk.Builder()
        self.log = []
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "export.glade"))
        self.wdialog = builder.get_object("dialog:export")
        self.progress = builder.get_object("dialog:progress")
        self.info_box = builder.get_object("dialog:export:info_box")
        self.filechooser = builder.get_object("dialog:export:filechooser")
        self.filechooser.set_filename(self.core.lib.xccdf or "")
        self.valid = builder.get_object("dialog:export:valid")
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

        self.wdialog.set_transient_for(self.core.main_window)
        self.wdialog.show()

    def __cb_profile_clicked(self, widget):
        self.profiles_cb.set_sensitive(widget.get_active())

    def __cb_switch(self, widget):
        self.guide_box.set_sensitive(widget == self.guide_rb)

    def __cb_report(self, msg, plugin):
        self.log.append(msg.string)
        return True

    def __action_link(self, widget, action):
        """ This function is called when user clicked on hyperlink
        in the text of notification message.
        """
        if action == "#overwrite":
            self.core.notify_destroy("notify:xccdf:export:dialog")
            self.__do(overwrite=True)
        if action == "#overvalid":
            self.core.notify_destroy("notify:xccdf:export:dialog")
            self.__do(overvalid=True)
        elif action == "#browser":
            self.core.notify_destroy("notify:xccdf:export")
            browser_val = self.data_model.open_webbrowser(self.export_file)
        elif action == "#webkit":
            self.core.notify_destroy("notify:xccdf:export")
            f = open(self.export_file)
            desc = f.read()
            f.close()
            self.preview(widget=None, desc=desc)
        elif action == "#log":
            builder = gtk.Builder()
            builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "preview.glade"))
            preview_dialog = builder.get_object("dialog:preview")
            box = gtk.VBox()
            box.set_spacing(2)
            box.show()
            builder.get_object("dialog:preview:scw").add_with_viewport(box)
            builder.get_object("dialog:preview:btn_ok").connect("clicked", lambda w: preview_dialog.destroy())
            builder.get_object("dialog:preview:btn_save").set_property("visible", False)
            for entry in self.log:
                self.core.notify("%s" % (entry,), Notification.WARNING, info_box=box)
            preview_dialog.set_transient_for(self.wdialog)
            preview_dialog.show()

        # return True to stop handling this event by builtin mechanism
        return True

    def __do(self, widget=None, overwrite=False, overvalid=False):
        #self.progress.set_transient_for(self.wdialog)
        #self.progress.show()
        export_file = self.filechooser.get_filename()
        if export_file == None:
            self.core.notify("Choose a file to save to first.",
                Notification.INFORMATION, info_box=self.info_box, msg_id="dialog:export:notify")
            #self.progress.destroy()
            return
        
        self.export_file = export_file

        if not overwrite and export_file == self.core.lib.xccdf and self.guide_rb.get_active():
            # We are trying to export guide to the XCCDF file (common mistake)
            self.core.notify("You are trying to overwrite loaded XCCDF Benchmark by XCCDF Guide ! <a href='#overwrite'>Proceed</a>", 
                    Notification.WARNING, info_box=self.info_box, msg_id="notify:xccdf:export:dialog", link_cb=self.__action_link)
            #self.progress.destroy()
            return

        if not overvalid and self.valid.get_active():
            # Test the validity of exported model
            self.log = []
            retval = self.data_model.validate(reporter=self.__cb_report)
            if not retval:
                self.core.notify("You are trying to export non-valid XCCDF Benchmark ! <a href='#overvalid'>Proceed</a> <a href='#log'>More</a>", 
                        Notification.WARNING, info_box=self.info_box, msg_id="notify:xccdf:export:dialog", link_cb=self.__action_link)
                #self.progress.destroy()
                return

        if self.file_rb.get_active():
            # we are exporting to file
            file_name = self.data_model.export(export_file)
            self.core.notify("Benchmark has been exported to \"%s\"" % (file_name,),
                    Notification.SUCCESS, msg_id="notify:xccdf:export")
            self.core.lib.xccdf = file_name
        else:
            # we are exporting as guide
            if not self.data_model.resolve():
                self.core.notify("Benchmark resolving failed",
                        Notification.ERROR, info_box=self.info_box, msg_id="notify:xccdf:export")
                #self.progress.destroy()
                return
            elif not self.core.lib.xccdf:
                self.core.notify("Benchmark is not exported. Export benchmark first !",
                        Notification.INFORMATION, info_box=self.info_box, msg_id="notify:xccdf:export")
                #self.progress.destroy()
                return

            temp = tempfile.NamedTemporaryFile()
            retval = self.data_model.export(temp.name)
            profile = None
            if self.profiles_cb.get_active() != -1:
                profile = self.profiles_cb.get_model()[self.profiles_cb.get_active()][0]
            self.data_model.export_guide(temp.name, export_file, profile, not self.profile.get_active())
            self.core.notify("The guide has been exported to \"%s\". <a href='#browser'>View in browser</a> <a href='#webkit'>View in WebKit</a>" % (export_file,),
                    Notification.SUCCESS, msg_id="notify:xccdf:export", link_cb=self.__action_link)
            temp.close()
            #self.progress.destroy()

        self.__dialog_destroy()

    def __dialog_destroy(self, widget=None):
        """
        """
        if self.wdialog: 
            self.wdialog.destroy()

        
