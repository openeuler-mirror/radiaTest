import shlex

from flask import current_app

from server.utils.shell import ShellCmd


class Executor:
    def __init__(self, conn, framework, git_repo, adaptor) -> None:
        # common params init
        self._conn = conn
        if conn:
            self._path = current_app.config.get("WORKER_DOWNLOAD_PATH").replace(
                "/$", ""
            )
        else:
            self._path = current_app.config.get("SERVER_DOWNLOAD_PATH").replace(
                "/$", ""
            )

        # special test frame init
        self._framework = framework
        self._git_repo = git_repo
        self._adaptor = adaptor

    def prepare_git(self):
        exitcode, output = ShellCmd(
            " which git || dnf install git -y", self._conn
        )._exec()
        if exitcode:
            raise RuntimeError("Failed to install git.")
        current_app.logger.info(output)

    def download(self, target):
        return ShellCmd(
            "git clone {} {}/{}".format(
                shlex.quote(target.url),
                shlex.quote(self._path),
                shlex.quote(target.name)
            ),
            self._conn,
        )._exec()

    def update(self, target):
        return ShellCmd(
            "cd {}/{} && git pull".format(
                shlex.quote(self._path),
                shlex.quote(target.name),
            ),
            self._conn,
        )._exec()

    def deploy(self, master_ip, machines):
        # download framework
        exitcode, output = self.download(self._framework)
        if exitcode:
            raise RuntimeError(
                "Failed to download the framework of {}.".format(
                    self._framework.name
                )
            )
        current_app.logger.info(output)

        if self._framework.name != self._git_repo.name:
            # download scripts
            exitcode, output = self.download(self._git_repo)
            if exitcode:
                raise RuntimeError(
                    "Failed to download scripts from {}.".format(
                        self._git_repo.url
                    )
                )
            current_app.logger.info(output)

        # deploy framework init
        if self._adaptor.deploy_init_cmd is not None:
            exitcode, output = ShellCmd(
                self._adaptor.deploy_init_cmd(self._path),
                self._conn,
            )._exec()

            if exitcode:
                raise RuntimeError("Failed to deploy the framework of {}.".format(
                    self._framework.name
                )
                )
            current_app.logger.info(output)

        # deploy framework main
        if self._adaptor.deploy_main_cmd is not None:
            for machine in machines:
                if machine.ip == master_ip:
                    exitcode, output = ShellCmd(
                        self._adaptor.deploy_main_cmd(machine),
                        self._conn,
                    )._exec()
                    if exitcode:
                        raise RuntimeError(
                            "The framework failed to configure the test environment of master node."
                        )
                    current_app.logger.info(output)
                    machines.remove(machine)
                    break

            for machine in machines:
                exitcode, output = ShellCmd(
                    self._adaptor.deploy_main_cmd(machine),
                    self._conn
                )._exec()
                if exitcode:
                    raise RuntimeError(
                        "The framework failed to configure the test environment of slave node."
                    )
                current_app.logger.info(output)

    def run_test(self, testcase=None, testsuite=None):
        if testcase is None and testsuite is None:
            return ShellCmd(
                self._adaptor.run_all_cmd(self._path),
                self._conn,
            )._exec()

        if testcase is None:
            return ShellCmd(
                self._adaptor.run_suite_cmd(self._path, testsuite),
                self._conn,
            )._exec()

        return ShellCmd(
            self._adaptor.run_case_cmd(self._path, testsuite, testcase),
            self._conn,
        )._exec()
