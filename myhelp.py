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
# df, file, getent, info, man, which, xdg-mime

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
import shlex
from enum import auto, IntEnum
from typing import Pattern
import textwrap

# Defaults:
PROGRAM_NAME = os.path.basename(sys.argv[0])
DESCRIPTION = """
Identifies the names provided.  Tries every test imaginable.  Looks for:
man pages, info pages, executables in PATH, aliases, shell variables, running
processes, shell functions, built-in shell commands, packages, filesystems,
and files relative to the current working directory."""

DEBUG = False


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
        del self


class PatternDict(dict):
    """
    A dictionary that allows keys to be searched with regexes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def search(self, pattern, return_tuple: bool = False):
        """
        Search for every key that matches `pattern`. If `return_tuple` is True, return
        a list of (key, value) pairs. Otherwise return a list of values.
        :param pattern: regex (assumes that keys are strings).
        :param return_tuple: bool
        :return: list of values or key/value pairs.
        """
        results = []
        for key, val in self.items():
            if pattern.search(key):
                if return_tuple:
                    results.append((key, val))
                else:
                    results.append(val)
        return results


class PatternCounter(collections.Counter):
    """
    A Counter that allows keys to be searched with regexes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def search(self, pattern, return_tuple: bool = False):
        """
        Search for every key that matches `pattern`. If `return_tuple` is True, return
        a list of (key, value) pairs. Otherwise return a list of values.
        :param pattern: regex (assumes that keys are strings).
        :param return_tuple: bool
        :return: list of values or key/value pairs.
        """
        results = []
        for key, val in self.items():
            if pattern.search(key):
                if return_tuple:
                    results.append((key, val))
                else:
                    results.append(val)
        return results


def run_cmd(
    cmd_str: str,
    ignore_rc=[0],
    ignore_stderr: bool = True,
    exit_on_error: bool = False,
    env=None,
):
    """
    Runs a shell command. Can ignore one or more return codes.
    :param cmd_str: Shell command to run.
    :param ignore_rc: Integer, string, or list of integers indicating return codes to ignore, or '*' to ignore all return codes.
    :param ignore_stderr: bool. Ignore any output to stderr.
    :param exit_on_error: bool. Exit program if error occurs, else raises exception.
    :param env: Dict of environment variables.
    :return: str
    :except subprocess.CalledProcessError
    :except ValueError
    """
    result = None
    if ignore_rc == "*":  # Ignore all return codes.
        ignore_rc = None
    elif isinstance(ignore_rc, list):
        if "*" in ignore_rc:  # Ignore all return codes.
            ignore_rc = None
        elif 0 not in ignore_rc:  # Always ignore return code 0.
            ignore_rc.append(0)
    elif isinstance(ignore_rc, int):
        ignore_rc = [0, ignore_rc]  # Always ignore return code 0.
    else:
        raise ValueError(ignore_rc)

    try:
        #print(f"run_cmd: {cmd_str}")
        result = subprocess.run(
            cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=env
        )
    except subprocess.CalledProcessError as e:
        # "ignore_rc" contains return codes that are not considered errors.
        # For example: grep will return errno == 1 if it doesn't match any
        # lines in its input stream.  We want to ignore this case since it's
        # not really an error. Note: pipelines return the errno of the last command
        # by default. Use `set -o pipefail` to override this behavior.
        if ignore_rc and e.returncode not in ignore_rc:
            if exit_on_error:
                exit(e.returncode)
            else:
                raise subprocess.CalledProcessError(
                    returncode=e.returncode, cmd=cmd_str
                )
    else:
        if (ignore_rc and result.returncode not in ignore_rc) or (
            not ignore_stderr and result.stderr
        ):
            if exit_on_error:
                # print(result.stderr)
                exit(result.returncode if result.returncode != 0 else 1)
            else:
                raise subprocess.CalledProcessError(
                    returncode=result.returncode,
                    cmd=cmd_str,
                    output=result.stdout,
                    stderr=result.stderr,
                )

    return result.stdout.decode().strip()


