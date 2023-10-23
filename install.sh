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
# Version:      0.3
# Written by:   Pete DiMarco <pete.dimarco.software@gmail.com>
# Date:         06/23/2020
#
# Description:  Installs the myhelp application.

# Defaults:
DEBUG=false
test_mode=false
force=
my_name=$(basename "$0")  # This script's name.
src_dir=$(dirname $(realpath "$0") )  # Source directory.
config_dir="${HOME}/.myhelp"
rc_file_name=.myhelprc
rc_file_path="${HOME}/${rc_file_name}"
cmd_alias='myhelp'
MYHELP_PYTHON=

# Find local bin directory.
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
  -a, --alias           User's alias for myhelp. Defaults to ${cmd_alias}.
  -c, --config          Configuration directory. Defaults to ${config_dir}.
  -f, --force           Overwrite existing files.
  -s, --src             Directory containing source files. Defaults to ${src_dir}.
  -t, --target          Directory to install files. ${msg}
  -D, --DEBUG           Set debugging mode.
  -T, --TEST            Test mode. Used by unit and integration tests.
HelpInfoHERE
    exit 0
}

check_for_python3 () {
    # Check for "python".
    if type python &>/dev/null; then
        python_version=$(python -V | sed -e 's/^Python \([^.]*\)\..*$/\1/i')
        if [[ "${python_version}" = '3' ]]; then
            MYHELP_PYTHON='python'
            return
        fi
    fi
    # Check for "python3".
    if type python3 &>/dev/null; then
        MYHELP_PYTHON='python3'
        return
    fi
    # Found neither.
    echo "ERROR: Can't find a Python interpreter. Please install it and try again."
    exit 1
}

check_for_pip () {
    # Check for "pip".
    if type pip &>/dev/null; then
        pip_name='pip'
        return
    fi
    # Check for "pip3".
    if type pip3 &>/dev/null; then
        pip_name='pip3'
        return
    fi
    # Found neither.
    echo "ERROR: Can't find pip. Please install it and try again."
    exit 1
}

get_pipenv () {
    "${pip_name}" show pipenv &>/dev/null
    if [[ $? -ne 0 ]]; then
        "${pip_name}" install -U pipenv
    fi
}

check_dir_exists () {
    if [[ ! -d "${1}" ]]; then
        echo "Directory ${1} does not exist. Exiting..."
        exit 1
    fi
}


# *****************************************************************************
# Process Command Line Options:
# *****************************************************************************

# Make sure we have the correct version of get_opt:
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "ERROR: This script requires the enhanced version of 'getopt'."
    exit 4
fi

# Parse commandline options:
OPTIONS='hDfs:c:t:a:T'
LONGOPTIONS='help,DEBUG,force,src:,config:,target:,alias:,TEST'

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

# bin_dir is required.
if [[ "${bin_dir}" = '?' ]]; then
    echo 'Please specify a target directory.'
    echo
    print_help
fi

# If force is true and we're not running tests, overwrite existing config files.
if [[ -n "${force}" ]] && [[ "${test_mode}" = false ]]; then
    rm -rf "${config_dir}"
fi

# Make paths absolute.
bin_dir=$(realpath "${bin_dir}")
config_dir=$(realpath "${config_dir}")
src_dir=$(realpath "${src_dir}")


# *****************************************************************************
# Main:
# *****************************************************************************

# Create the config directory (if it doesn't exist already).
if [[ ! -d "${config_dir}" ]]; then
    mkdir -p "${config_dir}"
fi

check_dir_exists "${bin_dir}"
check_dir_exists "${src_dir}"

# If we're running tests, create a local copy of the rc file.
if [[ "${test_mode}" = true ]]; then
    rc_file_path="${bin_dir}/${rc_file_name}"
fi
# Ask the user if they want to overwrite the rc file.
if [[ -f "${rc_file_path}" ]] && [[ -z "${force}" ]] \
        && [[ "${test_mode}" = false ]]; then
    read -p "\"${rc_file_path}\" file already exists. Overwrite it?" reply
    if [[ ! "${reply}" =~ ^\ *[yY] ]]; then
        echo "Installation aborted."
        exit 0
    fi
    echo
fi

export PIPENV_VENV_IN_PROJECT=1
check_for_python3
check_for_pip
get_pipenv

venv_dir="${src_dir}/venv"
if  [[ ! -d "${venv_dir}" ]]; then
    mkdir -p "${venv_dir}"
fi
pipenv install # &>/dev/null
venv_bin_dir="${venv_dir}/bin"
activate="${venv_bin_dir}/activate"
if [[ -f "${activate}" ]]; then
    # shellcheck disable=SC1090
    source "${activate}"
    PYTHONPATH="${src_dir}"
fi

cat >"${rc_file_path}" <<RC_END
export MYHELP_DIR="${config_dir}"
export MYHELP_PKG_DB="${config_dir}/packages.db"
export MYHELP_PKG_YAML="${config_dir}/packages.yaml"
export MYHELP_BIN_DIR="${bin_dir}"
export MYHELP_REFRESH=0
export MYHELP_ALIAS_NAME="${cmd_alias}"
export MYHELP_PYTHON="${MYHELP_PYTHON}"
export MYHELP_PYTHONPATH="${PYTHONPATH}"
export MYHELP_VENV_BIN="${venv_bin_dir}"
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
cp -f packages.yaml.DEFAULT "${config_dir}/packages.yaml"
cp -f myhelp.sh "${bin_dir}"
chmod u+x "${bin_dir}/myhelp.sh"
cp -f myhelp.py "${bin_dir}"
chmod u+x "${bin_dir}/myhelp.py"

# shellcheck disable=SC1090
source "${rc_file_path}"

interactive=
if [[ "${test_mode}" = false ]]; then
    interactive='--interactive'
fi

if [[ ! -f "${config_dir}/packages.db" ]] || [[ -n "${force}" ]]; then
    echo 'Initializing package name database. Please wait.'
    if "${bin_dir}/myhelp.py" --refresh "${interactive}" --standalone; then
        echo 'Initialization complete.'
    else
        echo 'Initialization failed.'
    fi
fi

