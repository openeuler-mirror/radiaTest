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
# @Date    : 2023/05/09
# @License : Mulan PSL v2
#####################################

from server.apps.git_repo.adaptor import GitRepoAdaptor


class Gcc(GitRepoAdaptor):
    # the kinds of filetype to be recognized as a testcase 
    CASES_FILETYPES = [
        ".c", ".cpp", ".c++", ".cc", ".cxx", ".C",
        ".F90", ".f90", ".f", ".for", ".f95", ".F95",
    ]

    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from gcc repo
            :params git_repo_id(int), the ID of testcase repo in database
            :returns [tuple], [(testsuite data，[testcase data])]
        """
        work_dir = self._get_work_dir(f"{self.oet_path}/gcc/testsuite")
        if not work_dir:
            return None
        
        return self._get_suites(
            dir=work_dir, 
            git_repo_id=git_repo_id, 
            pass_through=False,
        )