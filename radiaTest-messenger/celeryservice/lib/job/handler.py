import os
import hashlib
import hmac
import urllib.parse
import http.client
import json
import re
import shlex
from copy import deepcopy
import time
from datetime import datetime
import pytz

from flask import current_app
from celery import chord

from celeryservice import celeryconfig
from messenger.utils.requests_util import query_request, create_request, update_request
from messenger.utils.response_util import RET
from celeryservice.lib import TaskAuthHandler
from celeryservice.sub_tasks import job_result_callback, run_case
from messenger.utils.pssh import ConnectionApi
from messenger.utils.shell import ShellCmdApi


class RunJob(TaskAuthHandler):
    def __init__(self, body, promise, user, logger) -> None:
        self._body = body
        self.promise = promise
        self.app_context = current_app.app_context()

        super().__init__(user, logger)

        self._body.update({
            "status": "PENDING",
            "start_time": self.start_time,
            "running_time": 0,
        })

    @property
    def pmachine_pool(self):
        return query_request(
            "/api/v1/accessable-machines",
            {
                "machine_group_id": self._body.get("machine_group_id"),
                "machine_purpose": "run_job",
                "machine_type": "physical",
                "frame": self._body.get("frame"),
                "get_object": False,
            },
            self.user.get("auth")
        )

    def _create_job(self, multiple: bool, is_suite_job: bool):
        if self._body.get("id"):
            del self._body["id"]

        self._body.update({
            "multiple": multiple,
            "is_suite_job": is_suite_job,
            "start_time": self._body.get("start_time").strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
        })

        job = create_request(
            "/api/v1/ws/default/job",
            self._body,
            self.user.get("auth")
        )

        if not job:
            raise RuntimeError(
                "Failed to create job:%s."
                % self._body.get("name")
            )

        self._body.update(job)
        self._body.pop("milestone")
        return job.get("id")

    def _update_job(self, **kwargs):
        self.next_period()
        self._body.update({
            "running_time": self.running_time,
            **kwargs,
        })

        update_body = deepcopy(self._body)
        update_body.pop("id")
        if isinstance(update_body.get("master"), list):
            update_body.update(
                {
                    "master": ','.join(update_body.get("master"))
                }
            )

        update_request(
            "/api/v1/job/{}".format(
                self._body.get("id")
            ),
            update_body,
            self.user.get("auth")
        )


class RunSuite(RunJob):
    def run(self):
        self._create_job(multiple=False, is_suite_job=True)

        try:
            suite = query_request(
                "/api/v1/suite/{}".format(
                    self._body.get("suite_id")
                ),
                None,
                self.user.get("auth")
            )

            if not suite:
                raise RuntimeError(
                    "test suite of id: {} does not exist, please check testcase repo.".format(
                        self._body.get("suite_id"))
                )

            cases = query_request(
                "/api/v1/ws/default/case/preciseget",
                {
                    "suite_id": suite.get("id"),
                    "automatic": 1,
                    "usabled": 1,
                },
                self.user.get("auth")
            )

            if not cases:
                raise RuntimeError(
                    "the automatical and usabled testcases of suite {} do not exits".format(suite.get("name"))
                )

            env_params = {
                "machine_type": suite.get("machine_type"),
                "machine_num": suite.get("machine_num"),
                "add_network": suite.get("add_network_interface"),
                "add_disk": suite.get("add_disk"),
            }

            suites_cases = [
                (
                    suite.get("name"),
                    case.get("name")
                ) for case in cases
            ]

            _task = run_case.delay(
                self.user,
                self._body,
                env_params,
                suites_cases,
                self.pmachine_pool,
            )

            self._update_job(tid=_task.task_id)

        except RuntimeError as e:
            self.logger.error(str(e))
            self._update_job(
                result="fail",
                remark=str(e),
                end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                status="BLOCK",
            )


