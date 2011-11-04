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

from gi.repository import Gtk

import sys
import os.path

from scap_workbench.core import paths
from scap_workbench.core import version

class ExceptionDialog(object):
    """This is a dialog that gets shown whenever an exception is thrown and
    isn't caught.
    
    See ErrorHandler
    """

    def __init__(self, exc_type, exc_message, exc_traceback):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(paths.glade_prefix, "error.glade"))
        
        self.window = self.builder.get_object("exception_dialog")
        # keep the window above to prevent the user from ignoring it
        self.window.set_keep_above(True)
        self.details = self.builder.get_object("exception_dialog:details")
        
        self.builder.connect_signals(self)
        
        import traceback
        formatted_traceback = traceback.format_tb(exc_traceback)
        self.traceback_str = "\n".join(formatted_traceback)

        buffer = Gtk.TextBuffer()
        buffer.set_text("Version: %s\n"
                        "Python version: %s\n"
                        # FIXME!
                        #"GTK version: %s\n"
                        #"PyGTK version: %s\n"
                        "\n"
                        "Exception type: %s\n"
                        "Exception message: %s\n"
                        "\n"
                        "Traceback:\n"
                        "%s" % (version.as_string, sys.version,
                                exc_type, exc_message, self.traceback_str))
        
        self.details.set_buffer(buffer)
        
    def run(self):
        return self.window.run()

    def cb_continue_clicked(self, widget, user_data = None):
        # destroy the whole dialog
        self.window.destroy()

    def cb_close_clicked(self, widget, user_data = None):
        # stop annoying the user
        ErrorHandler.uninstall_exception_hook()
        # and try to quit as soon as possible
        # we don't care about exception safety/cleaning up at this point
        sys.exit(1)
        
class ErrorHandler(object):
    @classmethod
    def install_exception_hook(cls):
        """After this method is called all uncaught exceptions will spawn the ExceptionDialog.
        
        See uninstall_exception_hook
        """
        
        sys.excepthook = ErrorHandler.excepthook

    @classmethod
    def uninstall_exception_hook(cls):
        """After this method is called the standard __excepthook__ is used (outputs exceptions to stderr)
        """
        
        sys.excepthook = sys.__excepthook__

    @classmethod
    def excepthook(cls, exc_type, exc_message, exc_traceback):
        """We are overriding sys.excepthook and setting it to this method.
        
        Internal method, do not call directly!
        """
        
        dialog = ExceptionDialog(exc_type, exc_message, exc_traceback)
        dialog.run()

        # we also call the original excepthook which will just output things to stderr
        sys.__excepthook__(exc_type, exc_message, exc_traceback)
