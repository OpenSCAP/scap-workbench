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

from threads import ThreadManager
import getopt
import os

LOGGER_CONFIG_FILE='/etc/scap-workbench/logger.conf'
FILTER_DIR="/usr/share/scap-workbench/filters"
logging.config.fileConfig(LOGGER_CONFIG_FILE)
logger = logging.getLogger("scap-workbench")

try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OPENSCAP: %s", ex)
    openscap=None
    sys.exit(2)

def label_set_autowrap(widget): 
    "Make labels automatically re-wrap if their containers are resized.  Accepts label or container widgets."
    # For this to work the label in the glade file must be set to wrap on words.
    if isinstance(widget, gtk.Container):
        children = widget.get_children()
        for i in xrange(len(children)):
            label_set_autowrap(children[i])
    elif isinstance(widget, gtk.Label) and widget.get_line_wrap():
        widget.connect_after("size-allocate", label_size_allocate)


def label_size_allocate(widget, allocation):
    "Callback which re-allocates the size of a label."
    layout = widget.get_layout()
    lw_old, lh_old = layout.get_size()
    # fixed width labels
    if lw_old / pango.SCALE == allocation.width:
        return
    # set wrap width to the pango.Layout of the labels
    layout.set_width(allocation.width * pango.SCALE)
    lw, lh = layout.get_size()  # lw is unused.
    if lh_old != lh:
        widget.set_size_request(-1, lh / pango.SCALE)


class Notification:

    SUCCESS = 0
    INFORMATION = 1
    WARNING = 2
    ERROR = 3

    IMG = ["dialog-ok", "dialog-information", "dialog-warning", "dialog-error"]
    BG_COLOR = ["#DFF2BF", "#BDE5F8", "#FEEFB3", "#FFBABA"]
    COLOR = ["#4F8A10", "#00529B", "#9F6000", "#D8000C"]
    DEFAULT_SIZE = gtk.ICON_SIZE_LARGE_TOOLBAR
    DEFAULT_TIME = 10
    HIDE_LVLS = [0, 1] # TODO

    def __init__(self, text, lvl=0):

        if lvl > 3: lvl = 3
        if lvl < 0: lvl = 0

        logger.debug("Notification: %s", text)
        box = gtk.HBox()
        box.set_spacing(10)
        align = gtk.Alignment(0.5, 0.5, 1.0, 1.0)
        align.set_padding(2, 2, 5, 2)
        align.add(box)
        self.img = gtk.Image()
        self.img.set_from_icon_name(Notification.IMG[lvl], Notification.DEFAULT_SIZE)
        box.pack_start(self.img, False, False)
        self.label = gtk.Label(text)
        self.label.set_alignment(0, 0.5)
        label_set_autowrap(self.label)
        box.pack_start(self.label, True, True)
        self.btn = gtk.Button()
        self.btn.set_relief(gtk.RELIEF_NONE)
        self.btn.connect("clicked", self.__cb_destroy)
        self.btn.set_label("x")
        box.pack_start(self.btn, False, False)
        self.eb = gtk.EventBox()
        self.eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(Notification.BG_COLOR[lvl]))
        self.eb.set_border_width(1)
        self.eb.add(align)
        self.widget = gtk.EventBox()
        self.widget.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(Notification.COLOR[lvl]))
        self.widget.add(self.eb)
    
        self.widget.show_all()

    def __cb_destroy(self, widget):
        self.widget.destroy()
        self.widget = None

    def destroy(self):
        if self.widget:
            self.widget.destroy()
        

class Library:
    """ Abstract model of library variables that
    are static and should be singletons"""

    class OVAL:
        """ Class that represents OVAL file that is imported to
        library and used by XCCDF file"""
        def __init__(self, path, sess, model):
            self.path = path
            self.session = sess
            self.model = model

        def destroy(self):
            if self.session: self.session.free()
            if self.model: self.model.free()
    """*********"""

    def __init__(self):
        self.xccdf = None
        self.benchmark = None
        self.policy_model = None
        self.files = {}
        self.loaded = False

    def init_policy_model(self):
        """ This function should init policy model for scanning
        """
        raise Exception, "Not implemented yet"

    def new(self):
        """Create new XCCDF Benchmark
        """
        openscap.OSCAP.oscap_init()
        self.benchmark = openscap.xccdf.benchmark()
        self.loaded = True

    def add_file(self, path, sess, model):
        if path in self.files:
            logger.warning("%s is already in the list.")
        else: self.files[path] = Library.OVAL(path, sess, model)

    def import_xccdf(self, xccdf):
        """Import XCCDF Benchmark from file
        """
        openscap.OSCAP.oscap_init()
        self.xccdf = xccdf
        self.benchmark = openscap.xccdf.benchmark_import(xccdf)
        dirname = os.path.dirname(xccdf)

        for file in self.benchmark.to_item().get_files().strings:
            if os.path.exists(file):
                def_model = openscap.oval.definition_model_import(file)
            else:
                def_model = openscap.oval.definition_model_import(os.path.join(dirname, file))

            if def_model:
                self.files[file] = Library.OVAL(file, None, def_model)

        if self.benchmark: logger.debug("Initialization done.")
        else:
            logger.debug("Initialization failed. Benchmark can't be imported")
            raise Exception("Can't initialize openscap library, Benchmark import failed.")
        self.loaded = True

    def parse(self, lib):
        """
        """
        self.xccdf = lib["xccdf_path"]
        self.policy_model = lib["policy_model"]
        if self.policy_model:
            self.benchmark = self.policy_model.benchmark
            if self.benchmark == None or self.benchmark.instance == None:
                logger.error("XCCDF benchmark does not exists. Can't fill data")
                raise Error, "XCCDF benchmark does not exists. Can't fill data"
        if lib["names"]:
            for name in lib["names"].keys():
                self.files[name] = Library.OVAL(name, lib["names"][name][0], lib["names"][name][1])
        self.loaded = True

    def destroy(self):
        """
        """
        openscap.OSCAP.oscap_cleanup()
        if self.benchmark and self.policy_model == None:
            self.benchmark.free()
            for oval in self.files.values(): oval.destroy()
        elif self.policy_model != None:
            self.policy_model.free()
        self.xccdf = None
        self.benchmark = None
        self.policy_model = None
        self.loaded = False

