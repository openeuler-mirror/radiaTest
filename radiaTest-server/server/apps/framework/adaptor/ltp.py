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
# @Date    : 2023/05/04
# @License : Mulan PSL v2
#####################################

import shlex
import subprocess


class Ltp:
    @staticmethod
    def suite2cases_resolver(git_repo_id, oet_path):
        """
        部署框架的命令步骤

        Args:
            git_repo_id(int): 测试代码仓注册的ID
            oet_path(str): 测试项目所在路径

        Returns:
            [tuple]: [(测试套名，[测试用例名])]
        """
        exitcode, output = subprocess.getstatusoutput(
            "cd {}/runtest && ls | grep -v Makefile".format(
                shlex.quote(oet_path)
            )
        )
        if exitcode:
            return None
        else:
            suites_arr = output.strip().split('\n')

            suite2cases = []
            for suite in suites_arr:
                suite_data = {
                    "name": suite,
                    "git_repo_id": git_repo_id,
                }
                suite_data.update({
                    "machine_num": 1,
                    "machine_type": "physical",
                })

                cases_data = []
                with open(
                    "{}/runtest/{}".format(
                        oet_path,
                        suite,
                    ),
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

                        case_data = {
                            "suite": suite,
                            "automatic": True,
                            "usabled": False,
                            "name": case_name,
                            "code": case_command,
                            "machine_num": 1,
                            "machine_type": "physical",
                        }
                        cases_data.append(case_data)

                suite2cases.append(
                    (
                        suite_data,
                        cases_data,
                    )
                )

            return suite2cases