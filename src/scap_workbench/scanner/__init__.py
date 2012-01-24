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

""" Importing standard python libraries
"""
from gi.repository import Gtk
from gi.repository import Gdk

import threading        # Main window is running in thread
import os.path
import logging          # Logger for debug/info/error messages

""" Importing SCAP Workbench modules
"""
from scap_workbench import core
from scap_workbench.core import abstract
from scap_workbench import paths
from scap_workbench.core import error

from scap_workbench.scanner import xccdf
from scap_workbench.scanner import tailoring
from scap_workbench.scanner import scan

# Initializing Logger
logger = logging.getLogger("scap-workbench")

class MenuButtonOVAL(abstract.MenuButton):
    ## INTERNAL: This is not used anywhere in the application, probably work in progress code?
    def __init__(self, box, widget, core):
        logger = logging.getLogger(self.__class__.__name__)
        super(MenuButtonOVAL, self).__init__("gui:btn:main:oval", widget, core)
        
        self.box = box
        self.title = None
        self.description = None
        self.version = None
        self.url = None
        self.language = None
        self.body = self.draw_body()

    def draw_body(self):
        body = Gtk.VBox()

        body.show_all()
        body.hide()
        self.box.add(body)
        return body

class MainWindow(abstract.Window):
    """The central window of scap-workbench (scanner)
    """

    def __init__(self):
        error.install_exception_hook()

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(paths.glade_prefix, "scanner.glade"))
        self.builder.connect_signals(self)
        
        super(MainWindow, self).__init__("gui:main", core.SWBCore(self.builder, True))
        
        if self.core is None:
            raise RuntimeError("Initialization failed, core is None")

        self.window = self.builder.get_object("main:window")
        # we have to set the icon here because it would have to be hardcoded in the glade file,
        # this way the paths module guesses prefix and all paths for us
        self.window.set_icon_from_file(os.path.join(paths.pixmaps_prefix, "scap-workbench.png"))
        self.core.main_window = self.window
        self.main_box = self.builder.get_object("main:box")
        self.add_sender(self.id, "quit") # Quit the application

        # abstract the main menu
        # FIXME: Instantiating an abstract class?!
        self.menu = abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
        self.menu.add_item(xccdf.MenuButtonXCCDF(self.builder, self.builder.get_object("main:toolbar:main"), self.core))
        # FIXME: Instantiating an abstract class?!
        self.menu.add_item(abstract.MenuButton("gui:btn:menu:reports", self.builder.get_object("main:toolbar:reports"), self.core))
        self.menu.add_item(tailoring.MenuButtonTailoring(self.builder, self.builder.get_object("main:toolbar:tailoring"), self.core))
        self.menu.add_item(scan.MenuButtonScan(self.builder, self.builder.get_object("main:toolbar:scan"), self.core))
        
        self.window.show()
        self.builder.get_object("main:toolbar:main").set_active(True)

        self.core.get_item("gui:btn:main:xccdf").update()

    def __cb_info_close(self, widget):
        self.core.info_box.hide()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        self.emit("quit")
        Gdk.threads_leave()
        
        # since we are quitting gtk we can't be popping a dialog when exception happens anymore
        error.uninstall_exception_hook()
        Gtk.main_quit()
        return False

    def run(self):
        Gtk.main()

# we only expose the MainWindow from the entire scanner subpackage because that's all that's needed to start the app
__all__ = ["MainWindow"]