class RunTemplate(RunJob):
    def __init__(self, body, promise, user, logger) -> None:
        super().__init__(body, promise, user, logger)

        self._template = query_request(
            "/api/v1/template/{}".format(
                self._body.get("template_id")
            ),
            None,
            self.user.get("auth")
        )

        if not self._template:
            raise RuntimeError(
                "template with id {} is not exist".format(
                    self._body.get("template_id")
                )
            )

        _git_repo = self._template.get("git_repo")

        self._body.update({
            "milestone_id": self._template.get("milestone_id"),
            "git_repo_id": _git_repo.get("id") if _git_repo else None,
            "total": len(self._template.get("cases")),
            "success_cases": 0,
            "fail_cases": 0,
        })

    def run(self):
        parent_id = self._create_job(multiple=True, is_suite_job=False)

        try:
            if self._body.get("id") and self._body.get("taskmilestone_id"):
                resp = self._callback_task_job_init()
                if resp.get("error_code") != RET.OK:
                    self.logger.warn(
                        "cannot callback job_id to taskmilestone table: " + resp.get("error_msg")
                    )

            self._update_job(
                status="CLASSIFYING",
            )

            classify_cases = self._sort()

            tasks = []
            for cases in classify_cases:
                env_params = {
                    "machine_type": cases.get("type"),
                    "machine_num": cases.get("machine"),
                    "add_network": cases.get("network"),
                    "add_disk": cases.get("disk"),
                }

                tasks.append(
                    run_case.s(
                        self.user,
                        self._body,
                        env_params,
                        cases.get("suites_cases"),
                        self.pmachine_pool,
                    )
                )

            chord_task = chord(tasks)(
                job_result_callback.s(
                    auth=self.user.get("auth"),
                    parent_id=parent_id,
                    job_id=self._body.get("id"),
                    taskmilestone_id=self._body.get("taskmilestone_id")
                )
            )

            self._update_job(
                status="RUNNING",
                tid=chord_task.task_id,
            )

        except RuntimeError as e:
            self.logger.error(str(e))
            self._update_job(
                result="fail",
                remark=str(e),
                end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                status="BLOCK",
            )

    def _callback_task_job_init(self):
        return update_request(
            "/api/v1/task/milestones/{}".format(
                self._body.get("taskmilestone_id")
            ),
            {
                "job_id": self._body.get("id"),
                "result": "block"
            },
            self.user.get("auth")
        )

    def _sort(self):
        cases = self._template.get("cases")

        if not cases:
            raise RuntimeError(
                "template {} has no relative cases.".format(
                    self._template.get("name")
                )
            )

        machine_type = set()
        machine_num = set()
        add_network = set()
        add_disk = set()
        for case in cases:
            machine_type.add(case.get("machine_type"))
            machine_num.add(case.get("machine_num"))
            add_network.add(case.get("add_network_interface"))
            add_disk.add(case.get("add_disk"))

        classify_cases = []
        for m_type in machine_type:
            for machine in machine_num:
                for network in add_network:
                    for disk in add_disk:
                        cs = {}
                        cl = []
                        for case in cases:
                            if (
                                    case["machine_num"] == machine
                                    and case["add_network_interface"] == network
                                    and case["add_disk"] == disk
                            ):
                                cl.append([case["suite"], case["name"]])

                        if cl:
                            cs["type"] = m_type
                            cs["machine"] = machine
                            cs["network"] = network
                            cs["disk"] = disk
                            cs["suites_cases"] = cl
                            classify_cases.append(cs)

        return classify_cases


