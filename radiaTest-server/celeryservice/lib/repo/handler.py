import os
import shutil
import shlex
import subprocess
from time import sleep

from celeryservice.sub_tasks import update_suite
from celeryservice.lib import TaskHandlerBase
from .suite2cases_resolver import Resolver


class RepoTaskHandler(TaskHandlerBase):
    RETRY_LIMIT = 300
    RETRY_INTERVAL = 1

    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def _git_clone(self, url, branch, oet_path):
        exitcode, output = subprocess.getstatusoutput(
            "git config http.version HTTP/1.1 & git clone -b {} {} {}".format(
                shlex.quote(branch),
                shlex.quote(url),
                shlex.quote(oet_path),
            )
        )
        self.logger.info(output)
        return False if exitcode else True

    def main(self, id, name, url, branch, framework_name):
        self.promise.update_state(
            state="DOWNLOADING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        oet_path = "/tmp/{}".format(name)

        if os.path.isdir(oet_path):
            shutil.rmtree(oet_path)

        count = RepoTaskHandler.RETRY_LIMIT

        while count > 0:
            download_finish = self._git_clone(url, branch, oet_path)
            if download_finish:
                break

            count -= 1
            sleep(RepoTaskHandler.RETRY_INTERVAL)

        if count == 0:
            raise RuntimeError(
                f"download exceed retry limitation, git clone {url}@{branch} failed"
            )

        self.next_period()
        self.promise.update_state(
            state="RESOLVING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        resolver = getattr(Resolver, framework_name)

        if not resolver:
            raise RuntimeError(
                "no adaptive suite2cases resolver for testcase git repo {}".format(
                    name
                )
            )

        suite2cases = resolver(id, oet_path)

        if not isinstance(suite2cases, list):
            raise RuntimeError(
                "resolve suite2cases from {} failed".format(
                    url
                )
            )

        self.next_period()
        self.promise.update_state(
            state="UPDATING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        for (suite_data, cases_data) in suite2cases:
            update_suite.delay(suite_data, cases_data)

        self.next_period()
        self.promise.update_state(
            state="DONE",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )
