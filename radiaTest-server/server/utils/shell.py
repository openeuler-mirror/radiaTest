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

from subprocess import getstatusoutput

from flask import current_app

from server.utils.pssh import ConnectionApi


def local_cmd(cmd, conn=None):
    return getstatusoutput(cmd)


def remote_cmd(cmd, conn):
    return conn.command(cmd)


def add_escape(value):
    reserved_chars = r'''?&'''
    replace = ['\\' + l for l in reserved_chars]
    trans = str.maketrans(dict(zip(reserved_chars, replace)))
    return value.translate(trans)


class ShellCmd:
    def __init__(self, cmd, conn=None):
        self._cmd = cmd
        if conn:
            self._func = remote_cmd
        else:
            self._func = local_cmd
        self._conn = conn

    def _exec(self):
        exitcode, output = self._func(self._cmd, self._conn)
        if exitcode:
            current_app.logger.error(output)
            return exitcode, output

        if not output:
            current_app.logger.info("The output has not been callbacked")
        else:
            current_app.logger.info(output)

        return exitcode, output

    def _bexec(self):
        if self._exec()[0]:
            return False

        return True


class ShellCmdApi(ShellCmd):
    def __init__(self, cmd, conn=None):
        super().__init__(cmd, conn)

    def exec(self):
        return self._exec()


    def bexec(self):
        return self._bexec()