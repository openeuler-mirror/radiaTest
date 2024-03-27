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
# @Date    : 2023/05/08
# @License : Mulan PSL v2
#####################################

import os

from server.apps.git_repo.adaptor import GitRepoAdaptor


class JdkBaseAdaptor(GitRepoAdaptor):
    # the kinds of filetype to be recognized as a testcase 
    CASES_FILETYPES = [".java", ".sh"]


class Jdk8uDev(JdkBaseAdaptor):
    # the test suites defined by openjdk
    SUITES = ["jdk", "hotspot", "langtools", "corba", "jaxws", "jaxp"]

    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from jdk8u-dev repo
            :params git_repo_id(int), the ID of testcase repo in database
            :returns [tuple], [(testsuite data，[testcase data])]
        """
        work_dir = self._get_work_dir(self.oet_path)
        if not work_dir:
            return []

        suite2cases = []
        for suite in self.SUITES:
            suite_data = self.default_suite_dict
            suite_data.update({
                "name": f"jdk8-{suite}",
                "git_repo_id": git_repo_id,
            })
            cases_data = self._get_cases(
                suite, 
                os.path.join(work_dir, suite), 
                "jdk8-"
            )
            suite2cases.append((suite_data, cases_data))
        
        return suite2cases


class Jdk11uDev(JdkBaseAdaptor):
    SUITES = ["fmw", "hotspot", "jaxp", "jdk", "langtools", "lib-test", "micro", "nashorn"]

    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from jdk11u-dev repo
            :params git_repo_id(int), the ID of testcase repo in database
            :returns [tuple], [(testsuite data，[testcase data])]
        """
        work_dir = self._get_work_dir(
            os.path.join(self.oet_path, 'test')
        )
        if not work_dir:
            return []

        suite2cases = []
        for suite in self.SUITES:
            suite_data = self.default_suite_dict
            suite_data.update({
                "name": f"jdk11-{suite}",
                "git_repo_id": git_repo_id,
            })
            cases_data = self._get_cases(
                suite, 
                os.path.join(work_dir, suite), 
                "jdk11-"
            )
            suite2cases.append((suite_data, cases_data))
        
        return suite2cases


class Jdk17uDev(JdkBaseAdaptor):
    SUITES = ["hotspot", "jaxp", "jdk", "langtools", "lib-test", "micro"]

    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from jdk17u-dev repo
            :params git_repo_id(int), the ID of testcase repo in database
            :returns [tuple], [(testsuite data，[testcase data])]
        """
        work_dir = self._get_work_dir(
            os.path.join(self.oet_path, 'test')
        )
        if not work_dir:
            return []

        suite2cases = []
        for suite in self.SUITES:
            suite_data = self.default_suite_dict
            suite_data.update({
                "name": f"jdk17-{suite}",
                "git_repo_id": git_repo_id,
            })
            cases_data = self._get_cases(
                suite, 
                os.path.join(work_dir, suite), 
                "jdk17-"
            )
            suite2cases.append((suite_data, cases_data))
        
        return suite2cases
