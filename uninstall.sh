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
# Version:      0.1
# Written by:   Pete DiMarco <pete.dimarco.software@gmail.com>
# Date:         06/23/2020
#
# Description:  Un-installs the myhelp application.

# Defaults:
DEBUG=false
force='-n'
my_name=$(basename "$0")     # This script's name.
rc_file="${HOME}"/.myhelprc
source "${rc_file}"
if [[ $? -ne 0 ]]; then
    echo "ERROR: Could not find ${rc_file}."
    exit 2
fi


# *****************************************************************************
# Functions:
# *****************************************************************************

debug_msg () {
    if [[ "${DEBUG}" = true ]]; then
        echo 'DEBUG: '"$1"
    fi
}

print_help () {
    cat <<HelpInfoHERE
Usage: ${my_name} [-h] [-D] [-f]

Un-installs the myhelp application.

Optional Arguments:
  -h, --help            Show this help message and exit.
  -D, --DEBUG           Set debugging mode.
  -f, --force           Delete all contents of ${MYHELP_DIR}.
HelpInfoHERE
    exit 0
}

quiet_rm () {
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

        *)
            break
            ;;
    esac
done

if [[ "${force}" = '-f' ]]; then
    if [[ -d "${MYHELP_DIR}" ]]; then
        rm -rf "${MYHELP_DIR}"
    fi
else
    quiet_rm "${MYHELP_DIR}"/packages.yaml
    quiet_rm "${MYHELP_DIR}"/packages.db
    rmdir --ignore-fail-on-non-empty "${MYHELP_DIR}"
fi

quiet_rm "${rc_file}"
quiet_rm "${MYHELP_BIN_DIR}"/myhelp.sh
quiet_rm "${MYHELP_BIN_DIR}"/myhelp.py

echo 'Be sure to delete "source '"${rc_file}"'" from your .bashrc file.'

