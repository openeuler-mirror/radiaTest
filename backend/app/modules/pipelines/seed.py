# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Seed 6 个默认 update 测试模块模板。"""
# ruff: noqa: E501

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pipelines.models import PipelineType, TestModuleTemplate

# --- pipeline types ---

DEFAULT_PIPELINE_TYPES = [
    {
        "name": "update",
        "display_name": "Update 测试流水线",
        "strategy_kind": "update_strategy",
        "test_framework": "mugen",
        "is_system": True,
        "default_config": {},
    },
    {
        "name": "release",
        "display_name": "Release 测试流水线",
        "strategy_kind": "direct_run",
        "test_framework": "mugen",
        "is_system": True,
        "default_config": {},
    },
]


def seed_pipeline_types(db: Session) -> int:
    """Seed `update`(A-class，代码驱动)和 `release`(B-class，数据驱动)pipeline type。

    幂等：已有记录原地更新，缺失的才创建。
    """
    created = 0
    for type_data in DEFAULT_PIPELINE_TYPES:
        existing = db.execute(
            select(PipelineType).where(PipelineType.name == type_data["name"])
        ).scalar_one_or_none()
        if existing is not None:
            for key, value in type_data.items():
                if key != "name":
                    setattr(existing, key, value)
            continue
        db.add(PipelineType(**type_data))
        created += 1
    db.commit()
    return created


# --- common update repo setup (shared by all 5 update modules) ---
# 从 http://121.36.84.172/repo.openeuler.org/${KRONOS_OS_VERSION}/ 取最新
# update_YYYYMMDD/ 目录，写入 /etc/yum.repos.d/openEuler-update.repo，dnf clean + makecache。
# dnf makecache 重试 3 次（睡 10s）——OS/everything/source 走 repo.openeuler.org→CDN（公网
# DNS），VM 公网 DNS 偶发抖动时元数据下载失败，重试大概率过；全失败才 exit 1 让 pre_env 挂。
# KRONOS_OS_VERSION 和 KRONOS_ARCH 由 mugen_runner 注入到 env 文件。
# 注意：无 shebang / 无 set，设计为内联嵌入到各模块的 pre_env_script 里。
# docker 模块通过 docker exec 在容器内运行此代码块。

