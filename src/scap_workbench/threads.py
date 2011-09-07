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

import logging
import threading
import time
logger = logging.getLogger("scap-workbench")

def thread(func):
    def callback(self, *args, **kwargs):
        self.core.thread_handler.new_thread(func, self, *args, **kwargs)
    return callback

def thread_free(func):
    def callback(self, *args, **kwargs):
        handler = ThreadHandler(None, func, self, *args, **kwargs)
        if handler:
            logger.debug("Running thread handler (free) \"%s:%s\"", func, args)
            handler.start()
    return callback


class ThreadManager(object):

    def __init__(self, core):
        self.core = core
        self.handlers = []

    def new_thread(self, func, obj, *args, **kwargs):
        handler = ThreadHandler(self, func, obj, *args, **kwargs)
        if handler: handler.start()

    def start_thread(self, func, obj, *args, **kwargs):
        while func in self.handlers:
            logger.debug("Handler for function %s already running, waiting..." % (func,))
            time.sleep(1.0)

        self.handlers.append(func)
        func(obj, *args, **kwargs)
        logger.debug("Running thread handler \"%s:%s\"", func, args)

    def stop_thread(self, func):
        if func not in self.handlers:
            logger.warning("Function called stop, but no function %s running" % (func,))
        else: logger.debug("Thread function %s stopped." % (func,))
        self.handlers.remove(func)

class ThreadHandler(threading.Thread):
    """
    """
    def __init__(self, master, func, obj, *args, **kwargs):
        """ Initializing variables """
     
        self.running = False
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs
        self.__obj = obj
        self.__master = master

        threading.Thread.__init__(self)
        self.__stopthread = threading.Event()
 
    def __call__(self):
        self.start()

    def run(self):
        """ Run method, this is the code that runs while thread is alive """

        # Run the function
        if self.__master:
            self.__master.start_thread(self.__func, self.__obj, *self.__args, **self.__kwargs)
            self.__master.stop_thread(self.__func)
        else: self.__func(self.__obj, *self.__args, **self.__kwargs)


