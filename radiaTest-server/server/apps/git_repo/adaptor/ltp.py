# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang
# @email   : ethanzhang55@outlook.com
# @Date    : 2023/05/08
# @License : Mulan PSL v2
#####################################

import shlex
import subprocess

from server.apps.git_repo.adaptor import GitRepoAdaptor


class Ltp(GitRepoAdaptor):
    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from ltp repo
            :params git_repo_id(int), the ID of testcase repo in database
            :returns [tuple], [(testsuite data，[testcase data])]
        """

        _work_dir = self._get_work_dir(f"{self.oet_path}/runtest")
        if not _work_dir:
            return None

        exitcode, output = subprocess.getstatusoutput(
            "cd {} && ls | grep -v Makefile".format(
                shlex.quote(_work_dir)
            )
        )
        if exitcode:
            return None

        suites_arr = output.strip().split('\n')

        suite2cases = []
        for suite in suites_arr:
            suite_data = self.default_suite_dict
            suite_data.update({
                "name": suite,
                "git_repo_id": git_repo_id,
            })

            cases_data = self._get_cases(suite)

            suite2cases.append(
                (
                    suite_data,
                    cases_data,
                )
            )

        return suite2cases
    
    def _get_cases(self, suite: str):
        """rebuild function to get cases data from ltp repo
            :params suite(str), the name of target suite
            :returns [dict], the fields of each element of the 
                return list is served for add cases data to database
        """
        cases_data = []
        with open(
            "{}/runtest/{}".format(self.oet_path, suite),
            "r",
        ) as f:
            case_lines = f.readlines()

            for case_line in case_lines:
                if case_line.startswith('#'):
                    continue

                _case_words = case_line.strip().split()
                if len(_case_words) < 2:
                    continue

                case_name = _case_words[0]
                case_command = ' '.join(_case_words[1:])

                case_data = self.default_case_dict
                case_data.update({
                    "suite": suite,
                    "name": case_name,
                    "code": case_command,
                })
                cases_data.append(case_data)
        
        return cases_data