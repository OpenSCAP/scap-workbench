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

"""Implements the actual scanning process and GUI around it
"""

from gi.repository import Gtk
from gi.repository import Gdk

import os
import tempfile
import shutil

from scap_workbench import core
from scap_workbench import paths
from scap_workbench import l10n
from scap_workbench.core import abstract
from scap_workbench.core import commands
from scap_workbench.core import filter
from scap_workbench.core.threads import thread as threadSave
from scap_workbench.core.logger import LOGGER

import openscap_api as openscap

class ScanList(abstract.List):

    def __init__(self, widget, core, filter, data_model):
        self.data_model = data_model
        super(ScanList, self).__init__("gui:scan:scan_list", core, widget=widget)

        self.filter = filter

        selection = self.get_TreeView().get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
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

class DHScan(commands.DataHandler, commands.EventObject):

    COLUMN_ID = 0               # id of rule
    COLUMN_RESULT = 1           # Result of scan
    COLUMN_FIX = 2              # fix
    COLUMN_TITLE = 3            # Description of rule
    COLUMN_DESC = 4             # Description of rule
    COLUMN_COLOR_TEXT_TITLE = 5 # Color of text description
    COLUMN_COLOR_BACKG = 6      # Color of cell
    COLUMN_COLOR_TEXT_ID = 7    # Color of text ID

    RESULT_NAME = "SCAP WORKBENCH Test Result"

    FG_TITLE_NORMAL = "#000000"
    FG_TITLE_PASS   = "#333333"
    FG_TITLE_ERROR  = "#ff0000"
    FG_TITLE_FAIL   = "#ff0000"
    FG_TITLE_NOT_APPLICABLE = "#333333"
    FG_TITLE_NOT_CHECKED = "#333333"
    FG_TITLE_NOT_SELECTED = "#333333"
    FG_TITLE_INFORMATIONAL = "#333333"
    FG_TITLE_FIXED = "#333333"

    FG_ID_NORMAL    = "#000000"
    FG_ID_PASS      = "#333333"
    FG_ID_ERROR     = "#ff0000"

    BG_RUNNING = "#ffffff"
    BG_PASS    = "#9DF29D"
    BG_FAIL    = "#F29D9D"
    BG_ERROR   = "#ff0000"
    BG_UNKNOWN = "#666666"
    BG_NOT_APPLICABLE = "#ffffff"
    BG_NOT_CHECKED = "#ffffff"
    BG_NOT_SELECTED = "#ffffff"
    BG_INFORMATIONAL = "#ADFFAD"
    BG_FIXED  = "#00ff00"

    def __init__(self, id, core, progress=None):
        commands.DataHandler.__init__(self, core)
        commands.EventObject.__init__(self, core)

        self.id = id
        self.__progress=progress
        self.__cancel = False
        self.count_current = 0
        self.count_all = 0
        self.result = None

        core.register(id, self)
        self.add_sender(self.id, "filled")

        self.policy = None

    def new_model(self):
        return Gtk.TreeStore(str, str, str, str, str, str, str, str)

    def render(self, treeView):
        """ define treeView"""

        self.treeView = treeView

        #model: id rule, result, fix, description, color text desc, color background, color text res
        self.model = self.new_model()
        treeView.set_model(self.model)
        #treeView.set_grid_lines(Gtk.TREE_VIEW_GRID_LINES_BOTH)
        #treeView.set_property("tree-line-width", 10)

        # ID Rule
        txtcell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Rule ID"), txtcell, text=DHScan.COLUMN_ID)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT_ID)
        column.set_resizable(True)
        treeView.append_column(column)

        #Result
        txtcell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Result"), txtcell, text=DHScan.COLUMN_RESULT)
        column.add_attribute(txtcell, 'background', DHScan.COLUMN_COLOR_BACKG)
        # since we control the background in this case, we have to enforce foreground as well so
        # that the text is visible
        txtcell.set_property('foreground', '#000000')
        column.set_resizable(True)
        treeView.append_column(column)

        # Fix
        txtcell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Fix"), txtcell, text=DHScan.COLUMN_FIX)
        column.set_resizable(True)
        column.set_visible(False)
        treeView.append_column(column)

        # Title
        txtcell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), txtcell, text=DHScan.COLUMN_TITLE)
        column.add_attribute(txtcell, 'foreground', DHScan.COLUMN_COLOR_TEXT_TITLE)
        column.set_resizable(True)
        treeView.append_column(column)

        # Description
        txtcell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Description"), txtcell, text=DHScan.COLUMN_DESC)
        column.set_resizable(True)
        column.set_visible(False)
        id = treeView.append_column(column)
        treeView.set_tooltip_column(id-1)

    def fill(self, item, iter=None):
        #initialization
        colorText_title = DHScan.FG_TITLE_NORMAL
        color_backG = DHScan.BG_ERROR
        colorText_ID = DHScan.FG_ID_NORMAL
        text = ""

        # choose color for cell, and text of result
        if  item[DHScan.COLUMN_RESULT] == None:
            text = _("Running ..")
            color_backG = DHScan.BG_RUNNING
            colorText_title = DHScan.FG_TITLE_NORMAL
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_PASS:
            text = "PASS" # The test passed
            color_backG = DHScan.BG_PASS
            colorText_title = DHScan.FG_TITLE_PASS
            colorText_ID = DHScan.FG_ID_PASS

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_FAIL:
            text = "FAIL" # The test failed
            color_backG = DHScan.BG_FAIL
            colorText_title = DHScan.FG_TITLE_FAIL
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_ERROR:
            text = "ERROR" # An error occurred and test could not complete
            color_backG = DHScan.BG_ERROR
            colorText_title = DHScan.FG_TITLE_ERROR
            colorText_ID = DHScan.FG_ID_ERROR

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_UNKNOWN:
            text = "UNKNOWN" #  Could not tell what happened
            color_backG = DHScan.BG_UNKNOWN
            colorText_title = DHScan.FG_TITLE_NORMAL
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_APPLICABLE:
            text = "NOT_APPLICABLE" # Rule did not apply to test target
            color_backG = DHScan.BG_NOT_APPLICABLE
            colorText_title = DHScan.FG_TITLE_NOT_APPLICABLE
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_CHECKED:
            text = "NOT_CHECKED" # Rule did not cause any evaluation by the checking engine
            color_backG = DHScan.BG_NOT_CHECKED
            colorText_title = DHScan.FG_TITLE_NOT_CHECKED
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
            text = "NOT_SELECTED" #Rule was not selected in the @link xccdf_benchmark Benchmark@endlink
            color_backG = DHScan.BG_NOT_SELECTED
            colorText_title = DHScan.FG_TITLE_NOT_SELECTED
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_INFORMATIONAL:
            text = "INFORMATIONAL" # Rule was evaluated by the checking engine, but isn't to be scored
            color_backG = DHScan.BG_INFORMATIONAL
            colorText_title = DHScan.FG_TITLE_INFORMATIONAL
            colorText_ID = DHScan.FG_ID_NORMAL

        elif  item[DHScan.COLUMN_RESULT] == openscap.OSCAP.XCCDF_RESULT_FIXED:
            text = "FIXED" # Rule failed, but was later fixed
            color_backG = DHScan.BG_FIXED
            colorText_title = DHScan.FG_TITLE_FIXED
            colorText_ID = DHScan.FG_ID_NORMAL

        if not iter:
            iter = self.model.append(None)

        self.model.set(iter,
                DHScan.COLUMN_ID,   item[DHScan.COLUMN_ID],
                DHScan.COLUMN_RESULT,   text,
                DHScan.COLUMN_FIX,    str(item[DHScan.COLUMN_FIX]),
                DHScan.COLUMN_TITLE,  item[DHScan.COLUMN_TITLE],
                DHScan.COLUMN_DESC,  item[DHScan.COLUMN_DESC],
                DHScan.COLUMN_COLOR_TEXT_TITLE,  colorText_title,
                DHScan.COLUMN_COLOR_BACKG,  color_backG,
                DHScan.COLUMN_COLOR_TEXT_ID,  colorText_ID,
                )
        return iter

    @classmethod
    def __decode_callback_message(cls, msg):
        """Decodes a callback message and returns a 3-tuple containing the
        result, title and description of the test performed, in that order.

        This method is only to be used in __callback_start and __callback_output.
        """

        id = msg.user1str
        result = msg.user2num

        # The join of split string is used to convert all whitespace characters,
        # including newlines, tabs, etc, to plain spaces.
        #
        # In this case we need to do this because we are filling a table and
        # only have one line for all entries
        title = " ".join(msg.user3str.split()) if msg.user3str is not None else ""
        desc  = " ".join(msg.string.split()) if msg.string is not None else ""

        return (id, result, title, desc)

    def __callback_start(self, msg, plugin):
        """Start callback is registered in "prepare" method and is called
        when each of the tests to be performed starts.

        When a test ends, __callback_output is called for it. __callback_output is always
        called after __callback_start has been called for that particular test.

        See __callback_output
        """

        with core.gdk_lock:
            id, result, title, desc = DHScan.__decode_callback_message(msg)
            if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
                return self.__cancel

            self.__current_iter = self.fill([msg.user1str, None, False, title, desc])

            if self.__progress is not None:
                # a check is starting, that means that all the preparations
                # have just been done or have been already done long before
                # this point
                # we count the preparation as one step
                min_fraction = float(1) / float(self.count_all + 1)
                if self.__progress.get_fraction() < min_fraction:
                    self.__progress.set_fraction(min_fraction)

                self.__progress.set_text(_("Scanning rule '%(rule_id)s' ... (%(step)i/%(total)i)") % {"rule_id": id, "step": self.count_current + 1, "total": self.count_all})
                LOGGER.debug("[%s/%s] Scanning rule '%s'" % (self.count_current + 1, self.count_all, id))

                self.__progress.set_tooltip_text(_("Scanning rule '%s'") % (title))

            return self.__cancel

    def __callback_output(self, msg, plugin):
        """The output callback is registered in "prepare" method and is called
        when each of the tests to be performed ends (regardless of the result).

        See __callback_start
        """

        with core.gdk_lock:
            id, result, title, desc = DHScan.__decode_callback_message(msg)
            if result == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
                return self.__cancel

            self.count_current += 1

            self.fill([id, result, False, title, desc], iter=self.__current_iter)
            self.emit("filled")
            self.treeView.queue_draw()

            self.__progress.set_fraction(float(self.count_current + 1) / float(self.count_all + 1))

            return self.__cancel

    def clear(self, count_all = 0):
        self.model.clear()

        self.count_current = 0
        self.count_all = count_all

        if self.core.lib.sce_parameters is not None:
            # clear the SCE session of all previous results
            self.core.lib.sce_parameters.get_session().reset()

    def prepare(self):
        """Prepare system for evaluation
        return False if something goes wrong, True otherwise
        """

        if not self.core.registered_callbacks:
            self.core.lib.policy_model.register_start_callback(self.__callback_start, self)
            self.core.lib.policy_model.register_output_callback(self.__callback_output, self)
            self.core.registered_callbacks = True

        else:
            # callbacks were already registered, there is a chance an OVAL session
            # is still running and needs to be cancelled
            for oval in self.core.lib.oval_files.values():
                retval = openscap.oval.agent_reset_session(oval.session)
                LOGGER.debug("OVAL Agent session reset: %s" % (retval,))
                if retval != 0:
                    self.core.notify(_("OVAL agent reset session failed."), core.Notification.ERROR, msg_id="notify:scan:oval_reset")
                    raise RuntimeError("OVAL agent reset session failed, openscap return value: %i" % (retval))

        self.__cancel = False

        if self.core.selected_profile == None:
            self.policy = self.core.lib.policy_model.policies[0]
        else:
            self.policy = self.core.lib.policy_model.get_policy_by_id(str(self.core.selected_profile))

        self.clear(count_all = len(self.policy.selected_rules))

        return True

    def cancel(self):
        """ Called by user event when stop button pressed
        """
        self.__cancel = True
        if not self.check_library(): return None
        for oval in self.core.lib.oval_files.values():
            retval = openscap.oval.agent_abort_session(oval.session)
            LOGGER.debug("OVAL Agent session abort: %s" % (retval,))

    def export(self, file_name, result):
        """Exports a raw XML results file"""

        if self.core.lib == None:
            return False

        if file_name is None:
            file_name = self.file_browse(_("Save results"), file="results.xml")

        if file_name != "":
            sessions = {}
            for oval in self.core.lib.oval_files.values():
                sessions[oval.path] = oval.session

            files = self.policy.export(result, DHScan.RESULT_NAME, file_name, file_name, self.core.lib.xccdf, sessions)

            for file in files:
                LOGGER.debug("Exported: %s", file)

            if self.core.lib.sce_parameters is not None:
                # export SCE results to directory where file file_name is located
                self.core.lib.sce_parameters.get_session().export_to_directory(os.path.dirname(file_name))

            return file_name

        else:
            return None

    def perform_xslt_transformation(self, file, xslfile=None, expfile=None, hide_profile=None, result_id=None, oval_path="/tmp", sce_path="/tmp"):
        """Performs XSLT transformation on given file (raw XML results data, from DHScan.export for example).

        The resulting file (expfile) is the given raw XML results file transformed. Depending on the XSLT transformation
        used this can be anything XHTML, PDF, ...
        """

        params = [
            "result-id",         result_id,
            "show",              None,
            "profile",           self.core.selected_profile,
            "template",          None,
            "format",            None,
            "hide-profile-info", hide_profile,
            "verbosity",         "",
            "oscap-version",     openscap.common.oscap_get_version(),
            "pwd",               os.getcwd(),
            "oval-template",     os.path.join(oval_path, "%.result.xml"),
            "sce-template",      os.path.join(sce_path,  "%.result.xml")
        ]

        if not xslfile:
            xslfile = "xccdf-report.xsl"

        if not expfile:
            expfile = "%s-report.xhtml" % (file)

        retval = openscap.common.oscap_apply_xslt(file, xslfile, expfile, params)
        # TODO If this call (below) is not executed, there will come some strange behaviour
        LOGGER.debug("Export report file %s" % (["failed: %s" % (openscap.common.err_desc(),), "done"][retval],))
        return expfile

