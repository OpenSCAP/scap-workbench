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

""" Importing standard python libraries
"""
import gtk              # GTK library

""" Importing SCAP Workbench modules
"""
import logging                  # Logger for debug/info/error messages

# Initializing Logger
logger = logging.getLogger("scap-workbench")

""" Import OpenSCAP library as backend.
If anything goes wrong just end with exception"""
try:
    import openscap_api as openscap
except Exception as ex:
    logger.error("OpenScap library initialization failed: %s", ex)
    openscap=None

class enum(tuple):

    """ Enumeration inherited from tuple used for openscap
    enumerations filled to GTK Widgets.

    Use ENUM.map(id) when looking for item from model (known enum id)
    Use ENUM.pos(id) when looking for position of item in model (known position in model)
    Use ENUM.value(pos) when looking for first value of enumeration when known position in model
    Use ENUM.get_model() when creating model for this enumeration
    Use list funtions when looking for trouble :)

    if you are updating openscap model after selecting some item from model in GUI,
    use returning ENUM.XXX[widget.get_active()] for all item (list)
    or use ENUM.value()
    """

    def map(self, id):
        for item in tuple(self):
            if item[0] == id: return item
        return None

    def pos(self, id):
        for item in tuple(self):
            if item[0] == id: return tuple.index(self, item)
        return -1

    def value(self, id):
        if id > len(tuple(self)) or len(tuple(self)[id]) < 1:
            return None
        else: return tuple(self)[id][0]

    def get_model(self):
        model = gtk.ListStore(int, str, str)
        for item in tuple(self):
            model.append(item)
        return model

""" Below is the list of enumerations from OpenSCAP library
"""

STATUS_CURRENT=enum((
    [openscap.OSCAP.XCCDF_STATUS_NOT_SPECIFIED, "NOT SPECIFIED", "Status was not specified by benchmark."],
    [openscap.OSCAP.XCCDF_STATUS_ACCEPTED, "ACCEPTED", "Accepted."],
    [openscap.OSCAP.XCCDF_STATUS_DEPRECATED, "DEPRECATED", "Deprecated."],
    [openscap.OSCAP.XCCDF_STATUS_DRAFT, "DRAFT ", "Draft item."],
    [openscap.OSCAP.XCCDF_STATUS_INCOMPLETE, "INCOMPLETE", "The item is not complete. "],
    [openscap.OSCAP.XCCDF_STATUS_INTERIM, "INTERIM", "Interim."]))

WARNING=enum((
    [0, "UNKNOWN", "Unknown."],
    [openscap.OSCAP.XCCDF_WARNING_GENERAL, "GENERAL", "General-purpose warning."],
    [openscap.OSCAP.XCCDF_WARNING_FUNCTIONALITY, "FUNCTIONALITY", "Warning about possible impacts to functionality."],
    [openscap.OSCAP.XCCDF_WARNING_PERFORMANCE, "PERFORMANCE", "  Warning about changes to target system performance."],
    [openscap.OSCAP.XCCDF_WARNING_HARDWARE, "HARDWARE", "Warning about hardware restrictions or possible impacts to hardware."],
    [openscap.OSCAP.XCCDF_WARNING_LEGAL, "LEGAL", "Warning about legal implications."],
    [openscap.OSCAP.XCCDF_WARNING_REGULATORY, "REGULATORY", "Warning about regulatory obligations."],
    [openscap.OSCAP.XCCDF_WARNING_MANAGEMENT, "MANAGEMENT", "Warning about impacts to the mgmt or administration of the target system."],
    [openscap.OSCAP.XCCDF_WARNING_AUDIT, "AUDIT", "Warning about impacts to audit or logging."],
    [openscap.OSCAP.XCCDF_WARNING_DEPENDENCY, "DEPENDENCY", "Warning about dependencies between this Rule and other parts of the target system."]))