UPDATE_REPO_SETUP = r'''
# --- common update repo setup (strict translation of lkp-tests setup/repo) ---
source /etc/openEuler-latest
LANG=en_US.UTF-8
service_ip=121.36.84.172
version_info=${openeulerversion}
official_repo=http://repo.openeuler.org

test_update_repo=$(curl http://"${service_ip}"/repo.openeuler.org/"${version_info}"/"${version_info}"-update.json | grep dir | grep "[0-9]" | grep -v test | grep -v round | awk -F \" '{print $4}' | awk -F "/" '{print $1}' | sort | uniq | tail -n 1)
test_EPOL_update_repo=$(curl http://"${service_ip}"/repo.openeuler.org/"${version_info}"/EPOL/"${version_info}"-update.json | grep dir | grep "[0-9]" | grep -v test | grep -v round | awk -F \" '{print $4}' | awk -F "/" '{print $1}' | sort | uniq | tail -n 1 | awk -F "|" '{print $1}')

rm -rf /etc/yum.repos.d/*
echo "[${version_info}_OS]
name=${version_info}_OS
baseurl=${official_repo}/${version_info}/OS/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_everything]
name=${version_info}_everything
baseurl=${official_repo}/${version_info}/everything/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/everything/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_source]
name=${version_info}_source
baseurl=${official_repo}/${version_info}/source/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_update]
name=${version_info}_update
baseurl=${official_repo}/${version_info}/update/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_update_source]
name=${version_info}_update_source
baseurl=${official_repo}/${version_info}/update/source/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
" >/etc/yum.repos.d/"${version_info}".repo

if [ "${version_info}"x == "openEuler-20.03-LTS-SP1"x ]; then
        echo "[${version_info}_EPOL]
name=${version_info}_EPOL
baseurl=${official_repo}/${version_info}/EPOL/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_EPOL_source]
name=${version_info}_EPOL_source
baseurl=${official_repo}/${version_info}/EPOL/source/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_EPOL_update]
name=${version_info}_EPOL_update
baseurl=${official_repo}/${version_info}/EPOL/update/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_EPOL_update_source]
name=${version_info}_EPOL_update_source
baseurl=${official_repo}/${version_info}/EPOL/update/source/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler" >>/etc/yum.repos.d/"${version_info}".repo
    else
        echo "[${version_info}_EPOL]
name=${version_info}_EPOL
baseurl=${official_repo}/${version_info}/EPOL/main/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_EPOL_source]
name=${version_info}_EPOL_source
baseurl=${official_repo}/${version_info}/EPOL/main/source/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_EPOL_update]
name=${version_info}_EPOL_update
baseurl=${official_repo}/${version_info}/EPOL/update/main/$(arch)/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler

[${version_info}_EPOL_update_source]
name=${version_info}_EPOL_update_source
baseurl=${official_repo}/${version_info}/EPOL/update/main/source/
enabled=1
gpgcheck=1
gpgkey=${official_repo}/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler" >>/etc/yum.repos.d/"${version_info}".repo
    fi

    printf "
[${version_info}_%s]
name=${version_info}_%s
baseurl=http://${service_ip}/repo.openeuler.org/${version_info}/%s/$(arch)/
enabled=1
gpgcheck=1
gpgkey=http://repo.openeuler.org/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
priority=1
" "${test_update_repo}" "${test_update_repo}" "${test_update_repo}" >>/etc/yum.repos.d/"${version_info}".repo

    printf "
[${version_info}_source_%s]
name=${version_info}_source_%s
baseurl=http://${service_ip}/repo.openeuler.org/${version_info}/%s/source/
enabled=1
gpgcheck=1
gpgkey=http://repo.openeuler.org/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
priority=1
" "${test_update_repo}" "${test_update_repo}" "${test_update_repo}" >>/etc/yum.repos.d/"${version_info}".repo

        if [ "${version_info}"x == "openEuler-20.03-LTS-SP1"x ]; then
        if [ "${test_update_repo}"x == "${test_EPOL_update_repo}"x ]; then
            printf "
[${version_info}_EPOL_%s]
name=${version_info}_EPOL_%s
baseurl=http://${service_ip}/repo.openeuler.org/${version_info}/EPOL/%s/$(arch)/
enabled=1
gpgcheck=1
gpgkey=http://repo.openeuler.org/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
priority=1
" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" >>/etc/yum.repos.d/"${version_info}".repo

            printf "
[${version_info}_EPOL_source_%s]
name=${version_info}_EPOL_source_%s
baseurl=http://${service_ip}/repo.openeuler.org/${version_info}/EPOL/%s/source/
enabled=1
gpgcheck=1
gpgkey=http://repo.openeuler.org/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
priority=1
" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" >>/etc/yum.repos.d/"${version_info}".repo
        else
            printf "No ${version_info}_EPOL_%s repo" "$test_update_repo"
        fi
    else
        if [ "${test_update_repo}"x == "${test_EPOL_update_repo}"x ]; then
            printf "
[${version_info}_EPOL_%s]
name=${version_info}_EPOL_%s
baseurl=http://${service_ip}/repo.openeuler.org/${version_info}/EPOL/%s/main/$(arch)/
enabled=1
gpgcheck=1
gpgkey=http://repo.openeuler.org/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
priority=1
" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" >>/etc/yum.repos.d/"${version_info}".repo

            printf "
[${version_info}_EPOL_source_%s]
name=${version_info}_EPOL_source_%s
baseurl=http://${service_ip}/repo.openeuler.org/${version_info}/EPOL/%s/main/source/
enabled=1
gpgcheck=1
gpgkey=http://repo.openeuler.org/${version_info}/OS/$(arch)/RPM-GPG-KEY-openEuler
priority=1
" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" "${test_EPOL_update_repo}" >>/etc/yum.repos.d/"${version_info}".repo
        else
            printf "No ${version_info}_EPOL_%s repo" "${test_update_repo}"
        fi
    fi

dnf clean all
# dnf makecache 重试 3 次（瞬时公网 DNS 抖动时 repo 元数据下载会失败，重试大概率过）。
_makecache_ok=0
for _attempt in 1 2 3; do
  if dnf makecache; then
    _makecache_ok=1
    break
  fi
  echo "dnf makecache attempt ${_attempt} failed, retry in 10s" >&2
  sleep 10
done
if [[ ${_makecache_ok} -ne 1 ]]; then
  echo "dnf makecache failed after 3 attempts" >&2
  exit 1
fi
'''


# Restore root SSH password login for _self_collect_logs. Appended to module
# post_env scripts (pkgserver/pkgcmd/pkgmanage). docker (container) + kernel
# (LTP) don't touch host sshd, so they don't use it.
RESTORE_SSH_ACCESS = r'''
# pkgserver's clean_up_env (yum remove openssh-server) + reinstall, or any
# pkgcmd/pkgmanage case doing `dnf remove/install openssh-server`, resets
# sshd_config to the package default — on 24.03-SP4 that is
# PermitRootLogin prohibit-password, disabling root SSH password login (console
# still works). Re-assert the provisioning values (mirror pxe-install.sh) so the
# worker can SSH back to collect /opt/<module>-logs/*. Idempotent (no-op where
# already yes).
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/; s/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || true
'''


# --- docker module ---

