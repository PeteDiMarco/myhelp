#!/bin/bash
# *****************************************************************************
#  Copyright (c) 2020 Pete DiMarco
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# *****************************************************************************
#
# Name:         uninstall.sh
# Version:      0.5
# Written by:   Pete DiMarco <pete.dimarco.software@gmail.com>
# Date:         06/23/2020
#
# Description:  Un-installs the myhelp application.

# Defaults:
DEBUG=false
force='-n'
my_name=$(basename "$0")     # This script's name.
# Check if MYHELP_RC_FILE was defined in the parent shell.
rc_file="${MYHELP_RC_FILE}"
if [[ -z "${MYHELP_RC_FILE}" ]]; then
    # MYHELP_RC_FILE was not defined in the parent shell.
    if [[ -f "${HOME}/.config/myhelprc" ]]; then
        rc_file="${HOME}/.config/myhelprc"
    elif [[ -f "${HOME}/.myhelprc" ]]; then
        rc_file="${HOME}/.config/myhelprc"
    fi
fi


# *****************************************************************************
# Functions:
# *****************************************************************************

debug_msg () {
    # Prints $1 if DEBUG is true.
    if [[ "${DEBUG}" = true ]]; then
        echo 'DEBUG: '"$1"
    fi
}

print_help () {
    # Print help message, then exit.
    cat <<HelpInfoHERE
Usage: ${my_name} [-h] [-D] [-f]

Un-installs the myhelp application.

Optional Arguments:
  -h, --help                    Show this help message and exit.
  -D, --DEBUG                   Set debugging mode.
  -f, --force                   Delete myhelp's config directory.
  -c, --configfile CONFIGFILE   Path to myhelp's "rc" file.
HelpInfoHERE
    exit 0
}

quiet_rm () {
    # Don't delete nonexistent file.
    if [[ -f "$1" ]]; then
        rm -f "$1"
    fi
}


# *****************************************************************************
# Main:
# *****************************************************************************

# Make sure we have the correct version of get_opt:
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "ERROR: This script requires the enhanced version of 'getopt'."
    exit 4
fi

# Parse commandline options:
OPTIONS='hDf'
LONGOPTIONS='help,DEBUG,force'

PARSED=$(getopt --options="${OPTIONS}" --longoptions="${LONGOPTIONS}" --name "${my_name}" -- "$@")
if [[ $? -ne 0 ]]; then
    # If getopt has complained about wrong arguments to stdout:
    exit 2
fi

# Read getopt's output this way to handle the quoting right:
eval set -- "${PARSED}"

# Process options in order:
while true; do
    case "$1" in
        -h|--help)
            print_help
            ;;

        -D|--DEBUG)
            DEBUG=true
            shift
            ;;

        -f|--force)
            force='-f'
            shift
            ;;

        -c|--configfile)
            shift
            rc_file="$1"
            shift
            ;;

        *)
            break
            ;;
    esac
done

set -e

if [[ -n "${rc_file}" ]]; then
    source "${rc_file}"
fi

if [[ -z "${MYHELP_CFG_DIR}" ]]; then
    echo "ERROR: Can\'t find myhelp\'s configuration directory."
    exit 2
fi

if [[ "${force}" = '-f' ]]; then
    if [[ -d "${MYHELP_CFG_DIR}" ]]; then
        rm -rf "${MYHELP_CFG_DIR}"
    fi
else
    quiet_rm "${MYHELP_CFG_DIR}"/packages.yaml
    quiet_rm "${MYHELP_CFG_DIR}"/packages.db
    rmdir --ignore-fail-on-non-empty "${MYHELP_CFG_DIR}"
fi

quiet_rm "${rc_file}"
quiet_rm "${MYHELP_BIN_DIR}"/myhelp.sh
quiet_rm "${MYHELP_BIN_DIR}"/myhelp.py

echo 'Be sure to delete "source '"${rc_file}"'" from your .bashrc file.'

