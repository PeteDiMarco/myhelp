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
from typing import Pattern

# Defaults:
PROGRAM_NAME = os.path.basename(sys.argv[0])
DESCRIPTION = """
Identifies the names provided.  Tries every test imaginable.  Looks for:
man pages, info pages, executables in PATH, aliases, shell variables, running
processes, shell functions, built-in shell commands, packages, filesystems,
and files relative to the current working directory."""

EPILOG = ""
DEBUG = False
DB_TABLE = "Packages"
YAML_FILE_VERSION = 1


class Spinner:
    """
    Implements spinner object.
    """

    def __init__(self):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])

    def __next__(self):
        sys.stdout.write(next(self.spinner))
        sys.stdout.flush()
        sys.stdout.write("\b")

    def __enter__(self):
        next(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def stop(self):
        sys.stdout.write("\b")
        sys.stdout.write(" ")  # overwrite spinner with blank
        sys.stdout.write("\r")  # move to next line
        sys.stdout.flush()


def run_cmd(cmd_str: str, ignore=[0], exit_on_error: bool = False, env=None):
    """
    Runs a shell command. Can ignore one or more return codes.
    :param cmd_str: Shell command to run.
    :param ignore: Integer, string, or list of integers indicating return codes to ignore, or '*' to ignore all errors AND messages to stderr.
    :param exit_on_error: Exit program if error occurs, else raises exception.
    :param env: Dict of environment variables.
    :return: str
    :except subprocess.CalledProcessError
    :except ValueError
    """
    result = None
    ignore_all = False
    if isinstance(ignore, list):
        if "*" in ignore:  # Ignore all return codes.
            ignore_all = True
        elif 0 not in ignore:  # Always ignore return code 0.
            ignore.append(0)
    elif isinstance(ignore, int):
        ignore = [0, ignore]  # Always ignore return code 0.
    elif ignore == "*":  # Ignore all return codes.
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
        # not really an error. Note: pipelines return the errno of the last command
        # by default. Use `set -o pipefail` to override this behavior.
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
                exit(result.returncode if result.returncode != 0 else 1)
            else:
                raise subprocess.CalledProcessError(
                    returncode=result.returncode,
                    cmd=cmd_str,
                    output=result.stdout,
                    stderr=result.stderr,
                )

    return result.stdout.decode().strip()


def get_processes():
    """
    Gets the names of all running processes. Does not accept globs.
    :return: Counter dict of process names.
    """
    return collections.Counter(
        [proc.name() for proc in psutil.process_iter(attrs=["name"])]
    )


def search_processes(procs: collections.Counter, target):
    """
    Returns the names of all running processes that match `target`. Accepts
    compiled regexes or strings.
    :param procs: Dictionary of process names to counts.
    :param target: String or RE to search for.
    :return: list of str.
    """
    results = []
    if isinstance(target, str):
        if procs[term] == 1:
            results.append(f"There is 1 process called {target}.")
        elif procs[term] > 1:
            results.append(f"There are {procs[target]} processes called {target}.")
    elif isinstance(target, Pattern):
        for key, val in dict_get_regex(procs, target, return_tuple=True):
            if val == 1:
                results.append(f"There is 1 process called {key}.")
            elif val > 1:
                results.append(f"There are {val} processes called {key}.")
    else:
        raise ValueError(target)
    return results


def get_ent_info(target: str):
    """
    Uses the `getent` command (if available) to scan the user, group, hosts,
    and services databases for `target`. Does not accept globs.
    :param target: string to search for.
    :return: list of strings.
    """
    results = []
    ignore_list = [0, 2, 127]
    if run_cmd(f"getent passwd {target}", ignore=ignore_list):
        results.append(f"There is a user named {target}.")
    if run_cmd(f"getent group {target}", ignore=ignore_list):
        results.append(f"There is a group named {target}.")
    if run_cmd(f"getent hosts {target}", ignore=ignore_list):
        results.append(f"There is a host named {target}.")
    if run_cmd(f"getent services {target}", ignore=ignore_list):
        results.append(f"There is a network service named {target}.")
    return results


def get_file_type(token: str):
    """
    Uses the `file` command (if available) to analyze `token`. Accepts globs.
    :param token: string file name.
    :return: list of strings.
    """
    result = run_cmd(f"file -b {token}", ignore=[0, 127])
    if "No such file or directory" in result:
        return []
    if result == "directory":
        return [f"{token} is a {result}."]
    elif result:
        return [f"{token} is a(n) {result} file."]
    return []


def get_mime_type(token: str):
    """
    Uses the `xdg-mime` command (if available) to determine the MIME type of
    `token`. Only processes first argument if passed a glob.
    :param token: string object name.
    :return: list of 0 or 1 strings.
    """
    result = run_cmd(
        f"xdg-mime query filetype {token} 2>/dev/null", ignore=[0, 2, 5, 127]
    )
    if result:
        return [f"{term} has the MIME type {result}."]
    return []


def get_df_info(token: str):
    """
    Uses the `df` command (if available) to determine the name and type of the
    filesystem that `token` resides on. Accepts globs.
    :param token: string object name.
    :return: list of strings.
    """
    retval = []
    result = run_cmd(
        f"df --output=source,fstype {token} 2>/dev/null", ignore="*"
    ).splitlines()
    if result:
        for line in result[1:]:
            retval.append(
                "%s is on filesystem %s (type %s)." % tuple([token] + line.split())
            )
    return retval


def open_package_db(conn):
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS {DB_TABLE} (Name text, Type text, Description text)"
    )
    return cursor