DOCKER_PRE_ENV = r"""#!/bin/bash
export LANG="en_US.UTF-8"

# === 1. install_docker ===
echo "KRONOS_PROGRESS: 1/10 安装 docker-engine"
yum install -y docker-engine-*18.09* git

# === 2. prepare_docker (devicemapper + RAMDISK) ===
echo "KRONOS_PROGRESS: 2/10 配置 devicemapper + RAMDISK + 启动 docker"
systemctl stop docker 2>/dev/null || true
cat > /etc/docker/daemon.json <<'DMEOF'
{
  "storage-driver": "devicemapper",
  "storage-opts": [
  "dm.use_deferred_removal=true",
  "dm.use_deferred_deletion=true"
  ]
}
DMEOF
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/ramdisk.conf <<'RAMEOF'
[Service]
Environment="DOCKER_RAMDISK=true"
RAMEOF
depmod -a $(uname -r)
systemctl daemon-reload
systemctl start docker

# === 3. case_fix (pip mirror) ===
echo "KRONOS_PROGRESS: 3/10 配置 pip 镜像"
mkdir -p ~/.pip
echo -e "[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple" > ~/.pip/pip.conf

# === 4. Docker_image ===
echo "KRONOS_PROGRESS: 4/10 下载 docker 镜像"
VERSION=$(grep PRETTY_NAME /etc/os-release | awk -F '"' '{print $2}' | sed 's/[()]//g;s/ /-/g')
wget -q "http://121.36.84.172/repo.openeuler.org/${VERSION}/docker_img/${VERSION}-update.json" -O /tmp/docker-update.json
UPDATE_VER=$(cat /tmp/docker-update.json | grep dir | grep "[0-9]" | grep -v test | grep -v round | awk -F '"' '{print $4}' | awk -F "/" '{print $1}' | sort | uniq | tail -n 1)
ARCH=$(uname -i)
DOCKER_IMG_URL="http://121.36.84.172/repo.openeuler.org/${VERSION}/docker_img/${UPDATE_VER}/${ARCH}/openEuler-docker.${ARCH}.tar.xz"
wget -q "${DOCKER_IMG_URL}" -O /tmp/openEuler-docker.tar.xz

# === 5. Load_docker (use /bin/bash, change to /sbin/init later) ===
echo "KRONOS_PROGRESS: 5/10 docker load + 建容器"
IMG_NAME=$(docker load -i /tmp/openEuler-docker.tar.xz | grep "Loaded image" | awk '{print $3}')
docker run -itd --name openEuler_test --privileged -u root "${IMG_NAME}" /bin/bash

# === 6. Fix repos FIRST (before any dnf install inside container) ===
echo "KRONOS_PROGRESS: 6/10 容器内配源 + makecache"
docker exec -i -u root openEuler_test bash -c "rm -rf /etc/yum.repos.d && mkdir -p /etc/yum.repos.d"
if ls /etc/yum.repos.d/*.repo >/dev/null 2>&1; then
  for f in /etc/yum.repos.d/*.repo; do
    docker cp "$f" openEuler_test:/etc/yum.repos.d/
  done
else
  echo "ERROR: no .repo files found in /etc/yum.repos.d/" >&2
  exit 1
fi
docker exec -i -u root openEuler_test bash -c "dnf clean all; dnf makecache"

# === 7. Install deps in container ===
echo "KRONOS_PROGRESS: 7/10 容器内装依赖 (sudo/passwd/systemd/openssh/git)"
docker exec -i -u root openEuler_test bash -c "dnf install -y sudo passwd systemd openssh git iproute; ldconfig"
docker exec -i -u root openEuler_test bash -c "printf 'openEuler12#$\nopenEuler12#$\n' | passwd"
# Verify /sbin/init exists (systemd version varies across openEuler releases;
# the container start verification in step 9 catches broken systemd)
docker exec -i -u root openEuler_test bash -c "test -e /sbin/init" || {
  echo "ERROR: /sbin/init missing after dnf install" >&2
  exit 1
}

# === 8. Change entrypoint to /sbin/init ===
echo "KRONOS_PROGRESS: 8/10 改 entrypoint 为 /sbin/init"
CONTAINER_ID=$(docker ps -a | grep openEuler_test | awk '{print $1}')
CONTAINER_PATH=$(ls /var/lib/docker/containers | grep "${CONTAINER_ID}")
docker stop openEuler_test
systemctl stop docker
sed -i 's#/bin/bash#/sbin/init#g' /var/lib/docker/containers/${CONTAINER_PATH}/config.v2.json

# === 9. Start docker, clone mugen, configure container ===
echo "KRONOS_PROGRESS: 9/10 启动容器 + clone mugen + 配置"
systemctl start docker
docker start openEuler_test
sleep 2
# Verify container is running with /sbin/init (exits 127 if systemd libs broken)
if ! docker exec openEuler_test echo "container running"; then
  echo "ERROR: container failed to start with /sbin/init" >&2
  docker logs openEuler_test 2>&1 | tail -5 >&2
  exit 1
fi

git clone --depth=1 https://atomgit.com/openeuler/mugen.git /tmp/mugen
# pin mugen 到 TestJob 建时冻结的 sha,与其它 5 个模块 prepare_mugen 的 fetch+checkout
# 契约一致;不 pin 会静默跟 master tip 漂移,上游 breaking 直接击穿本次触发
# (ref: mugen 上游 eb987747b 2026-09-02 shellcheck 修复把 deploy_conf
# "${*//-c/}" 加引号破坏 word split)
if [ -z "${KRONOS_MUGEN_COMMIT_SHA:-}" ]; then
  echo "ERROR: KRONOS_MUGEN_COMMIT_SHA 未设置;拒绝用 master tip 跑 mugen" >&2
  exit 1
fi
cd /tmp/mugen
if ! git fetch --depth=1 origin "$KRONOS_MUGEN_COMMIT_SHA"; then
  echo "ERROR: 无法 fetch mugen_commit_sha=$KRONOS_MUGEN_COMMIT_SHA,拒绝降级到 master tip" >&2
  exit 1
fi
if ! git checkout "$KRONOS_MUGEN_COMMIT_SHA"; then
  echo "ERROR: 无法 checkout mugen_commit_sha=$KRONOS_MUGEN_COMMIT_SHA" >&2
  exit 1
fi
cd -
docker cp /tmp/mugen openEuler_test:/home/

# Enable IPv6
docker exec -i -u root openEuler_test bash -c "sysctl -w net.ipv6.conf.all.disable_ipv6=0"

# dnf check-update + docker.log
docker exec -u root openEuler_test bash -c 'dnf check-update | tee /home/check_update.log; check_code=${PIPESTATUS[0]}; if [[ $check_code == 100 ]]; then exit 0; else echo "nothing to do" > /home/check_update.log; exit 0; fi'
docker exec openEuler_test bash -c 'dnf list | grep @System > /home/docker.log' 2>/dev/null || true

# Remove non-docker-compatible cases from smoke.json
docker exec -i -u root openEuler_test bash -c "sed -i '7,9d' /home/mugen/suite2cases/smoke.json"

# === 10. dep_install + mugen.sh -c ===
echo "KRONOS_PROGRESS: 10/10 dep_install + mugen -c"
docker exec -i -u root openEuler_test bash -c "mkdir -p ~/.pip && echo -e '[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple' > ~/.pip/pip.conf"
docker exec -i -u root openEuler_test bash -c "cd /home/mugen && bash dep_install.sh"
CONTAINER_IP=$(docker exec -i openEuler_test ip addr show | grep inet | grep -v inet6 | grep -Ewv "lo.*|docker.*|vlan.*|bond.*|virbr.*|br-.*" | awk '{print $2}' | awk -F "/" '{print $1}' | head -1)
docker exec -i -u root openEuler_test bash -c "cd /home/mugen && bash mugen.sh -c --ip ${CONTAINER_IP} --password 'openEuler12#$' --user root"
"""


