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

wrapper_uid=$1
shift
wrapper_gid=$1
shift

real_uid=`id -u`
real_gid=`id -g`

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

function chown_copy
{
    local what="$1"
    local where="$2"

    [ ! -f "$what" ] || cp "$what" "$where"

    # chown only required if wrapper_{uid,gid} differs from real_{uid,gid}
    if [ $wrapper_uid -ne $real_uid ] || [ $wrapper_gid -ne $real_gid ]; then
        chown $wrapper_uid:$wrapper_gid $where
    fi
}

chown_copy "$TEMP_DIR/results-xccdf.xml" "$TARGET_RESULTS_XCCDF"
chown_copy "$TEMP_DIR/results-arf.xml" "$TARGET_RESULTS_ARF"
chown_copy "$TEMP_DIR/report.html" "$TARGET_REPORT"

rm -r "$TEMP_DIR"

exit $RET
