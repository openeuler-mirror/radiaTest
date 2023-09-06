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

import re

from celeryservice.lib.api.log_resolver import LogResolver


class MugenLogResolver(LogResolver):
    @staticmethod
    def loads_logs(logs_lines):
        """Loading text of logs file, stratifying data to store

            :param logs_lines: List[str]

            :return logs_data: List[dict]
        """
        logs_data = []

        _stages = ["pre_test", "run_test", "post_test"]

        _run_test_start = 0
        _post_test_start = len(logs_lines)

        _end_flag = dict()
        _end_flag["pre_test"] = 1

        if logs_lines[-1].find("INFO") != -1:
            _end_flag["post_test"] = 0
        else:
            _end_flag["post_test"] = 1

        for i, line in enumerate(logs_lines):
            if line == "+ run_test":
                _end_flag["pre_test"] = 0
                _run_test_start = i
            elif line == "+ post_test":
                _post_test_start = i

        _log_section = dict()
        _log_section["pre_test"] = logs_lines[:_run_test_start]
        _log_section["run_test"] = logs_lines[_run_test_start:_post_test_start]
        _log_section["post_test"] = logs_lines[_post_test_start:]

        for stage in _stages:
            if stage != "run_test" and _log_section.get(stage):
                logs_data.append({
                    "stage": stage,
                    "checkpoint": stage,
                    "expect_result": 0,
                    "actual_result": _end_flag.get(stage),
                    "mode": 0,
                    "section_log": '\n'.join(_log_section.get(stage)),
                })
            elif _log_section.get(stage):
                run_test_section = dict()
                start = 0
                step_num = 1
                checkpoint = ""
                actual_result = 0
                expect_result = 0
                mode = 0
                pattern = r'=(\d+)$'

                for i, line in enumerate(_log_section.get(stage)):
                    if line.find("+ CHECK_RESULT") != -1:
                        checkpoint = "step " + str(step_num)

                    if line.find("+ actual_result") != -1 and checkpoint:
                        match = re.search(pattern, line)
                        if match:
                            actual_result = int(match.group(1))

                    if line.find("+ expect_result") != -1 and checkpoint:
                        match = re.search(pattern, line)
                        if match:
                            expect_result = int(match.group(1))

                    if line.find("+ mode") != -1 and checkpoint:
                        match = re.search(pattern, line)
                        if match:
                            mode = int(match.group(1))

                    if line.find("+ return") != -1 and checkpoint:
                        run_test_section[checkpoint] = _log_section.get(stage)[start:i + 1]
                        start = i + 1
                        step_num += 1
                        logs_data.append({
                            "stage": stage,
                            "checkpoint": checkpoint,
                            "expect_result": expect_result,
                            "actual_result": actual_result,
                            "mode": mode,
                            "section_log": '\n'.join(
                                run_test_section.get(checkpoint)
                            ),
                        })
                        actual_result = 0
                        expect_result = 0
                        mode = 0

                if not checkpoint:
                    run_test_section["run_test"] = _log_section.get("run_test")
                    logs_data.append({
                        "stage": stage,
                        "checkpoint": "run_test",
                        "expect_result": 0,
                        "actual_result": _end_flag.get("post_test"),
                        "mode": 0,
                        "section_log": '\n'.join(run_test_section.get("run_test")),
                    })

        return logs_data
