#!/usr/bin/env python3
# ***************************************************************************
# Copyright 2020 Pete DiMarco
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ***************************************************************************
#
# Name:
# Version:
# Date:
# Written by: Pete DiMarco <pete.dimarco.software@gmail.com>
#
# Description:
#
# Dependencies:

import os
import sys
import subprocess
import argparse
import sqlite3
import re
import yaml
from enum import auto, IntEnum

# Defaults:
PROGRAM_NAME = os.path.basename(sys.argv[0])
EPILOG = ""
DEBUG = False
DB_TABLE = "Packages"
YAML_FILE_VERSION = 1


def run_cmd(cmd_str: str, ignore: list = [0], exit_on_error: bool = False, env=None):
    """

    :param cmd_str: Shell command to run.
    :param ignore: List of return codes to ignore.
    :param exit_on_error: Exit program if error occurs.
    :param env: Dict.
    :return: str
    """
    result = None
    if 0 not in ignore:
        ignore.append(0)

    try:
        result = subprocess.run(
            cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=env
        )
    except subprocess.CalledProcessError as e:
        # "ignore" contains return codes that are not considered errors.
        # For example: grep will return errno == 1 if it doesn't match any
        # lines in its input stream.  We want to ignore this case since it's
        # not really an error.
        if e.returncode not in ignore:
            if exit_on_error:
                exit(e.returncode)
            else:
                raise subprocess.CalledProcessError(
                    returncode=e.returncode, cmd=cmd_str
                )
    else:
        if result.returncode not in ignore or result.stderr:
            if exit_on_error:
                exit(result.returncode)
            else:
                raise subprocess.CalledProcessError(
                    returncode=result.returncode,
                    cmd=cmd_str,
                    output=result.stdout,
                    stderr=result.stderr,
                )

    return result.stdout.decode().strip()


"""
# Get the names of all the running processes.
# Process names in brackets []:
progs=$(ps --no-headers -Ao args -ww | grep '^\[' | sed -Ee 's/^\[([^]/:]+).*$/\1/')
# Process names without brackets and append to progs:
progs=${progs}$(ps --no-headers -Ao args -ww | grep -v '^\[' | sed -e 's/ .*$//')
# Filter and sort progs:
progs=$(echo "${progs}" | sort | uniq | xargs basename -a)
"""


def get_file_type(token: str):
    result = run_cmd(f"file -b {token}", ignore=[0, 127])
    if "No such file or directory" in result:
        return ""
    return result


def get_mime_type(token: str):
    return run_cmd(f"xdg-mime query filetype {token} 2>/dev/null", ignore=[0, 2, 127])


def open_package_db(conn):
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS {DB_TABLE} (Name text, Type text, Description text)"
    )
    return cursor


def refresh_package_db(cursor, config_filename: str):
    cursor.execute(f"DELETE FROM {DB_TABLE}")
    with open(config_filename, "r") as fp:
        pkg_data = yaml.load(fp, Loader=yaml.BaseLoader)
        assert int(pkg_data["version"]) == YAML_FILE_VERSION
        for key, val in pkg_data["packages"].items():
            pkg_list = run_cmd(val["command"], ignore=[0, 127]).splitlines()
            records = [(pkg, key, val["description"]) for pkg in pkg_list]
            cursor.executemany(
                f"INSERT INTO {DB_TABLE} (Name, Type, Description) VALUES (?,?,?)",
                records,
            )


def search_package_db(cursor, target: str):
    cursor.execute(f"SELECT * FROM {DB_TABLE} WHERE Name=?", (target,))
    return cursor.fetchall()


def has_info_page(token: str):
    result = run_cmd(f"info -w {token}", [127])
    if result in ["", "dir", "*manpages*"] or result.startswith('././'):
        return False
    return True


def has_man_page(token: str):
    result = run_cmd(f"man --whatis {token} 2>/dev/null", ignore=[16, 127])
    return bool(result)


def get_which_result(token: str):
    return run_cmd(f"which -a {token} 2>/dev/null", ignore=[1, 127])


