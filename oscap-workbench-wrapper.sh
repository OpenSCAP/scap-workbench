#!/usr/bin/bash

# Copyright 2014 Red Hat Inc., Durham, North Carolina.
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

set -u -o pipefail

uid=`id -u`
gid=`id -g`

PARENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

PKEXEC_PATH="pkexec"
OSCAP_WORKBENCH="$PARENT_DIR/oscap-workbench.sh"

$PKEXEC_PATH --disable-internal-agent $OSCAP_WORKBENCH $uid $gid $@ 2> >(tail -n +2 1>&2)
EC=$?

# 126 is a special exit code of pkexec when user dismisses the auth dialog
# 127 means auth can't be established or something in the script failed. We never know.
if [ $EC -eq 126 ]; then
    # in case of dismissed dialog we run without super user rights
    $OSCAP_WORKBENCH $uid $gid $@ 2> >(tail -n +2 1>&2);
    exit $?
fi

exit $EC
