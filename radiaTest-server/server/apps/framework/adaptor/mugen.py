import re
import os
import json
import shlex
import subprocess
from copy import deepcopy

from server.utils.bash import deploy_mugen_framwork


class Mugen:
    deploy_main_cmd = deploy_mugen_framwork

    @staticmethod
    def get_case_code(path, case):
        if not path or not case.get("name"):
            return None

        script_code = None

        for ext in ['.py', '.sh']:
            _filepath = path + '/' + case.get("name") + ext
            if os.path.isfile(_filepath):
                with open(_filepath, 'r') as script:
                    script_code = script.read()
                    break

        return script_code

    @staticmethod
    def mugen_suite2cases_resolver(git_repo_id, oet_path):
        exitcode, output = subprocess.getstatusoutput(
            'cd {}/suite2cases && \
            export SUITE=(*.json) && \
            echo "${{SUITE[@]%.*}}"'.format(
                shlex.quote(oet_path)
            )
        )
        if exitcode:
            return None
        else:
            suites_arr = output.strip().split()

            suite2cases = []
            for suite in suites_arr:
                origin_data = {}
                with open(
                    "{}/suite2cases/{}.json".format(
                        oet_path,
                        suite,
                    ),
                    "r",
                ) as f:
                    f_str = f.read()

                    old_keys = [
                        "machine num",
                        "machine type",
                        "add network interface",
                        "add disk",
                    ]
                    new_keys = [
                        "machine_num",
                        "machine_type",
                        "add_network_interface",
                        "add_disk",
                    ]
                    for i in range(4):
                        f_str = f_str.replace(old_keys[i], new_keys[i])
                    try:
                        origin_data = json.loads(f_str)
                    except:
                        continue

                suite_data = {
                    "name": suite,
                    "git_repo_id": git_repo_id,
                }
                suite_data.update(deepcopy(origin_data))

                if suite_data.get("add_disk") is not None:
                    suite_data["add_disk"] = ",".join(
                        [str(x) for x in suite_data["add_disk"]]
                    )

                suite_data.pop("cases")
                _raw_path = suite_data.pop("path")
                _suite_path = None

                result = re.search(r'^(\$OET_PATH\/)(.+)$', _raw_path)
                if result is not None:
                    _suite_path = '{}/{}'.format(
                        oet_path,
                        result[2]
                    )
                    if _suite_path[-1] == '/':
                        _suite_path = _suite_path[:-1]

                cases_data = []
                for case in origin_data["cases"]:
                    case_data = {
                        "suite": suite,
                        "description": "default",
                        "preset": "default",
                        "steps": "default",
                        "expection": "default",
                        "automatic": True,
                        "usabled": True,
                    }
                    if _suite_path:
                        case_data["code"] = Mugen.get_case_code(
                            _suite_path,
                            case,
                        )

                    case_data.update(case)

                    if case_data.get("add_disk") is not None:
                        case_data["add_disk"] = ",".join(
                            [str(x) for x in case_data["add_disk"]]
                        )

                    cases_data.append(case_data)

                suite2cases.append(
                    (
                        suite_data,
                        cases_data,
                    )
                )

            return suite2cases

    @staticmethod
    def deploy_init_cmd(path):
        return "cd %s/mugen && mkdir -p ~/.pip && echo -e '[global]\\nindex-url = https://repo.huaweicloud.com/repository/pypi/simple\\ntrusted-host = repo.huaweicloud.com\\ntimeout = 120\\n' > ~/.pip/pip.conf && bash dep_install.sh" % (path)

    @staticmethod
    def run_all_cmd(path):
        return "cd %s/mugen && bash mugen.sh -a -x" % (path)

    @staticmethod
    def run_suite_cmd(path, testsuite):
        return 'cd {}/mugen && bash mugen.sh -f "{}" -x'.format(
            path,
            testsuite,
        )

    @staticmethod
    def run_case_cmd(path, testsuite, testcase):
        return 'cd {}/mugen && bash mugen.sh -f "{}" -r "{}" -x'.format(
            path,
            testsuite,
            testcase,
        )

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
            if stage != "run_test" and _log_section[stage]:
                logs_data.append({
                    "stage": stage,
                    "checkpoint": stage,
                    "expect_result": 0,
                    "actual_result": _end_flag.get(stage),
                    "mode": 0,
                    "section_log": '\n'.join(_log_section[stage]),
                })
            elif _log_section[stage]:
                run_test_section = dict()
                start = 0
                step_num = 1
                checkpoint = ""
                actual_result = 0
                expect_result = 0
                mode = 0
                pattern = r'=(\d+)$'

                for i, line in enumerate(_log_section[stage]):
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
                        run_test_section[checkpoint] = _log_section[stage][start:i+1]
                        start = i + 1
                        step_num += 1
                        logs_data.append({
                            "stage": stage,
                            "checkpoint": checkpoint,
                            "expect_result": expect_result,
                            "actual_result": actual_result,
                            "mode": mode,
                            "section_log": '\n'.join(
                                run_test_section[checkpoint]
                            ),
                        })
                        actual_result = 0
                        expect_result = 0
                        mode = 0

                if not checkpoint:
                    run_test_section["run_test"] = _log_section["run_test"]
                    logs_data.append({
                        "stage": stage,
                        "checkpoint": "run_test",
                        "expect_result": 0,
                        "actual_result": _end_flag["post_test"],
                        "mode": 0,
                        "section_log": '\n'.join(run_test_section["run_test"]),
                    })

        return logs_data