DOCKER_MUGEN_EXEC = (
    "docker exec -u root openEuler_test bash -c "
    "'cd /home/mugen && bash mugen.sh -f {suite} -r {case} -x'"
)

DOCKER_POST_ENV = r"""#!/bin/bash
export LANG="en_US.UTF-8"
mkdir -p /opt/docker-logs

# Ensure dirs exist in container before copying
docker exec openEuler_test mkdir -p /home/mugen/logs /home/mugen/results 2>/dev/null || true

# Copy mugen logs and results from container
docker cp openEuler_test:/home/mugen/logs /opt/docker-logs/logs 2>/dev/null || true
docker cp openEuler_test:/home/mugen/results /opt/docker-logs/results 2>/dev/null || true
docker cp openEuler_test:/home/check_update.log /opt/docker-logs/check_update.log 2>/dev/null || true
docker cp openEuler_test:/home/docker.log /opt/docker-logs/docker.log 2>/dev/null || true
"""

DOCKER_RERUN_ENV = r"""#!/bin/bash
set -Eeuo pipefail
export LANG="en_US.UTF-8"
docker restart openEuler_test
for _ in $(seq 1 30); do
    test "$(docker inspect -f '{{.State.Running}}' openEuler_test 2>/dev/null)" = "true" && break
    sleep 2
done
test "$(docker inspect -f '{{.State.Running}}' openEuler_test 2>/dev/null)" = "true"
"""



# --- kernel module ---

KERNEL_PRE_ENV = r"""#!/bin/bash
set -Eeuo pipefail
export LANG="en_US.UTF-8"
export LTP_TIMEOUT_MUL=5
""" + UPDATE_REPO_SETUP + r"""

# Kernel module setup (all non-fatal — kernel paths may not exist on all versions)
modprobe vsock_loopback 2>/dev/null || true
echo 1024 > /proc/dirty/buffer_size 2>/dev/null || true
echo NO_RUN_TO_PARITY_WAKEUP > /sys/kernel/debug/sched/features 2>/dev/null || true
systemctl start irqbalance 2>/dev/null || true
setenforce 1 2>/dev/null || true

# Persist systemd journal so machine-side evidence (panic/OOM/sshd) survives
# mid-run reboots during case execution (PXE base image has volatile journal)
mkdir -p /var/log/journal 2>/dev/null || true
systemd-tmpfiles --create --prefix /var/log/journal 2>/dev/null || true
systemctl try-restart systemd-journald 2>/dev/null || true

# Patch cpufreq_boost for cppc_cpufreq (aarch64 only)
ARCH=$(uname -m)
if [[ "${ARCH}" == "aarch64" ]]; then
    CPUFREQ_FILE=$(find ${OET_PATH} -name cpufreq_boost.c 2>/dev/null | head -1)
    if [[ -n "${CPUFREQ_FILE}" ]]; then
        sed -i '/intel_pstate/a \        { "cppc_cpufreq", 0, "1", "0", SYSFS_CPU_DIR "cpufreq/boost" },' "${CPUFREQ_FILE}" || true
    fi
fi

# Patch LTP test to not remove /opt/ltp
LTP_SCRIPT="${OET_PATH}/testcases/system-test/ltp-test/oe_test_ltp.sh"
if [[ -f "${LTP_SCRIPT}" ]]; then
    sed -i '/rm -rf.*\/opt\/ltp/d' "${LTP_SCRIPT}" || true
fi
"""

