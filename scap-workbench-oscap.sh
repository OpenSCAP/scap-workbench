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

trap "" SIGHUP SIGINT

# pkexec writes a message to stderr when user dismisses it, we always skip 1 line.
# if user did not dismiss it we should print a dummy line to stderr so that nothing
# valuable gets skipped
echo "Dummy text" 1>&2

# prevent world-readable files being created
umask 0007

real_uid=`id -u`
real_gid=`id -g`

wrapper_uid=${PKEXEC_UID:-${real_uid}}
wrapper_gid=$(id -g ${wrapper_uid})

TEMP_DIR=`mktemp -d`

args=("$@")

# We have to rewrite result targets to a priv temp dir. We will later
# chown that dir to the target uid:gid and copy things where they belong
# using permissions of that user ONLY!
for i in $(seq 0 `expr $# - 1`); do
    let j=i+1

    case "${args[i]}" in
    ("--results")
        TARGET_RESULTS_XCCDF="${args[j]}"
        args[j]="$TEMP_DIR/results-xccdf.xml"
      ;;
    ("--results-arf")
        TARGET_RESULTS_ARF="${args[j]}"
        args[j]="$TEMP_DIR/results-arf.xml"
      ;;
    ("--report")
        TARGET_REPORT="${args[j]}"
        args[j]="$TEMP_DIR/report.html"
      ;;
    *)
      ;;
    esac
done

LOCAL_OSCAP="oscap"

pushd "$TEMP_DIR" > /dev/null
$LOCAL_OSCAP "${args[@]}" &
PID=$!
RET=1

while kill -0 $PID 2> /dev/null; do
    # check if the stdin is still available but return in one second
    read -t 1 dummy
    ret=$?
    if [ 0 -lt $ret -a $ret -lt 128 ]; then
        # If read failed & it was not due to timeout --> parents are gone.
        kill -s SIGTERM $PID 2> /dev/null
        break
    fi
done

wait $PID
RET=$?

popd > /dev/null

# only copy files with the target user's permissions via sudo if we're running
# privileged, otherwise he can trick us into overwriting arbitrary files
do_chown=false
if [ $wrapper_uid -ne $real_uid ] || [ $wrapper_gid -ne $real_gid ]; then
    do_chown=true
fi

function chown_copy
{
    local what="$1"
    local where="$2"

    [ -f "$what" ] || return

    if $do_chown; then
        chown $wrapper_uid:$wrapper_gid "$what"
        sudo -u "#${wrapper_uid}" cp "$what" "$where"
    else
        cp "$what" "$where"
    fi
}

if $do_chown; then
    # don't grant the user ownership of or write access to the directory,
    # otherwise he could trick us by replacing the files with symlinks
    chmod o+rx "${TEMP_DIR}"
fi

chown_copy "$TEMP_DIR/results-xccdf.xml" "$TARGET_RESULTS_XCCDF"
chown_copy "$TEMP_DIR/results-arf.xml" "$TARGET_RESULTS_ARF"
chown_copy "$TEMP_DIR/report.html" "$TARGET_REPORT"

rm -r "$TEMP_DIR"

exit $RET
