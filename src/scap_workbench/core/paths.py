# -*- coding: utf-8 -*-
#
# Copyright 2011 Red Hat Inc., Durham, North Carolina.
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
#      Martin Preisler <mpreisle@redhat.com>

"""This module holds path prefixes and is mostly useful for
packagers

(they can just patch this file with the standard location
on the target distro / platform)
"""

import os.path

# reasonable defaults for GNU/Linux distributions

# where configuration files *just* for scap-workbench are stored
etc_prefix = "/etc/scap-workbench"
# not used directly, only used to construct other paths
share_prefix = "/usr/share/scap-workbench"
# not used directly, only used to construct other paths
share_workbench_prefix = "/usr/share/scap-workbench"
# where .glade UI files except dialogs are stored
glade_prefix = os.path.join(share_workbench_prefix, "glade")
# where all dialog .glade files are stored
glade_dialog_prefix = os.path.join(glade_prefix, "dialogs")
# all filter modules are in this folder
filters_prefix = os.path.join(share_workbench_prefix, "filters")
# all pixmaps are stored here
pixmaps_prefix = os.path.join(share_prefix, "pixmaps")

# stock data from openscap is at this location
stock_data_prefix = "/usr/share/openscap"

def set_prefix(prefix):
    global etc_prefix, share_prefix, share_workbench_prefix, glade_prefix, glade_dialog_prefix
    global filters_prefix, stock_data_prefix, pixmaps_prefix
    
    etc_prefix = os.path.join(prefix, "etc")
    share_prefix = os.path.join(prefix, "share")
    share_workbench_prefix = os.path.join(share_prefix, "scap-workbench")
    glade_prefix = os.path.join(share_workbench_prefix, "glade")
    glade_dialog_prefix = os.path.join(glade_prefix, "dialogs")
    filters_prefix = os.path.join(share_workbench_prefix, "filters")
    pixmaps_prefix = os.path.join(share_prefix, "pixmaps")

def notify_executable_file_path(path):
    # the first dirname gets the directory of the executable, the second dirname gets the parent directory of that
    # so if the executable is in (something)/bin the prefix would be (something)
    set_prefix(os.path.dirname(os.path.dirname(os.path.abspath(path))))
