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
test_mode=false
fix_path=false
force=
my_name=$(basename "$0")     # This script's name.
src_dir=$(pwd)
config_dir="${HOME}"/.myhelp
rc_filename=.myhelprc
rc_file="${HOME}"/"${rc_filename}"
cmd_alias='myhelp'
MYHELP_PYTHON=

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
                  [-t TARGET_DIR] [-a ALIAS] [-T]

Installs the myhelp application in the user's local directory.

Optional Arguments:
  -h, --help            Show this help message and exit.
  -D, --DEBUG           Set debugging mode.
  -f, --force           Overwrite existing files.
  -s, --src             Directory containing source files. Defaults to ${src_dir}.
  -c, --config          Configuration directory. Defaults to ${config_dir}.
  -t, --target          Directory to install files. ${msg}
  -a, --alias           User's alias for myhelp. Defaults to ${cmd_alias}.
  -P, --PATH            Fix PATH to ignore virtual environment settings.
  -T, --TEST            Test mode.
HelpInfoHERE
    exit 0
}

get_python3 () {
    export MYHELP_PYTHON
    MYHELP_PYTHON=$(which python)
    if [[ $? -eq 0 ]] ; then
        python_version=$(python -V | sed -e 's/^Python \([^.]*\)\..*$/\1/i')
        if [[ "${python_version}" = '3' ]]; then
            return
        fi
    fi
    MYHELP_PYTHON=$(which python3)
    if [[ $? -eq 0 ]] ; then
        python_version=$(python -V | sed -e 's/^Python \([^.]*\)\..*$/\1/i')
        if [[ "${python_version}" = '3' ]]; then
            return
        fi
    fi
    echo "ERROR: Can't find a Python interpreter."
    exit 1
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
OPTIONS='hDfs:c:t:a:TP'
LONGOPTIONS='help,DEBUG,force,src:,config:,target:,alias:,TEST,PATH'

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

        -T|--TEST)
            shift
            test_mode=true
            ;;

        -P|--PATH)
            shift
            fix_path=true
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

if [[ "${bin_dir}" = '?' ]]; then
    echo 'Please specify a target directory.'
    echo
    print_help
fi

if [[ -n "${force}" ]] && [[ "${test_mode}" = false ]]; then
    rm -rf "${config_dir}"
fi

if [[ ! -d "${config_dir}" ]]; then
    mkdir -p "${config_dir}"
fi

bin_dir=$(realpath "${bin_dir}")
config_dir=$(realpath "${config_dir}")
src_dir=$(realpath "${src_dir}")

if [[ "${test_mode}" = true ]]; then
    rc_file="${bin_dir}"/"${rc_filename}"
fi

if [[ -f "${rc_file}" ]] && [[ -z "${force}" ]] && [[ "${test_mode}" = false ]]; then
    read -p "\"${rc_file}\" file already exists. Overwrite it?" reply
    if [[ ! "${reply}" =~ ^\ *[yY] ]]; then
        echo "Installation aborted."
        exit 0
    fi
    echo
fi

cat >"${rc_file}" <<RC_END
export MYHELP_DIR="${config_dir}"
export MYHELP_PKG_DB="${config_dir}"/packages.db
export MYHELP_PKG_YAML="${config_dir}"/packages.yaml
export MYHELP_BIN_DIR="${bin_dir}"
export MYHELP_REFRESH=0
export MYHELP_ALIAS_NAME=${cmd_alias}
export MYHELP_FIX_PATH=${fix_path}
alias ${cmd_alias}='source myhelp.sh'
RC_END

if [[ "${test_mode}" = false ]]; then
    echo 'Be sure to add the following to your ".bashrc" file if it is not already present:'
    cat <<BASHRC_CODE
if [ -f ~/.myhelprc ]; then
    source ~/.myhelprc
fi
BASHRC_CODE
fi

cd "${src_dir}"
cp -f packages.yaml.DEFAULT "${config_dir}"/packages.yaml
cp -f myhelp.sh "${bin_dir}"
chmod u+x "${bin_dir}"/myhelp.sh
cp -f myhelp.py "${bin_dir}"
chmod u+x "${bin_dir}"/myhelp.py

# shellcheck disable=SC1090
source "${rc_file}"

interactive=
if [[ "${test_mode}" = false ]]; then
    interactive='--interactive'
fi

if type pipenv &>/dev/null; then
    pipenv install # &>/dev/null
fi

if [[ ! -f "${config_dir}/packages.db" ]] || [[ -n "${force}" ]]; then
    echo 'Initializing package name database. Please wait.'
    if "${bin_dir}"/myhelp.py --refresh "${interactive}" --standalone; then
        echo 'Initialization complete.'
    else
        echo 'Initialization failed.'
    fi
fi

