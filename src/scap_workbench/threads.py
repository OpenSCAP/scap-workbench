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

import logging
import threading
logger = logging.getLogger("scap-workbench")

def thread(func):
    def callback(self, *args):
        handler = ThreadHandler(func, self, *args)
        logger.debug("Running thread handler \"%s:%s\"", func, args)
        handler.start()
    return callback

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

        # Run the function
        self.__func(self.obj, *self.args)