def refresh_package_db(cursor, config_filename: str, spinner=None):
    """
    Reloads the contents of the package name database from `config_filename`.
    :param cursor: SQLite cursor object.
    :param config_filename: string name of YAML file.
    :param spinner: Spinner object.
    :return: None
    """
    cursor.execute(f"DELETE FROM {DB_TABLE}")  # Delete all rows from table.
    with open(config_filename, "r") as fp:
        pkg_data = yaml.load(fp, Loader=yaml.BaseLoader)
        assert int(pkg_data["version"]) == YAML_FILE_VERSION  # Ensure we recognize the version of the YAML file.
        for key, val in pkg_data["packages"].items():
            if run_cmd(f"which {key}", ignore=[0, 1]).strip():  # If the command is executable:
                pkg_list = run_cmd(val["command"]).splitlines()  # Command should return 1 package name per line.
                records = [(pkg, key, val["description"]) for pkg in pkg_list]
                if spinner:
                    next(spinner)
                cursor.executemany(
                    f"INSERT INTO {DB_TABLE} (Name, Type, Description) VALUES (?,?,?)",
                    records,
                )


def search_package_db(cursor, target: str):
    """
    Searches the package name database for `target`. Accepts globs.
    :param cursor: SQLite cursor object.
    :param target: string name to search for.
    :return: list of strings.
    """
    if '%' in target:
        cursor.execute(f"SELECT * FROM {DB_TABLE} WHERE Name LIKE ?", (target,))
        return [ f"{record[0]} is a {record[2]}." for record in cursor.fetchall() ]
    else:
        cursor.execute(f"SELECT * FROM {DB_TABLE} WHERE Name=?", (target,))
        return [ f"{target} is a {record[2]}." for record in cursor.fetchall() ]


def get_devices():
    """
    Collects information on all devices, mount points, and file system types. Does not
    accept globs.
    :return: dict of Counter dicts.
    """
    devices = collections.Counter()
    mount_points = collections.Counter()
    fstypes = collections.Counter()
    for elt in psutil.disk_partitions(all=True):
        devices.update([elt.device])
        mount_points.update([elt.mountpoint])
        fstypes.update([elt.fstype])
    return {"devices": devices, "mount_points": mount_points, "fstypes": fstypes}


def search_devices(device_dict: dict, target: str):
    """
    Searches the dict of Counter dicts for any devices, mount points, or
    file system types called `target`. No globs.
    :param device_dict:
    :param target:
    :return: list of strings
    """
    results = []
    if isinstance(target, str):
        if device_dict["devices"][target]:
            results.append(f"There is at least 1 device called {target}.")
        if device_dict["mount_points"][target]:
            results.append(f"There is at least 1 mount point called {target}.")
        if device_dict["fstypes"][target]:
            results.append(f"There is at least 1 file system type called {target}.")
    elif isinstance(target, Pattern):
        for key, _ in dict_get_regex(device_dict["devices"], target, return_tuple=True):
            results.append(f"There is at least 1 device called {key}.")
        for key, _ in dict_get_regex(device_dict["mount_points"], target, return_tuple=True):
            results.append(f"There is at least 1 mount point called {key}.")
        for key, _ in dict_get_regex(device_dict["fstypes"], target, return_tuple=True):
            results.append(f"There is at least 1 file system type called {key}.")
    else:
        raise ValueError(target)
    return results


def has_info_page(token: str):
    """
    Checks if the `info` command (if available) has information on `token`. No globs.
    :param token:
    :return: list of 0 or 1 strings
    """
    result = run_cmd(f"info -w {token}", [127])
    if result in ["", "dir", "*manpages*"] or result.startswith("././"):
        return []
    return [f"{term} has an info page."]


