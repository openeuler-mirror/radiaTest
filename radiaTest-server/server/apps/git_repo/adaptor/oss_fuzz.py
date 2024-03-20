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
# @Date    : 2023/05/09
# @License : Mulan PSL v2
#####################################

from server.apps.git_repo.adaptor import GitRepoAdaptor


class OssFuzz(GitRepoAdaptor):
    # the filename which represent it is not a testcase
    NOT_CASES = ["build"]

    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from oss-fuzz repo
            :params git_repo_id(int), the ID of testcase repo in database
            :returns [tuple], [(testsuite data，[testcase data])]
        """
        work_dir = self._get_work_dir(f"{self.oet_path}/projects")
        if not work_dir:
            return []
        
        return self._get_suites(
            git_repo_id=git_repo_id,
            local_dir=work_dir,
            prefix='oss-fuzz-', 
            pass_through=False,
        )
