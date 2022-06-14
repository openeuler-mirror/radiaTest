import re
import os
import json
import shlex
import subprocess
from copy import deepcopy
from celeryservice.lib.api.executor import Executor
from messenger.utils.shell import ShellCmdApi
from flask import current_app


class MugenExecutor(Executor):

    @staticmethod
    def run_test(**kargs):
        if kargs.get('testcase') is None and kargs.get('testsuite') is None:
            return ShellCmdApipi(
                MugenExecutor.run_all_cases(kargs.get('download_path')),
                kargs.get('conn'),
            ).exec()

        if kargs.get('testcase') is None:
            return ShellCmdApi(
                MugenExecutor.run_suite(kargs.get('download_path'), kargs.get('testsuite')),
                kargs.get('conn'),
            ).exec()

        return ShellCmdApi(
            MugenExecutor.run_case(kargs.get('download_path'), kargs.get('testsuite'), kargs.get('testcase')),
            kargs.get('conn'),
        ).exec()

    @staticmethod
    def deploy(**kargs):
        # deploy framework init
        if MugenExecutor.init_env is not None:
            exitcode, output = ShellCmdApi(
                MugenExecutor.init_env(kargs.get('download_path')),
                kargs.get('conn'),
            ).exec()

            if exitcode:
                raise RuntimeError("Failed to deploy the framework of {}.".format(
                    kargs.get('framework')
                )
                )
            current_app.logger.info(output)

        # deploy framework main
        if MugenExecutor.init_conf is not None:
            for machine in kargs.get('machines'):
                if machine.get("ip") == kargs.get('master_ip'):
                    exitcode, output = ShellCmdApi(
                        MugenExecutor.init_conf(
                            current_app.config.get("WORKER_DOWNLOAD_PATH"),
                            machine
                        ),
                        kargs.get('conn'),
                    ).exec()
                    if exitcode:
                        raise RuntimeError(
                            "The framework failed to configure the test environment of master node."
                        )
                    current_app.logger.info(output)
                    kargs.get('machines').remove(machine)
                    break

            for machine in kargs.get('machines'):
                exitcode, output = ShellCmdApi(
                    MugenExecutor.init_conf(
                        current_app.config.get("WORKER_DOWNLOAD_PATH"),
                        machine
                    ),
                    kargs.get('conn')
                ).exec()
                if exitcode:
                    raise RuntimeError(
                        "The framework failed to configure the test environment of slave node."
                    )
                current_app.logger.info(output)

    @staticmethod
    def deploy_env():
        pass

    @staticmethod
    def init_env(path):
        return "cd %s/mugen && mkdir -p ~/.pip && " \
               "echo -e '[global]\\n" \
               "index-url = https://repo.huaweicloud.com/repository/pypi/simple\\n" \
               "trusted-host = repo.huaweicloud.com\\n" \
               "timeout = 120\\n' > ~/.pip/pip.conf && " \
               "bash dep_install.sh" % (
            path)

    @staticmethod
    def init_conf(path, machine):
        return "cd {}/mugen && \
                            bash mugen.sh -c --ip {} --password {} --port {} --user {}".format(
            path,
            shlex.quote(machine.get("ip")),
            shlex.quote(machine.get("password")),
            shlex.quote(str(machine.get("port"))),
            shlex.quote(machine.get("user")),
        )

    @staticmethod
    def get_case_code(path, case):
        if not path or not case.get("name"):
            raise FileNotFoundError("not found path {} or not found case {}"
                                    .format(path,case))

        script_code = None

        for ext in ['.py', '.sh']:
            _filepath = path + '/' + case.get("name") + ext
            if os.path.isfile(_filepath):
                with open(_filepath, 'r') as script:
                    script_code = script.read()
                    break

        return script_code

    @staticmethod
    def suite2cases_resolver(git_repo_id, oet_path):
        exitcode, output = subprocess.getstatusoutput(
            'cd {}/suite2cases && \
            export SUITE=(*.json) && \
            echo "${{SUITE[@]%.*}}"'.format(
                shlex.quote(oet_path)
            )
        )
        if exitcode:
            raise RuntimeError("get suite2cases failed.")
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
                    except RuntimeError as e:
                        current_app.logger.info(e)
                        continue

                suite_data = {
                    "name": suite,
                    "git_repo_id": git_repo_id,
                }
                suite_data.update(deepcopy(origin_data))

                if suite_data.get("add_disk") is not None:
                    suite_data["add_disk"] = ",".join(
                        [str(x) for x in suite_data.get("add_disk")]
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
                for case in origin_data.get("cases"):
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
                        case_data["code"] = MugenExecutor.get_case_code(
                            _suite_path,
                            case,
                        )

                    case_data.update(case)

                    if case_data.get("add_disk") is not None:
                        case_data["add_disk"] = ",".join(
                            [str(x) for x in case_data.get("add_disk")]
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
    def run_all_cases(path):
        return "cd %s/mugen && bash mugen.sh -a -x" % (path)

    @staticmethod
    def run_suite(path, testsuite):
        return 'cd {}/mugen && bash mugen.sh -f "{}" -x'.format(
            path,
            testsuite,
        )

    @staticmethod
    def run_case(path, testsuite, testcase):
        return 'cd {}/mugen && bash mugen.sh -f "{}" -r "{}" -x'.format(
            path,
            testsuite,
            testcase,
        )