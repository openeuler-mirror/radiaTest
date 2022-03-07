import os
import re
import abc
import json
import shlex
import requests
import datetime
import subprocess
from time import sleep
from copy import deepcopy

import ntplib
from server.utils.response_util import RET


class BaseMonitor:
    def __init__(self, app, interval) -> None:
        self.app = app
        self.interval = interval

    def run(self):
        while True:
            self.main()
            sleep(self.interval)

    @abc.abstractmethod
    def main(self):
        pass


class LifecycleMonitor(BaseMonitor):
    def main(self):
        self.app.logger.warn("LifecycleMonitor: Wake Up......")
        if self._sync_ntp_time():
            self.app.logger.warn("LifecycleMonitor: ......System Time Sync......")
            self._check_vmachines_lifecycle()
        else:
            raise Exception
        self.app.logger.warn("LifecycleMonitor: ......Sleep.")

    def _check_hardware_time(self):
        output = subprocess.getoutput("hwclock")
        hw_time = datetime.datetime.strptime(output[:25], "%Y-%m-%d %H:%M:%S.%f")
        sys_time = datetime.datetime.now()

        timedelta = hw_time - sys_time
        if timedelta.days < 0:
            timedelta = sys_time - hw_time

        if timedelta.seconds > 300:
            return False

        return True

    def _sync_ntp_time(self):
        client = ntplib.NTPClient()
        resp = None
        for host in self.app.config.get("NTP_SERVER"):
            try:
                resp = client.request(host, port="ntp", version=4, timeout=5)
                if resp:
                    break
            except Exception as e:
                pass

        if not resp:
            return self._check_hardware_time()

        ntp_time = resp.tx_time
        _date, _time = str(datetime.datetime.fromtimestamp(ntp_time))[:25].split(" ")

        exitcode = os.system('date -s "{}"'.format(_date + " " + _time))

        return True if exitcode == 0 else self._check_hardware_time()

    def _check_vmachines_lifecycle(self):
        v_machines = json.loads(
            requests.get(
                "http://{}:{}/api/v1/vmachine".format(
                    self.app.config.get("SERVER_IP"),
                    self.app.config.get("SERVER_PORT"),
                )
            ).text
        )

        if not isinstance(v_machines, list):
            self.app.logger.error(
                "LifecycleMonitor: Could not get vmachines data from server during running lifecycle monitor."
            )
            return

        timeout_vmachines = []

        for v_machine in v_machines:
            end_time = (
                datetime.datetime.strptime(
                    v_machine.get("end_time"), "%a, %d %b %Y %H:%M:%S %Z"
                )
                .replace(tzinfo=datetime.timezone.utc)
                .astimezone(datetime.timezone(datetime.timedelta(hours=8)))
            )

            if (
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
                > end_time
            ):
                timeout_vmachines.append(v_machine.get("id"))

        if timeout_vmachines:
            resp = requests.delete(
                "http://{}:{}/api/v1/vmachine".format(
                    self.app.config.get("SERVER_IP"),
                    self.app.config.get("SERVER_PORT"),
                ),
                data=json.dumps({"id": timeout_vmachines}),
                headers=self.app.config.get("HEADERS"),
            )
            if resp.status_code != 200:
                self.app.logger.error(
                    "LifecycleMonitor: Could not delete vmachines which exceed their end time."
                )


