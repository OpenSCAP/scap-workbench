# -*- coding: utf-8 -*-
#
# Copyright 2012 Red Hat Inc., Durham, North Carolina.
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
#      Martin Preisler      <mpreisle@redhat.com>

"""Configures logging using the standard 'logging' package Python ships,
exposes LOGGER variable that stores the logger we use to log everything
in scanner and editor.
"""

import logging
import logging.config
import os.path

from scap_workbench import paths

# we are intentionally not exposing this variable to the outside,
# logger config file loading is an internal detail of this package
LOGGER_CONFIG_PATH = os.path.join(paths.etc_workbench_prefix, "logger.conf")

# initializing and configuring Logger
try:
    # if we can, we load logger config from the path where it's supposed to be
    logging.config.fileConfig(LOGGER_CONFIG_PATH)
    
except: # ConfigParser.NoSectionError = actually file I/O error most of the time
    # when that fails, we will just set basic logger configuration and continue onwards, logging isn't mandatory
    logging.basicConfig()
    logging.getLogger("scap-workbench").error("Had to resort to basic logging config, logger config for openscap not found at '%s'" % (LOGGER_CONFIG_PATH))
    
LOGGER = logging.getLogger("scap-workbench")

__all__ = ["LOGGER"]
