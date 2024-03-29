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
import shlex
import json
from copy import deepcopy
from typing import List

from flask import current_app

from server.apps.git_repo.adaptor import GitRepoAdaptor
from server.utils.shell import run_cmd


class Mugen(GitRepoAdaptor):
    class MugenField:
        _supported_fields = {
            "machine num": "machine_num",
            "machine type": "machine_type",
            "add network interface": "add_network_interface",
            "add disk": "add_disk",
        }

        @classmethod
        def translate(cls, text: str):
            """translate keywords which does not match coding lint rule
                :params text(str), the original text to translate
                :returns str, the translated text, keywords would be change 
                    to words with '_', such as 'add_disk' for matching field
                    in database.
            """
            for key in cls._supported_fields.keys():
                text = text.replace(key, cls._supported_fields[key])
            return text

        @classmethod
        def translate_add_disk(cls, add_disk_list: list) -> str:
            return ",".join([str(x) for x in add_disk_list])

    def suite2cases_resolve(self, git_repo_id):
        """resolving testcases data from mugen repo
            :params git_repo_id(int)
            :returns [tuple], [(testsuite data，[testcase data])]
        """

        _work_dir = self._get_work_dir(f"{self.oet_path}/suite2cases")
        if not _work_dir:
            return []
        exitcode, output, _ = run_cmd('cd {} && export SUITE=(*.json) && echo "${{SUITE[@]%.*}}"'.format(
            shlex.quote(_work_dir))
        )

        if exitcode:
            return []

        suites_arr = output.strip().split()

        return self._get_suites(git_repo_id=git_repo_id, suites_arr=suites_arr)
    
    def _get_case_code(self, path: str, case: dict) -> str:
        """get code of testcase from given filepath
            :params path(str), the filepath of testsuite
            :params case(str), the name of testcase, commonly has fields below
                - name(str), the name of testcase
                - machine num(str), the number of machine the testcase needed
                - machine type(str), the type of machine the testcase needed
                - add network interface(int), the number of nics the testcase needed
                - add disk(List[int]), the disks with column needed by the testcase            
            :returns str, the resolved testscript code
        """
        if not path or not case.get("name"):
            raise FileNotFoundError(
                f"not found path {path} or not found case {case}")

        script_code = None

        for ext in ['.py', '.sh']:
            _filepath = path + '/' + case.get("name") + ext
            if os.path.isfile(_filepath):
                with open(_filepath, 'r') as script:
                    script_code = script.read()
                    break

        return script_code

    def _get_cases(self, suite: str = None, local_dir: str = None,
                   prefix: str = "", suite_path: str = None, cases: list = None) -> list:
        """rebuild function to get cases data with fixed format from given testsuite for mugen
            :params suite(str), the name of given testsuite
            :params suite_path(str), the filepath of testsuite
            :params cases(list), the original cases list
            :returns [dict], the target format of cases list
        """
        cases_data = []
        for case in cases:
            case_data = {
                "suite": suite,
                "automatic": True,
                "usabled": True,
            }
            if suite_path:
                case_data["code"] = self._get_case_code(suite_path, case)

            case_data.update(case)

            if case_data.get("add_disk") is not None:
                case_data["add_disk"] = ",".join(
                    [str(x) for x in case_data["add_disk"]]
                )

            cases_data.append(case_data)
        
        return cases_data

    def _get_suite(self, suite: str, git_repo_id: int) -> dict:
        """get single dict type data of testsuite
            :params suite(str), the name fo testsuite
            :params git_repo_id(int), the ID of testcases repo
            :returns dict, containing necessary fields to create 
                a new suite in db
        """
        origin_data = {}
        with open(
            "{}/suite2cases/{}.json".format(self.oet_path, suite), 
            "r"
        ) as f:
            f_str = f.read()
            translated_str = Mugen.MugenField.translate(f_str)
            origin_data = json.loads(translated_str)

        suite_data = {
            "name": suite,
            "git_repo_id": git_repo_id,
        }
        suite_data.update(deepcopy(origin_data))

        # translate value of add_disk to valid format
        if suite_data.get("add_disk") is not None:
            suite_data["add_disk"] = Mugen.MugenField.translate_add_disk(
                suite_data["add_disk"]
            )
        
        return suite_data

    def _get_suites(self, git_repo_id: int = None, local_dir: str = None,
                    prefix: str = "", pass_through: bool = False, suites_arr: List[str] = None) -> List[tuple]:
        """rebuild function to get suites from mugen repo
            :params suites_arr([str]), the list of suites name resolved
            :returns [tuple], [(suite data, [case data])]
        """
        suite2cases = []
        for suite in suites_arr:
            try:
                suite_data = self._get_suite(suite, git_repo_id)
                cases = suite_data.pop("cases")
                _raw_path = suite_data.pop("path")

                suite_path = None
                if _raw_path:
                    suite_path = _raw_path.repalce("$OET_PATH", self.oet_path)

                    if suite_path[-1] == '/':
                        suite_path = suite_path[:-1]

                cases_data = self._get_cases(suite=suite, suite_path=suite_path, cases=cases)

                suite2cases.append(
                    (suite_data, cases_data)
                )
            except Exception as e:
                current_app.logger.info(f"suite is not standard:{e}")

        return suite2cases