KERNEL_POST_ENV = r"""#!/bin/bash
set -Eeuo pipefail
mkdir -p /opt/kernel-logs

# Copy LTP results
BACK_DIR="/tmp/ltp_results"
mkdir -p "${BACK_DIR}"
if [[ -d /opt/ltp ]]; then
    cp -r /opt/ltp "${BACK_DIR}/" 2>/dev/null || true
fi

# Extract failed cases from LTP results
if ls "${BACK_DIR}/ltp/results/"*.log >/dev/null 2>&1; then
    awk '/FAIL/ {print $1}' "${BACK_DIR}/ltp/results/"*.log > /opt/kernel-logs/kernel_failed_cases.log
fi

# Copy mugen logs and results
cp -r ${OET_PATH}/logs /opt/kernel-logs/ 2>/dev/null || true
cp -r ${OET_PATH}/results /opt/kernel-logs/ 2>/dev/null || true
cp "${BACK_DIR}/ltp/ltp.txt" /opt/kernel-logs/ltp.txt 2>/dev/null || true
cp -r "${BACK_DIR}/ltp/results" /opt/kernel-logs/ltp_results 2>/dev/null || true
"""

# --- pkgcmd module ---

PKGCMD_PRE_ENV = r"""#!/bin/bash
set -Eeuo pipefail
export LANG="en_US.UTF-8"
""" + UPDATE_REPO_SETUP + r"""

mount --make-rshared /
sysctl -w kernel.unprivileged_userns_clone=1 2>/dev/null || true
dnf install -y polkit
"""

PKGCMD_POST_ENV = r"""#!/bin/bash
set -Eeuo pipefail
mkdir -p /opt/pkgcmd-logs

# pkgcmd.log is generated per-case by the mugen_runner (not here) —
# mugen.sh overwrites results between runs, so per-case collection is needed.
# Here we only copy mugen logs + results for browsing.

cp -r ${OET_PATH}/logs /opt/pkgcmd-logs/logs 2>/dev/null || true
cp -r ${OET_PATH}/results /opt/pkgcmd-logs/results 2>/dev/null || true
""" + RESTORE_SSH_ACCESS


# --- pkgmanage module ---

PKGMANAGE_PRE_ENV = r"""#!/bin/bash
set -Eeuo pipefail
export LANG="en_US.UTF-8"
""" + UPDATE_REPO_SETUP + r"""

ARCH=$(uname -m)
if [[ "${ARCH}" == "aarch64" ]]; then
    yum install -y edk2-aarch64 edk2-ovmf 2>/dev/null || true
fi
"""

PKGMANAGE_POST_ENV = r"""#!/bin/bash
set -Eeuo pipefail
mkdir -p /opt/pkgmanage-logs

CASE=$(printf "%02d" "${KRONOS_ENV_SET_INDEX}")
FILE_PATH="/opt/pkgmanage-logs/pkgmanage-details.log"

{
    printf "%.0s-" $(seq 1 80) && echo
    echo -e "\n${KRONOS_OS_VERSION}-${KRONOS_ARCH}-pkgmanage-0${CASE}"
    # 两架构包数检查结果（有差异才出，无差异不出）：
    #   - 差异不在白名单（ERROR）→ "not equal in number"
    #   - 差异在白名单（INFO All diff packages in whitelist）→ "diff in whitelist, pass"
    if grep -q 'ERROR -.*two architectures' ${OET_PATH}/logs/pkgmanager-test/oe_test_pkg_manager0${CASE}/*.log 2>/dev/null; then
        echo "== two architectures are not equal in number"
    elif grep -q 'All diff packages in whitelist' ${OET_PATH}/logs/pkgmanager-test/oe_test_pkg_manager0${CASE}/*.log 2>/dev/null; then
        echo "== two architectures diff in whitelist, pass"
    fi
    cat ${OET_PATH}/logs/pkgmanager-test/oe_test_pkg_manager0${CASE}/*.log 2>/dev/null | grep "test -n" | sed 's/^/    /g' || true
    echo -e "\n"
} >> "${FILE_PATH}"

# Collect fail_list files (matches lkp-tests mugen-oeupdate-pkgmanage)
DIR_PATH="/home/pkg_manager_folder"
all_contents=""
file_list=$(find "${DIR_PATH}" -maxdepth 1 -type f -name "*fail_list" 2>/dev/null | sort)

if [[ -z "${file_list}" ]]; then
    echo -e "    no fail_list\n" >> "${FILE_PATH}"
else
    {
        while IFS= read -r fail_file; do
            filename=$(basename "${fail_file}")
            file_prefix=${filename%_fail_list}

            echo "    ${file_prefix}:"
            cat "${fail_file}" | sed 's/^/        /g'

            file_content=$(cat "${fail_file}" | tr '\n' ' ')
            all_contents+="${file_content}"
        done <<< "${file_list}"

        echo -e "\n    ${all_contents}"
    } >> "${FILE_PATH}"
fi

# Copy pkg_manager_folder for collection
if [[ -d "${DIR_PATH}" ]]; then
    cp -r "${DIR_PATH}" "/opt/pkgmanage-logs/pkg_manager_folder-0${CASE}"
fi

# Copy mugen logs and results
cp -r ${OET_PATH}/logs /opt/pkgmanage-logs/logs 2>/dev/null || true
cp -r ${OET_PATH}/results /opt/pkgmanage-logs/results 2>/dev/null || true
""" + RESTORE_SSH_ACCESS