class ProcessViewer(PatternCounter):
    """
    Reads in all current processes.
    """

    def __init__(self):
        # Read the name of every current process and store it in a Counter.
        super().__init__([proc.name() for proc in psutil.process_iter(attrs=["name"])])

    @staticmethod
    def format(count: int, item: str):
        if count == 1:
            return [f"There is 1 process called {item}."]
        elif count > 1:
            return [f"There are {count} processes called {item}."]
        return []

    def __getitem__(self, item: str):
        """
        If item is in Counter, return a list of 1 message about item. Else return an empty list.
        :param item: str name of process.
        :return: list of 0 or 1 strings.
        """
        count = super().__getitem__(item)
        return ProcessViewer.format(count, item)

    def search(self, pattern, return_tuple: bool = False):
        """
        Search for every process name that matches `pattern`.
        :param pattern: regex or string glob.
        :param return_tuple: bool (IGNORED).
        :return: list of messages about process names that match `pattern`.
        """
        results = []
        if isinstance(pattern, str):
            pattern = glob_to_regex(pattern)
        for key, val in super().search(pattern, return_tuple=True):
            results.extend(ProcessViewer.format(val, key))
        return results


class OpenFileViewer(PatternCounter):
    """
    Reads in the names of all open files.
    """

    def __init__(self):
        names = []
        for line in run_cmd("lsof -b -F n 2>/dev/null").splitlines():
            if line[0] == "n":
                names.append(line[1:])
        super().__init__(names)

    @staticmethod
    def format(count: int, item: str):
        if count == 1:
            return [f"There is 1 open file called {item}."]
        elif count > 1:
            return [f"There are {count} open files called {item}."]
        return []

    def __getitem__(self, item):
        count = super().__getitem__(item)
        return OpenFileViewer.format(count, item)

    def search(self, pattern, return_tuple: bool = False):
        """
        Search for every open file whose name matches `pattern`.
        :param pattern: regex or string glob.
        :param return_tuple: bool.
        :return: list of messages about open files that match `pattern`.
        """
        results = []
        if isinstance(pattern, str):
            pattern = glob_to_regex(pattern)
        for key, val in super().search(pattern, return_tuple=True):
            results.extend(OpenFileViewer.format(val, key))
        return results


