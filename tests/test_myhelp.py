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

import pytest
import collections
import myhelp
import re
import sys
import os


SAMPLE_DICT = {"apple": 1, "able": 2, "baker": 3, "splunge": 7, "cat": 1000}
SAMPLE_COUNTER = collections.Counter(list(SAMPLE_DICT.keys()) + ["apple", "cat"])
A_PATTERN = myhelp.glob_to_regex("a*")
E_PATTERN = myhelp.glob_to_regex("*e")


def test_run_cmd():
    assert myhelp.run_cmd("echo 'Hello'", ignore_stderr=False) == "Hello"


def test_PatternDict():
    pd = myhelp.PatternDict(SAMPLE_DICT)
    assert pd["baker"] == 3
    assert set(pd.search(A_PATTERN)) == {1, 2}
    assert set(pd.search(E_PATTERN)) == {1, 2, 7}


def test_PatternCounter():
    pc = myhelp.PatternCounter(SAMPLE_COUNTER)
    assert pc["cat"] == 2
    assert set(pc.search(A_PATTERN)) == {2, 1}
    assert set(pc.search(E_PATTERN)) == {2, 1, 1}


def test_ProcessViewer():
    pv = myhelp.ProcessViewer()
    assert re.search(r"There are [0-9]+ processes called .*", pv["bash"][0])


#def test_OpenFileViewer():
#    assert False


def test_PackageViewer():
    db_file = os.environ["MYHELP_PKG_DB"]
    yaml_file = os.environ["MYHELP_PKG_YAML"]
    packages = myhelp.PackageViewer(db_file, yaml_file, reload=True, feedback=True)
    assert len(packages.search("python3")) > 0
    assert len(packages["python"]) > 0


def test_DeviceViewer():
    devices = myhelp.DeviceViewer()
    assert len(devices.search("*")) > 0


#def test_BuiltInViewer():
#    builtins = myhelp.BuiltInViewer(sys.stdin)
#    assert len(builtins["HOME"]) > 0


def test_CmdViewer():
    cmd = myhelp.CmdViewer("echo", 'echo "%s"', 0, False, (lambda target, result: [ f"{target}={result}" ]), False)
    assert cmd["TEST"] == ["TEST=TEST"]


def test_glob_to_regex():
    regex = myhelp.glob_to_regex("apple*jack")
    assert regex.search("apple    jack") is not None
    assert regex.search("squids") is None


def test_init_cmd_viewer():
    cmds = myhelp.init_cmd_viewers()
    assert isinstance(cmds, list)
    for cmd in cmds:
        assert isinstance(cmd, myhelp.CmdViewer)