class ShellBuiltIn:
    class Cmd(IntEnum):
        ALIAS = 0
        DECLARE = auto()
        SET = auto()
        TYPE = auto()

    _declare_attr_ = {
        "-": None,
        "a": "indexed array",
        "A": "associative array",
        "f": "function",
        "i": "integer",
        "l": "convert to lower",
        "n": "reference",
        "r": "readonly",
        "t": "trace",
        "u": "convert to upper case",
        "x": "export",
    }

    def __init__(self, input_file):
        self.results = dict()
        for cmd in ShellBuiltIn.Cmd.__members__.keys():
            self.results[cmd] = []
        self._cmd_parser_ = {
            ShellBuiltIn.Cmd.ALIAS.name.lower(): self.parse_alias,
            ShellBuiltIn.Cmd.DECLARE.name.lower(): self.parse_declare,
            ShellBuiltIn.Cmd.SET.name.lower(): self.parse_set,
            ShellBuiltIn.Cmd.TYPE.name.lower(): self.parse_type,
        }
        self._mode_ = None
        for line in map(str.rstrip, input_file):
            self.parse(line)

    def parse(self, line: str):
        if line.startswith("###") and line.endswith("###"):
            self._mode_ = line.strip("# ").lower()
        else:
            if self._mode_ is None:
                raise ValueError(line)
            self._cmd_parser_[self._mode_](line)

    def parse_alias(self, line: str):
        match = re.search(r"^alias ([^=]*)=(.*)$", line)
        if match:
            self.results[ShellBuiltIn.Cmd.ALIAS.name].append(
                (match.group(1), f'{match.group(1)} is aliased to "{match.group(2)}".')
            )
        else:
            raise ValueError(line)

    def parse_declare(self, line: str):
        match = re.search(r"^declare -([^ ]*) ([^ =]*).*$", line)
        if match:
            attr_list = []
            for char in match.group(1):
                attr_list.append(ShellBuiltIn._declare_attr_[char])
            if None in attr_list:
                msg = f"{match.group(2)} is a shell variable."
            else:
                msg = f"{match.group(2)} has the attribute(s): " + ", ".join(attr_list) + "."
            self.results[ShellBuiltIn.Cmd.DECLARE.name].append(
                (match.group(2), msg)
            )

    def parse_set(self, line: str):
        match = re.search(r"^([a-zA-Z0-9_]+)=", line)
        if match:
            self.results[ShellBuiltIn.Cmd.SET.name].append(
                (match.group(1), f"{match.group(1)} is a shell variable.")
            )
            return

        match = re.search(r"^([a-zA-Z0-9_]+) \(\)", line)
        if match:
            self.results[ShellBuiltIn.Cmd.SET.name].append(
                (match.group(1), f"{match.group(1)} is a shell function.")
            )
            return

    def parse_type(self, line: str):
        match = re.search(r"^([^ ]*) is (.*)$", line)
        if match:
            self.results[ShellBuiltIn.Cmd.ALIAS.name].append(
                (match.group(1), f"{match.group(1)} is {match.group(2)}.")
            )
        else:
            raise ValueError(line)

    def search(self, target: str):
        retval = []
        for key in self.results.keys():
            retval.extend([ msg for (label, msg) in self.results[key] if label == target ])
        return retval


def read_shell_builtins():
    builtin = ShellBuiltIn(sys.stdin)


if __name__ == "__main__":
    # Parse command line arguments:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="",
        epilog=EPILOG,
    )
    parser.add_argument(
        "-D",
        "--DEBUG",
        action="store_true",
        default=False,
        help="Enable debugging mode.",
    )
    parser.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        default=False,
        help="Refresh package cache.",
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", default=False, help="Show spinner."
    )
    parser.add_argument(
        "terms", metavar="NAME", type=str, nargs="*", help="Objects to identify."
    )

    args = parser.parse_args()
    DEBUG = args.DEBUG
    config_dir = os.environ["MYHELP_DIR"]
    if not os.path.isdir(config_dir):
        os.mkdir(config_dir)
    db_file = os.environ["MYHELP_PKG_DB"]
    yaml_file = os.environ["MYHELP_PKG_YAML"]
    refresh = args.refresh or int(os.environ["MYHELP_REFRESH"]) == 1
    builtins = ShellBuiltIn(sys.stdin)
    with sqlite3.connect(db_file) as conn:
        cursor = open_package_db(conn)
        if refresh:
            refresh_package_db(cursor, yaml_file)
            conn.commit()
        for term in args.terms:
            for result in builtins.search(term):
                print(result)
            result = get_file_type(term)
            if result == "directory":
                print(f"{term} is a {result}.")
            elif result:
                print(f"{term} is a(n) {result} file.")
            result = get_mime_type(term)
            if result:
                print(f"{term} has the MIME type {result}.")
            for result in search_package_db(cursor, term):
                print(f"{term} is a {result[2]}.")
            if has_info_page(term):
                print(f"{term} has an info page.")
            if has_man_page(term):
                print(f"{term} has a man page.")
            for result in get_which_result(term).splitlines():
                print(f"{term} is the command {result}.")