# --- pkgserver module ---

PKGSERVER_PRE_ENV = r"""#!/bin/bash
export LANG="en_US.UTF-8"

# Source mugen libraries (NOT designed for set -u/-e; mugen cases don't use strict mode)
source "${OET_PATH}/libs/locallibs/common_lib.sh"
source "${OET_PATH}/libs/locallibs/configure_repo.sh"
source "${OET_PATH}/testcases/system-test/service-test/common/common_lib.sh"
source "${OET_PATH}/testcases/cli-test/common/common_lib.sh"

# Work from /opt/pkgserver-logs/ so all analysis files land there
LOG_DIR="/opt/pkgserver-logs"
mkdir -p "${LOG_DIR}"
cd "${LOG_DIR}"

# 1. Configure repos (same as package_install but without installing everything)
rm -rf /etc/yum.repos.d/*
cfg_openEuler_repo
cfg_openEuler_update_test_repo

# 2. Generate update_list (full package list for analysis)
dnf list | grep "${version_info}_${test_update_repo}" | grep "arch\|x86_64" | awk '{print $1}' | awk -F. 'OFS="."{$NF="";print}' | awk '{print substr($0, 1, length($0)-1)}' > update_list

# 3. Install ONLY the packages we need to test (from builder repodata discovery)
#    KRONOS_TEST_PACKAGES is injected via kronos.env by the builder.
if [ -n "${KRONOS_TEST_PACKAGES:-}" ]; then
    echo "Installing test packages: ${KRONOS_TEST_PACKAGES}" > install_log
    for pkg in ${KRONOS_TEST_PACKAGES}; do
        echo "Installing ${pkg}..." >> install_log
        yum install -y "${pkg}" >> install_log 2>&1 || echo "${pkg}" >> failed_install
    done
else
    echo "KRONOS_TEST_PACKAGES not set, installing all update packages" >> install_log
    while read -r pkg; do
        yum install -y "${pkg}" >> install_log 2>&1 || echo "${pkg}" >> failed_install
    done < update_list
fi

# 4. Find systemd services from installed packages
: > all_services
if [ -s failed_install ]; then
    # Search only successfully installed packages
    while read -r package; do
        rpm -ql "${package}" 2>/dev/null | grep "/lib/systemd/system/" | grep -v "@" | grep -E "\.service$|\.target$|\.socket$" | awk -F '/' '{print $NF}' >> all_services
    done < <(comm -23 <(sort update_list) <(sort failed_install))
else
    while read -r package; do
        rpm -ql "${package}" 2>/dev/null | grep "/lib/systemd/system/" | grep -v "@" | grep -E "\.service$|\.target$|\.socket$" | awk -F '/' '{print $NF}' >> all_services
    done < update_list
fi

# 5. Classify services (generates new_service, adapted_service, json_file)
select_services

# 6. Test services without dedicated mugen cases
{
    if [ -s new_service ]; then
        while read -r service; do
            check_new_service "${service}"
        done < new_service
    else
        echo "No new_service to test"
    fi
} > new_service_test.log 2>&1 || true
"""

