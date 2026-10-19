# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.pipelines.models import PipelineType, TestModuleTemplate
from app.modules.pipelines.seed import seed_module_templates, seed_pipeline_types


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


def test_seed_creates_six_templates(db_session: Session) -> None:
    created = seed_module_templates(db_session)

    assert created == 6

    names = list(
        db_session.execute(
            select(TestModuleTemplate.name).order_by(TestModuleTemplate.name)
        ).scalars().all()
    )
    assert names == [
        "docker",
        "kernel",
        "pkgcmd",
        "pkgmanage",
        "pkgserver",
        "pkgunion",
    ]


def test_seed_is_idempotent(db_session: Session) -> None:
    seed_module_templates(db_session)
    created = seed_module_templates(db_session)

    assert created == 0


def test_seed_pkgmanage_has_correct_config(db_session: Session) -> None:
    seed_module_templates(db_session)

    pkgmanage = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "pkgmanage")
    ).scalar_one()

    assert pkgmanage.env_set_num == 2
    assert pkgmanage.node_num == 2


def test_seed_pkgcmd_env_type_both(db_session: Session) -> None:
    seed_module_templates(db_session)

    pkgcmd = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "pkgcmd")
    ).scalar_one()

    assert pkgcmd.env_type == "both"
    assert pkgcmd.case_filter == "repodata_packages"


def test_seed_pkgunion_has_correct_config(db_session: Session) -> None:
    """pkgunion：repodata_union 并集筛选 + pre_env 全量更新（换源后 dnf update -y，
    fail-fast 不 reboot）+ pkgserver 全套服务语义（check_new_service / clean_up_env）。
    """
    seed_module_templates(db_session)

    pkgunion = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "pkgunion")
    ).scalar_one()

    assert pkgunion.env_type == "both"
    assert pkgunion.case_filter == "repodata_union"
    assert pkgunion.result_parser == "pkgunion"
    # pre_env：换源 → 全量更新（fail-fast）→ pkgcmd 环境位 → 服务发现 + 冒烟
    assert "dnf update -y" in pkgunion.pre_env_script
    assert "dnf makecache" in pkgunion.pre_env_script  # UPDATE_REPO_SETUP 内嵌
    assert "mount --make-rshared /" in pkgunion.pre_env_script
    assert "dnf install -y polkit" in pkgunion.pre_env_script
    assert "check_new_service" in pkgunion.pre_env_script
    # post_env：卸载是服务测试动作的一部分 + 恢复 sshd 供自汇集
    assert "clean_up_env" in pkgunion.post_env_script
    assert "openssh-server" in pkgunion.post_env_script
    assert "pkgunion-details.log" in pkgunion.post_env_script


def test_seed_docker_has_local_rerun_hook(db_session: Session) -> None:
    seed_module_templates(db_session)

    docker = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "docker")
    ).scalar_one()

    assert 'export LANG="en_US.UTF-8"' in docker.rerun_env_script
    assert "docker restart openEuler_test" in docker.rerun_env_script
    assert "systemctl restart docker" not in docker.rerun_env_script


def test_seed_docker_pre_env_pins_mugen_commit_sha_with_fail_loud_guard(
    db_session: Session,
) -> None:
    """DOCKER pre_env 必须 fetch+checkout 到 `$KRONOS_MUGEN_COMMIT_SHA`
    (来自 cronos.env, 与 test_job.mugen_commit_sha 冻结契约一致),且失败
    显式 exit 1 —— 不能像以前那样静默 fall through 到 master tip 造成
    mugen 上游 breaking 直接击穿 (ref: mugen PR#5415/eb987747b shellcheck
    修复把 deploy_conf "\${*//-c/}" 加引号破坏 word split)。
    """
    seed_module_templates(db_session)

    docker = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "docker")
    ).scalar_one()

    assert 'git fetch --depth=1 origin "$KRONOS_MUGEN_COMMIT_SHA"' in docker.pre_env_script
    assert 'git checkout "$KRONOS_MUGEN_COMMIT_SHA"' in docker.pre_env_script
    # pin 失败必须显式挂,而不是继续跑未 pin 的 master tip
    assert "exit 1" in docker.pre_env_script


def test_seed_docker_pre_env_drops_global_sed_on_mugen_sh(db_session: Session) -> None:
    """删除历史遗留的全局 `sed 's#< <(#<<<\\$(#g' /home/mugen/mugen.sh`;
    modern bash ≥4 支持 process substitution; pin 到 mugen_commit_sha 后
    mugen 语法合法, 保留 sed 只会静默破坏 run_one_case/run_all_cases/build_all
    里 3 处 mapfile 语义。
    """
    seed_module_templates(db_session)

    docker = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "docker")
    ).scalar_one()

    assert "s#< <(#<<<" not in docker.pre_env_script


def test_seed_kernel_pre_env_enables_persistent_journal(db_session: Session) -> None:
    """kernel pre_env 必须开启 journald 持久化(/var/log/journal)：PXE 重装
    后的易失 journal 会让 LTP 中途 reboot/挂死时的机器侧日志全部丢失，
    挂死取证无法定界(ref: docs/adr/0042)。pre_env 在换内核重启之后执行，
    恰好覆盖用例执行期。
    """
    seed_module_templates(db_session)

    kernel = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "kernel")
    ).scalar_one()

    assert "mkdir -p /var/log/journal" in kernel.pre_env_script
    assert "systemctl try-restart systemd-journald" in kernel.pre_env_script


def test_seed_creates_two_pipeline_types(db_session: Session) -> None:
    created = seed_pipeline_types(db_session)

    assert created == 2

    types = list(
        db_session.execute(
            select(PipelineType).order_by(PipelineType.name)
        ).scalars().all()
    )
    assert [t.name for t in types] == ["release", "update"]

    update_type = next(t for t in types if t.name == "update")
    assert update_type.display_name == "Update 测试流水线"
    assert update_type.strategy_kind == "update_strategy"
    assert update_type.test_framework == "mugen"
    assert update_type.is_system is True
    assert update_type.default_config == {}

    release_type = next(t for t in types if t.name == "release")
    assert release_type.display_name == "Release 测试流水线"
    assert release_type.strategy_kind == "direct_run"
    assert release_type.test_framework == "mugen"
    assert release_type.is_system is True
    assert release_type.default_config == {}


def test_seed_pipeline_types_is_idempotent(db_session: Session) -> None:
    seed_pipeline_types(db_session)
    created = seed_pipeline_types(db_session)

    assert created == 0


def test_seed_pipeline_types_updates_existing_fields(db_session: Session) -> None:
    seed_pipeline_types(db_session)

    # Modify display_name to simulate stale data; re-seed should restore it.
    update_type = db_session.execute(
        select(PipelineType).where(PipelineType.name == "update")
    ).scalar_one()
    update_type.display_name = "stale name"
    db_session.flush()

    created = seed_pipeline_types(db_session)
    assert created == 0  # No new rows created.

    db_session.expunge_all()
    refreshed = db_session.execute(
        select(PipelineType).where(PipelineType.name == "update")
    ).scalar_one()
    assert refreshed.display_name == "Update 测试流水线"
