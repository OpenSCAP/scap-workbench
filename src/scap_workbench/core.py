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

import logging, logging.config
import sys, gtk, gobject
from events import EventHandler

from threads import thread
import render #TODO

LOGGER_CONFIG_FILE='/etc/scap-workbench/logger.conf'
FILTER_DIR="/usr/share/scap-workbench/filters"
logging.config.fileConfig(LOGGER_CONFIG_FILE)
logger = logging.getLogger("scap-workbench")

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")
sys.path.append("/tmp/scap/usr/local/lib/python2.6/site-packages")
#sys.path.append("/usr/lib64/python2.6/site-packages")
#sys.path.append("/usr/lib/python2.6/site-packages")

try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OPENSCAP: %s", ex)
    openscap=None

class Notification:

    IMG = ["dialog-information", "dialog-warning", "dialog-error"]
    COLOR = ["#C0C0FF", "#FFFFC0", "#FFC0C0" ]
    DEFAULT_SIZE = gtk.ICON_SIZE_LARGE_TOOLBAR
    DEFAULT_TIME = 10
    HIDE_LVLS = [0, 1]

    def __init__(self, text, lvl=0):

        if lvl > 2: lvl = 2
        if lvl < 0: lvl = 0

        logger.debug("Notification: %s", text)
        box = gtk.HBox()
        box.set_spacing(10)
        self.img = gtk.Image()
        self.img.set_from_icon_name(Notification.IMG[lvl], Notification.DEFAULT_SIZE)
        box.pack_start(self.img, False, False)
        self.label = gtk.Label(text)
        self.label.set_alignment(0, 0.5)
        render.label_set_autowrap(self.label)
        box.pack_start(self.label, True, True)
        self.btn = gtk.Button()
        self.btn.set_relief(gtk.RELIEF_NONE)
        self.btn.connect("clicked", self.__cb_destroy)
        self.btn.set_label("x")
        box.pack_start(self.btn, False, False)
        self.widget = gtk.EventBox()
        self.widget.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(Notification.COLOR[lvl]))
        self.widget.add(box)
    
        """
        if lvl in Notification.HIDE_LVLS: 
            self.destroy_timeout(self.widget)
        """
        self.widget.show_all()

    def __cb_destroy(self, widget):
        widget.parent.parent.destroy()
        self.widget = None

    def destroy(self):
        if self.widget: 
            self.widget.destroy()
        

class SWBCore:

    def __init__(self, builder):

        self.builder = builder
        self.lib = None
        self.__objects = {}
        self.main_window = None
        self.changed_profiles = []
        self.force_reload_items = False
        self.force_reload_profiles = False
        self.eventHandler = EventHandler(self)
        self.registered_callbacks = False
        self.selected_profile   = None
        self.selected_item      = None
        self.selected_deps      = None
        self.selected_lang      = ""
        self.langs              = []
        self.xccdf_file        = None
        self.filter_directory   = FILTER_DIR

        # Info Box
        self.info_box = self.builder.get_object("info_box")

        if len(sys.argv) > 1:
            logger.debug("Loading XCCDF file %s", sys.argv[1])
            self.init(sys.argv[1])

        self.set_receiver("gui:btn:main:xccdf", "load", self.__set_force)

    def init(self, XCCDF):
        if self.lib:
            if self.lib["policy_model"] != None:
                self.lib["policy_model"].free()
            for model in self.lib["def_models"]:
                model.free()
            for sess in self.lib["sessions"]:
                sess.free()
        for child in self.info_box:
            child.destroy()

        self.xccdf_file = XCCDF
        if openscap == None:
            logger.error("Can't initialize openscap library.")
            raise Exception("Can't initialize openscap library")
        self.lib = openscap.xccdf.init(XCCDF)
        if self.lib != None: 
            logger.info("Initialization done.")
            benchmark = self.lib["policy_model"].benchmark
            if benchmark == None or benchmark.instance == None:
                logger.error("XCCDF benchmark does not exists. Can't fill data")
                raise Error, "XCCDF benchmark does not exists. Can't fill data"
        else: logger.error("Initialization failed.")

        # Language of benchmark should be in languages
        benchmark = self.lib["policy_model"].benchmark
        if benchmark == None:
            logger.error("FATAL: Benchmark does not exist")
            raise Exception("Can't initialize openscap library")
        if not benchmark.lang in self.langs: 
            self.selected_lang = benchmark.lang
            self.langs.append(benchmark.lang)
        if benchmark.lang == None:
            self.notify("XCCDF Benchmark: No language specified.", 2)

    def notify(self, text, lvl=0, info_box=None):
        notification = Notification(text, lvl)
        if info_box: info_box.pack_start(notifycation.widget)
        else: self.info_box.pack_start(notification.widget)
        return notification

    def set_sender(self, signal, sender):
        self.eventHandler.set_sender(signal, sender)

    def set_receiver(self, sender_id, signal, callback, position=-1):
        self.eventHandler.register_receiver(sender_id, signal, callback, position)

    def set_callback(self, action, callback, position=None):
        pass

    def __set_force(self):
        self.registered_callbacks = False
        self.force_reload_items = True
        self.force_reload_profiles = True

    def __destroy__(self):
        if self.lib == None: return
        if self.lib["policy_model"] != None:
            self.lib["policy_model"].free()
        for model in self.lib["def_models"]:
            model.free()
        for sess in self.lib["sessions"]:
            sess.free()

    def get_item(self, id):
        if id not in self.__objects:
            raise Exception, "FATAL: Object %s not registered" % (id,)
        return self.__objects[id]

    def register(self, id, object):

        if id in self.__objects:
            raise Exception, "FATAL: Object %s already registered" % (id,)
        logger.debug("Registering object %s done.", id)
        self.__objects[id] = object


class Wizard:

    def __init__(self, core):

        self.__core = core
        self.__list = [ "gui:btn:main:xccdf",
                        "gui:menu:tailoring",
                        "gui:btn:tailoring:refines",
                        "gui:btn:menu:scan" ]
        self.__active = 0

    def forward(self, widget):
        if self.__active+1 > len(self.__list):
            raise Exception, "Wizard list out of range"
        self.__core.get_item(self.__list[self.__active]).set_active(False)
        self.__core.get_item("main:button_back").set_sensitive(True)
        self.__active += 1
        if self.__active == len(self.__list):
            widget.set_sensitive(False)
        self.__core.get_item(self.__list[self.__active]).set_active(True)


    def back(self, widget):
        if self.__active-1 < 0:
            raise Exception, "Wizard list out of range"
        self.__core.get_item(self.__list[self.__active]).set_active(False)
        self.__core.get_item("main:button_forward").set_sensitive(True)
        self.__active -= 1
        if self.__active == 0:
            widget.set_sensitive(False)
        self.__core.get_item(self.__list[self.__active]).set_active(True)
