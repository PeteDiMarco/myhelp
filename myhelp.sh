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
# Version: 0.2
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
fix_path=false
bin_directory=
#my_name=$(basename "$0")             # This script's name.
my_shell=$(basename "$BASH")          # This script's shell.
preferred_shell=$(basename "$SHELL")  # User's shell from passwd.
rc_file=${HOME}/.myhelprc
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

remove_venv_from_path () {
    local -a array
    IFS=':' read -ra array <<<"${PATH}"
    for i in "${!array[@]}"; do
        dir="${array[$i]}"
        if [[ -d "${dir}" ]]; then
            matches=$(find "${dir}" '(' -name 'activate' -o -name 'activate.csh' -o \
                                        -name 'activate.fish' ')' -print | wc -l)
            if [[ "${matches}" = '3' ]]; then
                unset "array[$i]"
            fi
        elif [[ "${DEBUG}" = true ]]; then
            echo "${dir} not found."
        fi
    done
    export NEW_PATH=$(IFS=':' ; echo "${array[*]}")
}


# *****************************************************************************
# Command line options:
# *****************************************************************************

# Make sure we have the correct version of get_opt:
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "ERROR: This script requires the enhanced version of 'getopt'."
    exit 4
fi

# Parse commandline options:
OPTIONS='hDrp:siT:P'
LONGOPTIONS='help,DEBUG,refresh,pattern:,standalone,interactive,TEST:,PATH'

PARSED=$(getopt --options="${OPTIONS}" --longoptions="${LONGOPTIONS}" --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    # If getopt has complained about wrong arguments to stdout:
    exit 2
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

        -P|--PATH)
            fix_path=true
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
    echo "ERROR: Can't find ${rc_file}!"
    exit 1
fi

if [[ "${fix_path}" = true ]] || [[ "${MYHELP_FIX_PATH}" = true ]]; then
    remove_venv_from_path
    # unset PYTHONHOME VIRTUAL_ENV
fi

# If bin_directory wasn't set by --TEST:
if [[ -z "${bin_directory}" ]]; then
    bin_directory="${MYHELP_BIN_DIR}"
fi


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

# Can't pipe subshell directly to myhelp.py because `terms` and `flags` would become local
# to the subshell.
if [[ "${DEBUG}" = true ]]; then
    echo "PATH=${NEW_PATH}" "${bin_directory}/myhelp.py" "${flags[@]}" "${terms[@]}" "< ${temp_file}"
fi
PATH="${NEW_PATH}" "${bin_directory}/myhelp.py" "${flags[@]}" "${terms[@]}" < "${temp_file}"
rm -f "${temp_file}"

