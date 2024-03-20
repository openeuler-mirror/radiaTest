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

import os
import shutil
from time import sleep

from server.model.testcase import Suite
from celeryservice.sub_tasks import update_suite
from celeryservice.lib import TaskHandlerBase
from celeryservice.lib.repo.repo_adaptor import GitRepoAdaptor


class RepoTaskHandler(TaskHandlerBase):
    """the celery task handler for resolving testcases repo to get testcases data"""
    # 重试次数(times)
    RETRY_LIMIT = 300
    # 重试间隔(s)
    RETRY_INTERVAL = 1

    def __init__(self, logger, promise):
        """initializing function for RepoTaskHandler
            :params logger, the celery logger instance, here to storage to 
                handler instance, could be used by:
                - self.logger.info('info message')
                - self.logger.warning('warning message')
                - self.logger.error('error message')
            :params promise, the celery task instance, which represent the 
                task itself, primarily used to:
                - self.promise.update_state() => look up details from CELERY documents
            :returns the new instance of RepoTaskHandler
        """
        self.promise = promise
        super().__init__(logger)

    def main(self, repo_id: int, repo_name: str, repo_url: str, repo_branch: str):
        """start resolve target repo, and get all testcases data
            :params repo_id(int), the ID of the target testcase repo to resolve
            :params repo_name(str), the name of the target testcase repo to resolve
            :params repo_url(str), the full path url of the target testcase repo to resolve
            :params repo_branch(str), the target branch of the target testcase repo to resolve
        """

        # change the state of this task to DOWNLOADING, and record the clock
        self.promise.update_state(
            state="DOWNLOADING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        oet_path = "/tmp/{}".format(repo_name)
        if os.path.isdir(oet_path):
            shutil.rmtree(oet_path)

        # get the adaptor class of target repo, adapting by repo name
        repo_adaptor = getattr(GitRepoAdaptor, repo_name, None)
        if not repo_adaptor:
            raise RuntimeError(
                "no adaptive suite2cases resolver for testcase git repo {}".format(
                    repo_name
                )
            )

        # instantiating
        resolver = repo_adaptor(repo_url, repo_branch, oet_path)

        self._download_repo(resolver, repo_url, repo_branch)

        # change the state of task to RESOLVING, record the clock
        self.next_period()
        self.promise.update_state(
            state="RESOLVING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )
        # resolve to get the suite2cases data
        suite2cases = resolver.suite2cases_resolve(repo_id)
        if not isinstance(suite2cases, list):
            raise RuntimeError(
                "resolve suite2cases from {} failed".format(
                    repo_url
                )
            )

        # change the state of task to UPDATING, record the clock
        self.next_period()
        self.promise.update_state(
            state="UPDATING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        radia_suites = set()
        suites = Suite.query.filter_by(git_repo_id=repo_id).all()
        [radia_suites.add(suite.name) for suite in suites]

        git_suites = set()
        # update suites and cases data of the target repo to database by celery task
        for (suite_data, cases_data) in suite2cases:
            git_suites.add(suite_data.get('name'))
            update_suite.delay(suite_data, cases_data)

        rm_suites = radia_suites - git_suites
        for rm_suite in rm_suites:
            suite = Suite.query.filter_by(git_repo_id=repo_id, name=rm_suite).first()
            suite.deleted = True
            suite.add_update()
            suite.commit()

        # set the state to DONE, record the clock
        self.next_period()
        self.promise.update_state(
            state="DONE",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

    def _download_repo(self, resolver, repo_url, repo_branch):
        # try limit times trying to download the repo 
        count = RepoTaskHandler.RETRY_LIMIT
        while count > 0:
            exitcode, output = resolver.download()
            self.logger.info(output)

            if exitcode == 0:
                break

            count -= 1
            sleep(RepoTaskHandler.RETRY_INTERVAL)

        if count == 0:
            raise RuntimeError(
                f"download exceed retry limitation, git clone {repo_url}@{repo_branch} failed"
            )

