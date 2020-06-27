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
# Name:         myhelp.py
# Version:      0.2
# Date:         06/23/2020
# Written by:   Pete DiMarco <pete.dimarco.software@gmail.com>
#
# Description:
#
# Dependencies:
# getent, xdg-mime, file, info, man, which

import os
import sys
import subprocess
import argparse
import sqlite3
import re
import yaml
import psutil
import collections
import itertools
from enum import auto, IntEnum

# Defaults:
PROGRAM_NAME = os.path.basename(sys.argv[0])
DESCRIPTION="""
Identifies the names provided.  Tries every test imaginable.  Looks for:
man pages, info pages, executables in PATH, aliases, shell variables, running
processes, shell functions, built-in shell commands, packages, filesystems,
and files relative to the current working directory."""

EPILOG = ""
DEBUG = False
DB_TABLE = "Packages"
YAML_FILE_VERSION = 1


class Spinner:
    def __init__(self):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])

    def __next__(self):
        sys.stdout.write(next(self.spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')

    def __enter__(self):
        next(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def stop(self):
        sys.stdout.write('\b')
        sys.stdout.write(' ')   # overwrite spinner with blank
        sys.stdout.write('\r')  # move to next line
        sys.stdout.flush()


def run_cmd(cmd_str: str, ignore=[0], exit_on_error: bool = False, env=None):
    """

    :param cmd_str: Shell command to run.
    :param ignore: List of return codes to ignore.
    :param exit_on_error: Exit program if error occurs.
    :param env: Dict.
    :return: str
    """
    result = None
    ignore_all = False
    if isinstance(ignore, list):
        if '*' in ignore:
            ignore_all = True
        elif 0 not in ignore:
            ignore.append(0)
    elif isinstance(ignore, int):
        ignore = [0, ignore]
    elif ignore =='*':
        ignore_all = True
    else:
        raise ValueError(ignore)

    try:
        result = subprocess.run(
            cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=env
        )
    except subprocess.CalledProcessError as e:
        # "ignore" contains return codes that are not considered errors.
        # For example: grep will return errno == 1 if it doesn't match any
        # lines in its input stream.  We want to ignore this case since it's
        # not really an error.
        if not ignore_all and e.returncode not in ignore:
            if exit_on_error:
                exit(e.returncode)
            else:
                raise subprocess.CalledProcessError(
                    returncode=e.returncode, cmd=cmd_str
                )
    else:
        if not ignore_all and (result.returncode not in ignore or result.stderr):
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


def get_processes():
    return collections.Counter(
        [proc.name() for proc in psutil.process_iter(attrs=["name"])]
    )


def get_ent_info(target: str):
    results = []
    if run_cmd(f"getent passwd {target}", ignore=[0, 2]):
        results.append(f"There is a user named {target}.")
    if run_cmd(f"getent group {target}", ignore=[0, 2]):
        results.append(f"There is a group named {target}.")
    if run_cmd(f"getent hosts {target}", ignore=[0, 2]):
        results.append(f"There is a host named {target}.")
    if run_cmd(f"getent services {target}", ignore=[0, 2]):
        results.append(f"There is a network service named {target}.")
    return results


def get_file_type(token: str):
    result = run_cmd(f"file -b {token}", ignore=[0, 127])
    if "No such file or directory" in result:
        return []
    if result == "directory":
        return [f"{token} is a {result}."]
    elif result:
        return [f"{token} is a(n) {result} file."]
    return []


def get_mime_type(token: str):
    result = run_cmd(
        f"xdg-mime query filetype {token} 2>/dev/null", ignore=[0, 2, 5, 127]
    )
    if result:
        return [f"{term} has the MIME type {result}."]
    return []


def get_df_info(token: str):
    retval = []
    result = run_cmd(
        f"df --output=source,fstype {token} 2>/dev/null", ignore='*'
    ).splitlines()
    if result:
        for line in result[1:]:
            retval.append("%s is on filesystem %s (type %s)." % tuple([token] + line.split()))
    return retval


def open_package_db(conn):
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS {DB_TABLE} (Name text, Type text, Description text)"
    )
    return cursor


def refresh_package_db(cursor, config_filename: str, spinner=None):
    cursor.execute(f"DELETE FROM {DB_TABLE}")
    with open(config_filename, "r") as fp:
        pkg_data = yaml.load(fp, Loader=yaml.BaseLoader)
        assert int(pkg_data["version"]) == YAML_FILE_VERSION
        for key, val in pkg_data["packages"].items():
            if run_cmd(f"which {key}", ignore=[0, 1]).strip():
                pkg_list = run_cmd(val["command"]).splitlines()
                records = [(pkg, key, val["description"]) for pkg in pkg_list]
                if spinner:
                    next(spinner)
                cursor.executemany(
                    f"INSERT INTO {DB_TABLE} (Name, Type, Description) VALUES (?,?,?)",
                    records,
                )


def search_package_db(cursor, target: str):
    results = []
    cursor.execute(f"SELECT * FROM {DB_TABLE} WHERE Name=?", (target,))
    for record in cursor.fetchall():
        results.append(f"{target} is a {record[2]}.")
    return results


def get_devices():
    devices = collections.Counter()
    mount_points = collections.Counter()
    fstypes = collections.Counter()
    for elt in psutil.disk_partitions(all=True):
        devices.update([elt.device])
        mount_points.update([elt.mountpoint])
        fstypes.update([elt.fstype])
    return {"devices": devices, "mount_points": mount_points, "fstypes": fstypes}


def search_devices(device_dict: dict, target: str):
    results = []
    if device_dict["devices"][target]:
        results.append(f"There is at least 1 device called {target}.")
    if device_dict["mount_points"][target]:
        results.append(f"There is at least 1 mount point called {target}.")
    if device_dict["fstypes"][target]:
        results.append(f"There is at least 1 file system type called {target}.")
    return results


def has_info_page(token: str):
    result = run_cmd(f"info -w {token}", [127])
    if result in ["", "dir", "*manpages*"] or result.startswith("././"):
        return []
    return [f"{term} has an info page."]


def has_man_page(token: str):
    result = run_cmd(f"man --whatis {token} 2>/dev/null", ignore=[16, 127])
    if bool(result):
        return [f"{term} has a man page."]
    return []


def get_which_results(token: str):
    results = []
    for line in run_cmd(f"which -a {token} 2>/dev/null", ignore=[1, 127]).splitlines():
        results.append(f"{token} is the command {line}.")
    return results


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
        # Dispatch parsing based on command type:
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
                msg = (
                    f"{match.group(2)} has the attribute(s): "
                    + ", ".join(attr_list)
                    + "."
                )
            self.results[ShellBuiltIn.Cmd.DECLARE.name].append((match.group(2), msg))

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
            retval.extend(
                [msg for (label, msg) in self.results[key] if label == target]
            )
        return retval


if __name__ == "__main__":
    # Parse command line arguments:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=os.environ["MYHELP_ALIAS_NAME"],
        description=DESCRIPTION,
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
        "-s", "--standalone", action="store_true", default=False, help="Don't read shell builtins."
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", default=False, help="Show spinner when refreshing package cache."
    )
    parser.add_argument(
        "terms", metavar="NAME", type=str, nargs="*", help="Object to identify."
    )

    args = parser.parse_args()
    DEBUG = args.DEBUG
    config_dir = os.environ["MYHELP_DIR"]
    if not os.path.isdir(config_dir):
        os.mkdir(config_dir)
    db_file = os.environ["MYHELP_PKG_DB"]
    yaml_file = os.environ["MYHELP_PKG_YAML"]
    refresh = args.refresh or int(os.environ["MYHELP_REFRESH"]) == 1
    if not args.standalone:
        builtins = ShellBuiltIn(sys.stdin)
    proc_dict = get_processes()
    if DEBUG:
        print(proc_dict)
    device_dict = get_devices()
    if DEBUG:
        print(device_dict)
    with sqlite3.connect(db_file) as conn:
        cursor = open_package_db(conn)
        if refresh:
            spinner = Spinner() if args.interactive else None
            refresh_package_db(cursor, yaml_file, spinner)
            conn.commit()
            if spinner:
                spinner.stop()
        for term in args.terms:
            results = (
                get_file_type(term)
                + get_mime_type(term)
                + search_package_db(cursor, term)
                + has_info_page(term)
                + has_man_page(term)
                + get_which_results(term)
                + search_devices(device_dict, term)
                + get_ent_info(term)
                + get_df_info(term)
            )
            if not args.standalone:
                results.extend(builtins.search(term))
            if proc_dict[term] == 1:
                results.append(f"There is 1 process called {term}.")
            elif proc_dict[term] > 1:
                results.append(f"There are {proc_dict[term]} processes called {term}.")
            if results:
                for res in results:
                    print(res)
            else:
                print(f"Nothing found for {term}.")
            print()
