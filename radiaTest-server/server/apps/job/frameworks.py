import re

from server.utils.bash import deploy_mugen_framwork


class Mugen:
    url = "https://gitee.com/openeuler/mugen.git"

    repo_name = "mugen"

    logs_path = "/mugen/logs"

    deploy_main_cmd = deploy_mugen_framwork

    @staticmethod
    def deploy_init_cmd(path):
        return "cd %s/mugen && mkdir -p ~/.pip && echo -e '[global]\\nindex-url = https://repo.huaweicloud.com/repository/pypi/simple\\ntrusted-host = repo.huaweicloud.com\\ntimeout = 120\\n' > ~/.pip/pip.conf && bash dep_install.sh" % (path)

    @staticmethod
    def run_all_cmd(path):
        "cd %s/mugen && bash mugen.sh -a -x" % (path)

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