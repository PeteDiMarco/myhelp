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

# Defaults:
DEBUG=false
#my_name=$(basename "$0")             # This script's name.
my_shell=$(basename "$BASH")         # This script's shell.
preferred_shell=$(basename "$SHELL") # User's shell from passwd.
rc_file=${HOME}/.myhelprc

declare -a flags=()
declare -a terms=()

# We need a temporary file to store the output of the shell builtin commands.
temp_file=$(mktemp /tmp/$$.XXXXXX)
trap "rm -f $temp_file" 0 2 3 15

# Are we being sourced?
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0

if [[ ${SOURCED} -eq 0 ]]; then
  echo "WARNING: Shell aliases will not be scanned."
fi

if [[ -f "${rc_file}" ]]; then
  source "${rc_file}"
else
  echo "ERROR: Can't find ${rc_file}!"
  exit 1
fi

{
  # Check aliases in the current shell.
  echo "###alias###"
  alias -p
  if [[ $? -ne 0 ]]; then
    echo "Error reading aliases ($?)" 1>&2
  fi

  # Check aliases in the current shell.
  echo "###set###"
  set
  if [[ $? -ne 0 ]]; then
    echo "Error reading variables ($?)" 1>&2
  fi

  # Check aliases in the current shell.
  echo "###declare###"
  declare -p
  if [[ $? -ne 0 ]]; then
    echo "Error reading declarations -p ($?)" 1>&2
  fi
  declare -F
  if [[ $? -ne 0 ]]; then
    echo "Error reading declarations -F ($?)" 1>&2
  fi

  # Check types in the current shell.
  echo "###type###"
  # Iterate through all remaining arguments.
  while [[ $# -ne 0 ]]; do
    if [[ -z "$1" ]]; then	# Skip over blanks.
      echo # NOP
    elif [[ "$1" = "-D" ]] || [[ "$1" = "--DEBUG" ]]; then
      flags+=( "$1" )
      DEBUG=true
    elif [[ "$1" = "--" ]]; then
      shift
      # push all remaining as terms
      while [[ $# -ne 0 ]]; do
        # push term
        terms+=( "'$1'" )
        retval=$(type -a "'$1'" 2>/dev/null)
        if [[ $? -eq 0 ]]; then
          echo "$retval"
        fi
        shift
      done
      break
    elif [[ "$1" = '-p' ]] || [[ "$1" =~ ^--pattern ]]; then
      # push flag
      flags+=( "$1" )
      shift
      # push flag argument
      flags+=( "'$1'" )
    elif [[ "$1" =~ ^- ]]; then
      # push flag
      flags+=( "$1" )
    else
      # push term
      terms+=( "'$1'" )
      # Use `type` built-in.
      retval=$(type -a "'$1'" 2>/dev/null)
      if [[ $? -eq 0 ]]; then
        echo "$retval"
      fi
    fi
    shift
  done
} > "${temp_file}"
# Can't pipe subshell directly to myhelp.py because `terms` and `flags` would become local
# to the subshell. Do not double quote `terms` or `flags` below:
if [[ "${DEBUG}" = true ]]; then
  echo myhelp.py ${flags[@]} ${terms[@]} < "${temp_file}"
fi
myhelp.py ${flags[@]} ${terms[@]} < "${temp_file}"
rm -f "${temp_file}"