PKGSERVER_POST_ENV = r"""#!/bin/bash

source "${OET_PATH}/libs/locallibs/common_lib.sh"
source "${OET_PATH}/libs/locallibs/configure_repo.sh"
source "${OET_PATH}/testcases/system-test/service-test/common/common_lib.sh"

LOG_DIR="/opt/pkgserver-logs"
cd "${LOG_DIR}"

# 1. Clean up: stop services + remove packages (generates remove_log).
#    This mirrors mugen's oe_test_service_restart.sh post_test() — the removal
#    is part of the full test action, not just cleanup.
clean_up_env

# 1.5. Restore sshd so the worker can SSH back to collect /opt/pkgserver-logs/*.
#      clean_up_env does yum remove -y on ALL update packages incl. openssh-server,
#      which removes the sshd binary. Reinstall + restart so _self_collect_logs
#      (tasks.py) can pull logs. This does NOT affect test results or remove_log.
yum install -y openssh-server >/dev/null 2>&1 || true
systemctl restart sshd 2>/dev/null || true

# 2. Generate pkgserver-details.log: scan ALL result suites (not just service-test)
: > pkgserver-details.log
{
    printf "%.0s-" $(seq 1 80) && echo
    echo -e "\npkgserver\n"
    for suite_dir in "${OET_PATH}"/results/*/; do
        [ -d "${suite_dir}" ] || continue
        suite=$(basename "${suite_dir}")
        echo "=== ${suite} ==="
        echo "failed:"
        if [ -d "${suite_dir}failed" ] && [ -n "$(ls -A "${suite_dir}failed" 2>/dev/null)" ]; then
            ls -1 "${suite_dir}failed" | sed 's/^/    /'
        else
            echo "    none"
        fi
        echo "skipped:"
        if [ -d "${suite_dir}skipped" ] && [ -n "$(ls -A "${suite_dir}skipped" 2>/dev/null)" ]; then
            ls -1 "${suite_dir}skipped" | sed 's/^/    /'
        else
            echo "    none"
        fi
        echo "succeeded:"
        if [ -d "${suite_dir}succeed" ]; then
            ls -1 "${suite_dir}succeed" 2>/dev/null | sed 's/^/    /' || echo "    none"
        else
            echo "    none"
        fi
        echo ""
    done
} >> pkgserver-details.log

# 3. Copy mugen logs and results
cp -r ${OET_PATH}/logs /opt/pkgserver-logs/logs 2>/dev/null || true
cp -r ${OET_PATH}/results /opt/pkgserver-logs/results 2>/dev/null || true
""" + RESTORE_SSH_ACCESS


# --- pkgunion module ---
# pkgcmd + pkgserver 的用例并集模块（case_filter=repodata_union，builder 按
# (suite, case) 去重两路解析结果）。与两老模块的差异：换源后全量更新
# （dnf update -y，fail-fast；不 reboot——运行旧内核+新 userland，最新内核由
# kernel 模块在物理机单独覆盖），并保留 pkgserver 全套服务语义
# （check_new_service 冒烟 + clean_up_env 卸载，卸载是服务测试动作的一部分）。
# 无 set -Eeuo pipefail：mugen 库函数不兼容 strict mode（同 PKGSERVER_PRE_ENV），
# 关键步骤（makecache / dnf update）显式 fail-fast。

PKGUNION_PRE_ENV = r"""#!/bin/bash
export LANG="en_US.UTF-8"
""" + UPDATE_REPO_SETUP + r"""

# Full system update to the latest round (fail-fast; NO reboot — old kernel +
# new userland is the real-world post-`dnf update` state; latest kernel is
# covered by the kernel module on physical machines).
if ! dnf update -y; then
    echo "dnf update -y failed" >&2
    exit 1
fi

# --- pkgcmd environment bits ---
mount --make-rshared /
sysctl -w kernel.unprivileged_userns_clone=1 2>/dev/null || true
dnf install -y polkit

# --- pkgserver service semantics ---
# Source mugen libraries (NOT designed for set -u/-e; mugen cases don't use strict mode)
source "${OET_PATH}/libs/locallibs/common_lib.sh"
source "${OET_PATH}/libs/locallibs/configure_repo.sh"
source "${OET_PATH}/testcases/system-test/service-test/common/common_lib.sh"
source "${OET_PATH}/testcases/cli-test/common/common_lib.sh"

# Work from /opt/pkgunion-logs/ so all analysis files land there
LOG_DIR="/opt/pkgunion-logs"
mkdir -p "${LOG_DIR}"
cd "${LOG_DIR}"

# 1. Generate update_list (full package list for analysis; repos already
#    configured by UPDATE_REPO_SETUP above, no cfg_* calls needed here)
dnf list | grep "${version_info}_${test_update_repo}" | grep "arch\|x86_64" | awk '{print $1}' | awk -F. 'OFS="."{$NF="";print}' | awk '{print substr($0, 1, length($0)-1)}' > update_list

# 2. Install the test packages (KRONOS_TEST_PACKAGES = repodata + service union,
#    injected via kronos.env by the builder). After dnf update -y this mostly
#    pulls in packages newly added in this update round (no-op if already latest).
if [ -n "${KRONOS_TEST_PACKAGES:-}" ]; then
    echo "Installing test packages: ${KRONOS_TEST_PACKAGES}" > install_log
    for pkg in ${KRONOS_TEST_PACKAGES}; do
        echo "Installing ${pkg}..." >> install_log
        yum install -y "${pkg}" >> install_log 2>&1 || echo "${pkg}" >> failed_install
    done
else
    echo "KRONOS_TEST_PACKAGES not set, installing all update packages" >> install_log
    while read -r pkg; do
        yum install -y "${pkg}" >> install_log 2>&1 || echo "${pkg}" >> failed_install
    done < update_list
fi

# 3. Find systemd services from installed packages
: > all_services
if [ -s failed_install ]; then
    # Search only successfully installed packages
    while read -r package; do
        rpm -ql "${package}" 2>/dev/null | grep "/lib/systemd/system/" | grep -v "@" | grep -E "\.service$|\.target$|\.socket$" | awk -F '/' '{print $NF}' >> all_services
    done < <(comm -23 <(sort update_list) <(sort failed_install))
else
    while read -r package; do
        rpm -ql "${package}" 2>/dev/null | grep "/lib/systemd/system/" | grep -v "@" | grep -E "\.service$|\.target$|\.socket$" | awk -F '/' '{print $NF}' >> all_services
    done < update_list
fi

# 4. Classify services (generates new_service, adapted_service, json_file)
select_services

# 5. Test services without dedicated mugen cases
{
    if [ -s new_service ]; then
        while read -r service; do
            check_new_service "${service}"
        done < new_service
    else
        echo "No new_service to test"
    fi
} > new_service_test.log 2>&1 || true
"""

