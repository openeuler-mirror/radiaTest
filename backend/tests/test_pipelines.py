# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.test_management.models import TestCaseRunDetail, TestLogArtifact


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


def test_create_module_template(db_session: Session) -> None:
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker Update Test",
        suite_name="smoke",
        env_set_num=1,
        node_num=1,
        case_filter="none",
        env_type="vm",
        skip_packages=[],
        pre_env_script="echo prepare",
        post_env_script="echo cleanup",
        result_parser="docker",
    )
    db_session.add(template)
    db_session.commit()

    result = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "docker")
    ).scalar_one()

    assert result.id is not None
    assert result.name == "docker"
    assert result.display_name == "Docker Update Test"
    assert result.suite_name == "smoke"
    assert result.env_set_num == 1
    assert result.node_num == 1
    assert result.case_filter == "none"
    assert result.env_type == "vm"
    assert result.skip_packages == []
    assert result.pre_env_script == "echo prepare"
    assert result.post_env_script == "echo cleanup"
    assert result.result_parser == "docker"
    assert result.created_at is not None
    assert result.updated_at is not None


def test_create_module_template_pkgmanage_config(db_session: Session) -> None:
    template = TestModuleTemplate(
        name="pkgmanage",
        display_name="Package Manager Test",
        suite_name="pkgmanager-test",
        env_set_num=2,
        node_num=2,
        case_filter="none",
        env_type="vm",
        skip_packages=[],
        pre_env_script="",
        post_env_script="",
        result_parser="pkgmanage",
    )
    db_session.add(template)
    db_session.commit()

    result = db_session.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == "pkgmanage")
    ).scalar_one()

    assert result.env_set_num == 2
    assert result.node_num == 2


def test_create_pipeline_config(db_session: Session) -> None:
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    db_session.add(template)
    db_session.commit()

    config = PipelineConfig(
        name="openEuler Update Weekly",
        versions=["24.03-LTS-SP3", "22.03-LTS-SP4"],
        archs=["aarch64", "x86_64"],
        config_data={"module_template_ids": [template.id], "repo_base_url": "http://121.36.84.172/repo.openeuler.org"},
    )
    db_session.add(config)
    db_session.commit()

    result = db_session.execute(
        select(PipelineConfig).where(PipelineConfig.name == "openEuler Update Weekly")
    ).scalar_one()

    assert result.id is not None
    assert result.name == "openEuler Update Weekly"
    assert result.config_data["module_template_ids"] == [template.id]
    assert result.versions == ["24.03-LTS-SP3", "22.03-LTS-SP4"]
    assert result.archs == ["aarch64", "x86_64"]
    assert result.config_data["repo_base_url"] == "http://121.36.84.172/repo.openeuler.org"


def test_create_pipeline_run(db_session: Session) -> None:
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add(config)
    db_session.commit()

    run = PipelineRun(
        config_id=config.id,
        version="24.03-LTS-SP3",
        status="running",
        triggered_by="admin",
    )
    db_session.add(run)
    db_session.commit()

    result = db_session.execute(
        select(PipelineRun).where(PipelineRun.version == "24.03-LTS-SP3")
    ).scalar_one()

    assert result.id is not None
    assert result.config_id == config.id
    assert result.version == "24.03-LTS-SP3"
    assert result.status == "running"
    assert result.triggered_by == "admin"
    assert result.triggered_at is not None
    assert result.completed_at is None


def test_create_pipeline_run_job(db_session: Session) -> None:
    template = TestModuleTemplate(name="kernel", display_name="Kernel", suite_name="ltp")
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add_all([template, config])
    db_session.commit()

    run = PipelineRun(
        config_id=config.id, version="24.03-LTS-SP3", status="running", triggered_by="admin"
    )
    db_session.add(run)
    db_session.commit()

    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="aarch64",
        env_type="vm",
        test_job_id=None,
        status="pending",
    )
    db_session.add(run_job)
    db_session.commit()

    result = db_session.execute(
        select(PipelineRunJob).where(PipelineRunJob.arch == "aarch64")
    ).scalar_one()

    assert result.id is not None
    assert result.pipeline_run_id == run.id
    assert result.module_template_id == template.id
    assert result.arch == "aarch64"
    assert result.env_type == "vm"
    assert result.test_job_id is None
    assert result.status == "pending"


def test_create_case_run_detail(db_session: Session) -> None:
    detail = TestCaseRunDetail(
        case_run_id="case-run-001",
        sub_test_name="syscalls_01",
        status="passed",
        detail={"duration": 1.5},
    )
    db_session.add(detail)
    db_session.commit()

    result = db_session.execute(
        select(TestCaseRunDetail).where(TestCaseRunDetail.sub_test_name == "syscalls_01")
    ).scalar_one()

    assert result.id is not None
    assert result.case_run_id == "case-run-001"
    assert result.sub_test_name == "syscalls_01"
    assert result.status == "passed"
    assert result.detail == {"duration": 1.5}


def test_create_log_artifact(db_session: Session) -> None:
    artifact = TestLogArtifact(
        job_id="job-001",
        module="kernel",
        arch="aarch64",
        artifact_type="auxiliary",
        artifact_name="ltp.log",
        storage_path="/data/test-logs/pipeline-001/kernel/aarch64/ltp.log",
    )
    db_session.add(artifact)
    db_session.commit()

    result = db_session.execute(
        select(TestLogArtifact).where(TestLogArtifact.artifact_name == "ltp.log")
    ).scalar_one()

    assert result.id is not None
    assert result.job_id == "job-001"
    assert result.module == "kernel"
    assert result.arch == "aarch64"
    assert result.artifact_type == "auxiliary"
    assert result.artifact_name == "ltp.log"
    assert result.storage_path == "/data/test-logs/pipeline-001/kernel/aarch64/ltp.log"
