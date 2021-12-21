# @Author : lemon-higgins
# @Date   : 2021-10-02 10:13:40
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Desc   :


import paramiko
from flask import current_app


class SSH(object):
    def __init__(self, ip, passwd=None, port=22, user="root", pkey="/root/.ssh/id_rsa"):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self._ip = ip
        self._port = port
        self._user = user
        self._passwd = passwd
        if passwd:
            self._pkey = None
        else:
            self._pkey = paramiko.RSAKey.from_private_key_file(pkey)


class Connection(SSH):
    def _conn(self):
        try:
            self._client.connect(
                self._ip,
                self._port,
                self._user,
                password=self._passwd,
                timeout=300,
                look_for_keys=False,
                pkey=self._pkey,
            )
        except:
            return False

        return self._client

    def _command(self, cmd):
        stdin, stdout, stderr = self._client.exec_command(
            cmd, get_pty=True, timeout=None
        )
        exitcode = stdout.channel.recv_exit_status()

        output = stdout.read().decode("utf-8").strip("\n")
        errput = stderr.read().decode("utf-8").strip("\n")

        if exitcode:
            result = errput if errput else output
            current_app.logger.error(
                "Failed to execute command remotely.\n%s\n%s" % (cmd, result)
            )
        else:
            result = output if output else errput

        return exitcode, result

    def _close(self):
        self._client.close()