class PackageViewer:
    """
    Searches all available packages on system.
    """

    DB_TABLE = "Packages"
    CONFIG_TABLE = "HyHelp"
    YAML_FILE_VERSION = 1

    def __init__(
        self,
        db_file: str,
        config_file: str,
        reload: bool = False,
        feedback: bool = True,
    ):
        """
        Opens the SQLite database. May also reload its contents.
        :param db_file: str (name of SQLite database)
        :param config_file: str (name of YAML file)
        :param reload: bool (force reloading of package names into database)
        :param feedback: bool (show a spinner while working)
        """
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = '%s'"
            % PackageViewer.DB_TABLE
        )
        if int(self.cursor.fetchone()[0]) == 0:
            self.cursor.execute(
                "CREATE TABLE %s (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, Name text, Type text, Description text)"
                % PackageViewer.DB_TABLE, 
            )
        self.cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = '%s'"
            % PackageViewer.CONFIG_TABLE
        )
        if int(self.cursor.fetchone()[0]) == 0:
            self.cursor.execute(
                "CREATE TABLE %s (id INTEGER PRIMARY KEY NOT NULL, last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, version INTEGER)"
                % PackageViewer.CONFIG_TABLE
            )
            self.cursor.execute("INSERT INTO %s (id) VALUES (1)" % PackageViewer.CONFIG_TABLE)
            reload = True
        if reload:
            self.reload(config_file, feedback)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.cursor.close()
        self.conn.commit()
        self.conn.close()

    def reload(self, config_filename: str, feedback: bool = True):
        """
        Reloads the contents of the package name database from `config_filename`.
        :param config_filename: string name of YAML file.
        :param feedback: bool
        :return: None
        """
        spinner = Spinner() if feedback else None
        self.cursor.execute(
            f"DELETE FROM {PackageViewer.DB_TABLE}"
        )  # Delete all rows from table.
        with open(config_filename, "r") as fp:
            pkg_data = yaml.load(fp, Loader=yaml.BaseLoader)
            # Ensure we recognize the version of the YAML file.
            assert int(pkg_data["version"]) == PackageViewer.YAML_FILE_VERSION
            for key, val in pkg_data["packages"].items():
                # If the command is executable:
                if run_cmd(f"which {key}", [1]).strip():
                    # Command should return 1 package name per line.
                    pkg_list = run_cmd(val["command"]).splitlines()
                    # Build a list of values to be inserted into the database.
                    records = [(pkg, key, val["description"]) for pkg in pkg_list]
                    if spinner:
                        next(spinner)
                    self.cursor.executemany(
                        f"INSERT INTO {PackageViewer.DB_TABLE} (Name, Type, Description) VALUES (?,?,?)",
                        records,
                    )
        self.cursor.execute(f"UPDATE {PackageViewer.CONFIG_TABLE} SET last_update=?, version=? WHERE id=1",
                            (1, int(pkg_data["version"])))
        self.conn.commit()
        if spinner:
            spinner.stop()

    def __getitem__(self, target: str):
        """
        Searches the package name database for `target`. Does not accept globs.
        :param target: string name to search for.
        :return: list of strings.
        """
        self.cursor.execute(
            f"SELECT * FROM {PackageViewer.DB_TABLE} WHERE Name=?", (target,)
        )
        return [f"{target} is a {record[3]}." for record in self.cursor.fetchall()]

    def search(self, target: str):
        """
        Searches the package name database for `target`. Accepts globs, but not regexes.
        :param target: string name to search for.
        :return: list of strings.
        """
        if "*" in target:
            target = PackageViewer.glob_to_sql(target)
        if "%" in target:
            self.cursor.execute(
                f"SELECT * FROM {PackageViewer.DB_TABLE} WHERE Name LIKE ?", (target,)
            )
            return [
                f"{record[0]} is a {record[2]}." for record in self.cursor.fetchall()
            ]
        else:
            self.cursor.execute(
                f"SELECT * FROM {PackageViewer.DB_TABLE} WHERE Name=?", (target,)
            )
            return [f"{target} is a {record[3]}." for record in self.cursor.fetchall()]

    @staticmethod
    def glob_to_sql(pattern: str):
        return pattern.replace("*", "%")


class DeviceViewer:
    """
    Searches all devices detected by psutil.disk_partitions.
    """

    def __init__(self):
        self._devices = PatternCounter()
        self._mount_points = PatternCounter()
        self._fstypes = PatternCounter()
        for elt in psutil.disk_partitions(all=True):
            self._devices.update([elt.device])
            self._mount_points.update([elt.mountpoint])
            self._fstypes.update([elt.fstype])

    def __str__(self):
        return "DeviceViewer(" + "\n".join(["_devices: " + str(self._devices),
               "_mount_points: " + str(self._mount_points), 
               "_fstypes: " + str(self._fstypes)]) + ")"

    def __getitem__(self, item):
        """
        Returns a list of all devices, file system types, and mount points called `item`.
        :param item: str to search for.
        :return: list of str.
        """
        results = []
        results.extend(DeviceViewer.format("device", item, self._devices[item]))
        results.extend(
            DeviceViewer.format("file system type", item, self._fstypes[item])
        )
        results.extend(
            DeviceViewer.format("mount point", item, self._mount_points[item])
        )
        return results

    @staticmethod
    def format(category: str, key: str, value: int):
        if value == 1:
            return [f"There is 1 {category} called {key}."]
        elif value > 1:
            return [f"There are {value} {category}s called {key}."]
        return []

    def search(self, pattern, return_tuple: bool = False):
        """
        Search
        :param pattern: regex or string glob.
        :param return_tuple: bool (IGNORED).
        :return: list of str.
        """
        results = []
        if isinstance(pattern, str):
            pattern = glob_to_regex(pattern)
        for key, val in self._devices.search(pattern, return_tuple=True):
            results.extend(DeviceViewer.format("device", key, val))
        for key, val in self._fstypes.search(pattern, return_tuple=True):
            results.extend(DeviceViewer.format("file system type", key, val))
        for key, val in self._mount_points.search(pattern, return_tuple=True):
            results.extend(DeviceViewer.format("mount point", key, val))
        return results


