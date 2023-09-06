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

import shlex
from celeryservice.lib.api.executor import Executor
from messenger.utils.shell import ShellCmdApi
from flask import current_app


class MugenExecutor(Executor):

    @staticmethod
    def run_test(**kargs):
        if kargs.get('testcase') is None and kargs.get('testsuite') is None:
            return ShellCmdApi(
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