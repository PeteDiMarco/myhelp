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
# Name:         install.sh
# Version:      0.1
# Written by:   Pete DiMarco <pete.dimarco.software@gmail.com>
# Date:         06/23/2020
#
# Description:  Installs the myhelp application.

# Defaults:
DEBUG=false
force=
my_name=$(basename "$0")     # This script's name.
src_dir=$(pwd)
config_dir="${HOME}"/.myhelp
rc_file="${HOME}"/.myhelprc
cmd_alias='myhelp'

if [[ -d "${HOME}/bin" ]]; then
    bin_dir="${HOME}/bin"
elif [[ -d "${HOME}/.local/bin" ]]; then
    bin_dir="${HOME}/.local/bin"
else
    bin_dir='?'
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
    if [[ "${bin_dir}" = '?' ]]; then
        msg='REQUIRED!'
    else
        msg="Defaults to ${bin_dir}."
    fi
    cat <<HelpInfoHERE
Usage: ${my_name} [-h] [-D] [-f] [-s SOURCE_DIR] [-c CONFIGURATION_DIR]
                  [-t TARGET_DIR] [-a ALIAS]

Installs the myhelp application in the user's local directory.

Optional Arguments:
  -h, --help            Show this help message and exit.
  -D, --DEBUG           Set debugging mode.
  -f, --force           Overwrite existing files.
  -s, --src             Directory containing source files. Defaults to ${src_dir}.
  -c, --config          Configuration directory. Defaults to ${config_dir}.
  -t, --target          Directory to install files. ${msg}
  -a, --alias           User's alias for myhelp. Defaults to ${cmd_alias}.
HelpInfoHERE
    exit 0
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
OPTIONS='hDfs:c:t:a:'
LONGOPTIONS='help,DEBUG,force,src:,config:,target:,alias:'

PARSED=$(getopt --options="${OPTIONS}" --longoptions="${LONGOPTIONS}" --name "$0" -- "$@")
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
            force='1'
            shift
            ;;

        -s|--src)
            shift
            src_dir="$1"
            shift
            ;;

        -c|--config)
            shift
            config_dir="$1"
            shift
            ;;

        -t|--target)
            shift
            bin_dir="$1"
            shift
            ;;

        -a|--alias)
            shift
            cmd_alias="$1"
            shift
            ;;

        *)
            break
            ;;
    esac
done

set -e

if [[ "${bin_dir}" = '?' ]]; then
    echo 'Please specify a target directory.'
    echo
    print_help
fi

if [[ ! -d "${config_dir}" ]]; then
    mkdir -p "${config_dir}"
fi

bin_dir=$(realpath "${bin_dir}")
config_dir=$(realpath "${config_dir}")
src_dir=$(realpath "${src_dir}")

cd "${src_dir}"
cp -f packages.yaml.DEFAULT "${config_dir}"/packages.yaml
cp -f myhelp.sh "${bin_dir}"
chmod u+x "${bin_dir}"/myhelp.sh
cp -f myhelp.py "${bin_dir}"
chmod u+x "${bin_dir}"/myhelp.py

if [[ ! -f "${rc_file}" ]] || [[ -n "${force}" ]]; then
    cat >"${rc_file}" <<RC_END
export MYHELP_DIR="${config_dir}"
export MYHELP_PKG_DB="${config_dir}"/packages.db
export MYHELP_PKG_YAML="${config_dir}"/packages.yaml
export MYHELP_BIN_DIR="${bin_dir}"
export MYHELP_REFRESH=0
export MYHELP_ALIAS_NAME=${cmd_alias}
alias ${cmd_alias}='source myhelp.sh'
RC_END
    echo 'Be sure to add "source '"${rc_file}"'" to your .bashrc file.'
fi

source "${rc_file}"

set +e

if type pipenv &>/dev/null; then
    pipenv install &>/dev/null
fi

if [[ ! -f "${config_dir}/packages.db" ]] || [[ -n "${force}" ]]; then
    echo 'Initializing package name database. Please wait.'
    if python3 "${bin_dir}"/myhelp.py --refresh --interactive --standalone; then
        echo 'Initialization complete.'
    else
        echo 'Initialization failed.'
    fi
fi