class BuiltInViewer:
    """
    Collects data from Bash built-in commands for easy searching.
    """

    class Cmd(IntEnum):
        ALIAS = 0
        DECLARE = auto()
        SET = auto()
        TYPE = auto()

    # Attributes used by the `declare` command.
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
        # `results` maps the built-in command to a list of its output.
        self.results = dict()
        for cmd in BuiltInViewer.Cmd.__members__.keys():
            self.results[cmd] = []
        # Dispatch parsing method based on command type:
        self._cmd_parser_ = {
            BuiltInViewer.Cmd.ALIAS.name.lower(): self._parse_alias,
            BuiltInViewer.Cmd.DECLARE.name.lower(): self._parse_declare,
            BuiltInViewer.Cmd.SET.name.lower(): self._parse_set,
            BuiltInViewer.Cmd.TYPE.name.lower(): self._parse_type,
        }
        # `_mode_` is the type of command output we are currently parsing.
        self._mode_ = None
        # Read `input_file` one line at a time:
        for line in map(str.rstrip, input_file):
            self.parse(line)

    def parse(self, line: str):
        """
        Parses the `line` string.
        :param line: string
        :return: None
        """
        # If we have found a line that indicates the output of a built-in command
        # will follow, then set `_mode_` to the name of that command.
        if line.startswith("###") and line.endswith("###"):
            self._mode_ = line.strip("# ").lower()
        else:
            # If we don't know what kind of command output has been read:
            if self._mode_ is None:
                raise ValueError(line)
            # `_cmd_parser_` dispatches the correct parsing method.
            if len(line.strip()) > 0:
                self._cmd_parser_[self._mode_](line)

    def _parse_alias(self, line: str):
        """
        Parses shell aliases.
        :param line: string
        :return: None
        """
        match = re.search(r"^alias ([^=]*)=(.*)$", line)
        if match:
            self.results[BuiltInViewer.Cmd.ALIAS.name].append(
                (match.group(1), f'{match.group(1)} is aliased to {match.group(2)}.')
            )
        else:
            raise ValueError(line)

    def _parse_declare(self, line: str):
        """
        Parses shell declarations.
        :param line: string
        :return: None
        """
        match = re.search(r"^declare -([^ ]*) ([^ =]*).*$", line)
        if match:
            attr_list = []
            for char in match.group(1):
                attr_list.append(BuiltInViewer._declare_attr_[char])
            if None in attr_list:
                msg = f"{match.group(2)} is a shell variable."
            else:
                msg = (
                    f"{match.group(2)} has the attribute(s): "
                    + ", ".join(attr_list)
                    + "."
                )
            self.results[BuiltInViewer.Cmd.DECLARE.name].append((match.group(2), msg))

    def _parse_set(self, line: str):
        """
        Parses `set` commands for shell variable and function names. Ignores
        lines that don't match those patterns.
        :param line: str
        :return:
        """
        match = re.search(r"^([a-zA-Z0-9_]+)=", line)
        if match:
            self.results[BuiltInViewer.Cmd.SET.name].append(
                (match.group(1), f"{match.group(1)} is a shell variable.")
            )
            return

        match = re.search(r"^([a-zA-Z0-9_]+) \(\)", line)
        if match:
            self.results[BuiltInViewer.Cmd.SET.name].append(
                (match.group(1), f"{match.group(1)} is a shell function.")
            )
            return

    def _parse_type(self, line: str):
        """
        Parses the output of the `type` command.
        :param line:
        :return:
        """
        match = re.search(r"^([^ ]*) is (.*)$", line)
        if match:
            self.results[BuiltInViewer.Cmd.ALIAS.name].append(
                (match.group(1), f"{match.group(1)} is {match.group(2)}.")
            )
        else:
            raise ValueError(line)

    def __getitem__(self, target: str):
        """
        Search all results for `target`.
        :param target: string name to search for.
        :return: list of strings.
        """
        retval = []
        # Iterate over shell command names.
        for key in self.results.keys():
            retval.extend(
                [msg for (label, msg) in self.results[key] if label == target]
            )
        return retval

    def search(self, pattern):
        """
        Search all results for `pattern`. Accepts string globs and regexes.
        :param pattern: regex or string glob to search for.
        :return: list of strings.
        """
        retval = []
        if isinstance(pattern, str):
            pattern = glob_to_regex(pattern)
        # Iterate over shell command names.
        for key in self.results.keys():
            retval.extend(
                [msg for (label, msg) in self.results[key] if pattern.search(label)]
            )
        return retval


