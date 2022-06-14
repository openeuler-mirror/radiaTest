import shlex

from flask import current_app

from messenger.utils.shell import ShellCmdApi


class ExecutorAdaptor:
    def __init__(self, conn, framework, git_repo, executor) -> None:
        # common params init
        self._conn = conn
        if conn:
            self._download_path = current_app.config.get("WORKER_DOWNLOAD_PATH").replace(
                "/$", ""
            )
        else:
            self._download_path = current_app.config.get("SERVER_DOWNLOAD_PATH").replace(
                "/$", ""
            )

        # special test frame init
        self._framework = framework
        self._git_repo = git_repo
        self._executor = executor

    def prepare_git(self):
        exitcode, output = ShellCmdApi(
            " which git || dnf install git -y", self._conn
        ).exec()
        if exitcode:
            raise RuntimeError("Failed to install git.")
        current_app.logger.info(output)

    def download(self, url, name):
        return ShellCmdApi(
            "git clone {} {}/{}".format(
                url,
                self._download_path,
                name
            ),
            self._conn,
        ).exec()

    def update(self, target):
        return ShellCmdApi(
            "cd {}/{} && git pull".format(
                shlex.quote(self._download_path),
                shlex.quote(target.get("name")),
            ),
            self._conn,
        ).exec()

    def deploy(self, master_ip, machines):
        # download framework
        exitcode, output = self.download(
            self._framework.get("url"),
            self._framework.get("name")
        )
        if exitcode:
            exitcode, output = self.update(self._framework)
            if exitcode:
                raise RuntimeError(
                    "Failed to download the framework of {}.".format(
                        self._framework.get("name")
                    )
                )
        current_app.logger.info(output)

        if self._framework.get("name") != self._git_repo.get("name"):
            # download scripts
            exitcode, output = self.download(
                self._git_repo.get("git_url"),
                self._git_repo.get("name")
            )
            if exitcode:
                raise RuntimeError(
                    "Failed to download scripts from {}.".format(
                        self._git_repo.get("git_url")
                    )
                )
            current_app.logger.info(output)
        self._executor.deploy(download_path = self._download_path, conn = self._conn, master_ip = master_ip,
                              machines = machines, framework = self._framework.get("name"))


    def run_test(self, testcase=None, testsuite=None):
        return self._executor.run_test(download_path = self._download_path, conn = self._conn,
                                       testcase = testcase, testsuite = testsuite)