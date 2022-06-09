from subprocess import getstatusoutput

from flask import current_app


def local_cmd(cmd, conn=None):
    return getstatusoutput(cmd)


def remote_cmd(cmd, conn):
    return conn._command(cmd)


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
    def exec(self):
        return self._exec()