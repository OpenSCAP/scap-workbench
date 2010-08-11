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
import render

logging.config.fileConfig("logger.conf")
# create logger
logger = logging.getLogger("OSCAPEditor")

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")

try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    openscap=None

class EODataHandler:

    def __init__(self, library):
        self.lib = library
        logger.debug("Created Data Handler")

    def __get_item_data(self, item):

        if item.type == openscap.XCCDF_GROUP:
            pass

    def __fill_items_to_list(self, model, xitem=None, parent=None):
        
        # Iteration (not first)
        if xitem != None:
            # store data to model
            logger.info("Adding row with %s", xitem.id)
            item_it = model.append(parent, [xitem.id])
            if xitem.type in [openscap.OSCAP.XCCDF_GROUP, openscap.OSCAP.XCCDF_BENCHMARK]:
                for item in xitem.content:
                    self.__fill_items_to_list(model, item, item_it)
            return

        # xitem == None so we have callback call
        benchmark = self.lib["policy_model"].benchmark
        if benchmark == None or benchmark.instance == None:
            logger.error("XCCDF benchmark does not exists. Can't fill data")
            return False
        
        for item in benchmark.content:
            self.__fill_items_to_list(model, item)

        return True

    def get_items_model(self, filter=None):
        # Make a model
        model = gtk.TreeStore(
                #gtk.gdk.Pixbuf,
                str)#,
                #gobject.TYPE_PYOBJECT)

        items = [{"id":"Rule/Group ID", "type":"text", "cb":self.__empty}]
        return (items, model, self.__fill_items_to_list)

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

        self.data = EODataHandler(self.lib)

    def render(self):
        self.mainWindow = render.MainWindow(self)

    def run(self):
        self.render()
        gtk.main()

    def __destroy__(self):
        if self.lib == None: return
        if self.lib["policy_model"] != None:
            self.lib["policy_model"].free()
        for model in self.lib["def_models"]:
            model.free()
        for sess in self.lib["sessions"]:
            sess.free()

