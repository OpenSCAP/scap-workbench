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
#      Martin Preisler <mpreisle@redhat.com>

import locale
import gettext

from scap_workbench import paths

TRANSLATION_DOMAIN = "scap-workbench"

def init():
    """Initializes localization support within scap-workbench
    
    The main reason for this method is to synchronize python's gettext with
    the real gettext Gtk uses when loading layouts
    """
    
    # gettext module doesn't call the C gettext functions, we have to use both
    # python gettext module and locale to make sure everything is in sync
    
    locale.setlocale(locale.LC_ALL, "")
    
    locale.bindtextdomain(TRANSLATION_DOMAIN, paths.translation_prefix)
    gettext.bindtextdomain(TRANSLATION_DOMAIN, paths.translation_prefix)
    
    gettext.textdomain(TRANSLATION_DOMAIN)
    
    gettext.install(TRANSLATION_DOMAIN, paths.translation_prefix, unicode = 1)

__all__ = ["TRANSLATION_DOMAIN", "init"]
