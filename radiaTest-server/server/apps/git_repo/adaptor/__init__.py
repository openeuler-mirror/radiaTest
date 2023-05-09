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

import abc
import os
import subprocess
import shlex
from typing import List


class GitRepoAdaptor:
    # the kinds of filetype to be recognized as a testcase 
    CASES_FILETYPES = [".java", ".sh", ".py", ".c", ".c++", ".cpp"]
    # the filename which represent it is not a testcase
    NOT_CASES = []

    def __init__(self, git_url: str, branch: str, oet_path: str) -> None:
        """ initialization of resolver
            :params url(str), the url of testcase repo
            :params branch(str), the branch of testcase repo
            :params oet_path(str), the storage filepath
        """
        self.git_url = git_url
        self.branch = branch
        self.oet_path = oet_path

    @property
    def default_suite_dict(self):
        return {
            "machine_num": 1,
            "machine_type": "physical",
        }

    @property
    def default_case_dict(self):
        return {
            "machine_num": 1,
            "machine_type": "physical",
            "automatic": True,
            "usabled": False,
        }

    def download(self) -> tuple:
        """download testcases to local env
            :returns [tuple]:
                - exitcode(int): when exitcode is not equal to 0, download failed
                - output(str): the output of executing the download command
        """
        exitcode, output = subprocess.getstatusoutput(
            "git config http.version HTTP/1.1 & git clone -b {} {} {}".format(
                shlex.quote(self.branch),
                shlex.quote(self.git_url),
                shlex.quote(self.oet_path),
            )
        )
        return exitcode, output

    @abc.abstractmethod
    def suite2cases_resolve(self, git_repo_id: int) -> List[tuple]:
        """
        abstract interface, acting as the main entrance to resolve testcases 
        of target git repo
            :params git_repo_id(int)
            :returns [tuple], [(testsuite data，[testcase data])]
        """
    
    def _get_work_dir(self, work_dir: str) -> str:
        """
        Determine whether the root path of the test case resolution is 
        a directory, and store it as an instance variable if the 
        directory path is valid
            :returns str, the valid directory path
        """
        if not os.path.isdir(work_dir):
            return None

        return work_dir

    def _get_suites(self,
        git_repo_id: int, dir: str, 
        prefix: str = "", pass_through: bool = False) -> List[tuple]:
        """
        Retrieve all projects within the specified directory, 
        with each project treated as a test suite.
            :params git_repo_id(int), the ID of the target repo.
            :params dir(str), the current directory to look up.
            :params prefix(str), the prefix word for the name of suite, 
                default as void string.
            :params pass_through(bool), whether the prefix of suite would be 
                pass through to its children case.
                - when pass_through is true: prefix-suitename => prefix-casename
                - when pass_through is false: prefix-suitename => casename
            :returns [tuple], [(testsuite data，[testcase data])]
        """
        suite2cases = []

        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            if not os.path.isdir(file_path):
                continue
            
            suite_data = self.default_suite_dict
            suite_data.update({
                "name": f"{prefix}{filename}",
                "git_repo_id": git_repo_id,                                                                                                                                                                                                                                                                                                                                                                                                                           
            })
            suite2cases.append(
                (
                    suite_data, 
                    self._get_cases(
                        suite=filename, 
                        dir=file_path,
                        prefix="" if not pass_through else prefix,
                    )
                )
            )

        return suite2cases

    def _get_cases(self, suite: str, dir: str, prefix: str = "") -> List[dict]:
        """
        Recursively obtain all use cases in the suite directory, 
        and determine the use case file based on the class variable CASES_ FILETYPES.
        Not applicable to all test code repositories, but applicable to most structures

        Args:
            suite(str): the name of test suites, the directory name in the meanwhile
            dir(str): the current directory to look up
            prefix(str): the prefix word for the name of suite and case, 
                default as void string
        
        Returns:
            [dict]: the list of testcases, which content filled with fixed template.

            - machine_num(int): the required machine quantity of the case, 
                for openjdk it will be set as 1
            - machine_type(str): pysical machine or virtual machine, 
                for openjdk it will be set as physical
            - suite(str): the suite that the case belongs to
            - automatic(bool): whether the case has test script, 
                for openjdk it will be set as true
            - usabled(bool): whether the script cound be utilized by radiaTest, 
                currently false
        """
        cases = []

        for filename in os.listdir(dir):
            _file_path = os.path.join(dir, filename)
            
            _case_name, _case_ext = os.path.splitext(filename)
            if not _case_name or not _case_ext:
                continue

            if (
                os.path.isfile(_file_path) 
                and _case_ext in self.CASES_FILETYPES
                and _case_name not in self.NOT_CASES
            ):
                case = self.default_case_dict
                case.update({
                    "suite": f"{prefix}{suite}",
                    "name": f"{prefix}{os.path.splitext(filename)[0]}",                                                                                                                                                                                                                                                                                                                                                                                                                               
                })
                cases.append(case)

            if os.path.isdir(_file_path):
                cases += self._get_cases(suite, _file_path, prefix)
        
        return cases