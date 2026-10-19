# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""流水线执行测试：构建、状态聚合、日志解析、入队、挂起处理及环境切换。"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.leases.models import ResourceLease
from app.modules.pipelines import builder as pipeline_builder
from app.modules.pipelines.builder import build_test_job_for_run_job
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.pipelines.service import (
    PipelineRunJobRerunConflict,
    PipelineRunJobRerunError,
    _execution_status_from_runs,
    _worst_wins_run_status,
    create_run_job_rerun,
    get_case_mugen_log,
    get_execution_summary,
    get_run_job_detail,
    list_run_logs,
    read_run_log_content,
)
from app.modules.resources.models import Resource, ResourceType
from app.modules.tasks.models import TaskEvent
from app.modules.test_management.errors import EnvSetHangError
from app.modules.test_management.frameworks import mugen_runner
from app.modules.test_management.frameworks.mugen_runner import _HeartbeatStats
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import (
    MugenCase,
    TestCaseRun,
    TestCaseRunDetail,
    TestCaseRunStatus,
    TestEnvNode,
    TestEnvSet,
    TestEnvSetStatus,
    TestEnvType,
    TestJob,
)
from app.modules.test_management.remote import RemoteCommandResult
from app.modules.test_management.result_parser import parse_pkgmanage_log


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


def _seed_mugen_case(db, *, suite_name, case_name, env_type="vm", node_num=1):
    db.add(
        MugenCase(
            suite_name=suite_name,
            case_name=case_name,
            env_type=env_type,
            node_num=node_num,
            commit_sha="abc123",
        )
    )
    db.flush()


def test_test_management_does_not_import_pipeline_modules() -> None:
    """Test Job execution must not resolve Pipeline-owned state."""
    test_management_root = Path(__file__).parents[1] / "app/modules/test_management"
    offenders = [
        source.relative_to(test_management_root)
        for source in test_management_root.rglob("*.py")
        if "app.modules.pipelines" in source.read_text(encoding="utf-8")
    ]

    assert offenders == []


def _make_run_job(
    db,
    *,
    template,
    arch="x86_64",
    env_type=None,
    version="24.03-LTS-SP3",
    pipeline_type="update",
):
    config = PipelineConfig(
        name="cfg",
        pipeline_type=pipeline_type,
        versions=[version],
        archs=[arch],
        config_data={"module_template_ids": [template.id], "repo_base_url": "http://example/repo"},
        dist="openEuler",
        image_round="round-9",
    )
    db.add(config)
    db.flush()
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=[version], archs=[arch]
    )
    db.add(execution)
    db.flush()
    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version=version,
        status="pending",
        triggered_by="admin",
    )
    db.add(run)
    db.flush()
    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch=arch,
        env_type=env_type,
        status="pending",
    )
    db.add(run_job)
    db.flush()
    return config, execution, run, run_job


# ---------- parse_pkgmanage_log ----------


def test_parse_pkgmanage_log_fail_list_extracts_failed() -> None:
    log = (
        "-" * 80 + "\n"
        "20.03-LTS-SP4-aarch64-pkgmanage-01\n\n"
        "    + test -n 'some message'\n"
        "\n"
        "    group1:\n"
        "        pkgB\n"
        "        pkgX\n"
    )
    results = {r.sub_test_name: r.status for r in parse_pkgmanage_log(log)}
    assert results == {"pkgB": "failed", "pkgX": "failed"}


def test_parse_pkgmanage_log_no_fail_list_empty() -> None:
    log = "-" * 80 + "\n20.03-LTS-SP4-aarch64-pkgmanage-02\n\n    no fail_list\n"
    results = parse_pkgmanage_log(log)
    assert len(results) == 0


def test_parse_pkgmanage_log_test_n_not_extracted() -> None:
    log = (
        "20.03-LTS-SP4-aarch64-pkgmanage-01\n\n"
        "    + test -n 'The two architectures are not equal'\n"
        "\n"
        "    no fail_list\n"
    )
    results = parse_pkgmanage_log(log)
    assert len(results) == 0


# ---------- worst-wins read-time ----------


def test_worst_wins_run_status() -> None:
    class JobStub:
        def __init__(self, status: str) -> None:
            self.status = status

    assert _worst_wins_run_status([]) == "pending"
    assert _worst_wins_run_status([JobStub("succeeded")]) == "succeeded"
    assert _worst_wins_run_status([JobStub("succeeded"), JobStub("failed")]) == "failed"
    assert _worst_wins_run_status([JobStub("succeeded"), JobStub("error")]) == "error"
    assert _worst_wins_run_status([JobStub("succeeded"), JobStub("running")]) == "running"
    assert _worst_wins_run_status([JobStub("preparing")]) == "running"
    # cancelled 是终态:混入 succeeded 时优先返回 cancelled,不再显示 running。
    assert _worst_wins_run_status([JobStub("succeeded"), JobStub("cancelled")]) == "cancelled"
    assert _worst_wins_run_status([JobStub("failed"), JobStub("cancelled")]) == "cancelled"
    assert _worst_wins_run_status([JobStub("error"), JobStub("cancelled")]) == "error"
    assert _execution_status_from_runs([]) == "pending"
    assert _execution_status_from_runs([{"status": "running"}]) == "running"
    assert _execution_status_from_runs([{"status": "failed"}, {"status": "succeeded"}]) == "failed"
    # Execution 层同规则:cancelled 视为终态并优先于 failed。
    assert _execution_status_from_runs([{"status": "cancelled"}]) == "cancelled"
    assert _execution_status_from_runs(
        [{"status": "succeeded"}, {"status": "cancelled"}]
    ) == "cancelled"
    assert _execution_status_from_runs(
        [{"status": "failed"}, {"status": "cancelled"}]
    ) == "cancelled"


