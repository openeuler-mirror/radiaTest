import os
import shutil
import shlex
import subprocess

from celeryservice.sub_tasks import update_suite
from celeryservice.lib import TaskHandlerBase
from .suite2cases_resolver import Resolver


class RepoTaskHandler(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def _git_clone(self, url, oet_path):
        exitcode, output = subprocess.getstatusoutput(
            "git clone {}.git {}".format(
                url,
                shlex.quote(oet_path),
            )
        )
        return False if exitcode else True

    def main(self, id, name, url):
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

        self._git_clone(url, oet_path)

        self.next_period()
        self.promise.update_state(
            state="RESOLVING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        resolver = getattr(Resolver, name)

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
            _task = update_suite.delay(suite_data, cases_data)
            self.logger.warn(_task.task_id)

        self.next_period()
        self.promise.update_state(
            state="DONE",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )
