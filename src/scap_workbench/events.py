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

import gobject, gtk
import logging

logger = logging.getLogger("scap-workbench")

class EventObject(gobject.GObject):

    def __init__(self, core=None):
        self.__gobject_init__()
        self.core = core
        gobject.type_register(EventObject)
        self.object = self
    
    def emit_signal(self, signal):
        logger.debug("Emiting signal %s from %s", signal, self.id)
        self.emit(signal)

    def add_sender(self, id, signal, *args):

        if not gobject.signal_lookup(signal, EventObject): 
            logger.debug("Creating signal %s::%s", id, signal)
            gobject.signal_new(signal, EventObject, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())

        if self.core != None: self.core.set_sender(signal, self)

    def add_receiver(self, id, signal, callback, position=-1, *args):

        if self.core != None: self.core.set_receiver(id, signal, callback, position)

class EventHandler(EventObject):

    def __init__(self, core):
        """
        event is dictionary: "<action_name>": list of actions
        """
        super(EventHandler, self).__init__(core)
        self.core = core
        self.receivers = {}

    def set_sender(self, signal, sender):
        sender.connect(signal, self.propagate, signal)

    def register_receiver(self, sender_id, signal, callback, position=-1):

        if position == None or not isinstance(position, int):
            logger.error("Position has to be an Integer ! Got %s", type(position))
            return False

        if not callable(callback):
            logger.error("Given callback is not callable: %s", callback)
            return False

        logger.debug("Adding receiver %s::%s::%s", sender_id, signal, callback)
        if sender_id in self.receivers:
            if signal in self.receivers[sender_id]:
                self.receivers[sender_id][signal].insert(position, callback)
            else: self.receivers[sender_id][signal] = [callback]
        else: 
            self.receivers[sender_id] = {}
            self.receivers[sender_id][signal] = [callback]

        return True

    def propagate(self, sender, signal):
        if sender.id in self.receivers:
            if signal in self.receivers[sender.id]:
                for cb in self.receivers[sender.id][signal]:
                    if callable(cb): cb()
                    else: 
                        logger.error("Callback %s is not callable", cb)
                        raise Exception