def test_compute_execution_status_cancelled_not_running(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DB 集成:一个 run 的 RunJobs 全部终态且含 cancelled → execution 状态
    `cancelled`(不再返回 `running`)。覆盖 P0-终止后 pipeline 看板显示 bug。
    """

    from app.modules.pipelines.service import compute_execution_status

    template = TestModuleTemplate(name="mod-cancel", display_name="ModCancel", suite_name="s1")
    db_session.add(template)
    db_session.flush()
    _config, execution, run, run_job = _make_run_job(db_session, template=template)

    # 两条 job:一条 succeeded,一条 cancelled;run job 全终态。
    run_job.status = "succeeded"
    second = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        status="cancelled",
        test_job_id=None,
    )
    db_session.add_all([second])
    db_session.commit()

    assert compute_execution_status(db_session, execution) == "cancelled"

    # 未终止的 cancelling 状态仍视为 running(worker 未收敛)。
    second.status = "cancelling"
    db_session.commit()
    assert compute_execution_status(db_session, execution) == "running"

    # 引入 error: error 优先于 cancelled。
    second.status = "cancelled"
    run_job.status = "error"
    db_session.commit()
    assert compute_execution_status(db_session, execution) == "error"


# ---------- get_execution_summary ----------


def test_get_execution_summary_aggregates(db_session: Session) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    # 给 run_job 一个 test_job + case_runs
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="failed",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
    )
    db_session.add(job)
    db_session.flush()
    run_job.test_job_id = job.id
    run_job.status = "failed"
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.flush()
    db_session.add(
        TestCaseRun(job=job, env_set=env_set, suite_name="smoke", case_name="c1", status="passed")
    )
    db_session.add(
        TestCaseRun(job=job, env_set=env_set, suite_name="smoke", case_name="c2", status="failed")
    )
    db_session.add(
        TestCaseRun(job=job, env_set=env_set, suite_name="smoke", case_name="c3", status="skipped")
    )
    db_session.add(
        TestCaseRun(job=job, env_set=env_set, suite_name="smoke", case_name="c4", status="pending")
    )
    db_session.add(
        TestCaseRun(job=job, env_set=env_set, suite_name="smoke", case_name="c5", status="running")
    )
    resource = Resource(
        resource_code="vm-1",
        resource_type=ResourceType.VIRTUAL.value,
        ssh_username="root",
        ssh_password_ciphertext="x",
    )
    db_session.add(resource)
    db_session.flush()
    db_session.add(
        TestEnvNode(
            env_set=env_set,
            node_index=0,
            role="control",
            resource_id=resource.id,
            primary_ip="192.0.2.10",
        )
    )
    db_session.commit()

    summary = get_execution_summary(db_session, execution.id)
    assert summary is not None
    assert summary["status"] == "failed"  # run_job failed → run failed → execution failed
    assert summary["runs"][0]["version"] == "24.03-LTS-SP3"
    job_summary = summary["runs"][0]["jobs"][0]
    assert job_summary["counts"] == {
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "no_case": 0,
        "not_executed": 0,
        "pending": 1,
        "running": 1,
        "error": 0,
        "timeout": 0,
    }
    assert job_summary["nodes"] == [
        {
            "primary_ip": "192.0.2.10",
            "resource_code": "vm-1",
            "role": "control",
            "env_set_index": 1,
            "node_index": 0,
        }
    ]


def test_get_execution_summary_pending_when_no_terminal(db_session: Session) -> None:
    template = TestModuleTemplate(name="kernel", display_name="Kernel", suite_name="ltp")
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    db_session.commit()
    summary = get_execution_summary(db_session, execution.id)
    assert summary["status"] == "running"  # run_job pending → running


def test_get_execution_summary_overlays_only_rerun_cases(db_session: Session) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, execution, run, source = _make_run_job(db_session, template=template)
    source.status = "failed"
    source_job = TestJob(
        creator_user_id="admin",
        name="source",
        status="failed",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version=run.version,
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
    )
    db_session.add(source_job)
    db_session.flush()
    source.test_job_id = source_job.id
    source_env = TestEnvSet(job=source_job, set_index=1, node_num=1)
    db_session.add(source_env)
    db_session.flush()
    rerun_source = TestCaseRun(
        job=source_job,
        env_set=source_env,
        suite_name="smoke",
        case_name="failed-case",
        status="failed",
    )
    untouched = TestCaseRun(
        job=source_job,
        env_set=source_env,
        suite_name="smoke",
        case_name="passed-case",
        status="passed",
    )
    untouched_failed = TestCaseRun(
        job=source_job,
        env_set=source_env,
        suite_name="smoke",
        case_name="untouched-failed-case",
        status="failed",
    )
    db_session.add_all([rerun_source, untouched, untouched_failed])
    db_session.flush()
    rerun_job = TestJob(
        creator_user_id="admin",
        name="rerun",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version=run.version,
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        rerun_source_job_id=source_job.id,
    )
    db_session.add(rerun_job)
    db_session.flush()
    rerun_env = TestEnvSet(job=rerun_job, set_index=1, node_num=1)
    db_session.add(rerun_env)
    db_session.flush()
    db_session.add(
        TestCaseRun(
            job=rerun_job,
            env_set=rerun_env,
            suite_name="smoke",
            case_name="failed-case",
            status="passed",
            rerun_source_case_run_id=rerun_source.id,
            rerun_root_case_run_id=rerun_source.id,
        )
    )
    rerun_run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        test_job_id=rerun_job.id,
        rerun_source_run_job_id=source.id,
        rerun_root_run_job_id=source.id,
        status="succeeded",
    )
    db_session.add(rerun_run_job)
    db_session.commit()

    summary = get_execution_summary(db_session, execution.id)

    assert summary is not None
    assert summary["runs"][0]["jobs"][0]["counts"]["passed"] == 2
    assert summary["runs"][0]["jobs"][0]["counts"]["failed"] == 1

    detail = get_run_job_detail(db_session, rerun_run_job.id)
    assert detail is not None
    assert [item["case_name"] for item in detail["case_runs"]] == ["failed-case"]
    candidates = {item["case_name"]: item for item in detail["rerun_candidates"]}
    assert set(candidates) == {
        "failed-case",
        "passed-case",
        "untouched-failed-case",
    }
    assert candidates["failed-case"]["status"] == "passed"
    assert candidates["failed-case"]["latest_rerun_attempt"] == 1
    assert candidates["untouched-failed-case"]["status"] == "failed"
    assert candidates["untouched-failed-case"]["latest_rerun_attempt"] == 0


def test_get_execution_summary_not_found(db_session: Session) -> None:
    assert get_execution_summary(db_session, "nope") is None


# ---------- get_run_job_detail ----------


def test_get_run_job_detail_structure(db_session: Session) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
    )
    db_session.add(job)
    db_session.flush()
    run_job.test_job_id = job.id
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.flush()
    cr = TestCaseRun(job=job, env_set=env_set, suite_name="smoke", case_name="c1", status="passed")
    db_session.add(cr)
    db_session.commit()
    detail = get_run_job_detail(db_session, run_job.id)
    assert detail is not None
    assert detail["arch"] == "x86_64"
    assert detail["case_runs"][0]["case_name"] == "c1"
    assert detail["case_runs"][0]["sub_cases"] == []


def test_get_run_job_detail_query_count_does_not_scale_with_cases(
    db_session: Session,
) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    job = TestJob(
        creator_user_id="admin",
        name="large-job",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
    )
    db_session.add(job)
    db_session.flush()
    run_job.test_job_id = job.id
    env_set = TestEnvSet(job=job, set_index=1, node_num=1)
    db_session.add(env_set)
    db_session.flush()
    resource = Resource(
        resource_code="large-job-vm",
        resource_type=ResourceType.VIRTUAL.value,
        primary_ip="192.0.2.20",
        ssh_username="root",
        ssh_password_ciphertext="x",
    )
    db_session.add(resource)
    db_session.flush()
    lease = ResourceLease(resource_id=resource.id, user_id="admin", purpose="pipeline")
    db_session.add(lease)
    db_session.flush()
    resource.current_lease_id = lease.id
    db_session.add(
        TestEnvNode(
            env_set=env_set,
            node_index=0,
            role="control",
            status="ready",
            resource_id=resource.id,
            primary_ip=resource.primary_ip,
        )
    )
    case_runs = [
        TestCaseRun(
            job=job,
            env_set=env_set,
            suite_name="smoke",
            case_name=f"case-{index}",
            status="passed",
        )
        for index in range(40)
    ]
    db_session.add_all(case_runs)
    db_session.flush()
    db_session.add_all(
        [
            TestCaseRunDetail(
                case_run_id=case_run.id,
                sub_test_name="sub-test",
                status="passed",
            )
            for case_run in case_runs
        ]
    )
    db_session.commit()
    db_session.expire_all()

    statement_count = 0

    def count_statement(*_args: object) -> None:
        nonlocal statement_count
        statement_count += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        detail = get_run_job_detail(db_session, run_job.id)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert detail is not None
    assert len(detail["case_runs"]) == 40
    assert len(detail["rerun_candidates"]) == 40
    assert statement_count <= 25


def test_create_run_job_rerun_accepts_latest_cases_across_chain(
    db_session: Session,
) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, run, source = _make_run_job(db_session, template=template)
    source.status = "failed"
    job = TestJob(
        creator_user_id="admin",
        name="source",
        status="failed",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
    )
    db_session.add(job)
    db_session.flush()
    source.test_job_id = job.id
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.flush()
    resource = Resource(
        resource_code="rerun-vm-1",
        resource_type=ResourceType.VIRTUAL.value,
        primary_ip="192.0.2.10",
        ssh_username="root",
        ssh_password_ciphertext="x",
    )
    db_session.add(resource)
    db_session.flush()
    lease = ResourceLease(resource_id=resource.id, user_id="admin", purpose="pipeline")
    db_session.add(lease)
    db_session.flush()
    resource.current_lease_id = lease.id
    db_session.add(
        TestEnvNode(
            env_set=env_set,
            node_index=0,
            role="control",
            status="ready",
            resource_id=resource.id,
            primary_ip=resource.primary_ip,
        )
    )
    _seed_mugen_case(db_session, suite_name="smoke", case_name="c1")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="c2")
    failed = TestCaseRun(
        job=job,
        env_set=env_set,
        suite_name="smoke",
        case_name="c1",
        status=TestCaseRunStatus.FAILED.value,
    )
    passed = TestCaseRun(
        job=job,
        env_set=env_set,
        suite_name="smoke",
        case_name="c2",
        status=TestCaseRunStatus.PASSED.value,
    )
    db_session.add_all([failed, passed])
    db_session.flush()
    previous_job = TestJob(
        creator_user_id="admin",
        name="previous-rerun",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        rerun_source_job_id=job.id,
    )
    db_session.add(previous_job)
    db_session.flush()
    previous_env = TestEnvSet(
        job=previous_job,
        set_index=1,
        node_num=1,
        rerun_source_env_set_id=env_set.id,
    )
    db_session.add(previous_env)
    db_session.flush()
    latest_c1 = TestCaseRun(
        job=previous_job,
        env_set=previous_env,
        suite_name="smoke",
        case_name="c1",
        status=TestCaseRunStatus.PASSED.value,
        rerun_source_case_run_id=failed.id,
        rerun_root_case_run_id=failed.id,
    )
    db_session.add(latest_c1)
    previous_run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        env_type="vm",
        test_job_id=previous_job.id,
        rerun_source_run_job_id=source.id,
        rerun_root_run_job_id=source.id,
        status="succeeded",
    )
    db_session.add(previous_run_job)
    db_session.commit()

    env_set.status = TestEnvSetStatus.DESTROYING.value
    db_session.commit()
    with pytest.raises(PipelineRunJobRerunConflict, match="销毁"):
        create_run_job_rerun(
            db_session,
            source_run_job_id=previous_run_job.id,
            case_run_ids=[latest_c1.id],
        )
    env_set.status = TestEnvSetStatus.FAILED.value
    db_session.commit()

    with pytest.raises(PipelineRunJobRerunError, match="latest"):
        create_run_job_rerun(
            db_session,
            source_run_job_id=previous_run_job.id,
            case_run_ids=[failed.id],
        )

    rerun = create_run_job_rerun(
        db_session,
        source_run_job_id=previous_run_job.id,
        case_run_ids=[latest_c1.id, passed.id],
    )

    assert rerun.rerun_source_run_job_id == previous_run_job.id
    assert rerun.rerun_root_run_job_id == source.id
    assert {item["case_run_id"] for item in rerun.rerun_case_selections} == {
        latest_c1.id,
        passed.id,
    }
    assert source.test_job_id == job.id


def test_build_rerun_job_reuses_exact_source_nodes_and_case(
    db_session: Session,
) -> None:
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
        rerun_env_script="restart docker",
    )
    db_session.add(template)
    db_session.flush()
    config, _execution, run, source = _make_run_job(db_session, template=template, env_type="vm")
    source_job = TestJob(
        creator_user_id="admin",
        name="source",
        status="failed",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version=run.version,
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_env=True,
        rerun_env_script="source restart",
    )
    db_session.add(source_job)
    db_session.flush()
    source.test_job_id = source_job.id
    source_env = TestEnvSet(
        job=source_job,
        set_index=2,
        node_num=1,
        env_type="vm",
        add_disk_num=0,
        add_nic_num=0,
    )
    db_session.add(source_env)
    db_session.flush()
    source_node = TestEnvNode(
        env_set=source_env,
        node_index=0,
        role="control",
        status="ready",
        resource_id="resource-1",
        primary_ip="192.0.2.20",
    )
    source_case = TestCaseRun(
        job=source_job,
        env_set=source_env,
        suite_name="smoke",
        case_name="c1",
        status="failed",
    )
    untouched_case = TestCaseRun(
        job=source_job,
        env_set=source_env,
        suite_name="smoke",
        case_name="c2",
        status="passed",
    )
    db_session.add_all([source_node, source_case, untouched_case])
    db_session.flush()
    previous_job = TestJob(
        creator_user_id="admin",
        name="previous-rerun",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version=run.version,
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_env=True,
        rerun_env_script="source restart",
        rerun_source_job_id=source_job.id,
    )
    db_session.add(previous_job)
    db_session.flush()
    previous_env = TestEnvSet(
        job=previous_job,
        set_index=2,
        node_num=1,
        env_type="vm",
        rerun_source_env_set_id=source_env.id,
    )
    db_session.add(previous_env)
    db_session.flush()
    latest_source_case = TestCaseRun(
        job=previous_job,
        env_set=previous_env,
        suite_name="smoke",
        case_name="c1",
        status="passed",
        rerun_source_case_run_id=source_case.id,
        rerun_root_case_run_id=source_case.id,
    )
    db_session.add(latest_source_case)
    db_session.flush()
    previous_run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        env_type="vm",
        test_job_id=previous_job.id,
        rerun_source_run_job_id=source.id,
        rerun_root_run_job_id=source.id,
        status="succeeded",
    )
    db_session.add(previous_run_job)
    db_session.flush()
    rerun = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        env_type="vm",
        rerun_source_run_job_id=previous_run_job.id,
        rerun_root_run_job_id=source.id,
        rerun_case_selections=[
            {"case_run_id": latest_source_case.id},
            {"case_run_id": untouched_case.id},
        ],
    )
    db_session.add(rerun)
    db_session.flush()

    job = build_test_job_for_run_job(
        db_session,
        run_job=rerun,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="user-1",
    )

    assert job.rerun_source_job_id == previous_job.id
    assert job.rerun_env_script == "source restart"
    assert len(job.env_sets) == 1
    assert job.env_sets[0].set_index == 2
    assert job.env_sets[0].rerun_source_env_set_id == source_env.id
    assert job.env_sets[0].nodes[0].resource_id == source_node.resource_id
    assert {item.rerun_source_case_run_id for item in job.case_runs} == {
        latest_source_case.id,
        untouched_case.id,
    }
    assert {item.rerun_root_case_run_id for item in job.case_runs} == {
        source_case.id,
        untouched_case.id,
    }


# ---------- get_case_mugen_log ----------


def _make_run_job_with_case_run(
    db: Session,
    *,
    suite_name: str = "smoke",
    case_name: str = "c1",
    template_name: str = "docker",
) -> tuple:
    template = TestModuleTemplate(
        name=template_name,
        display_name=template_name.capitalize(),
        suite_name="smoke",
    )
    db.add(template)
    db.flush()
    _config, _execution, run, run_job = _make_run_job(db, template=template)
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc123",
        env_set_num=1,
    )
    db.add(job)
    db.flush()
    run_job.test_job_id = job.id
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db.add(env_set)
    db.flush()
    case_run = TestCaseRun(
        job=job,
        env_set=env_set,
        suite_name=suite_name,
        case_name=case_name,
        status="passed",
    )
    db.add(case_run)
    db.commit()
    return run, run_job, job, case_run


def test_get_case_mugen_log_found(db_session: Session, tmp_path: Path) -> None:
    run, run_job, job, case_run = _make_run_job_with_case_run(db_session)
    log_dir = tmp_path / "logs"
    case_log_dir = log_dir / "smoke" / "c1"
    case_log_dir.mkdir(parents=True)
    (case_log_dir / "mugen.log").write_text("mugen test output line1\nline2\n")
    collector = LogCollector(base_dir=str(tmp_path))
    collector.store_dir_artifact(
        db=db_session,
        pipeline_run_id=run.id,
        job_id=job.id,
        module="docker",
        arch="x86_64",
        artifact_type="pkg_folder",
        artifact_name="logs",
        local_dir=str(log_dir),
    )
    db_session.commit()

    result = get_case_mugen_log(db_session, run_job.id, case_run.id)
    assert result is not None
    assert result["content"] == "mugen test output line1\nline2\n"
    assert result["file_path"] == "smoke/c1/mugen.log"
    assert result["files"] == ["smoke/c1/mugen.log"]


def test_get_case_mugen_log_not_found(db_session: Session) -> None:
    _run, run_job, _job, case_run = _make_run_job_with_case_run(db_session)

    result = get_case_mugen_log(db_session, run_job.id, case_run.id)
    assert result is None


# ---------- list / read run logs ----------


def test_list_and_read_run_logs(db_session: Session, tmp_path: Path) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    collector = LogCollector(base_dir=str(tmp_path))
    artifact = collector.store_artifact(
        db=db_session,
        pipeline_run_id=run.id,
        job_id="job1",
        module="docker",
        arch="x86_64",
        artifact_type="module_log",
        artifact_name="smoke.log",
        content="line1\nline2\n",
    )
    db_session.commit()

    logs = list_run_logs(db_session, run.id)
    assert len(logs) == 1
    assert logs[0].artifact_name == "smoke.log"
    content = read_run_log_content(db_session, run.id, artifact.id)
    assert content == "line1\nline2\n"
    assert read_run_log_content(db_session, run.id, "missing") is None
    assert read_run_log_content(db_session, "other-run", artifact.id) is None


def test_read_run_log_truncates_large_content(db_session: Session, tmp_path: Path) -> None:
    template = TestModuleTemplate(name="kernel", display_name="K", suite_name="ltp")
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    big = "x" * (1024 * 1024 + 100)
    collector = LogCollector(base_dir=str(tmp_path))
    artifact = collector.store_artifact(
        db=db_session,
        pipeline_run_id=run.id,
        job_id="job1",
        module="kernel",
        arch="x86_64",
        artifact_type="module_log",
        artifact_name="ltp.log",
        content=big,
    )
    db_session.commit()
    content = read_run_log_content(db_session, run.id, artifact.id)
    assert "truncated" in content
    assert len(content) < len(big)


# ---------- builder ----------


def test_build_test_job_none_filter(db_session: Session) -> None:
    _seed_mugen_case(db_session, suite_name="smoke", case_name="smoke_case_1")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="smoke_case_2")
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
        env_set_num=1,
        node_num=1,
        case_filter="none",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    run_job.task_id = "pipeline-task"
    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    assert job.env_type == TestEnvType.VM.value
    assert job.keep_env is True
    assert job.physical_usage_scenario == "docker-update"
    assert job.result_parser == template.result_parser
    assert job.task_id == run_job.task_id
    assert len(job.env_sets) == 1
    assert len(job.env_sets[0].case_runs) == 2
    assert run_job.test_job_id == job.id


def test_build_test_job_filters_dangerous_cases_and_records_event(
    db_session: Session,
) -> None:
    """危险用例不进执行清单;名字规则与同步扫描标记都拦截;事件留痕。"""
    _seed_mugen_case(
        db_session, suite_name="systemd", case_name="oe_test_service_initrd-cleanup"
    )
    _seed_mugen_case(db_session, suite_name="systemd", case_name="oe_test_safe_case")
    scanned = MugenCase(
        suite_name="systemd",
        case_name="oe_test_service_custom-bad",
        env_type="vm",
        node_num=1,
        commit_sha="abc123",
        dangerous=True,
        dangerous_reason="脚本伪造 initrd 环境(/etc/initrd-release)",
    )
    db_session.add(scanned)
    db_session.flush()
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="systemd",
        env_set_num=1,
        node_num=1,
        case_filter="none",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )

    case_names = [
        cr.case_name for cr in job.env_sets[0].case_runs
    ]
    assert case_names == ["oe_test_safe_case"]

    db_session.commit()
    events = list(
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_id == str(job.id),
                TaskEvent.phase == "cases_filtered",
            )
        ).scalars()
    )
    assert len(events) == 1
    assert "2" in events[0].message
    assert "oe_test_service_initrd-cleanup" in events[0].message
    assert "oe_test_service_custom-bad" in events[0].message


def test_build_test_job_no_filter_event_when_all_cases_safe(
    db_session: Session,
) -> None:
    _seed_mugen_case(db_session, suite_name="smoke", case_name="smoke_case_1")
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
        env_set_num=1,
        node_num=1,
        case_filter="none",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    db_session.commit()
    events = list(
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_id == str(job.id),
                TaskEvent.phase == "cases_filtered",
            )
        ).scalars()
    )
    assert events == []


def test_build_test_job_repodata_with_skipped(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_mugen_case(db_session, suite_name="pkgA", case_name="pkgA")
    _seed_mugen_case(db_session, suite_name="pkgB", case_name="pkgB")
    template = TestModuleTemplate(
        name="pkgcmd",
        display_name="Pkgcmd",
        suite_name="cli-test",
        env_set_num=1,
        node_num=1,
        case_filter="repodata_packages",
        env_type="both",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template, env_type="vm")
    monkeypatch.setattr(
        pipeline_builder,
        "fetch_update_packages",
        lambda *, repo_base_url, version: ["pkgA", "pkgB", "pkgNoCase"],
    )
    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    statuses = [cr.status for cr in job.env_sets[0].case_runs]
    assert TestCaseRunStatus.NO_CASE.value in statuses
    assert statuses.count(TestCaseRunStatus.PENDING.value) == 2  # pkgA + pkgB


def test_build_test_job_physical_env_type(db_session: Session) -> None:
    _seed_mugen_case(db_session, suite_name="pkgA", case_name="pkgA", env_type="physical")
    template = TestModuleTemplate(
        name="pkgcmd",
        display_name="Pkgcmd",
        suite_name="cli-test",
        env_set_num=1,
        node_num=1,
        case_filter="repodata_packages",
        env_type="both",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(
        db_session, template=template, env_type="physical"
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        pipeline_builder,
        "fetch_update_packages",
        lambda *, repo_base_url, version: ["pkgA"],
    )
    try:
        job = build_test_job_for_run_job(
            db_session,
            run_job=run_job,
            config=config,
            template=template,
            version=run.version,
            actor_user_id="admin",
        )
        assert job.env_type == TestEnvType.PHYSICAL.value
    finally:
        monkeypatch.undo()


def test_build_test_job_both_physical_disabled_marks_env_set_not_executed(
    db_session: Session,
) -> None:
    """pkgcmd both 模块 config_data.pkgcmd_physical_enabled=False → physical env_set
    照建（可见）但 case_runs NOT_EXECUTED + 不建 node；vm env_set 正常 PENDING。
    """
    _seed_mugen_case(db_session, suite_name="pkgA", case_name="pkgA", env_type="vm")
    _seed_mugen_case(db_session, suite_name="pkgB", case_name="pkgB", env_type="physical")
    template = TestModuleTemplate(
        name="pkgcmd",
        display_name="Pkgcmd",
        suite_name="cli-test",
        env_set_num=1,
        node_num=1,
        case_filter="repodata_packages",
        env_type="both",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template, env_type="vm")
    config.config_data["pkgcmd_physical_enabled"] = False
    db_session.flush()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        pipeline_builder,
        "fetch_update_packages",
        lambda *, repo_base_url, version: ["pkgA", "pkgB"],
    )
    try:
        job = build_test_job_for_run_job(
            db_session,
            run_job=run_job,
            config=config,
            template=template,
            version=run.version,
            actor_user_id="admin",
        )
        # 2 env_sets: vm (PENDING) + physical (NOT_EXECUTED, no nodes)
        assert len(job.env_sets) == 2
        vm_set, phys_set = job.env_sets
        assert all(cr.status == TestCaseRunStatus.PENDING.value for cr in vm_set.case_runs)
        assert all(cr.status == TestCaseRunStatus.NOT_EXECUTED.value for cr in phys_set.case_runs)
        assert len(phys_set.nodes) == 0
    finally:
        monkeypatch.undo()


def test_build_test_job_non_kernel_ltp_suite_runs_all_cases(db_session: Session) -> None:
    _seed_mugen_case(db_session, suite_name="ltp", case_name="oe_test_ltp")
    _seed_mugen_case(db_session, suite_name="ltp", case_name="oe_test_posix")
    template = TestModuleTemplate(
        name="ltp-release",
        display_name="LTP Release",
        suite_name="ltp",
        env_set_num=1,
        node_num=1,
        case_filter="none",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    case_names = {cr.case_name for cr in job.env_sets[0].case_runs}
    assert case_names == {"oe_test_ltp", "oe_test_posix"}


def test_build_test_job_kernel_ltp_excludes_posix_from_default(db_session: Session) -> None:
    _seed_mugen_case(db_session, suite_name="ltp", case_name="oe_test_ltp", env_type="physical")
    _seed_mugen_case(db_session, suite_name="ltp", case_name="oe_test_posix", env_type="physical")
    template = TestModuleTemplate(
        name="kernel",
        display_name="Kernel",
        suite_name="ltp",
        env_set_num=1,
        node_num=1,
        case_filter="none",
        env_type="physical",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(
        db_session, template=template, env_type="physical"
    )
    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    case_names = {cr.case_name for cr in job.env_sets[0].case_runs}
    assert case_names == {"oe_test_ltp"}


def test_build_test_job_service_test_cases_from_repodata(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pkgserver: case_filter=service_test_cases -> repodata filelists -> MugenCase match."""
    _seed_mugen_case(
        db_session, suite_name="openssh", case_name="oe_test_service_sshd", env_type="vm"
    )
    _seed_mugen_case(
        db_session,
        suite_name="systemd",
        case_name="oe_test_service_systemd",
        env_type="physical",
    )
    template = TestModuleTemplate(
        name="pkgserver",
        display_name="Service Test",
        suite_name="service-test",
        env_set_num=1,
        node_num=1,
        case_filter="service_test_cases",
        env_type="both",
        result_parser="pkgserver",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template, env_type=None)

    from app.modules.pipelines import builder as builder_module

    monkeypatch.setattr(
        builder_module,
        "fetch_service_packages",
        lambda **kw: [("openssh", "sshd", "service"), ("systemd", "systemd", "service")],
    )

    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    assert len(job.env_sets) == 2
    all_runs = [cr for es in job.env_sets for cr in es.case_runs]
    assert len(all_runs) == 2
    case_names = {cr.case_name for cr in all_runs}
    assert case_names == {"oe_test_service_sshd", "oe_test_service_systemd"}


def test_build_test_job_repodata_union_merges_and_dedupes(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pkgunion: case_filter=repodata_union → repodata + service 两路并集，(suite, case) 去重。"""
    _seed_mugen_case(db_session, suite_name="nginx", case_name="oe_test_nginx_01")
    # 两路都命中：repodata 路(suite=nginx 在更新列表选全 suite) + service 路(case_name 匹配)
    _seed_mugen_case(db_session, suite_name="nginx", case_name="oe_test_service_nginx")
    # 仅 service 路命中：包 openssh 不在 update source 列表
    _seed_mugen_case(
        db_session, suite_name="openssh", case_name="oe_test_service_sshd", env_type="physical"
    )
    template = TestModuleTemplate(
        name="pkgunion",
        display_name="Package Union Test",
        suite_name="cli-test",
        env_set_num=1,
        node_num=1,
        case_filter="repodata_union",
        env_type="both",
        result_parser="pkgunion",
    )
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template, env_type=None)

    from app.modules.pipelines import builder as builder_module

    monkeypatch.setattr(
        builder_module,
        "fetch_update_packages",
        lambda **kw: ["nginx", "pkgNoCase"],
    )
    monkeypatch.setattr(
        builder_module,
        "fetch_service_packages",
        lambda **kw: [("nginx", "nginx", "service"), ("openssh", "sshd", "service")],
    )

    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version=run.version,
        actor_user_id="admin",
    )
    # 并集去重：重叠的 oe_test_service_nginx 只出现一次
    executable = []
    for es in job.env_sets:
        for cr in es.case_runs:
            if cr.status == TestCaseRunStatus.PENDING.value:
                executable.append(cr)
    assert sorted(cr.case_name for cr in executable) == [
        "oe_test_nginx_01",
        "oe_test_service_nginx",
        "oe_test_service_sshd",
    ]
    # env_type 拆分：vm=nginx 两例，physical=sshd（vm 集另挂 no_case 包行）
    by_env = {es.env_type: es for es in job.env_sets}
    assert sorted(
        cr.case_name
        for cr in by_env["vm"].case_runs
        if cr.status == TestCaseRunStatus.PENDING.value
    ) == ["oe_test_nginx_01", "oe_test_service_nginx"]
    assert [cr.case_name for cr in by_env["physical"].case_runs] == ["oe_test_service_sshd"]
    # no_case 只来自 repodata 路（service 路无 no_case 概念）
    no_case = []
    for es in job.env_sets:
        for cr in es.case_runs:
            if cr.status == TestCaseRunStatus.NO_CASE.value:
                no_case.append(cr)
    assert [cr.suite_name for cr in no_case] == ["pkgNoCase"]
    # update_packages = 两路包名并集（供 pre_env 补装 update 轮新增包）
    assert set(job.update_packages) == {"nginx", "pkgNoCase", "openssh"}


# ---------- enqueue_run_job ----------


def test_prepare_env_skips_mugen_when_exec_command_set(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """prepare_env skips prepare_mugen + configure_mugen_node when mugen_exec_command is set."""
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="running",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        mugen_exec_command="docker exec openEuler_test bash mugen.sh -f {suite} -r {case} -x",
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.commit()

    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )

    called = {"prepare_mugen": False, "configure_mugen_node": False}
    monkeypatch.setattr(mugen_runner, "wait_for_ssh_ready", lambda *a, **kw: None)
    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **kw: None)
    monkeypatch.setattr(mugen_runner, "write_control_file", lambda **kw: None)
    monkeypatch.setattr(
        mugen_runner,
        "prepare_mugen",
        lambda *a, **kw: called.__setitem__("prepare_mugen", True),
    )
    monkeypatch.setattr(
        mugen_runner,
        "configure_mugen_node",
        lambda *a, **kw: called.__setitem__("configure_mugen_node", True),
    )

    mugen_runner.prepare_env(db_session, job=job, env_set=env_set, control=control, peer=None)
    assert called["prepare_mugen"] is False
    assert called["configure_mugen_node"] is False


def test_prepare_env_runs_mugen_when_no_exec_command(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """prepare_env runs prepare_mugen + configure_mugen_node when mugen_exec_command is None."""
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="running",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        mugen_exec_command=None,
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.commit()

    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )

    called = {"prepare_mugen": False, "configure_mugen_node": False}
    monkeypatch.setattr(mugen_runner, "wait_for_ssh_ready", lambda *a, **kw: None)
    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **kw: None)
    monkeypatch.setattr(mugen_runner, "write_control_file", lambda **kw: None)
    monkeypatch.setattr(
        mugen_runner,
        "prepare_mugen",
        lambda *a, **kw: called.__setitem__("prepare_mugen", True),
    )
    monkeypatch.setattr(
        mugen_runner,
        "configure_mugen_node",
        lambda *a, **kw: called.__setitem__("configure_mugen_node", True),
    )

    mugen_runner.prepare_env(db_session, job=job, env_set=env_set, control=control, peer=None)
    assert called["prepare_mugen"] is True
    assert called["configure_mugen_node"] is True


def test_enqueue_run_job_raises_without_broker() -> None:
    from app.modules.pipelines.service import enqueue_run_job

    run_job = PipelineRunJob(
        pipeline_run_id="r", module_template_id="t", arch="x86", env_type=None, status="pending"
    )
    with pytest.raises(Exception, match="broker"):
        enqueue_run_job(run_job, "admin")


def test_enqueue_run_jobs_persists_task_id_before_sending(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.pipelines import service as pipeline_service

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    db_session.commit()

    sent_task_ids: list[str] = []
    call_order: list[str] = []
    original_commit = db_session.commit

    def tracked_commit() -> None:
        original_commit()
        call_order.append("commit")

    def fake_send_task(_name: str, *, args: list[str], task_id: str) -> SimpleNamespace:
        assert args == [run_job.id, "admin"]
        call_order.append("send")
        sent_task_ids.append(task_id)
        return SimpleNamespace(id=task_id)

    monkeypatch.setattr(
        pipeline_service,
        "get_settings",
        lambda: SimpleNamespace(celery_broker_url="redis://broker"),
    )
    monkeypatch.setattr(db_session, "commit", tracked_commit)
    monkeypatch.setattr(pipeline_service.celery_app, "send_task", fake_send_task)

    pipeline_service.enqueue_run_jobs(db_session, [run_job], "admin")

    db_session.expire_all()
    stored = db_session.get(PipelineRunJob, run_job.id)
    assert stored is not None
    assert stored.task_id == sent_task_ids[0]
    assert call_order[:2] == ["commit", "send"]


def test_run_job_task_rolls_back_before_recording_executor_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """失败事务先 rollback，RunJob error 与事件才能在新事务提交。"""
    from app.modules.pipelines import tasks as pipeline_tasks

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    run_job.task_id = "pipeline-task"
    db_session.commit()

    rollback_calls = 0
    original_rollback = db_session.rollback

    def track_rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1
        original_rollback()

    class FailingExecutor:
        @staticmethod
        def prepare_and_execute(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
            raise RuntimeError("test_jobs.keep_env does not exist")

    monkeypatch.setattr(db_session, "rollback", track_rollback)
    monkeypatch.setattr(pipeline_tasks, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(pipeline_tasks, "get_framework_executor", lambda _name: FailingExecutor())

    pipeline_tasks.run_pipeline_run_job_task.run(run_job.id, "admin")

    db_session.expire_all()
    assert rollback_calls == 1
    assert db_session.get(PipelineRunJob, run_job.id).status == "error"
    started = db_session.scalar(
        select(TaskEvent).where(
            TaskEvent.subject_id == run_job.id,
            TaskEvent.phase == "started",
        )
    )
    assert started is not None
    assert started.celery_task_id == run_job.task_id
    error_event = db_session.scalar(
        select(TaskEvent).where(
            TaskEvent.subject_id == run_job.id,
            TaskEvent.phase == "runjob_error",
        )
    )
    assert error_event is not None
    assert "keep_env" in error_event.message


def test_run_job_task_finalizes_cancelling_run_job_before_building_test_job(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cancelling RunJob 到达 worker 时直接完成，不能再建 TestJob。"""
    from app.modules.pipelines import tasks as pipeline_tasks

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    run_job.status = "cancelling"
    run_job.cancel_requested = True
    db_session.commit()

    monkeypatch.setattr(pipeline_tasks, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        pipeline_tasks,
        "get_framework_executor",
        lambda _name: pytest.fail("cancelled RunJob must not build a TestJob"),
    )

    pipeline_tasks.run_pipeline_run_job_task.run(run_job.id, "admin")

    db_session.refresh(run_job)
    assert run_job.status == "cancelled"
    assert run_job.test_job_id is None


def test_run_job_task_keeps_cancelled_status_when_execution_finishes(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """执行期间到达的取消不能被 executor 的成功终态覆盖。"""
    from app.modules.pipelines import tasks as pipeline_tasks

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    db_session.commit()

    class CancellingExecutor:
        @staticmethod
        def prepare_and_execute(*_: object, **__: object) -> str:
            run_job.cancel_requested = True
            run_job.status = "cancelling"
            db_session.commit()
            return "succeeded"

    monkeypatch.setattr(pipeline_tasks, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        pipeline_tasks, "get_framework_executor", lambda _name: CancellingExecutor()
    )

    pipeline_tasks.run_pipeline_run_job_task.run(run_job.id, "admin")

    db_session.refresh(run_job)
    assert run_job.status == "cancelled"


def test_run_job_task_preserves_recovery_terminal_status(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """旧 Worker 的 executor 返回不能覆盖恢复服务已经写入的 error。"""
    from app.modules.pipelines import tasks as pipeline_tasks

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    db_session.commit()

    class RecoveredExecutor:
        @staticmethod
        def prepare_and_execute(*_: object, **__: object) -> str:
            run_job.status = "error"
            db_session.commit()
            return "succeeded"

    monkeypatch.setattr(pipeline_tasks, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        pipeline_tasks, "get_framework_executor", lambda _name: RecoveredExecutor()
    )

    pipeline_tasks.run_pipeline_run_job_task.run(run_job.id, "admin")

    db_session.refresh(run_job)
    assert run_job.status == "error"


def test_run_job_task_ignores_self_collect_log_failure(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """任务终态已提交后，日志归集异常只能记录日志，不能反向失败任务。"""
    from app.modules.pipelines import tasks as pipeline_tasks

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    db_session.commit()

    class SuccessfulExecutor:
        @staticmethod
        def prepare_and_execute(*_: object, **__: object) -> str:
            return "succeeded"

    monkeypatch.setattr(pipeline_tasks, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        pipeline_tasks, "get_framework_executor", lambda _name: SuccessfulExecutor()
    )
    monkeypatch.setattr(
        pipeline_tasks,
        "_self_collect_logs",
        lambda *_, **__: (_ for _ in ()).throw(RuntimeError("log collection failed")),
    )

    pipeline_tasks.run_pipeline_run_job_task.run(run_job.id, "admin")

    db_session.refresh(run_job)
    assert run_job.status == "succeeded"


def test_mugen_executor_skips_new_test_job_when_run_job_was_cancelled(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """建完 TestJob 后命中的取消不允许进入 process_test_job。"""
    from app.modules.pipelines.framework_executors import mugen as mugen_executor
    from app.modules.test_management.models import TestJobStatus

    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    config, _execution, _run, run_job = _make_run_job(db_session, template=template)
    job, env_set, case_run = _make_job_with_case_run(db_session)
    job.status = TestJobStatus.PENDING.value
    db_session.commit()

    def _build_cancelled_test_job(_db: Session, **_: object) -> TestJob:
        run_job.cancel_requested = True
        return job

    monkeypatch.setattr(mugen_executor, "build_test_job_for_run_job", _build_cancelled_test_job)
    monkeypatch.setattr(
        mugen_executor,
        "process_test_job",
        lambda _job_id: pytest.fail("cancelled RunJob must not execute its new TestJob"),
    )

    terminal = mugen_executor.MugenFrameworkExecutor().prepare_and_execute(
        db_session,
        run_job=run_job,
        config=config,
        actor_user_id="admin",
    )

    assert terminal == "cancelled"
    db_session.refresh(job)
    db_session.refresh(env_set)
    db_session.refresh(case_run)
    assert job.cancel_requested is True
    assert job.status == TestJobStatus.CANCELLED.value
    assert env_set.status == TestEnvSetStatus.NOT_EXECUTED.value
    assert case_run.status == TestCaseRunStatus.NOT_EXECUTED.value


# ---------- run_case 挂死处理 ----------


def _make_job_with_case_run(db: Session, *, result_parser: str | None = "none") -> tuple:
    from app.modules.test_management.models import utc_now

    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="running",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        result_parser=result_parser,
        created_at=utc_now(),
    )
    db.add(job)
    db.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db.add(env_set)
    db.flush()
    case_run = TestCaseRun(
        job=job, env_set=env_set, suite_name="s", case_name="c", status="pending"
    )
    db.add(case_run)
    db.flush()
    return job, env_set, case_run


def test_run_case_hang_marks_error_and_raises(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(returncode=0, stdout="", stderr=""),
    )

    class FakeDetector:
        @staticmethod
        def start() -> None:
            pass

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return True

    monkeypatch.setattr(mugen_runner, "HangDetector", lambda **_: FakeDetector())
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert case_run.status == TestCaseRunStatus.ERROR.value


# ---------- 心跳失败模式统计 ----------


def test_heartbeat_stats_classifies_failure_modes() -> None:
    stats = _HeartbeatStats()

    # exit 255 + 连接阶段超时/无路由 = 网络层不可达（整机失联特征）。
    stats.record_result(
        RemoteCommandResult(
            returncode=255,
            stdout="",
            stderr="ssh: connect to host 10.0.0.1 port 22: Connection timed out",
        )
    )
    stats.record_result(
        RemoteCommandResult(returncode=255, stdout="", stderr="No route to host")
    )
    # 进程级超时：TCP 已建立、echo 卡死到 30s —— OS 活着但重度受阻。
    stats.record_result(RemoteCommandResult(returncode=None, stdout="", stderr="", timed_out=True))
    stats.record_result(
        RemoteCommandResult(returncode=255, stdout="", stderr="ssh: Connection refused")
    )
    stats.record_result(
        RemoteCommandResult(returncode=255, stdout="", stderr="Connection reset by peer")
    )
    stats.record_result(
        RemoteCommandResult(
            returncode=255, stdout="", stderr="Connection timed out during banner exchange"
        )
    )
    stats.record_result(RemoteCommandResult(returncode=255, stdout="", stderr="kex typo ???"))

    assert stats.summary() == "：失联×2，超时×1，拒绝×1，断连×2，其他×1；末次错误：kex typo ???"
    # banner exchange 必须先于失联关键词匹配，保持断连判定。
    single = _HeartbeatStats()
    single.record_result(
        RemoteCommandResult(
            returncode=255, stdout="", stderr="Connection timed out during banner exchange"
        )
    )
    assert "断连×1" in single.summary()


def test_heartbeat_stats_summary_empty_and_last_error() -> None:
    stats = _HeartbeatStats()
    assert stats.summary() == ""

    stats.record_result(
        RemoteCommandResult(returncode=255, stdout="", stderr="ssh: Connection refused\n")
    )
    assert stats.summary() == "：拒绝×1；末次错误：ssh: Connection refused"
