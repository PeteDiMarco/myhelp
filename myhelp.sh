#!/bin/bash
#***************************************************************************
#* Copyright 2019-2020 Pete DiMarco
#*
#* Licensed under the Apache License, Version 2.0 (the "License");
#* you may not use this file except in compliance with the License.
#* You may obtain a copy of the License at
#*
#*     http://www.apache.org/licenses/LICENSE-2.0
#*
#* Unless required by applicable law or agreed to in writing, software
#* distributed under the License is distributed on an "AS IS" BASIS,
#* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#* See the License for the specific language governing permissions and
#* limitations under the License.
#***************************************************************************
#
# Name: myhelp.sh
# Version: 0.5
# Date: 2020-06-09
# Written by: Pete DiMarco <pete.dimarco.software@gmail.com>
#
# Description:
# A "super help" command that tries to identify the name(s) provided on the
# commandline.
#
# See also:
# http://mywiki.wooledge.org/BashFAQ/081
#
# * Dependencies:
# ** Executables:
# basename, cat, cut, echo, grep, mktemp, ps,
# readlink, sed, sort, uniq, wc
# ** Built-ins:
# alias, declare, set, type
#
# DO NOT ADD "set -e" TO THIS SCRIPT!

# Defaults:
DEBUG=false
bin_directory=
# Check if MYHELP_RC_FILE was defined in the parent shell.
rc_file="${MYHELP_RC_FILE}"
if [[ -z "${MYHELP_RC_FILE}" ]]; then
    if [[ -f "${HOME}/.config/myhelprc" ]]; then
        rc_file="${HOME}/.config/myhelprc"
    elif [[ -f "${HOME}/.myhelprc" ]]; then
        rc_file="${HOME}/.myhelprc"
    fi
fi

NEW_PATH="${PATH}"

# Flags passed to myhelp.py.
declare -a flags=()
# Terms to search for from command line.
declare -a terms=()

# We need a temporary file to store the output of the shell builtin commands.
temp_file=$(mktemp /tmp/$$.XXXXXX)
# Remove the temporary file on exit.
trap "rm -f $temp_file" 0 2 3 15

# Are we being sourced?
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0
if [[ ${SOURCED} -eq 0 ]]; then
    echo "WARNING: Shell aliases will not be scanned."
fi

# *****************************************************************************
# Functions:
# *****************************************************************************


# *****************************************************************************
# Command line options:
# *****************************************************************************

# Make sure we have the correct version of get_opt:
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "ERROR: This script requires the enhanced version of 'getopt'."
    return 4 2>/dev/null | exit 4
fi

# Parse commandline options:
OPTIONS='hDrp:siT:'
LONGOPTIONS='help,DEBUG,refresh,pattern:,standalone,interactive,TEST:'

PARSED=$(getopt --options="${OPTIONS}" --longoptions="${LONGOPTIONS}" --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    # If getopt has complained about wrong arguments to stdout:
    return 2 2>/dev/null | exit 2
fi

# Read getopt's output this way to handle the quoting right:
eval set -- "${PARSED}"

# Header for `type` section. We call `type` on terms.
echo "###type###" > "${temp_file}"

# Process options in order:
while [[ $# -ne 0 ]]; do
    case "$1" in
        -D|--DEBUG)
            flags+=( "$1" )
            DEBUG=true
            shift
            ;;

        -p|--pattern)
            # push flag
            flags+=( "$1" )
            shift
            # push flag argument
            flags+=( "'$1'" )
            shift
            ;;

        -T|--TEST)
            shift
            # Override bin directory and rc file location for testing.
            bin_directory="$1"
            rc_file="${bin_directory}"/.myhelprc
            shift
            ;;

        --)
            shift
            # push all remaining as terms
            while [[ $# -ne 0 ]]; do
                # push term
                terms+=( "'$1'" )
                # Use `type` built-in.
                retval=$(type -a "$1" 2>/dev/null)
                if [[ $? -eq 0 ]]; then
                    echo "$retval" | head -1 >> "${temp_file}"
                fi
                shift
            done
            ;;

        -*)
            # push flag
            flags+=( "$1" )
            shift
            ;;

        *)
            # push term
            terms+=( "'$1'" )
            # Use `type` built-in.
            retval=$(type -a "$1" 2>/dev/null)
            if [[ $? -eq 0 ]]; then
                echo "$retval" | head -1 >> "${temp_file}"
            fi
            shift
            ;;
    esac
done


if [[ -f "${rc_file}" ]]; then
    # shellcheck disable=SC1090
    source "${rc_file}"
else
    echo "ERROR: Can't find myhelp\'s rc file: ${rc_file}"
    return 1 2>/dev/null | exit 1
fi

# If bin_directory wasn't set by --TEST:
if [[ -z "${bin_directory}" ]]; then
    bin_directory="${MYHELP_BIN_DIR}"
fi

# Collect output from commands.
{
    # Check aliases in the current shell.
    echo "###alias###"
    alias -p
    if [[ $? -ne 0 ]]; then
        echo "Error reading aliases ($?)" 1>&2
    fi

    # Check variables in the current shell.
    echo "###set###"
    set
    if [[ $? -ne 0 ]]; then
        echo "Error reading variables ($?)" 1>&2
    fi

    # Check declarations in the current shell.
    echo "###declare###"
    declare -p
    if [[ $? -ne 0 ]]; then
        echo "Error reading declarations -p ($?)" 1>&2
    fi
    declare -F
    if [[ $? -ne 0 ]]; then
        echo "Error reading declarations -F ($?)" 1>&2
    fi
} >> "${temp_file}"

# Can't pipe subshell directly to myhelp.py because `terms` and `flags` would
# become local to the subshell.

bash -s <<EOF
    if [[ -f "${MYHELP_VENV_BIN}/activate" ]]; then
        source "${MYHELP_VENV_BIN}/activate"
    fi

    PYTHONPATH="${MYHELP_PYTHONPATH}" "${MYHELP_PYTHON}" \
        "${bin_directory}/myhelp.py" ${flags[@]} ${terms[@]} < "${temp_file}"

    if type deactivate &>/dev/null; then
        deactivate
    fi
EOF

rm -f "${temp_file}"
