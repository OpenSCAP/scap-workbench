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

import sys, gtk
import render

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")
try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    openscap=None


class OSCAPWrapper:

    def __init__(self, XCCDF=None):
        if openscap == None:
            print >>sys.stderr, "Can't initialize openscap library."
            return
        self.lib = openscap.xccdf.init(XCCDF)
        if self.lib != None: print "Initialization done."

    def __destroy__(self):
        if self.lib == None: return
        if self.lib["policy_model"] != None:
            self.lib["policy_model"].free()
        for model in self.lib["def_models"]:
            model.free()
        for sess in self.lib["sessions"]:
            sess.free()


class OECore:

    def __init__(self):

        self.openscap = OSCAPWrapper()

    def render(self):
        render.MainWindow()
        gtk.main()