# PKGUNION_POST_ENV 与 PKGSERVER_POST_ENV 仅模块名不同：单模板派生，防止两份拷贝漂移。
PKGUNION_POST_ENV = PKGSERVER_POST_ENV.replace("pkgserver", "pkgunion")


DEFAULT_TEMPLATES = [
    {
        "name": "docker",
        "display_name": "Docker Update Test",
        "suite_name": "smoke",
        "pipeline_type": "update",
        "env_set_num": 1,
        "node_num": 1,
        "case_filter": "none",
        "env_type": "vm",
        "skip_packages": [],
        "pre_env_script": DOCKER_PRE_ENV,
        "rerun_env_script": DOCKER_RERUN_ENV,
        "post_env_script": DOCKER_POST_ENV,
        "mugen_exec_command": DOCKER_MUGEN_EXEC,
        "result_parser": "mugen_results",
        "test_framework": "mugen",
    },
    {
        "name": "kernel",
        "display_name": "Kernel LTP Test",
        "suite_name": "ltp",
        "pipeline_type": "update",
        "env_set_num": 1,
        "node_num": 1,
        "case_filter": "none",
        "env_type": "physical",
        "skip_packages": [],
        "pre_env_script": KERNEL_PRE_ENV,
        "rerun_env_script": "",
        "post_env_script": KERNEL_POST_ENV,
        "result_parser": "ltp",
        "test_framework": "mugen",
    },
    {
        "name": "pkgcmd",
        "display_name": "Package Command Test",
        "suite_name": "cli-test",
        "pipeline_type": "update",
        "env_set_num": 1,
        "node_num": 1,
        "case_filter": "repodata_packages",
        "env_type": "both",
        "skip_packages": [],
        "pre_env_script": PKGCMD_PRE_ENV,
        "rerun_env_script": "",
        "post_env_script": PKGCMD_POST_ENV,
        "result_parser": "pkgcmd",
        "test_framework": "mugen",
    },
    {
        "name": "pkgmanage",
        "display_name": "Package Manager Test",
        "suite_name": "pkgmanager-test",
        "pipeline_type": "update",
        "env_set_num": 2,
        "node_num": 2,
        "case_filter": "none",
        "env_type": "vm",
        "skip_packages": [],
        "pre_env_script": PKGMANAGE_PRE_ENV,
        "rerun_env_script": "",
        "post_env_script": PKGMANAGE_POST_ENV,
        "result_parser": "pkgmanage",
        "test_framework": "mugen",
    },
    {
        "name": "pkgserver",
        "display_name": "Service Test",
        "suite_name": "service-test",
        "pipeline_type": "update",
        "env_set_num": 1,
        "node_num": 1,
        "case_filter": "service_test_cases",
        "env_type": "both",
        "skip_packages": [],
        "pre_env_script": PKGSERVER_PRE_ENV,
        "rerun_env_script": "",
        "post_env_script": PKGSERVER_POST_ENV,
        "result_parser": "pkgserver",
        "test_framework": "mugen",
    },
    {
        "name": "pkgunion",
        "display_name": "Package Union Test",
        "suite_name": "cli-test",
        "pipeline_type": "update",
        "env_set_num": 1,
        "node_num": 1,
        "case_filter": "repodata_union",
        "env_type": "both",
        "skip_packages": [],
        "pre_env_script": PKGUNION_PRE_ENV,
        "rerun_env_script": "",
        "post_env_script": PKGUNION_POST_ENV,
        "result_parser": "pkgunion",
        "test_framework": "mugen",
    },
]


def seed_module_templates(db: Session) -> int:
    created = 0
    for tmpl_data in DEFAULT_TEMPLATES:
        existing = db.execute(
            select(TestModuleTemplate).where(
                TestModuleTemplate.name == tmpl_data["name"]
            )
        ).scalar_one_or_none()
        if existing is not None:
            # Update scripts on existing templates
            for key, value in tmpl_data.items():
                if key != "name":
                    setattr(existing, key, value)
            continue
        db.add(TestModuleTemplate(**tmpl_data))
        created += 1
    db.commit()
    return created