class SWBCore:

    def __init__(self, builder, with_policy=False):

        self.thread_handler = ThreadManager(self)
        self.builder = builder
        self.lib = Library()
        self.__objects = {}
        self.main_window = None
        self.force_reload_items = False
        self.force_reload_profiles = False
        self.eventHandler = EventHandler(self)
        self.registered_callbacks = False
        self.selected_profile   = None
        self.selected_item      = None
        self.selected_lang      = ""
        self.langs              = []
        self.filter_directory   = FILTER_DIR
        self.with_policy = with_policy

        # Global notifications
        self.__global_notifications = {}
        self.__global_notifications[None] = []

        # Info Box
        self.info_box = self.builder.get_object("info_box")

        # parse imput arguments
        arguments = sys.argv[1:]

        try:
            opts, args = getopt.getopt(arguments, "+D", ["debug"])
        except getopt.GetoptError, err:
            # print help information and exit
            print >>sys.stderr, "(ERROR)", str(err)
            print >>sys.stderr, "Try 'scap-workbench --help' for more information."
            sys.exit(2)

        for o, a in opts:
            if o in ("-D", "--version"):
                logger.setLevel(logging.DEBUG)
                logger.root.setLevel(logging.DEBUG)
            else:
                print >>sys.stderr, "(ERROR) Unknown option or missing mandatory argument '%s'" % (o,)
                print >>sys.stderr, "Try 'scap-workbench --help' for more information."
                sys.exit(2)

        if len(args) > 0:
            logger.debug("Loading XCCDF file %s", sys.argv[1])
            self.init(args[0])

        self.set_receiver("gui:btn:main:xccdf", "load", self.__set_force)

    def init(self, XCCDF):
        """Free self.lib
        """
        if self.lib: self.lib.destroy()
        if self.info_box:
            for child in self.info_box:
                child.destroy()

        if openscap == None:
            logger.error("Can't initialize openscap library.")
            raise Exception("Can't initialize openscap library")

        if not XCCDF:
            # No XCCDF specified: Create new Benchmark
            self.lib.new()
        elif not self.with_policy:
            # Trying to import XCCDF in editor
            self.lib.import_xccdf(XCCDF)
        else:
            # Trying to import XCCDF in scanner - we need policies
            try:
                lib = openscap.xccdf.init(XCCDF)
                self.lib.parse(lib)
            except ImportError, err:
                logger.error(err)
                return False

            # Language of benchmark should be in languages
        if self.lib.benchmark == None:
            logger.error("FATAL: Benchmark does not exist")
            raise Exception("Can't initialize openscap library")
        if not self.lib.benchmark.lang in self.langs: 
            self.langs.append(self.lib.benchmark.lang)
        self.selected_lang = self.lib.benchmark.lang
        if self.lib.benchmark.lang == None:
            self.notify("XCCDF Benchmark: No language specified.", Notification.WARNING)
        return True


    def notify(self, text, lvl=0, info_box=None, msg_id=None):

        notification = Notification(text, lvl)
        if msg_id:
            if msg_id in self.__global_notifications:
                self.__global_notifications[msg_id].destroy()
            self.__global_notifications[msg_id] = notification
        else:
            self.__global_notifications[None].append(notification)

        if info_box: info_box.pack_start(notification.widget)
        else: self.info_box.pack_start(notification.widget)
        return notification

    def notify_destroy(self, msg_id):
        if not msg_id:
            raise AttributeError("notify_destroy: msg_id can't be None -> not allowed to destroy global notifications")
        if msg_id in self.__global_notifications:
            self.__global_notifications[msg_id].destroy()

    def set_sender(self, signal, sender):
        self.eventHandler.set_sender(signal, sender)

    def set_receiver(self, sender_id, signal, callback, *args):
        self.eventHandler.register_receiver(sender_id, signal, callback, args)

    def __set_force(self):
        self.registered_callbacks = False
        self.force_reload_items = True
        self.force_reload_profiles = True
        self.selected_profile = None

    def destroy(self):
        self.__set_force()
        self.__destroy__()

    def __destroy__(self):
        if self.lib == None: return
        self.lib.destroy()

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
                        "gui:btn:tailoring",
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
