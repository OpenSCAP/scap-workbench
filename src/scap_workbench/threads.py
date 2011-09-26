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
    """Usually used as a decorator to make a method start a thread
    and execute itself in it. The central self.core.thread_handler
    is used (despite being called thread_handler it is actually
    threads.ThreadManager).
    
    IMPORTANT: Only use on methods from classes that have attribute "core",
               so that self.core is accessible!
    """
    
    def callback(self, *args, **kwargs):
        self.core.thread_handler.new_thread(func, self, *args, **kwargs)
    return callback

def thread_free(func):
    """See threads.thread decorated. The difference is that a new thread
    handler is created instead of using self.core.thread_handler,
    so this can be used in cases where self.core isn't accessible.
    """
    
    def callback(self, *args, **kwargs):
        handler = ThreadHandler(None, func, self, *args, **kwargs)
        if handler:
            logger.debug("Running thread handler (free) \"%s:%s\"", func, args)
            handler.start()
    return callback


class ThreadManager(object):
    """A singleton thread manager used to start new threads. You can access it
    via core.thread_handler.
    
    Instead of using it directly, consider using one of the decorators defined
    in this module.
    """

    def __init__(self, core):
        self.core = core
        self.handlers = []

    def new_thread(self, func, obj, *args, **kwargs):
        handler = ThreadHandler(self, func, obj, *args, **kwargs)
        handler.start()
            
        return handler

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
    """A callable wrapper used to execute such a callable in a thread.
    
    Not intended to be used directly! Use one of the 2 decorators or ThreadManager instead.
    """
    def __init__(self, master, func, obj, *args, **kwargs):
        """ Initializing variables """
        
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs
        self.__obj = obj
        self.__master = master

        super(ThreadHandler, self).__init__()

    def run(self):
        """ Run method, this is the code that runs while thread is alive """

        # Run the callable we've been given (self.__func)
        if self.__master:
            self.__master.start_thread(self.__func, self.__obj, *self.__args, **self.__kwargs)
            self.__master.stop_thread(self.__func)
            
        else:
            self.__func(self.__obj, *self.__args, **self.__kwargs)
