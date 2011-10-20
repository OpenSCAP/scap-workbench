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
usr_share_prefix = "/usr/share/scap-workbench"
# where .glade UI files except dialogs are stored
glade_prefix = usr_share_prefix
# where all dialog .glade files are stored
glade_dialog_prefix = os.path.join(glade_prefix, "dialogs")
# all filter modules are in this folder
filters_prefix = os.path.join(usr_share_prefix, "filters")
# stock data from openscap is at this location
stock_data_prefix = "/usr/share/openscap"
