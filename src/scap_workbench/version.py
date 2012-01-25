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

"""This module holds version info for reuse in both scap workbench
scanner and editor.
"""

MAJOR = 0
MINOR = 6
PATCH = 2

AS_STRING = "%i.%i.%i" % (MAJOR, MINOR, PATCH)

__all__ = ["MAJOR", "MINOR", "PATCH", "AS_STRING"]

# if somebody just executes this module, print the version string
if __name__ == '__main__':
    print(AS_STRING)
