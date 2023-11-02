#!/bin/bash

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
SCAP_WORKBENCH_OSCAP="$PARENT_DIR/scap-workbench-oscap.sh"

# Preserve proxy variables if they exist
ENV_STR=""
if [ -n "${http_proxy+x}" ]; then
    ENV_STR+="http_proxy=\"$http_proxy\" "
fi

if [ -n "${https_proxy+x}" ]; then
    ENV_STR+="https_proxy=\"$https_proxy\" "
fi

if [ -n "${no_proxy+x}" ]; then
    ENV_STR+="no_proxy=\"$no_proxy\" "
fi

if [ -n "$ENV_STR" ]; then
    ENV_STR="env $ENV_STR"
fi

# We run unprivileged if pkexec was not found.
#which $PKEXEC_PATH > /dev/null || exit 1 # fail if pkexec was not found

$PKEXEC_PATH $ENV_STR --disable-internal-agent "$SCAP_WORKBENCH_OSCAP" $uid $gid "$@" 2> >(tail -n +2 1>&2)
EC=$?

# 126 is a special exit code of pkexec when user dismisses the auth dialog
# 127 means auth can't be established or something in the script failed. We never know.
# We will retry with 127 because pkexec returns 127 when no polkit auth agent is present.
# This is common in niche desktop environments.
if [ $EC -eq 126 ] || [ $EC -eq 127 ]; then
    # in case of dismissed dialog we run without super user rights
    "$SCAP_WORKBENCH_OSCAP" $uid $gid "$@" 2> >(tail -n +2 1>&2);
    exit $?
fi

exit $EC
