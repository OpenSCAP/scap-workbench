#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Authors:
#      Maros Barabas        <mbarabas@redhat.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

import logging, logging.config
import sys, gtk, gobject, threading
from events import EventObject, EventHandler

logging.config.fileConfig("logger.conf")
logger = logging.getLogger("OSCAPEditor")

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")
sys.path.append("/tmp/scap/usr/local/lib/python2.6/site-packages")

try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    openscap=None


class OECore:

    def __init__(self):

        if len(sys.argv) > 1:
            XCCDF = sys.argv[1]
        else: XCCDF = None

        if openscap == None:
            logger.error("Can't initialize openscap library.")
            raise Exception("Can't initialize openscap library")
        self.lib = openscap.xccdf.init(XCCDF)
        if self.lib != None: 
            logger.info("Initialization done.")
        else: logger.error("Initialization failed.")

        self.eventHandler = EventHandler(self)

        self.selected_profile   = None
        self.selected_item      = None
        self.selected_deps      = None
        self.selected_lang      = "en"

    def set_sender(self, signal, sender):
        self.eventHandler.set_sender(signal, sender)

    def set_receiver(self, sender_id, signal, callback, position):
        self.eventHandler.register_receiver(sender_id, signal, callback, position)

    def set_callback(self, action, callback, position=None):
        pass

    def __destroy__(self):
        if self.lib == None: return
        if self.lib["policy_model"] != None:
            self.lib["policy_model"].free()
        for model in self.lib["def_models"]:
            model.free()
        for sess in self.lib["sessions"]:
            sess.free()

class ThreadHandler(threading.Thread):
    """
    """
    
    def __init__(self, func, obj, *args):
        """ Initializing variables """
        
        self.running = False
        self.__func = func
        self.args = args
        self.obj = obj

        threading.Thread.__init__(self)
        self.__stopthread = threading.Event()
 
    def __call__(self):
        self.start()

    def run(self):
        """ Run method, this is the code that runs while thread is alive """

        logger.debug("Running thread handler ...")

        # Run the function
        self.__func(self.obj, *self.args)


def thread(func):
    def callback(self, *args):
        handler = ThreadHandler(func, self, *args)
        handler.start()
    return callback