OPERATOR=enum((
    [openscap.OSCAP.XCCDF_OPERATOR_EQUALS, "EQUALS", "Equality"],
    [openscap.OSCAP.XCCDF_OPERATOR_NOT_EQUAL, "NOT EQUAL", "Inequality"],
    [openscap.OSCAP.XCCDF_OPERATOR_GREATER, "GREATER", "Greater than"],
    [openscap.OSCAP.XCCDF_OPERATOR_GREATER_EQUAL, "GREATER OR EQUAL", "Greater than or equal."],
    [openscap.OSCAP.XCCDF_OPERATOR_LESS , "LESS", "Less than."],
    [openscap.OSCAP.XCCDF_OPERATOR_LESS_EQUAL, "LESS OR EQUAL", "Less than or equal."]))

TYPE=enum((
    [0, "UNKNOWN", "Unknown."],
    [openscap.OSCAP.XCCDF_TYPE_NUMBER, "NUMBER", ""],
    [openscap.OSCAP.XCCDF_TYPE_STRING, "STRING", ""],
    [openscap.OSCAP.XCCDF_TYPE_BOOLEAN, "BOOLEAN", ""]))

LEVEL=enum((
    [openscap.OSCAP.XCCDF_UNKNOWN, "UNKNOWN", "Unknown."],
    [openscap.OSCAP.XCCDF_INFO, "INFO", "Info."],
    [openscap.OSCAP.XCCDF_LOW, "LOW", "Low."],
    [openscap.OSCAP.XCCDF_MEDIUM, "MEDIUM", "Medium"],
    [openscap.OSCAP.XCCDF_HIGH, "HIGH", "High."]))

ROLE=enum((
    [openscap.OSCAP.XCCDF_ROLE_FULL, "FULL", "Check the rule and let the result contriburte to the score and appear in reports.."],
    [openscap.OSCAP.XCCDF_ROLE_UNSCORED, "UNSCORED", "Check the rule and include the result in reports, but do not include it into score computations"],
    [openscap.OSCAP.XCCDF_ROLE_UNCHECKED, "UNCHECKED", "Don't check the rule, result will be XCCDF_RESULT_UNKNOWN."]))

STRATEGY=enum((
    [openscap.OSCAP.XCCDF_STRATEGY_UNKNOWN, "UNKNOWN", "Strategy not defined."],
    [openscap.OSCAP.XCCDF_STRATEGY_CONFIGURE, "CONFIGURE", "Adjust target config or settings."],
    [openscap.OSCAP.XCCDF_STRATEGY_DISABLE, "DISABLE", "Turn off or deinstall something."],
    [openscap.OSCAP.XCCDF_STRATEGY_ENABLE, "ENABLE", "Turn on or install something."],
    [openscap.OSCAP.XCCDF_STRATEGY_PATCH, "PATCH", "Apply a patch, hotfix, or update."],
    [openscap.OSCAP.XCCDF_STRATEGY_POLICY, "POLICY", "Remediation by changing policies/procedures."],
    [openscap.OSCAP.XCCDF_STRATEGY_RESTRICT, "RESTRICT", "Adjust permissions or ACLs."],
    [openscap.OSCAP.XCCDF_STRATEGY_UPDATE, "UPDATE", "Install upgrade or update the system"],
    [openscap.OSCAP.XCCDF_STRATEGY_COMBINATION, "COMBINATION", "Combo of two or more of the above."]))

OPERATOR_BOOL=enum((
    [openscap.OSCAP.XCCDF_OPERATOR_EQUALS, "EQUALS", "Equality"],
    [openscap.OSCAP.XCCDF_OPERATOR_NOT_EQUAL, "NOT EQUAL", "Inequality"]))

OPERATOR_STRING=enum((
    [openscap.OSCAP.XCCDF_OPERATOR_EQUALS, "EQUALS", "Equality"],
    [openscap.OSCAP.XCCDF_OPERATOR_NOT_EQUAL, "NOT EQUAL", "Inequality"],
    [openscap.OSCAP.XCCDF_OPERATOR_PATTERN_MATCH, "PATTERN_MATCH", "Match a regular expression."]))


