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
import sys, gtk, gobject
from events import EventObject, EventHandler
import render

logging.config.fileConfig("logger.conf")
logger = logging.getLogger("OSCAPEditor")

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")

try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    openscap=None


class DataHandler:

    def __init__(self, library):
        self.lib = library
        logger.debug("Created Data Handler")

    def __fill_items(self, model, xitem=None, parent=None):
        
        # Iteration (not first)
        if xitem != None:
            # store data to model
            if xitem.type == openscap.OSCAP.XCCDF_GROUP:
                item_it = model.append(parent, ["Group "+xitem.id])
                for item in xitem.content:
                    self.__fill_items(model, item, item_it)
            elif xitem.type == openscap.OSCAP.XCCDF_RULE:
                item_it = model.append(parent, ["Rule "+xitem.id])
            else: logger.warning("Unknown type: %s - %s", xitem.type, xitem.id)

            return

        # xitem == None so we have callback call
        model.clear()
        benchmark = self.lib["policy_model"].benchmark
        if benchmark == None or benchmark.instance == None:
            logger.error("XCCDF benchmark does not exists. Can't fill data")
            return False
        
        for item in benchmark.content:
            self.__fill_items(model, item)

        return True

    def __fill_profiles(self, model):
        
        model.clear()
        benchmark = self.lib["policy_model"].benchmark
        if benchmark == None or benchmark.instance == None:
            logger.error("XCCDF benchmark does not exists. Can't fill data")
            return False
        
        for item in benchmark.profiles:
            logger.debug("Adding profile %s", item.id)
            model.append(["Profile "+item.id])

        return True

    def set_selected_profile(self, profile):
        self.profile = profile

    def get_items_model(self, filter=None):
        # Make a model
        model = gtk.TreeStore(str)
        items = [{"id":"Rule/Group ID", "type":"text", "cb":self.__empty}]
        return (items, model, self.__fill_items)

    def get_profiles_model(self, filter=None):
        # Make a model
        model = gtk.ListStore(str)
        items = [{"id":"Profile ID", "type":"text", "cb":self.__empty}]
        return (items, model, self.__fill_profiles)

    def __empty(self):
        pass


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

        self.data = DataHandler(self.lib)
        self.eventHandler = EventHandler(self)

    def render(self):
        self.mainWindow = render.MainWindow(self)

    def set_sender(self, signal, sender):
        self.eventHandler.set_sender(signal, sender)

    def set_receiver(self, sender_id, signal, callback, position):
        self.eventHandler.register_receiver(sender_id, signal, callback, position)

    def run(self):
        self.render()
        gtk.main()

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