class CmdViewer:
    """
    Runs a shell command and returns a report.
    """

    CMD_OK = 0  # Command returned no error.
    CMD_NOT_FOUND = 127  # Command not found by shell.

    def __init__(
        self,
        cmd_name: str,
        cmd_string: str,
        ignore_rc,
        ignore_stderr: bool,
        function,
        glob_able: bool,
    ):
        """
        Create CmdViewer object.
        :param cmd_name: str name of command to run.
        :param cmd_string: str to pass to shell.
        :param ignore_rc: list of return codes or single return code to ignore.
        :param ignore_stderr: bool. Don't report error if stderr contains message.
        :param function: function to format results of shell command.
        :param glob_able: bool. Can pass a glob for pattern matching.
        """
        self.cmd_name = cmd_name
        self.cmd_string = cmd_string
        self.ignore_stderr = ignore_stderr
        self.fn = function
        self.glob_able = glob_able
        if ignore_rc == "*":
            self.ignore_rc = "*"
        elif isinstance(ignore_rc, collections.abc.Iterable):
            # "*" means ignore all return codes.
            if "*" in ignore_rc:
                self.ignore_rc = "*"
            else:
                # Convert `ignore_rc` to a set, thus removing all duplicate elements.
                # Then union that set with `CMD_OK` and `CMD_NOT_FOUND`. Finally, convert
                # the set to a list.
                self.ignore_rc = list(
                    set(ignore_rc).union({CmdViewer.CMD_OK, CmdViewer.CMD_NOT_FOUND})
                )
        elif isinstance(ignore_rc, int):
            self.ignore_rc = list(
                {ignore_rc, CmdViewer.CMD_OK, CmdViewer.CMD_NOT_FOUND}
            )
        else:
            raise ValueError(f'Bad value for ignore_rc ({ignore_rc}).')

    def __getitem__(self, target: str):
        """
        Search for `target`, which is a literal string.
        :param target: str.
        :return: list of str.
        """
        # Escape the shell command before running it.
        result = run_cmd(
            self.cmd_string % shlex.quote(target),
            ignore_rc=self.ignore_rc,
            ignore_stderr=self.ignore_stderr,
        )
        return self.fn(target, result)

    def search(self, pattern: str):
        """
        If this command accepts globs, search for `pattern`.
        :param pattern: str (may be a glob).
        :return:
        """
        if self.glob_able:
            #print(f"search: pattern={self.cmd_string % escape_glob(pattern)}")
            result = run_cmd(
                self.cmd_string % escape_glob(pattern),
                ignore_rc=self.ignore_rc,
                ignore_stderr=self.ignore_stderr,
            )
            return self.fn(pattern, result)
        else:
            raise ValueError(f'Pattern search not allowed for "{self.cmd_name}".')


def glob_to_regex(pattern: str):
    """
    Convert a string to a regex. If `pattern` contains "*", it is a glob.
    :param pattern: str (may be glob).
    :return: regex
    """
    if "*" in pattern:
        # Replace all "*" with ".*". *** DOESN'T HANDLE ESCAPED "*" ***
        clean_pat = ".*".join(map(re.escape, pattern.split("*")))
    else:
        clean_pat = re.escape(pattern)
    if DEBUG:
        print(f"glob_to_regex: {pattern} -> {clean_pat}")
    return re.compile("^" + clean_pat + "$")


