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
#      Martin Preisler <mpreisle@redhat.com>

"""This package encapsulates all editor specific functionality
"""

from gi.repository import Gtk

from scap_workbench import core
from scap_workbench import paths

from scap_workbench.core import abstract
from scap_workbench.core import error

from scap_workbench.editor import xccdf
from scap_workbench.editor import profiles
from scap_workbench.editor import items

import os.path

import logging
logger = logging.getLogger("scap-workbench")

class MainWindow(abstract.Window):
    """The central window of scap-workbench-editor
    """
    
    def __init__(self):
        error.install_exception_hook()
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(paths.glade_prefix, "editor.glade"))
        self.builder.connect_signals(self)
        
        super(MainWindow, self).__init__("main:window", core.SWBCore(self.builder))
        
        if self.core is None:
            raise RuntimeError("Initialization failed, core is None")

        self.window = self.builder.get_object("main:window")
        # we have to set the icon here because it would have to be hardcoded in the glade file,
        # this way the paths module guesses prefix and all paths for us
        self.window.set_icon_from_file(os.path.join(paths.pixmaps_prefix, "scap-workbench-editor.png"))
        self.core.main_window = self.window
        self.main_box = self.builder.get_object("main:box")

        # abstract the main menu
        # FIXME: Instantiating abstract class
        self.menu = abstract.Menu("gui:menu", self.builder.get_object("main:toolbar"), self.core)
        self.menu.add_item(xccdf.MenuButtonEditXCCDF(self.builder, self.builder.get_object("main:toolbar:main"), self.core))
        self.menu.add_item(profiles.MenuButtonEditProfiles(self.builder, self.builder.get_object("main:toolbar:profiles"), self.core))
        self.menu.add_item(items.MenuButtonEditItems(self.builder, self.builder.get_object("main:toolbar:items"), self.core))

        self.window.show()
        self.builder.get_object("main:toolbar:main").set_active(True)

        self.core.get_item("gui:btn:menu:edit:XCCDF").update()
        if self.core.lib.loaded:
            self.core.get_item("gui:btn:menu:edit:profiles").set_sensitive(True)
            self.core.get_item("gui:btn:menu:edit:items").set_sensitive(True)

    def delete_event(self, widget, event, data=None):
        """Closes the window and quits
        """
        
        # since we are quitting gtk we can't be popping a dialog when exception happens anymore
        error.uninstall_exception_hook()
 
        Gtk.main_quit()
        return False

    def run(self):
        Gtk.main()

# we only expose the MainWindow from the entire editor subpackage because that's all that's needed to start the app
__all__ = ["MainWindow"]