class RepoMonitor(BaseMonitor):
    def main(self):
        self.app.logger.warn("RepoMonitor: Wake Up......")

        is_updated = self._update_mugen()
        if not is_updated:
            self.app.logger.error(
                "RepoMonitor: Fail to update or download mugen, please check the network status"
            )
        else:
            suite2cases = self._resolve_suite2cases()

            if not isinstance(suite2cases, list):
                self.app.logger.error("RepoMonitor: Could not get suite2cases files")
                self.app.logger.warn("RepoMonitor: ......Sleep.")
                return

            for (
                suite_data,
                cases_data,
            ) in suite2cases:
                resp = requests.get(
                    "http://{}:{}/api/v1/repo_monitor/suite".format(
                        self.app.config.get("SERVER_IP"),
                        self.app.config.get("SERVER_PORT"),
                    ),
                    params={"name": suite_data["name"]},
                    headers=self.app.config.get("HEADERS"),
                )
                suite = json.loads(resp.text)
                if not isinstance(suite, list):
                    self.app.logger.error(
                        "RepoMonitor: " + suite.get("error_msg")
                    )
                    continue

                if not suite:
                    if self._handle_suite_data("POST", suite_data):
                        self._handle_cases_data(cases_data)
                else:
                    self._handle_cases_data(cases_data)

        self.app.logger.warn("RepoMonitor: ......Sleep.")
    
    def _git_clone(self):
        exitcode, output = subprocess.getstatusoutput(
            "git clone https://gitee.com/openeuler/mugen.git {}/mugen".format(
                shlex.quote(self.app.config.get("SERVER_FRAMEWORK_PATH"))
            )
        )
        return False if exitcode else True

    def _git_pull(self):
        exitcode, output = subprocess.getstatusoutput(
            "cd {}/mugen && \
            git pull https://gitee.com/openeuler/mugen".format(
                shlex.quote(self.app.config.get("SERVER_FRAMEWORK_PATH"))
            )
        )
        return False if exitcode else True

    def _update_mugen(self):
        if not os.path.exists(self.app.config.get("SERVER_FRAMEWORK_PATH") + "/mugen"):
            return self._git_clone()

        else:
            git_pull_result = self._git_pull()
            
            if git_pull_result:
                return git_pull_result
            
            exitcode, output = subprocess.getstatusoutput(
                "cd {} && \
                rm -rf ./mugen &&\
                git clone https://gitee.com/openeuler/mugen".format(
                    shlex.quote(self.app.config.get("SERVER_FRAMEWORK_PATH"))
                )
            )
            return False if exitcode else True
    
    def get_case_code(self, _path, _case):
        if not _path or not _case.get("name"):
            return None
        
        script_code = None

        # 支持的脚本文件类型后续写入配置文件中['.py', '.sh']
        for ext in ['.py', '.sh']:
            _filepath = _path + '/' +  _case.get("name") + ext
            if os.path.isfile(_filepath):
                with open(_filepath, 'r') as script:
                    script_code = script.read()
                    break
        
        return script_code

    def _resolve_suite2cases(self):
        exitcode, output = subprocess.getstatusoutput(
            'cd {}/mugen/suite2cases && \
            export SUITE=(*.json) && \
            echo "${{SUITE[@]%.*}}"'.format(
                shlex.quote(self.app.config.get("SERVER_FRAMEWORK_PATH"))
            )
        )
        if exitcode:
            self.app.logger.error("RepoMonitor: " + output)
        else:
            suites_arr = output.strip().split()
            suite2cases = []
            for suite in suites_arr:
                origin_data = {}
                with open(
                    "{}/mugen/suite2cases/{}.json".format(
                        self.app.config.get("SERVER_FRAMEWORK_PATH"),
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
                    origin_data = json.loads(f_str)

                suite_data = {
                    "name": suite,
                    "framework_id": 1,
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
                    _suite_path = '{}/mugen/{}'.format(
                        self.app.config.get("SERVER_FRAMEWORK_PATH"),
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
                        case_data["code"] = self.get_case_code(
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

    def _check_response(self, resp):
        resp.encoding = resp.apparent_encoding

        if resp.status_code != 200:
            self.app.logger.error("RepoMonitor: " + resp.text)
        elif json.loads(resp.text).get("error_code") != RET.OK:
            self.app.logger.error(
                "RepoMonitor: " + json.loads(resp.text).get("error_msg")
            )
        else:
            return True

        return False

    def _handle_suite_data(self, handler, data):
        resp = requests.request(
            handler,
            "http://{}:{}/api/v1/repo_monitor/suite".format(
                self.app.config.get("SERVER_IP"),
                self.app.config.get("SERVER_PORT"),
                handler,
            ),
            data=json.dumps(data),
            headers=self.app.config.get("HEADERS"),
        )
        return self._check_response(resp)

    def _handle_cases_data(self, cases_data):
        for case_data in cases_data:
            resp = requests.get(
                "http://{}:{}/api/v1/repo_monitor/case".format(
                    self.app.config.get("SERVER_IP"),
                    self.app.config.get("SERVER_PORT"),
                ),
                params={"name": case_data["name"]},
                headers=self.app.config.get("HEADERS"),
            )
            case = json.loads(resp.text)

            if not isinstance(case, list):
                if case.get("error_msg"):
                    self.app.logger.error(
                        "RepoMonitor: " + case.get("error_msg")
                    )
                elif case.get("error_msg"):
                    self.app.logger.error(
                        "RepoMonitor: " + case.get("error_msg")
                    )
                elif case.get("message"):
                    self.app.logger.error(
                        "RepoMonitor: " + case.get("message")
                    )
                continue

            if not case:
                resp = requests.post(
                    "http://{}:{}/api/v1/repo_monitor/case".format(
                        self.app.config.get("SERVER_IP"),
                        self.app.config.get("SERVER_PORT"),
                    ),
                    data=json.dumps(case_data),
                    headers=self.app.config.get("HEADERS"),
                )
                self._check_response(resp)
            else:
                case_data["id"] = case[0].get("id")
                resp = requests.put(
                    "http://{}:{}/api/v1/repo_monitor/case".format(
                        self.app.config.get("SERVER_IP"),
                        self.app.config.get("SERVER_PORT"),
                    ),
                    data=json.dumps(case_data),
                    headers=self.app.config.get("HEADERS"),
                )
                self._check_response(resp)