def escape_glob(string: str):
    """
    Escape a file name that may contain globs without escaping the '*' characters themselves.
    :param string: str
    :return: str
    """
    split_pts = []
    escape_on = False
    # Search string for unescaped *'s:
    for ind in range(len(string)):
        chr = string[ind]
        if escape_on:
            escape_on = False
        elif chr == r'\\':
            escape_on = True
        elif chr == r'*':
            split_pts.append(ind)   # Found an unescaped "*". Record its index.
    substrs = []
    prev = 0
    # Split string into substrings based on split_pts:
    for ind in split_pts:
        substrs.append(string[prev:ind])
        prev = ind + 1
    # Append the trailing substring:
    substrs.append(string[prev:])
    # Use `shlex.quote` on every substring, then glue together with "*":
    return "*".join(map(shlex.quote, substrs))


def escape_space(string: str):
    """
    Returns a copy of `string` with all it's spaces prefixed with "\".
    :param string: str
    :return: str
    """
    if not string or " " not in string:
        return string

    length = len(string)
    if length == 1:
        return r"\ " if string == " " else string

    result = ""
    if string[0] == " ":
        result = "\\"
    for ind in range(length - 1):
        if string[ind] != "\\" and string[ind + 1] == " ":
            result += string[ind] + "\\"
        else:
            result += string[ind]
    result += string[-1]

    return result


def a_or_an(word: str, lowercase: bool = True):
    """
    Returns "an" if `word` starts with a, e, i, o, or u. Otherwise returns "a".
    May not be compatible with British English.
    :param word: str
    :param lowercase: bool
    :return: str
    """
    if lowercase:
        a = "a"
        an = "an"
    else:
        a = "A"
        an = "An"
    if word[0].lower() in ["a", "e", "i", "o", "u"]:
        return an
    else:
        return a


def print_results(results, term):
    """
    Print all results for `term`.
    :param results: list of str or None.
    :param term: str
    :return: None
    """
    if results:
        for res in results:
            print(res)
    else:
        print(f'Nothing found for "{term}".')
    print()


def init_cmd_viewers():
    """
    Initialize all CmdViewer objects.
    :return: list of CmdViewer
    """
    def file(token: str, result: str):
        """
        Process the results of a `file` command.
        :param token: str to examine.
        :param result: str returned by `file` command.
        :return: list of 0 or 1 strings.
        """
        # Accepts globs
        retval = []
        lines = result.splitlines()
        for line in lines:
            match = re.search(r"^([^:]*):\s+(.*)$", line)
            if match:
                target = match.group(1)
                is_a = match.group(2)
                article = a_or_an(is_a)
                if "No such file or directory" in is_a:
                    pass
                elif is_a == "directory":
                    retval.append(f"{target} is a directory.")
                else:
                    retval.append(f"{target} is {article} {is_a} file.")
        return retval

    def df(token: str, result: str):
        """
        Process the results of a `df` command.
        :param token: str to examine.
        :param result: multi-line str returned by `df` command.
        :return: list of str.
        """
        # Accepts globs
        retval = []
        lines = result.splitlines()
        if lines:
            col2_index = lines[0].find("Filesystem")
            col3_index = lines[0].find("Type")
            for line in lines[1:]:
                filename = line[:col2_index].strip()
                filesys = line[col2_index:col3_index].strip()
                filetype = line[col3_index:].strip()
                retval.append(f"{filename} is on filesystem {filesys} (type {filetype}).")
        return retval

    def which(token: str, result: str):
        """
        Process the results of a `which` command.
        :param token: str to examine.
        :param result: multi-line str returned by `df` command.
        :return: list of str.
        """
        # No globs
        retval = []
        for line in result.splitlines():
            retval.append(f"{token} is the command {line}.")
        return retval

    def info(token: str, result: str):
        if token.strip() == "" or result in ["", "dir", "*manpages*"]:
            return []
        if os.path.abspath(token) == os.path.abspath(result):
            return []
        return [f"{token} has an info page."]

    viewers = [
        CmdViewer(
            "getent passwd",
            "getent passwd %s",
            2,
            True,
            lambda target, result: [f"There is a user named {target}."] if result else [],
            False,
        ),
        CmdViewer(
            "getent group",
            "getent group %s",
            2,
            True,
            lambda target, result: [f"There is a group named {target}."] if result else [],
            False,
        ),
        CmdViewer(
            "getent hosts",
            "getent hosts %s",
            2,
            True,
            lambda target, result: [f"There is a host named {target}."] if result else [],
            False,
        ),
        CmdViewer(
            "getent services",
            "getent services %s",
            2,
            True,
            lambda target, result: [f"There is a service named {target}."] if result else [],
            False,
        ),
        CmdViewer("file", "file %s", "*", True, file, True),
        CmdViewer(
            "xdg-mime",
            "xdg-mime query filetype %s 2>/dev/null",
            "*",
            True,
            lambda target, result: [f"{target} has the MIME type {result}."] if result else [],
            False,  # No globs
        ),
        CmdViewer("df", "df --output=file,source,fstype %s 2>/dev/null", "*", True, df, True),
        CmdViewer("info", "info -w %s", [], True, info, False),
        CmdViewer(
            "man",
            "man --whatis %s 2>/dev/null",
            16,
            True,
            lambda target, result: [f"{target} has a man page."] if bool(result) else [],
            False,
        ),
        CmdViewer("which", "which -a %s 2>/dev/null", 1, True, which, False),
    ]
    return viewers


