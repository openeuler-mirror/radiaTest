# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import TestLogArtifact


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


@pytest.fixture()
def collector(tmp_path: Path) -> LogCollector:
    return LogCollector(base_dir=str(tmp_path))


def test_store_artifact_creates_file_and_db_record(
    db_session: Session, collector: LogCollector
) -> None:
    artifact = collector.store_artifact(
        db=db_session,
        pipeline_run_id="run-001",
        job_id="job-001",
        module="kernel",
        arch="aarch64",
        artifact_type="auxiliary",
        artifact_name="ltp.log",
        content="kernel panic output\n",
    )

    assert artifact.id is not None
    assert artifact.module == "kernel"
    assert artifact.arch == "aarch64"
    assert artifact.artifact_name == "ltp.log"
    assert artifact.storage_path is not None
    assert os.path.exists(artifact.storage_path)
    with open(artifact.storage_path) as f:
        assert f.read() == "kernel panic output\n"


def test_store_artifact_path_convention(
    db_session: Session, collector: LogCollector, tmp_path: Path
) -> None:
    artifact = collector.store_artifact(
        db=db_session,
        pipeline_run_id="run-001",
        job_id="job-001",
        module="docker",
        arch="x86_64",
        artifact_type="mugen_logs",
        artifact_name="logs.tar",
        content=b"binary data",
    )

    expected_dir = tmp_path / "run-001" / "docker" / "x86_64"
    assert Path(artifact.storage_path).parent == expected_dir
    assert Path(artifact.storage_path).name == "logs.tar"


def test_store_artifact_list_by_job(
    db_session: Session, collector: LogCollector
) -> None:
    collector.store_artifact(
        db=db_session, pipeline_run_id="run-1", job_id="job-1",
        module="kernel", arch="aarch64",
        artifact_type="auxiliary", artifact_name="ltp.log", content="a",
    )
    collector.store_artifact(
        db=db_session, pipeline_run_id="run-1", job_id="job-1",
        module="kernel", arch="aarch64",
        artifact_type="mugen_results", artifact_name="results.tar", content=b"b",
    )

    artifacts = db_session.execute(
        select(TestLogArtifact).where(TestLogArtifact.job_id == "job-1")
    ).scalars().all()

    assert len(artifacts) == 2
