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

"""Provides means to do event emiting and handling
"""

from gi.repository import GObject
from gi.repository import Gtk

from scap_workbench.core.logger import LOGGER

class EventObject(GObject.GObject):
    """EventObject is abstract class handling all events between various object
    in application and general notifications.

    All objects should implement this  class.
    """

    def __init__(self, core=None):
        """ Constructor of EventObject. Call Gobject constructor for 
        signals handling. Register objects.
        """
        
        super(EventObject, self).__init__()
        self.core = core
        GObject.type_register(EventObject)
        self.object = self

        # Notifications are global for each event object
        self.notifications = []
    
    def emit(self, signal):
        """Emit signal. This is overriding GObject's method
        for better logging.

        signal: string representing the signal
        """
        
        LOGGER.debug("Emiting signal %s from %s", signal, self.id)
        super(EventObject, self).emit(signal)

    def add_sender(self, id, signal, *args):
        """Each object should register itself for sending some type
        of signal. Without registering it will be prohibited to propagate
        that signal to recievers.

        ID: unique identificator of sender
        signal: string representing the signal
        *args: optional arguments (TODO: propagation not implemented)
        """
        
        if not GObject.signal_lookup(signal, EventObject): 
            LOGGER.debug("Creating signal %s::%s", id, signal)
            GObject.signal_new(signal, EventObject, GObject.SignalFlags.RUN_FIRST, None, ())

        if self.core != None:
            self.core.set_sender(signal, self)

    def add_receiver(self, id, signal, callback, *args):
        """Add receiver by specifing what type of signal from what
        sender it should handle.

        ID: unique identifier of SENDER! of signal
        signal: identifier of signal
        callback: callable function called when signal is emitted
        """
        
        if self.core != None:
            self.core.set_receiver(id, signal, callback, args)

    def activate(self, active):
        """ This function is used to clear all general notifications
        """
        if not active:
            for notify in self.notifications:
                notify.destroy()

class EventHandler(EventObject):
    """Class EventHandler is used by CORE class and should be always
    a singleton (as well as the core object).

    This class is used to save senders and receivers and handling
    propagations of signals within them.
    """

    def __init__(self, core):
        """ Constructor of EventHandler class. EventHandler inherits
        EventObject and contains dictionary of receivers.
        """
        
        super(EventHandler, self).__init__(core)
        
        self.receivers = {}

    def set_sender(self, signal, sender):
        """This is used to connect the signal to the sender
        to call __propagate function on emit.

        The third argument of connect function is used to
        pass the name of signal to __propagate function
        """
        
        sender.connect(signal, self.__propagate, signal)

    def register_receiver(self, sender_id, signal, callback, *args):
        """Register the receiver object. There is a receivers dictionary
        which contains senders as keys and signal dictionary as value of receiver
        dictionary. The signal dictionary contains signal strings as keys
        and list of callbacks as value of the dictionary.
        """
        
        if not callable(callback):
            LOGGER.error("Given callback is not callable: %s", callback)
            return False

        LOGGER.debug("Adding receiver %s::%s::%s", sender_id, signal, callback)
        if sender_id in self.receivers:
            if signal in self.receivers[sender_id]:
                self.receivers[sender_id][signal].append(callback)
            else:
                self.receivers[sender_id][signal] = [callback]
        else: 
            self.receivers[sender_id] = {}
            self.receivers[sender_id][signal] = [callback]

        return True

    def __propagate(self, sender, signal):
        """Propagate the signal to all receivers from the sender.
        If callback is not callable, raise Exception.
        """
        
        if sender.id in self.receivers:
            if signal in self.receivers[sender.id]:
                for cb in self.receivers[sender.id][signal]:
                    LOGGER.debug("Received signal \"%s\" from \"%s\" into \"%s\"" % (signal, sender.id, cb))
                    
                    if callable(cb): 
                        cb()
                    else: 
                        LOGGER.error("Callback %s is not callable", cb)
                        raise ValueError("Registered callback is not callable! signal: %s, sender id: %s, callback: %s" % (signal, sender.id, cb))

__all__ = ["EventObject", "EventHandler"]