if __name__ == "__main__":
    cmd_viewers = init_cmd_viewers()
    no_patterns = sorted([cmd.cmd_name for cmd in cmd_viewers if not cmd.glob_able])
    EPILOG = """Pattern searches use "globs". Pattern searches cannot be performed with the
following commands:\n""" + textwrap.indent(textwrap.fill(", ".join(no_patterns)), "    ")

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
        "-p", "--pattern", action="append",
        help="Search for glob pattern. The pattern should be wrapped in quotes."
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
        # If config_dir doesn't exist, create it.
        os.mkdir(config_dir)
    db_file = os.environ["MYHELP_PKG_DB"]
    yaml_file = os.environ["MYHELP_PKG_YAML"]
    refresh = args.refresh or int(os.environ["MYHELP_REFRESH"]) == 1
    if args.pattern is None:
        args.pattern = []

    # Initialize viewers:
    if args.standalone:
        builtins = None
    else:
        builtins = BuiltInViewer(sys.stdin)
    processes = ProcessViewer()
    devices = DeviceViewer()
    # open_files = OpenFileViewer()
    packages = PackageViewer(
        db_file, yaml_file, reload=refresh, feedback=args.interactive
    )

    got_results = False

    for pattern in args.pattern:
        # Scan for each search pattern (glob):
        if DEBUG:
            print(f"Checking pattern {pattern}")
        pattern = pattern.strip("'")
        if pattern == "":
            continue
        got_results = True
        patt_re = glob_to_regex(pattern)
        results = (
            packages.search(pattern)
            + devices.search(patt_re)
            + processes.search(patt_re)
            # + open_files.search(patt_re)
        )
        for viewer in cmd_viewers:
            if viewer.glob_able:
                results.extend(viewer.search(pattern))
        if builtins:
            results.extend(builtins.search(patt_re))
        print_results(results, pattern)

    for term in args.terms:
        term = term.strip("'")
        if term == "":
            continue
        got_results = True
        if "*" in term:
            print(
                f'WARNING: Treating "*" in "{term}" as a literal character, not a glob.'
            )
        # Scan for each search term:
        results = (
            packages[term]
            + devices[term]
            + processes[term]
            # + open_files[term]
        )
        for viewer in cmd_viewers:
            results.extend(viewer[term])
        if builtins:
            results.extend(builtins[term])
        print_results(results, term)

    if not refresh and not got_results:
        print(f'Nothing to search for. Use "{os.environ["MYHELP_ALIAS_NAME"]} -h" for help.')

    packages.close()

