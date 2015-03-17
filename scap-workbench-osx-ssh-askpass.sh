#!/bin/sh

# Taken from git-cola.
#
# git-cola is a powerful Git GUI with a slick and intuitive user interface.
#
# Copyright (C) 2007-2015, David Aguilar and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

TITLE=${MACOS_ASKPASS_TITLE:-"SSH"}
DIALOG="display dialog \"$@\" default answer \"\" with title \"$TITLE\""
DIALOG="$DIALOG with icon caution"

yesno=
if echo "$1" | grep "'yes'" 2>&1 >/dev/null ||
	echo "$1" | grep "yes/no" 2>&1 >/dev/null
then
	yesno=true
fi

if test -z "$yesno"
then
	DIALOG="$DIALOG with hidden answer"
fi

result=$(osascript \
	-e 'tell application "Finder"' \
	-e "activate"  \
	-e "$DIALOG" \
	-e 'end tell' 2>/dev/null)

if test -z "$result"
then
	exit 1
fi

# The beginning of the output can be either "text returned:"
# or "button returned:", and is Mac OS X version-dependent.
# Account for both output styles.
printf '%s\n' "$result" |
sed -e 's/^text returned://' -e 's/, button returned:.*$//' \
    -e 's/^button returned:OK, text returned://'
exit 0