class MenuButtonScan(abstract.MenuButton, abstract.Func):
    """Button and GUI for scanning, contains results and various buttons to control
    the scanning process.
    """

    def __init__(self, builder, widget, core):
        self.builder = builder

        abstract.MenuButton.__init__(self, "gui:btn:menu:scan", widget, core)
        abstract.Func.__init__(self, core)

        self.exported_file = None
        self.scan_running = False
        self.scan_cancelled = False
        self.selected_profile = None

        self.progress = self.builder.get_object("scan:progress")
        self.data_model = DHScan("gui:scan:DHScan", core, self.progress)

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
        self.add_receiver("gui:btn:main:xccdf", "load", self.__cb_clear)

        self.set_scan_in_progress(False, previously_scanned = False)

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
                self.notifications.append(self.core.notify(_("Selected profile: \"%s\".") % (title,), core.Notification.SUCCESS, msg_id="notify:scan:selected_profile"))
                # profile changed so we make export and view results buttons insensitive
                self.set_scan_in_progress(False, previously_scanned = False)

            self.selected_profile = self.core.selected_profile

            self.profile.set_tooltip_text(_("Current profile: %s") % (title))

        else:
            # if self.core.selected_profile is None the current profile is "No profile"
            if self.selected_profile != self.core.selected_profile:
                self.notifications.append(self.core.notify(_("Selected default document profile."), core.Notification.SUCCESS, msg_id="notify:scan:selected_profile"))
                # profile changed so we make export and view results buttons insensitive
                self.set_scan_in_progress(False, previously_scanned = False)

            self.selected_profile = None

            self.profile.set_tooltip_text(_("Current profile: (No profile)"))

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
            Gdk.flush()

            dirname = tempfile.mkdtemp()
            try:
                raw_file = os.path.join(dirname, "result.xml")
                transformed_file = os.path.join(dirname, "report.html")

                if not self.data_model.export(file_name = raw_file,
                                              result = self.result):
                    self.notifications.append(self.core.notify(_("Export failed."), core.Notification.ERROR, msg_id="notify:scan:export"))
                    return

                self.data_model.perform_xslt_transformation(file = raw_file,
                                                            expfile = transformed_file,
                                                            result_id = self.result.id,
                                                            oval_path = dirname,
                                                            sce_path = dirname)

                desc = open(transformed_file).read()

                self.preview(widget = None, desc = desc, save = self.__cb_save_report)

            finally:
                # no matter what happens, make sure we clean up after ourselves
                shutil.rmtree(dirname)

        else:
            self.notifications.append(self.core.notify(_("Nothing to export."), core.Notification.ERROR, msg_id="notify:scan:export"))

    def __cb_save_report(self, append_notifications = False):
        """ This method is used as callback to preview dialog window. When user press "save" button
        this function will be called and saved the report to the file.

        append_notifications - if True this method will immediately append notifications as necessary,
                               otherwise it will return a notification 2-tuple
        """

        chooser = Gtk.FileChooserDialog(title = _("Save results to directory"),
                                        action = Gtk.FileChooserAction.SELECT_FOLDER,
                                        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            dirname = chooser.get_uri()
            assert(dirname.startswith("file://"))
            dirname = dirname[7:] # strips the "file://" prefix

            file_name = os.path.join(dirname, "result.xml")

            chooser.destroy()

            # this would have better been solved with exceptions (see http://en.wikipedia.org/wiki/Time-of-check-to-time-of-use)
            # however in this case we have to work with what we have and openscap won't return this info in any form we could use

            # the reason for the double check is that os.access("nonexistant file but user can create it", os.W_OK) returns False,
            # so we check the parent directory for writing instead in that case
            if (os.path.isfile(file_name) and not os.access(file_name, os.W_OK)) or (not os.access(os.path.dirname(file_name), os.W_OK)):
                ret = (core.Notification.ERROR, _("Export failed - chosen file path isn't accessible for writing"))
                if append_notifications:
                    self.notifications.append(self.core.notify(ret[1], ret[0], msg_id="notify:scan:export"))
                else:
                    return ret

            else:
                retval = self.data_model.export(file_name, self.result)
                # TODO: More info about the error
                ret = (core.Notification.ERROR, _("Export failed")) if not retval else (core.Notification.SUCCESS, _("Report file and results exported successfully"))

                # TODO: We should be more robust and do more error checking here
                self.data_model.perform_xslt_transformation(file = retval,
                                                            result_id = self.result.id,
                                                            expfile = os.path.join(dirname, "report.html"),
                                                            oval_path = dirname,
                                                            sce_path = dirname)

                if append_notifications:
                    self.notifications.append(self.core.notify(ret[1], ret[0], msg_id="notify:scan:export"))
                else:
                    return ret

        else:
            chooser.destroy()
            return None, None

    def __cb_profile(self, widget):
        for notify in self.notifications:
            notify.destroy()
        if self.core.lib.loaded == None:
            self.core.notify(_("Library not initialized or XCCDF file not specified"),
                    core.Notification.INFORMATION, msg_id="notify:xccdf:not_loaded")
            return
        ProfileChooser(self.core, self.__update_profile)

    def __cb_scan(self, widget=None):
        if self.scan_running:
            LOGGER.error("Scan already running")
            return

        self.exported_file = None
        for notify in self.notifications:
            notify.destroy()

        self.emit("scan")
        self.data_model.prepare()
        self.__th_scan()

    def set_scan_in_progress(self, active, previously_scanned = True):
        """This method manages sensitivity of various buttons according to whether scanning
        is in progress or not. Also manages self.scan_running

        active - whether scanning is currently underway
        previously_scanned - have we scanned before? only applies if active if False
        """

        self.scan_running = active
        if active:
            self.scan_cancelled = False

        self.stop.set_sensitive(active)
        self.scan.set_sensitive(not active)
        self.export.set_sensitive(not active and previously_scanned)
        self.results.set_sensitive(not active and previously_scanned)
        self.profile.set_sensitive(not active)

    @threadSave
    def __th_scan(self):
        """Starts scanning in a separate thread (via the @threadSave decorator, see threads.py)
        """

        with core.gdk_lock:
            if not self.data_model.check_library():
                return None

            self.set_scan_in_progress(True)

            if self.progress is not None:
                self.progress.set_fraction(0.0)
                self.progress.set_text(_("Preparing..."))

            self.core.notify_destroy("notify:scan:complete")

            LOGGER.debug("Scanning %s ..", self.data_model.policy.id)

        # at this point evaluation will keep working in this thread,
        # DHScan.__callback_start and DHScan.__callback_end will get called when each
        # of the tests will run and that is what is filling the scan results table
        self.result = self.data_model.policy.evaluate()

        # the scan finished (successfully or maybe it was canceled)
        with core.gdk_lock:
            if self.progress:
                # set the progress to 100% regardless of how many tests were actually run
                self.progress.set_fraction(1.0)
                self.progress.set_text(_("Finished %(finished_rules)i of %(total)i rules") % {"finished_rules": self.data_model.count_current, "total": self.data_model.count_all})
                self.progress.set_has_tooltip(False)

            LOGGER.debug("Finished scanning")
            if self.scan_cancelled:
                self.core.notify(_("Scanning prematurely interrupted by user"), core.Notification.INFORMATION, msg_id="notify:scan:complete")
            else:
                self.core.notify(_("Scanning finished successfully"), core.Notification.SUCCESS, msg_id="notify:scan:complete")

            self.core.notify_destroy("notify:scan:cancel")

            self.set_scan_in_progress(False)

    def __cb_cancel(self, widget=None):
        """ Called by user event when stop button pressed
        """
        if self.scan_running:
            self.core.notify(_("Scanning canceled. Please wait for openscap to finish current task."), core.Notification.INFORMATION, msg_id="notify:scan:cancel")
            self.scan_cancelled = True
            self.data_model.cancel()

    def __cb_help(self, widget):
        window = HelpWindow(self.core)

    def __cb_clear(self):
        self.data_model.clear()

class ProfileChooser(object):
    """
    Modal window for choosing profile before scan
    """

    def __init__(self, core, callback=None):
        self.callback = callback
        self.core = core
        self.data_model = commands.DHProfiles(core)

        builder = Gtk.Builder()
        builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "profile_change.glade"))

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

    def __do(self, widget, event = None):
        if event and event.type == Gdk.EventType.KEY_PRESS and event.keyval != Gdk.KEY_Return:
            return

        selection = self.profiles.get_selection()
        model, it = selection.get_selected()
        if it is None:
            LOGGER.debug("Nothing selected, skipping")
            self.__dialog_destroy()
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

        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(l10n.TRANSLATION_DOMAIN)
        self.builder.add_from_file(os.path.join(paths.glade_prefix, "scan_help.glade"))

        self.window = None
        self.treeView = None
        self.help_model = None

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
        selection.set_mode(Gtk.SelectionMode.NONE)

        self.help_model[0][1] = DHScan.BG_PASS
        self.help_model[1][1] = DHScan.BG_FAIL
        self.help_model[2][1] = DHScan.BG_ERROR
        self.help_model[3][1] = DHScan.BG_UNKNOWN
        self.help_model[4][1] = DHScan.BG_NOT_APPLICABLE
        self.help_model[5][1] = DHScan.BG_NOT_CHECKED
        self.help_model[6][1] = DHScan.BG_NOT_SELECTED
        self.help_model[7][1] = DHScan.BG_INFORMATIONAL
        self.help_model[8][1] = DHScan.BG_FIXED

        self.window.set_transient_for(self.core.main_window)
        self.window.show_all()

    def destroy_window(self, widget):
        self.window.destroy()