def has_man_page(token: str):
    """
    Checks if the `man` command (if available) has information on `token`. No globs.
    :param token:
    :return: list of 0 or 1 strings
    """
    result = run_cmd(f"man --whatis {token} 2>/dev/null", ignore=[16, 127])
    if bool(result):
        return [f"{term} has a man page."]
    return []


def get_which_results(token: str):
    """
    Uses the `which` command (if available) to determine if `token` is executable. No globs.
    :param token:
    :return: list of strings
    """
    results = []
    for line in run_cmd(f"which -a {token} 2>/dev/null", ignore=[1, 127]).splitlines():
        results.append(f"{token} is the command {line}.")
    return results


class ShellBuiltIn:
    """
    Collects data from Bash built-in commands for easy searching.
    """
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
        """
        Reads the results of several Bash built-in commands from `input_file`.
        :param input_file: file-like object to read from.
        """
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
        """
        Parses the `line` string.
        :param line:
        :return:
        """
        if line.startswith("###") and line.endswith("###"):
            self._mode_ = line.strip("# ").lower()
        else:
            if self._mode_ is None:
                raise ValueError(line)
            self._cmd_parser_[self._mode_](line)

    def parse_alias(self, line: str):
        """
        Parses aliases.
        :param line:
        :return:
        """
        match = re.search(r"^alias ([^=]*)=(.*)$", line)
        if match:
            self.results[ShellBuiltIn.Cmd.ALIAS.name].append(
                (match.group(1), f'{match.group(1)} is aliased to "{match.group(2)}".')
            )
        else:
            raise ValueError(line)

    def parse_declare(self, line: str):
        """
        Parses declarations.
        :param line:
        :return:
        """
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
        """
        Parses `set` commands for shell variable and function names.
        :param line:
        :return:
        """
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
        """
        Parses the output of the `type` command.
        :param line:
        :return:
        """
        match = re.search(r"^([^ ]*) is (.*)$", line)
        if match:
            self.results[ShellBuiltIn.Cmd.ALIAS.name].append(
                (match.group(1), f"{match.group(1)} is {match.group(2)}.")
            )
        else:
            raise ValueError(line)

    def search(self, target: str):
        """
        Search all results for `target`.
        :param target: string name to search for.
        :return: list of strings.
        """
        retval = []
        for key in self.results.keys():
            retval.extend(
                [msg for (label, msg) in self.results[key] if label == target]
            )
        return retval

    def pattern_search(self, pattern):
        """
        Search all results for `pattern`. Accepts globs.
        :param pattern: string glob to search for.
        :return: list of strings.
        """
        retval = []
        if isinstance(pattern, str):
            patt_re = glob_to_regex(pattern)
        elif isinstance(pattern, Pattern):
            patt_re = pattern
        else:
            raise ValueError(pattern)

        for key in self.results.keys():
            retval.extend(
                [msg for (label, msg) in self.results[key] if patt_re.search(label)]
            )
        return retval


def glob_to_regex(pattern: str):
    return re.compile('^' + pattern.replace('*', '.*') + '$')


def glob_to_sql(pattern: str):
    return pattern.replace('*', '%')


def dict_get_regex(d, patt_re, return_tuple: bool = False):
    results = []
    key_list = d.keys()
    if isinstance(patt_re, str):
        patt_re = glob_to_regex(patt_re)

    for key, val in d.items():
        if patt_re.search(key):
            if return_tuple:
                results.append( (key, val) )
            else:
                results.append(val)
    return results


def print_results(results, term):
    if results:
        for res in results:
            print(res)
    else:
        print(f"Nothing found for {term}.")
    print()


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
        "-p",
        "--pattern",
        action='append',
        help="Search for glob pattern.",
    )
    parser.add_argument(
        "-s",
        "--standalone",
        action="store_true",
        default=False,
        help="Don't read shell builtins.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        default=False,
        help="Show spinner when refreshing package cache.",
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
    if args.pattern is None:
        args.pattern = []

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
                + search_processes(proc_dict, term)
            )
            if not args.standalone:
                results.extend(builtins.search(term))
            print_results(results, term)

        for pattern in args.pattern:
            patt_re = glob_to_regex(pattern)
            results = (
                get_file_type(pattern)
                + search_package_db(cursor, glob_to_sql(pattern))
                + search_devices(device_dict, patt_re)
                + get_df_info(pattern)
                + search_processes(proc_dict, patt_re)
            )
            if not args.standalone:
                results.extend(builtins.pattern_search(patt_re))
            print_results(results, pattern)

