# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

import subprocess
import shlex
from itertools import groupby

from flask import current_app


def check_cmd(cmds):
    for item in cmds:
        if item and item[0] in ["bash", "cmd", "cmd.exe", "/bin/sh", "/usr/bin/expect"]:
            raise RuntimeError("unsupported command")
        if len(item) > 2 and item[1] == "-c":
            raise RuntimeError("unsupported command")
    return cmds


def standard_cmd(cmd):
    if isinstance(cmd, str):
        command_list = shlex.split(cmd)
        cmds = [list(group) for key, group in groupby(command_list, lambda x: x != '&&') if key]
        cmds = check_cmd(cmds)
        return cmds
    elif isinstance(cmd, list):
        if all(isinstance(item, str) for item in cmd):
            cmds = check_cmd([cmd])
            return cmds
        elif all(isinstance(item, list) and all(isinstance(subitem, str) for subitem in item) for item in cmd):
            cmds = check_cmd(cmd)
            return cmds
        else:
            return []
    else:
        return []


def run_cmd(cmd):
    cmds = standard_cmd(cmd)
    returncode = 1
    output = ""
    error = ""
    if not cmds:
        return returncode, output, "unsupported input type"
    for item in cmds:
        try:
            process = subprocess.Popen(
                item,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            process.wait()
            output, error = process.communicate(timeout=30)
            returncode = process.returncode
        except Exception as e:
            current_app.logger.error(f"command execute failed due to:{e}")
            return 1, "", "command execute failed"
    return returncode, output.decode("utf-8"), error.decode("utf-8")


def add_escape(value):
    reserved_chars = r'''?&'''
    replace = ['\\' + char for char in reserved_chars]
    trans = str.maketrans(dict(zip(reserved_chars, replace)))
    return value.translate(trans)
