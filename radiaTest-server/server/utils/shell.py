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


def standard_cmd(input):
    if isinstance(input, str):
        command_list = shlex.split(input)
        cmds = [list(group) for key, group in groupby(command_list, lambda x: x != '&&') if key]
        return cmds
    elif isinstance(input, list):
        if all(isinstance(item, str) for item in input):
            return [input]
        elif all(isinstance(item, list) and all(isinstance(subitem, str) for subitem in item) for item in input):
            return input
        else:
            return []
    else:
        return []


def run_cmd(input):
    cmds = standard_cmd(input)
    returncode = 1
    output = ""
    error = ""
    if not cmds:
        return returncode, output, "unsupported input type"
    for item in cmds:
        process = subprocess.Popen(
            item,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        process.wait()
        output, error = process.communicate()
        returncode = process.returncode
    return returncode, output.decode("utf-8"), error.decode("utf-8")


def add_escape(value):
    reserved_chars = r'''?&'''
    replace = ['\\' + l for l in reserved_chars]
    trans = str.maketrans(dict(zip(reserved_chars, replace)))
    return value.translate(trans)