class RunAt(RunJob):
    def __init__(self, body, promise, user, logger) -> None:
        super().__init__(body, promise, user, logger)
        self._pxe_repo_path = self._body.get("pxe_repo_path")
        self._pxe_tftpboot_path = self._body.get("pxe_tftpboot_path")
        self._pxe_efi_path = self._body.get("pxe_efi_path")
        self.con = ConnectionApi(
            ip=celeryconfig.pxe_ip,
            user=celeryconfig.pxe_ssh_user,
            port=celeryconfig.pxe_ssh_port,
            pkey=celeryconfig.pxe_pkey
        )
        self.con.conn()
        self.con_openqa = ConnectionApi(
            ip=self._body.get("ip"),
            port=self._body.get("port"),
            user=self._body.get("user"),
            passwd=self._body.get("password"),
        )
        self.con_openqa.conn()
        self._release_url = self._body.get("release_url")
        self._release_path = self._release_url.split("dailybuild")[1].replace("//", "")
        self._iso_path = os.path.join(celeryconfig.iso_local_path, self._release_path)
        self._iso_url = os.path.join(celeryconfig.iso_local_path, self._release_path)
        self._iso_name = self._release_url.split("/")[-1]
        self._release_date = re.findall(r'\d+-\d+-\d+-\d+-\d+-\d+', self._release_path.split("/")[1])[0]
        self._release_path_item = self._release_path.split("/")
        self.arch = self._release_path_item[-2]
        self.product = self._release_path_item[-1].split("-" + self.arch)[0]

        self.logger.info(
            "release_path:{},iso_path:{},iso_name:{},release_path_item:{}".format(
                self._release_path,
                self._iso_path,
                self._iso_name,
                self._release_path_item)
        )

    def run(self):
        try:
            exitcode, output = ShellCmdApi(
                "mkdir -p {} {} {}".format(
                    shlex.quote(self._pxe_repo_path),
                    shlex.quote(self._pxe_tftpboot_path),
                    shlex.quote(self._pxe_efi_path)
                ),
                self.con
            ).exec()
            if exitcode:
                raise RuntimeError("prepare pxe dir is failed")

            self._wget_source()
            self._pxe_mugen_docker()
            self._pxe_mugen_stratovirt()
            self._pxe_release_iso()
            self._pxe_repo()
            self._pxe_tftpboot()

            self.logger.info("pxe environment is already prepare finished")

            exitcode, out = ShellCmdApi(
                "rm -rf  {} && wget -c {} -O {}".format(
                    os.path.join(celeryconfig.at_iso_dir, self._iso_name),
                    os.path.join(celeryconfig.iso_web_addr, self._release_path),
                    os.path.join(celeryconfig.at_iso_dir, self._iso_name)
                ),
                self.con_openqa
            ).exec()
            if not exitcode:
                self.logger.info("openqa already download iso {}".format(self._iso_name))

            if "netinst" not in self._iso_name and "Desktop" not in self._iso_name:
                exitcode, out = ShellCmdApi(
                    "rm -rf  {}* && wget -c {} -O {} && xz -d {} && rm -rf {} && cp {} {}".format(
                        os.path.join(celeryconfig.at_qcow2_dir, self._iso_name.replace("-dvd.iso", ".qcow2")),
                        os.path.join(
                            celeryconfig.iso_web_addr,
                            self._release_path_item[0],
                            self._release_path_item[1],
                            "virtual_machine_img",
                            self.arch,
                            self._iso_name.replace("-dvd.iso", ".qcow2.xz")
                        ),
                        os.path.join(celeryconfig.at_qcow2_dir, self._iso_name.replace("-dvd.iso", ".qcow2.xz")),
                        os.path.join(celeryconfig.at_qcow2_dir, self._iso_name.replace("-dvd.iso", ".qcow2.xz")),
                        os.path.join(
                            celeryconfig.at_qcow2_dir,
                            self._iso_name.replace("-dvd.iso", ".qcow2").replace("openEuler-", "openEuler-Server-")
                        ),
                        os.path.join(
                            celeryconfig.at_qcow2_dir,
                            self._iso_name.replace("-dvd.iso", ".qcow2")
                        ),
                        os.path.join(
                            celeryconfig.at_qcow2_dir,
                            self._iso_name.replace("-dvd.iso", ".qcow2").replace("openEuler-", "openEuler-Server-")
                        )
                    ),
                    self.con_openqa
                ).exec()
                if not exitcode:
                    self.logger.info("openqa already download qcow2 {}".format(self._iso_name))

            ShellCmdApi(
                "chmod 777 /var/lib/openqa/share/factory -R;chown geekotest:geekotest /var/lib/openqa/share/factory -R",
                self.con_openqa
            ).exec()
            job_ids = self._start_template(
                self._body.get("test_suite"),
                release=self._iso_name.replace(".iso", ""),
                build="-" + self._release_date
            )
            self.logger.info("openqa job id:{}".format(job_ids))
            at_job_name = self._get_at_job_info(job_ids)

            update_request(
                "/api/v1/openeuler/at",
                {
                    "build_name": self._body.get("release_url"),
                    "at_job_name": ",".join(at_job_name)
                },
                self.user.get("auth")
            )

        except RuntimeError as e:
            self.logger.error(str(e))
        finally:
            self.con.close()
            self.con_openqa.close()

    def _check_sha256sum(self, local_iso, remote_sha256):
        self.logger.info("local_iso:{},remote_sha256:{}".format(local_iso, remote_sha256))
        exitcode, fileexist = ShellCmdApi(
            "ls %s" % local_iso,
            self.con
        ).exec()
        if exitcode:
            return True
        else:
            exitcode, output = ShellCmdApi(
                "curl %s | awk '{print $1}'" % remote_sha256,
                self.con
            ).exec()
            if exitcode:
                raise RuntimeError("remote sha256 file not exits:{}".format(remote_sha256))
            exitcode, local_sha256sum = ShellCmdApi(
                "sha256sum %s | awk '{print $1}'" % local_iso,
                self.con
            ).exec()
            if local_sha256sum not in output:
                return True
            else:
                return False

    def _download(self, path, source_url, remote_sha256_file, local_name):
        self.logger.info(
            "path:{},source_url:{},remote_sha256_file:{},local_name:{}".format(
                path,
                source_url,
                remote_sha256_file,
                local_name
            )
        )
        ShellCmdApi(
            "rm -rf {}* && cd {} && wget -c {} && wget -c {}".format(local_name, path, remote_sha256_file, source_url),
            self.con
        ).exec()
        for times in range(int(celeryconfig.waiting_time)):
            time.sleep(60)
            exitcode, remote_sha256 = ShellCmdApi(
                "cat %s | awk '{print $1}'" % (local_name + ".sha256sum"),
                self.con
            ).exec()

            exitcode, local_sha256 = ShellCmdApi(
                "sha256sum %s | awk '{print $1}'" % local_name,
                self.con
            ).exec()
            if local_sha256 == remote_sha256:
                ShellCmdApi(
                    "chmod 777 -R {}".format(shlex.quote(path)),
                    self.con
                ).exec()
                self.logger.info("{} is download success".format(local_name))
                break
            else:
                if times == int(celeryconfig.waiting_time) - 1:
                    raise RuntimeError("downloading is too slow and failed:{}".format(source_url))
                continue

    def _wget_source(self):
        home_path = os.path.join(
            celeryconfig.iso_local_path, self._release_path_item[0], self._release_path_item[1], ""
        )
        url_home_path = os.path.join(
            celeryconfig.source_iso_addr, self._release_path_item[0], self._release_path_item[1]
        )
        block_path = os.path.join(
            '/tmp', self._release_path_item[0], self._release_path_item[1], self._release_path_item[3], ""
        )
        block_file = os.path.join(shlex.quote(block_path), "block")
        self.logger.info("home_path:{}, url_home_path:{}, block_file:{}".format(home_path, url_home_path, block_file))
        for _ in range(int(celeryconfig.waiting_time)):
            exitcode, output = ShellCmdApi(
                "ls {}".format(block_file),
                self.con
            ).exec()
            if not exitcode:
                self.logger.info("there is another at job prepare env,waiting...")
            else:
                break
            time.sleep(120)
        ShellCmdApi(
            "mkdir -p {} && mkdir -p {} && echo block > {}".format(
                shlex.quote(home_path),
                shlex.quote(block_path),
                shlex.quote(block_file)
            ),
            self.con
        ).exec()

        try:
            if "Desktop" in self._release_path:
                self.logger.info("desktop iso prepare begin")
                workstation_path = os.path.join(home_path, "workstation", self._body.get("frame"))

                ShellCmdApi(
                    "mkdir -p {}".format(shlex.quote(workstation_path)),
                    self.con
                ).exec()

                remote_iso = os.path.join(celeryconfig.source_iso_addr, self._release_path)
                remote_sha256 = os.path.join(celeryconfig.source_iso_addr, self._release_path + ".sha256sum")
                local_iso = os.path.join(celeryconfig.iso_local_path, self._release_path)

                check_result = self._check_sha256sum(local_iso, remote_sha256)

                if check_result:
                    self._download(
                        workstation_path,
                        remote_iso,
                        remote_sha256,
                        local_iso
                    )
            elif "netinst" in self._release_path:
                self.logger.info("net iso  prepare")
                pass
            else:
                self.logger.info("standard iso prepare begin")
                iso_path = os.path.join(home_path, "ISO", self.arch)
                virt_path = os.path.join(home_path, "virtual_machine_img", self.arch)
                virt_url = os.path.join(
                    url_home_path,
                    "virtual_machine_img",
                    self.arch,
                    self._iso_name.replace("-dvd.iso", ".qcow2.xz")
                )
                docker_path = os.path.join(home_path, "docker_img", self.arch)
                docker_url = os.path.join(
                    url_home_path,
                    "docker_img",
                    self.arch,
                    "openEuler-docker." + self.arch + ".tar.xz"
                )
                stratovirt_path = os.path.join(home_path, "stratovirt_img", self.arch)
                strat_bin_url = os.path.join(
                    url_home_path,
                    "stratovirt_img",
                    self.arch,
                    "vmlinux.bin"
                )
                strat_img_url = os.path.join(
                    url_home_path,
                    "stratovirt_img",
                    self.arch,
                    self.product + "-stratovirt-" + self.arch + ".img.xz"
                )
                self.logger.info(
                    "iso_path:{}, virt_path:{}, virt_url:{}, docker_path:{}, docker_url:{}, stratovirt_path:{},"
                    "strat_bin_url:{} , strat_img_url:{}".format(
                        iso_path,
                        virt_path,
                        virt_url,
                        docker_path,
                        docker_url,
                        stratovirt_path,
                        strat_bin_url,
                        strat_img_url
                    )
                )
                ShellCmdApi(
                    "mkdir -p {} && mkdir -p {} && mkdir -p {} && mkdir -p {}".format(
                        shlex.quote(iso_path),
                        shlex.quote(virt_path),
                        shlex.quote(docker_path),
                        shlex.quote(stratovirt_path)
                    ),
                    self.con
                ).exec()

                check_result = self._check_sha256sum(
                    os.path.join(iso_path, self._iso_name),
                    os.path.join(celeryconfig.source_iso_addr, self._release_path + ".sha256sum")
                )
                if check_result:
                    self._download(
                        iso_path,
                        os.path.join(celeryconfig.source_iso_addr, self._release_path),
                        os.path.join(celeryconfig.source_iso_addr, self._release_path + ".sha256sum"),
                        os.path.join(iso_path, self._iso_name)
                    )

                check_result = self._check_sha256sum(
                    os.path.join(virt_path, self._iso_name.replace("-dvd.iso", ".qcow2.xz")),
                    virt_url + ".sha256sum"
                )
                if check_result:
                    self._download(
                        virt_path,
                        virt_url,
                        virt_url + ".sha256sum",
                        os.path.join(virt_path, self._iso_name.replace("-dvd.iso", ".qcow2.xz"))
                    )
                    ShellCmdApi(
                        "rm -rf {}* && cd {} && cp {} . && xz -d {}".format(
                            os.path.join(celeryconfig.local_hdd, self._iso_name.replace("-dvd.iso", ".qcow2")),
                            celeryconfig.local_hdd,
                            os.path.join(virt_path, self._iso_name.replace("-dvd.iso", ".qcow2.xz")),
                            self._iso_name.replace("-dvd.iso", ".qcow2.xz")
                        ),
                        self.con
                    ).exec()

                check_result = self._check_sha256sum(
                    os.path.join(docker_path, "openEuler-docker." + self.arch + ".tar.xz"),
                    docker_url + ".sha256sum"
                )
                if check_result:
                    self._download(
                        docker_path,
                        docker_url,
                        docker_url + ".sha256sum",
                        os.path.join(docker_path, "openEuler-docker." + self.arch + ".tar.xz")
                    )

                check_result = self._check_sha256sum(
                    os.path.join(stratovirt_path, "vmlinux.bin"),
                    strat_bin_url + ".sha256sum"
                )
                if check_result:
                    self._download(
                        stratovirt_path,
                        strat_bin_url,
                        strat_bin_url + ".sha256sum",
                        os.path.join(stratovirt_path, "vmlinux.bin")
                    )

                check_result = self._check_sha256sum(
                    os.path.join(
                        stratovirt_path,
                        self.product + "-stratovirt-" + self.arch + ".img.xz"
                    ),
                    strat_img_url + ".sha256sum"
                )
                if check_result:
                    self._download(
                        stratovirt_path,
                        strat_img_url,
                        strat_img_url + ".sha256sum",
                        os.path.join(
                            stratovirt_path,
                            self.product + "-stratovirt-" + self.arch + ".img.xz"
                        )
                    )
        except RuntimeError as e:
            self.logger.error(e)
        finally:
            ShellCmdApi(
                "rm -rf {}".format(block_file),
                self.con
            ).exec()

    def _pxe_mugen_docker(self):
        self.logger.info("pxe_mugen_docker prepare begin")
        docker_name = "openEuler-docker." + self.arch + ".tar.xz"
        at_docker_path = os.path.join(
            celeryconfig.mugen_path_docker,
            self.product,
            docker_name
        )
        local_docker_path = os.path.join(
            celeryconfig.iso_local_path,
            self._release_path_item[0],
            self._release_path_item[1],
            "docker_img",
            self.arch,
            docker_name
        )
        self.logger.info("at_docker_path:{}, local_docker_path:{}".format(at_docker_path, local_docker_path))
        ShellCmdApi(
            "rm -rf {} && cp -a {} {} && chmod 755 {} -R".format(
                shlex.quote(at_docker_path),
                shlex.quote(local_docker_path),
                shlex.quote(os.path.dirname(at_docker_path)),
                shlex.quote(celeryconfig.mugen_path_docker)
            ),
            self.con
        ).exec()

    def _pxe_mugen_stratovirt(self):
        self.logger.info("stratovirt begin prepare")
        at_straovirt_path = os.path.join(
            celeryconfig.mugen_path_stra,
            self.product,
            self.arch,
            ""
        )
        local_straovirt_path = os.path.join(
            celeryconfig.iso_local_path,
            self._release_path_item[0],
            self._release_path_item[1],
            "stratovirt_img",
            self.arch,
            ""
        )
        self.logger.info(
            "at_straovirt_path:{}, local_straovirt_path:{}".format(at_straovirt_path, local_straovirt_path))
        ShellCmdApi(
            "rm -rf {}* && cp -raf {}* {} && chmod 755 {} -R".format(
                shlex.quote(at_straovirt_path),
                shlex.quote(local_straovirt_path),
                shlex.quote(os.path.dirname(at_straovirt_path)),
                shlex.quote(at_straovirt_path)
            ),
            self.con
        ).exec()

    def _pxe_release_iso(self):
        self.logger.info("release iso file begin prepare")
        if self.arch == "x86_64":
            pxe_frame = "openeuler_X86"
        elif self.arch == "aarch64":
            pxe_frame = "openeuler_ARM64"
        else:
            raise RuntimeError("unknown frame is set")
        if "netinst" in self.product:
            pxe_release_iso = "pxe_release_netinst"
        else:
            pxe_release_iso = "pxe_release_iso"

        ShellCmdApi(
            "echo {} > {}".format(
                shlex.quote(celeryconfig.iso_web_addr + self._release_url.split("dailybuild")[1]),
                shlex.quote(
                    os.path.join(
                        "/var/www/html/pxe_release_iso",
                        self.product,
                        pxe_frame,
                        pxe_release_iso
                    )
                )
            ),
            self.con
        ).exec()

    def _pxe_repo(self):
        mount_dir = os.path.join(self._pxe_repo_path, "mnt")
        iso_path = os.path.join(celeryconfig.iso_local_path, self._release_path)
        self.logger.info("mount_dir:{},iso_path:{}".format(mount_dir, iso_path))
        ShellCmdApi(
            """umount {}""".format(
                mount_dir
            ),
            self.con
        ).exec()
        ShellCmdApi(
            """rm -rf {} && mkdir -p {} && cp {} {} && mount {} {} && sleep 3 && cp -r {} {} && umount {} && chmod 777 {} -R""".format(
                self._pxe_repo_path,
                mount_dir,
                iso_path,
                os.path.join(self._pxe_repo_path, ""),
                os.path.join(self._pxe_repo_path, self._iso_name),
                mount_dir,
                mount_dir,
                os.path.join(self._pxe_repo_path, "latest"),
                mount_dir,
                self._pxe_repo_path
            ),
            self.con
        ).exec()

    def _pxe_tftpboot(self):
        exitcode, output = ShellCmdApi(
            "rm -rf {} && mkdir -p {} && cp -r {} {} && chmod 777 {} -R && cp -ar {} {}".format(
                shlex.quote(self._pxe_tftpboot_path),
                shlex.quote(
                    os.path.join(
                        self._pxe_tftpboot_path,
                        "latest"
                    )
                ),
                shlex.quote(
                    os.path.join(self._pxe_repo_path, "latest/images")
                ),
                shlex.quote(
                    os.path.join(
                        self._pxe_tftpboot_path,
                        "latest",
                        ""
                    )
                ),
                shlex.quote(
                    self._pxe_tftpboot_path
                ),
                os.path.join(
                    self._pxe_repo_path,
                    "latest/EFI/BOOT/grub*efi"
                ),
                shlex.quote(
                    os.path.join(
                        self._pxe_efi_path,
                        ""
                    )
                )
            ),
            self.con
        ).exec()
        if exitcode:
            raise RuntimeError("prepare pxe_tftpboot failed:{}".format(output))

    def _update_headers(self):
        headers = {}
        headers['Content-type'] = 'application/x-www-form-urlencoded'
        headers['Accept'] = 'application/json'
        headers['X-API-Key'] = celeryconfig.api_key
        timestamp = time.time()
        api_hash = hmac.new(celeryconfig.api_secret.encode(),
                            '{0}{1}'.format(celeryconfig.at_post_url, timestamp).encode(),
                            hashlib.sha1)
        headers['X-API-Microtime'] = str(timestamp).encode()
        headers['X-API-Hash'] = api_hash.hexdigest()
        return headers

    def _start_template(self, template, **kwargs):
        http_con = http.client.HTTPConnection(self._body.get("ip"), int(celeryconfig.openqa_port), timeout=10)
        url = celeryconfig.at_post_url
        headers = self._update_headers()
        form = {}
        arr = []
        form['TEST'] = template
        for k, w in kwargs.items():
            form[k] = w
        try:
            arr = form['release'].split('-')
        except IndexError as e:
            self.logger.error("release key is not exist:{}".format(e))

        if len(arr) == 4:
            form['DISTRI'] = arr[0]
            form['VERSION'] = arr[1]
            form['ARCH'] = arr[2]
            form['FLAVOR'] = arr[3]
        elif len(arr) == 5:
            form['DISTRI'] = arr[0]
            form['VERSION'] = arr[1] + "-" + arr[2]
            form['ARCH'] = arr[3]
            form['FLAVOR'] = arr[4]
        elif len(arr) == 6:
            form['DISTRI'] = arr[0]
            form['VERSION'] = arr[1] + "-" + arr[2] + "-" + arr[3]
            form['ARCH'] = arr[4]
            form['FLAVOR'] = arr[5]
        elif len(arr) == 7:
            form['DISTRI'] = arr[0]
            form['VERSION'] = arr[1] + "-" + arr[2] + "-" + arr[3] + "-" + arr[4]
            form['ARCH'] = arr[5]
            form['FLAVOR'] = arr[6]
        else:
            form['DISTRI'] = 'openeuler'
            form['VERSION'] = '1.0'
            form['ARCH'] = 'aarch64'
            form['FLAVOR'] = 'dvd'

        job_ids = None
        try:
            params = urllib.parse.urlencode(form)
            http_con.request('POST', url, body=params, headers=headers)
            r = http_con.getresponse()
            self.logger.info('openqa response:{} {}'.format(r.status, r.reason))
            r_str = r.read()
            r_dict = json.loads(r_str)
            job_ids = r_dict.get("ids")
        except http.client.HTTPConnection as e:
            self.logger.error("openqa post request error:{}".format(e))
        return job_ids

    def _get_at_job_info(self, job_ids):
        at_job_name = list()
        http_con = http.client.HTTPConnection(self._body.get("ip"), int(celeryconfig.openqa_port), timeout=10)
        url = celeryconfig.at_get_url
        for job_id in job_ids:
            http_con.request('GET', os.path.join(url, str(job_id)))
            res = http_con.getresponse()
            r_str = res.read()
            r_dict = json.loads(r_str)
            name = r_dict.get("job").get("name")
            test_suite_name = name.split("@")[0].split(self._release_date + "-")[1]
            job_name = self._release_path_item[0] + "_Build-" + self._release_date + "_" + test_suite_name
            at_job_name.append(job_name)
        return at_job_name