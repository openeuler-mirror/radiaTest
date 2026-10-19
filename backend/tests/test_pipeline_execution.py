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
    PipelineType,
    TestModuleTemplate,
)
from app.modules.pipelines.registry import get_pipeline_strategy
from app.modules.pipelines.service import (
    PipelineEnvironmentBusyError,
    PipelineRunJobRerunConflict,
    PipelineRunJobRerunError,
    _execution_status_from_runs,
    _worst_wins_run_status,
    create_run_job_rerun,
    ensure_execution_envs_destroyable,
    get_case_mugen_log,
    get_execution_summary,
    get_run_job_detail,
    list_run_logs,
    read_run_log_content,
)
from app.modules.resources.models import Resource, ResourceType
from app.modules.tasks.models import TaskEvent
from app.modules.test_management.errors import EnvSetHangError, TestJobExecutionError
from app.modules.test_management.frameworks import mugen_runner
from app.modules.test_management.frameworks.mugen_runner import (
    _capture_and_store_console,
    _HeartbeatStats,
    _parse_and_store_subcases,
    _per_case_collect_log,
)
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import (
    MugenCase,
    TestCaseRun,
    TestCaseRunDetail,
    TestCaseRunStatus,
    TestEnvNode,
    TestEnvNodeStatus,
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


def test_run_case_hang_detail_includes_failure_modes(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vm_hang 判死时 detail 带失败模式摘要，随 case_error 事件流出。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )
    events: list[str] = []

    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("message"))
    )
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)

    def fake_run_control(**kw: object) -> object:
        # 等 on_hung 触发的 cancel_event 再返回，消除 detector 判死与命令返回的竞态。
        cancel_event = kw.get("cancel_event")
        if cancel_event is not None:
            cancel_event.wait(timeout=5)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", fake_run_control)
    monkeypatch.setattr(
        mugen_runner,
        "run_ssh_command",
        lambda **_: RemoteCommandResult(returncode=255, stdout="", stderr="Connection refused"),
    )
    # 真实 HangDetector 换快速节奏：2 连败 + 复核失败 → 判死。
    real_hang_detector = mugen_runner.HangDetector

    def fast_detector(**kw: object) -> object:
        return real_hang_detector(interval=0.01, max_failures=2, **kw)

    monkeypatch.setattr(mugen_runner, "HangDetector", fast_detector)
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert case_run.status == TestCaseRunStatus.ERROR.value
    assert any(
        message and "心跳连续失败：拒绝×" in message and "末次错误" in message
        for message in events
    )


# ---------- BMC 交叉确认门（观察模式） ----------


def _bmc_control() -> SimpleNamespace:
    return SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(
            host_resource_id=None,
            physical_spec=SimpleNamespace(
                bmc_ip="192.0.2.10",
                bmc_username="ADMIN",
                bmc_password_ciphertext="cipher",
            ),
        ),
    )


def test_run_case_bmc_alive_enters_watch_and_recovers(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OOM 类瞬断：BMC 报未重启 → 观察事件留痕；SSH 恢复后用例继续完成，不抛挂死。"""
    import threading

    import app.modules.test_management.hang_detector as hang_detector_module

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _bmc_control()
    events: list[tuple[str | None, str | None]] = []
    artifacts: list[str | None] = []
    recovered_event = threading.Event()

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(mugen_runner, "decrypt_secret", lambda _cipher: "pw")
    monkeypatch.setattr(mugen_runner, "bmc_power_on", lambda **_kw: True)
    monkeypatch.setattr(
        mugen_runner,
        "_record_hang_watch_event",
        lambda _job_id, **kw: (
            events.append((kw.get("phase"), kw.get("message"))),
            recovered_event.set() if kw.get("phase") == "hang_recovered" else None,
        ),
    )
    monkeypatch.setattr(
        mugen_runner,
        "_store_hang_watch_artifact",
        lambda **kw: artifacts.append(kw.get("artifact_name")),
    )
    monkeypatch.setattr(
        mugen_runner, "run_control_command", lambda **_: (
            recovered_event.wait(timeout=5),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        )[1]
    )

    def fake_ssh_alive(_control: object, _stats: object = None) -> bool:
        probe_count[0] += 1
        return probe_count[0] > 5

    monkeypatch.setattr(mugen_runner, "_ssh_alive", fake_ssh_alive)
    real_hang_detector = mugen_runner.HangDetector
    probe_count = [0]

    def fast_detector(**kw: object) -> object:
        return real_hang_detector(interval=0.02, max_failures=3, **kw)

    monkeypatch.setattr(mugen_runner, "HangDetector", fast_detector)
    monkeypatch.setattr(mugen_runner, "_parse_and_store_subcases", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "_per_case_collect_log", lambda *_, **__: None)
    monkeypatch.setattr(hang_detector_module, "WATCH_TIMEOUT_SECONDS", 5.0)

    mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert recovered_event.wait(timeout=1)
    phases = [phase for phase, _ in events]
    assert "hang_watch" in phases
    assert "hang_recovered" in phases
    assert artifacts == [
        f"bmc-{case_run.suite_name}-{case_run.case_name}-watch-entry.log",
        f"bmc-{case_run.suite_name}-{case_run.case_name}-watch-recovered.log",
    ]
    assert case_run.status == TestCaseRunStatus.PASSED.value


def test_run_case_watch_timeout_declares_hang(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BMC 一直活着但 SSH 不恢复 → 观察上限后判死，事件与 case ERROR 齐全。"""
    import app.modules.test_management.hang_detector as hang_detector_module

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _bmc_control()
    events: list[str | None] = []

    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("message"))
    )
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(mugen_runner, "decrypt_secret", lambda _cipher: "pw")
    monkeypatch.setattr(mugen_runner, "bmc_power_on", lambda **_kw: True)
    monkeypatch.setattr(
        mugen_runner,
        "_record_hang_watch_event",
        lambda _job_id, **kw: events.append(kw.get("message")),
    )
    monkeypatch.setattr(
        mugen_runner, "_store_hang_watch_artifact", lambda **_kw: None
    )

    def fake_run_control(**kw: object) -> object:
        cancel_event = kw.get("cancel_event")
        if cancel_event is not None:
            cancel_event.wait(timeout=5)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", fake_run_control)
    monkeypatch.setattr(
        mugen_runner,
        "run_ssh_command",
        lambda **_: RemoteCommandResult(returncode=255, stdout="", stderr="Connection refused"),
    )
    real_hang_detector = mugen_runner.HangDetector

    def fast_detector(**kw: object) -> object:
        return real_hang_detector(interval=0.02, max_failures=2, **kw)

    monkeypatch.setattr(mugen_runner, "HangDetector", fast_detector)
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)
    monkeypatch.setattr(hang_detector_module, "WATCH_TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(hang_detector_module, "WATCH_CONFIRM_INTERVAL_SECONDS", 0.05)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert case_run.status == TestCaseRunStatus.ERROR.value
    assert any(message and "观察模式" in message for message in events)
    assert any(message and "观察期" in message and "未见恢复" in message for message in events)


def test_run_case_bmc_power_off_deadline_declares_hang(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """阈值首查即电源 off → 进观察锚定断电宽限；宽限内未恢复判死，detail 带电源证据。"""
    import app.modules.test_management.hang_detector as hang_detector_module

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _bmc_control()
    events: list[str | None] = []

    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("message"))
    )
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(mugen_runner, "decrypt_secret", lambda _cipher: "pw")
    monkeypatch.setattr(mugen_runner, "bmc_power_on", lambda **_kw: False)
    monkeypatch.setattr(
        mugen_runner,
        "_record_hang_watch_event",
        lambda _job_id, **kw: events.append(kw.get("message")),
    )
    monkeypatch.setattr(mugen_runner, "_store_hang_watch_artifact", lambda **_kw: None)

    def fake_run_control(**kw: object) -> object:
        cancel_event = kw.get("cancel_event")
        if cancel_event is not None:
            cancel_event.wait(timeout=5)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", fake_run_control)
    monkeypatch.setattr(
        mugen_runner,
        "run_ssh_command",
        lambda **_: RemoteCommandResult(returncode=255, stdout="", stderr="Connection refused"),
    )
    real_hang_detector = mugen_runner.HangDetector

    def fast_detector(**kw: object) -> object:
        return real_hang_detector(interval=0.02, max_failures=2, **kw)

    monkeypatch.setattr(mugen_runner, "HangDetector", fast_detector)
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)
    # 检测器宽限缩短到 0.15s 判死；mugen_runner 文案仍用真实常量渲染"10 分钟"。
    monkeypatch.setattr(hang_detector_module, "WATCH_POWER_OFF_DEADLINE_SECONDS", 0.15)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert case_run.status == TestCaseRunStatus.ERROR.value
    # 首查 off 也进观察模式，watch-entry 事件注明电源断开。
    assert any(
        message and "电源断开" in message and "观察模式" in message for message in events
    )
    assert any(
        message and "BMC 报告电源断开" in message and "10 分钟内 SSH 未恢复" in message
        for message in events
    )


def test_run_case_vm_without_bmc_has_no_confirm_gate(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VM/无 BMC 资源不建确认门，维持阈值+复核即判的现有行为。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )
    captured: dict[str, object] = {}

    class FakeDetector:
        def __init__(self, **kw: object) -> None:
            captured.update(kw)

        @staticmethod
        def start() -> None:
            pass

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return True

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(mugen_runner, "HangDetector", FakeDetector)
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert captured.get("confirm_fn") is None
    assert captured.get("on_watch_start") is None
    assert captured.get("on_recovered") is None


# ---------- 物理机挂死 BMC 取证 ----------


def test_capture_console_physical_stores_bmc_diagnostic(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(
            host_resource_id=None,
            physical_spec=SimpleNamespace(
                bmc_ip="192.0.2.10",
                bmc_username="ADMIN",
                bmc_password_ciphertext="cipher",
            ),
        ),
    )
    stored: dict[str, object] = {}

    class FakeCollector:
        def __init__(self, base_dir: str) -> None:
            self.base_dir = base_dir

        @staticmethod
        def store_artifact(db: Session, **kw: object) -> None:
            stored.update(kw)

    monkeypatch.setattr(mugen_runner, "LogCollector", FakeCollector)
    monkeypatch.setattr(mugen_runner, "decrypt_secret", lambda _cipher: "pw")
    monkeypatch.setattr(
        mugen_runner, "capture_bmc_diagnostics", lambda **_kw: "SEL OUTPUT"
    )

    _capture_and_store_console(
        db_session, job=job, control=control, case_run=case_run
    )

    assert stored["artifact_type"] == "bmc_diagnostic"
    assert stored["artifact_name"] == f"bmc-{case_run.suite_name}-{case_run.case_name}.log"
    assert stored["content"] == "SEL OUTPUT"
    assert stored["job_id"] == job.id
    assert stored["module"] == "hang"


def test_capture_console_physical_without_bmc_is_noop(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )

    def fail_collector(*_args: object, **_kw: object) -> None:
        raise AssertionError("physical resource without BMC must not store artifacts")

    monkeypatch.setattr(mugen_runner, "LogCollector", fail_collector)

    _capture_and_store_console(
        db_session, job=job, control=control, case_run=case_run
    )


def test_capture_console_physical_with_incomplete_bmc_is_noop(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """physical_spec 存在但 bmc_ip/username 缺失时同样零副作用。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(
            host_resource_id=None,
            physical_spec=SimpleNamespace(
                bmc_ip="", bmc_username=None, bmc_password_ciphertext="c"
            ),
        ),
    )

    def fail_collector(*_args: object, **_kw: object) -> None:
        raise AssertionError("incomplete BMC spec must not store artifacts")

    monkeypatch.setattr(mugen_runner, "LogCollector", fail_collector)

    _capture_and_store_console(
        db_session, job=job, control=control, case_run=case_run
    )


def test_run_case_parses_subcases_after_success(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    job, _env_set, case_run = _make_job_with_case_run(db_session, result_parser="ltp")
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
            return False

    monkeypatch.setattr(mugen_runner, "HangDetector", lambda **_: FakeDetector())
    monkeypatch.setattr(
        mugen_runner,
        "_ssh_read_file",
        lambda _control, _path: "foo 1 TPASS\nbar 2 TFAIL\n",
    )

    mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert case_run.status == TestCaseRunStatus.PASSED.value
    details = list(
        db_session.execute(
            select(TestCaseRunDetail).where(TestCaseRunDetail.case_run_id == case_run.id)
        )
        .scalars()
        .all()
    )
    assert len(details) == 2


# ---------- destroy_execution_envs ----------


def test_destroy_execution_envs_calls_destroy(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    config, execution, run, run_job = _make_run_job(db_session, template=template)
    resource = Resource(
        resource_code="vm-1",
        resource_type=ResourceType.VIRTUAL.value,
        ssh_username="root",
        ssh_password_ciphertext="x",
    )
    db_session.add(resource)
    db_session.flush()
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="succeeded",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
    )
    db_session.add(job)
    db_session.flush()
    run_job.test_job_id = job.id
    run_job.status = "succeeded"
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.flush()
    db_session.add(
        TestEnvNode(env_set=env_set, node_index=0, role="control", resource_id=resource.id)
    )
    db_session.commit()

    destroyed: list[str] = []
    monkeypatch.setattr(
        "app.modules.test_management.envs.vm.destroy_env_node_vm",
        lambda db, *, job, node, actor: destroyed.append(node.resource_id),
    )

    from app.modules.pipelines.service import destroy_execution_envs

    result = destroy_execution_envs(
        db_session, execution=execution, actor=SimpleNamespace(id="admin")
    )
    assert destroyed == [resource.id]
    assert result["destroyed"] == [resource.id]


def test_destroy_environment_rejects_active_rerun_with_lock(db_session: Session) -> None:
    template = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(template)
    db_session.flush()
    _config, execution, _run, run_job = _make_run_job(db_session, template=template)
    run_job.status = "running"
    db_session.commit()

    with pytest.raises(PipelineEnvironmentBusyError):
        ensure_execution_envs_destroyable(db_session, execution.id, lock=True)


# ---------- execute_env_set physical 切换 ----------


def test_execute_env_set_uses_physical_node_creation(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.models import utc_now

    physical_calls: list[str] = []
    vm_calls: list[str] = []

    def fake_physical(db, *, job, env_set, node, actor):
        physical_calls.append(node.node_index)
        return True

    def fake_vm(db, *, job, env_set, node, actor):
        vm_calls.append(node.node_index)
        return True

    monkeypatch.setattr(test_execution, "create_env_node_physical", fake_physical)
    monkeypatch.setattr(test_execution, "create_env_node_vm", fake_vm)
    monkeypatch.setattr(
        test_execution,
        "node_runtime",
        lambda db, node: SimpleNamespace(
            ip="1.1.1.1",
            username="root",
            password="p",
            resource=SimpleNamespace(host_resource_id=None),
        ),
    )
    monkeypatch.setattr(test_execution, "prepare_env", lambda *_, **__: "/tmp/dir")
    monkeypatch.setattr(test_execution, "run_hook", lambda *_, **__: None)
    monkeypatch.setattr(test_execution, "run_case", lambda *_, **__: None)

    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="pending",
        framework="mugen",
        env_type=TestEnvType.PHYSICAL.value,
        dist="openEuler",
        os_version="v",
        image_round="",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        keep_env=True,
        created_at=utc_now(),
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.flush()
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert physical_calls == [0]
    assert vm_calls == []
    assert has_error is False


def test_execute_env_set_rerun_skips_environment_creation(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.models import utc_now

    calls: list[str] = []
    monkeypatch.setattr(
        test_execution,
        "create_env_node_vm",
        lambda *_, **__: pytest.fail("rerun must not create a VM"),
    )
    monkeypatch.setattr(
        test_execution,
        "create_env_node_physical",
        lambda *_, **__: pytest.fail("rerun must not PXE a physical node"),
    )
    monkeypatch.setattr(
        test_execution,
        "node_runtime",
        lambda db, node: SimpleNamespace(
            ip="192.0.2.30",
            username="root",
            password="p",
            resource=SimpleNamespace(host_resource_id=None),
        ),
    )
    monkeypatch.setattr(
        test_execution,
        "prepare_rerun_env",
        lambda *_, **__: "/root/kronos/jobs/rerun",
    )
    monkeypatch.setattr(
        test_execution,
        "archive_rerun_case_outputs",
        lambda **__: calls.append("archive"),
    )
    monkeypatch.setattr(
        test_execution,
        "run_hook",
        lambda *_, script_name, **__: calls.append(script_name),
    )

    def run_case(db, *, job, control, case_run, **kwargs):
        calls.append(case_run.case_name)
        case_run.status = TestCaseRunStatus.PASSED.value

    monkeypatch.setattr(test_execution, "run_case", run_case)
    job = TestJob(
        creator_user_id="admin",
        name="rerun",
        status="pending",
        framework="mugen",
        env_type="physical",
        dist="openEuler",
        os_version="v",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        keep_env=True,
        rerun_source_job_id=10000,
        rerun_env_script="prepare rerun",
        post_env_script="collect",
        created_at=utc_now(),
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, env_type="physical")
    db_session.add(env_set)
    db_session.flush()
    db_session.add(
        TestEnvNode(
            env_set=env_set,
            node_index=0,
            role="control",
            status="ready",
            resource_id="resource-1",
        )
    )
    db_session.add(
        TestCaseRun(
            job=job,
            env_set=env_set,
            suite_name="smoke",
            case_name="case-1",
        )
    )
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="user")
    )

    assert calls == ["rerun_env.sh", "archive", "case-1", "post_env.sh"]
    assert has_failure is False
    assert has_error is False


def test_rerun_env_error_survives_post_env_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.models import utc_now

    calls: list[str] = []
    monkeypatch.setattr(
        test_execution,
        "node_runtime",
        lambda db, node: SimpleNamespace(
            ip="192.0.2.31",
            username="root",
            password="p",
            resource=SimpleNamespace(host_resource_id=None),
        ),
    )
    monkeypatch.setattr(
        test_execution,
        "prepare_rerun_env",
        lambda *_, **__: "/root/kronos/jobs/rerun",
    )

    def fail_hooks(*_, script_name: str, **__) -> None:
        calls.append(script_name)
        code = "rerun_env_failed" if script_name == "rerun_env.sh" else "hook_failed"
        raise TestJobExecutionError(code, script_name)

    monkeypatch.setattr(test_execution, "run_hook", fail_hooks)
    job = TestJob(
        creator_user_id="admin",
        name="rerun",
        status="pending",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        keep_env=True,
        rerun_source_job_id=10000,
        rerun_env_script="prepare rerun",
        post_env_script="collect",
        created_at=utc_now(),
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1)
    db_session.add(env_set)
    db_session.flush()
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    case_run = TestCaseRun(
        job=job,
        env_set=env_set,
        suite_name="smoke",
        case_name="case-1",
    )
    db_session.add(case_run)
    db_session.commit()

    with pytest.raises(TestJobExecutionError) as error:
        test_execution.execute_env_set(
            db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="user")
        )

    assert error.value.code == "rerun_env_failed"
    assert calls == ["rerun_env.sh", "post_env.sh"]
    assert case_run.status == TestCaseRunStatus.ERROR.value


def test_archive_rerun_outputs_moves_module_logs_instead_of_deleting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scripts: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, script, **__: (
            scripts.append(script)
            or mugen_runner.RemoteCommandResult(returncode=0, stdout="", stderr="")
        ),
    )
    mugen_runner.archive_rerun_case_outputs(
        job=SimpleNamespace(
            id=42,
            mugen_exec_command=None,
            result_parser="pkgcmd",
            created_at=mugen_runner.utc_now(),
        ),
        control=SimpleNamespace(),
        case_runs=[SimpleNamespace(suite_name="suite", case_name="case")],
    )

    assert "rm -rf" not in scripts[0]
    assert "mv /opt/pkgcmd-logs/*" in scripts[0]
    assert "mv /opt/mugen/logs/suite/case" in scripts[0]


# ---------- pkgunion result_parser 接入点 ----------


def test_archive_rerun_outputs_pkgunion_module_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pkgunion 的 rerun 归档走 /opt/pkgunion-logs（per-case 日志与自汇集同目录）。"""
    scripts: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, script, **__: (
            scripts.append(script)
            or mugen_runner.RemoteCommandResult(returncode=0, stdout="", stderr="")
        ),
    )
    mugen_runner.archive_rerun_case_outputs(
        job=SimpleNamespace(
            id=42,
            mugen_exec_command=None,
            result_parser="pkgunion",
            created_at=mugen_runner.utc_now(),
        ),
        control=SimpleNamespace(),
        case_runs=[SimpleNamespace(suite_name="suite", case_name="case")],
    )

    assert "mv /opt/pkgunion-logs/*" in scripts[0]


def test_per_case_collect_log_pkgunion(monkeypatch: pytest.MonkeyPatch) -> None:
    """pkgunion 逐 case 收集 mugen 结果到 /opt/pkgunion-logs/pkgunion.log。"""
    scripts: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, script, **__: (
            scripts.append(script)
            or mugen_runner.RemoteCommandResult(returncode=0, stdout="", stderr="")
        ),
    )
    _per_case_collect_log(
        db=None,
        job=SimpleNamespace(result_parser="pkgunion"),
        control=SimpleNamespace(),
        case_run=SimpleNamespace(),
    )

    assert len(scripts) == 1
    assert "/opt/pkgunion-logs/pkgunion.log" in scripts[0]


def test_parse_and_store_subcases_pkgunion_dispatches_to_mugen_results(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pkgunion 子用例解析走 parse_mugen_results_dir（与 pkgcmd/pkgserver 同路）。"""
    job = TestJob(
        creator_user_id="admin",
        name="tj",
        status="running",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        result_parser="pkgunion",
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1)
    db_session.add(env_set)
    db_session.flush()
    case_run = TestCaseRun(
        job=job, env_set=env_set, suite_name="nginx", case_name="oe_test_service_nginx"
    )
    db_session.add(case_run)
    db_session.commit()

    listed: dict[str, str] = {}
    monkeypatch.setattr(
        mugen_runner,
        "_ssh_results_listing",
        lambda control, suite: listed.setdefault("suite", suite) or [],
    )
    monkeypatch.setattr(
        mugen_runner,
        "parse_mugen_results_dir",
        lambda listing: [
            mugen_runner.SubTestResult(sub_test_name="x", status="succeed")
        ],
    )

    _parse_and_store_subcases(
        db_session, job=job, control=SimpleNamespace(), case_run=case_run
    )

    assert listed["suite"] == "nginx"
    details = list(
        db_session.execute(
            select(TestCaseRunDetail).where(TestCaseRunDetail.case_run_id == case_run.id)
        ).scalars().all()
    )
    assert len(details) == 1
    assert details[0].status == "succeed"


# ---------- execute_env_set vm_hang / RemoteCommandError catch + continue + 熔断 ----------


def _make_job_with_env_set_and_cases(db: Session, *, num_cases: int) -> tuple:
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
        keep_env=True,
        created_at=utc_now(),
    )
    db.add(job)
    db.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db.add(env_set)
    db.flush()
    case_runs = []
    for i in range(num_cases):
        cr = TestCaseRun(
            job=job,
            env_set=env_set,
            suite_name="s",
            case_name=f"c{i}",
            status="pending",
        )
        db.add(cr)
        case_runs.append(cr)
    db.flush()
    return job, env_set, case_runs


def _patch_env_set_basics(monkeypatch, test_execution):
    """Patch prepare_env, run_hook, and node_runtime."""
    monkeypatch.setattr(
        test_execution,
        "node_runtime",
        lambda db, node: SimpleNamespace(
            ip="1.1.1.1",
            username="root",
            password="p",
            resource=SimpleNamespace(host_resource_id=None),
        ),
    )
    monkeypatch.setattr(test_execution, "prepare_env", lambda *_, **__: "/tmp/dir")
    monkeypatch.setattr(test_execution, "run_hook", lambda *_, **__: None)
    monkeypatch.setattr(test_execution, "create_env_node_vm", lambda *_, **__: True)


def test_execute_env_set_hang_continues_to_next_case(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vm_hang on case 0 → case 1 should still run."""
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)

    call_results: list[Exception | None] = [EnvSetHangError("hang"), None]

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        result = call_results.pop(0)
        if result is not None:
            case_run.status = TestCaseRunStatus.ERROR.value
            raise result
        case_run.status = TestCaseRunStatus.PASSED.value

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=2)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    assert case_runs[0].status == TestCaseRunStatus.ERROR.value
    assert case_runs[1].status == TestCaseRunStatus.PASSED.value


def test_execute_env_set_remote_error_continues(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RemoteCommandError on case 0 → case 1 should still run."""
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.remote import RemoteCommandError

    _patch_env_set_basics(monkeypatch, test_execution)

    call_results: list[Exception | None] = [RemoteCommandError("ssh failed"), None]

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        result = call_results.pop(0)
        if result is not None:
            case_run.status = TestCaseRunStatus.ERROR.value
            raise result
        case_run.status = TestCaseRunStatus.PASSED.value

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=2)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    assert case_runs[0].status == TestCaseRunStatus.ERROR.value
    assert case_runs[1].status == TestCaseRunStatus.PASSED.value


def test_execute_env_set_circuit_breaker_after_3_failures(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3 consecutive hang → remaining cases marked ERROR, loop breaks."""
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        case_run.status = TestCaseRunStatus.ERROR.value
        raise EnvSetHangError("hang")

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=5)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    # first 3 ran and errored
    for i in range(3):
        assert case_runs[i].status == TestCaseRunStatus.ERROR.value
    # remaining 2 marked ERROR (circuit breaker)
    for i in range(3, 5):
        assert case_runs[i].status == TestCaseRunStatus.ERROR.value


def test_execute_env_set_resets_counter_on_success(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """hang, success, hang → no circuit breaker (counter reset)."""
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)

    call_results: list[Exception | None] = [
        EnvSetHangError("hang"),
        None,
        EnvSetHangError("hang"),
        None,
    ]

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        result = call_results.pop(0)
        if result is not None:
            case_run.status = TestCaseRunStatus.ERROR.value
            raise result
        case_run.status = TestCaseRunStatus.PASSED.value

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=4)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    assert case_runs[0].status == TestCaseRunStatus.ERROR.value
    assert case_runs[1].status == TestCaseRunStatus.PASSED.value
    assert case_runs[2].status == TestCaseRunStatus.ERROR.value
    assert case_runs[3].status == TestCaseRunStatus.PASSED.value


def test_execute_env_set_cancel_between_cases(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cancel_requested → remaining cases marked not_executed, env_set not_executed."""
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)

    cancel_state = {"cancelled": False}

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        case_run.status = TestCaseRunStatus.PASSED.value
        cancel_state["cancelled"] = True

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)
    monkeypatch.setattr(
        test_execution, "_is_cancel_requested",
        lambda d, j: cancel_state["cancelled"],
    )
    monkeypatch.setattr(
        test_execution, "_cancel_check_factory", lambda j: lambda: False,
    )

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=3)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_failure is False
    assert has_error is False
    assert case_runs[0].status == TestCaseRunStatus.PASSED.value
    assert case_runs[1].status == TestCaseRunStatus.NOT_EXECUTED.value
    assert case_runs[2].status == TestCaseRunStatus.NOT_EXECUTED.value


def test_execute_env_set_pre_env_cancel_propagates_without_unbound_local(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pre_env 期间取消：原始 job_cancelled 正常传播，finally 的 post_env 探针
    门不得因 vm_recovery_used 未赋值抛 UnboundLocalError（job 10244/10245 实证
    bug：取消被吞、任务误标 unexpected_execution_error、用例滞留 pending）。
    """
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)

    def fake_run_hook(
        db, *, job, control, directory, script_name, phase,
        error_code="hook_failed", cancel_event=None,
    ):
        if script_name == "pre_env.sh":
            raise TestJobExecutionError("job_cancelled", "测试任务已取消")
        return None

    monkeypatch.setattr(test_execution, "run_hook", fake_run_hook)
    # 宿主通道非空 → finally 探针门会求值 not vm_recovery_used（bug 触发条件）
    monkeypatch.setattr(
        test_execution, "vm_host_channel", lambda db, control: ("h", "v", "k")
    )
    monkeypatch.setattr(test_execution, "ssh_connect_refused", lambda control: False)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=2)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    job.pre_env_script = "echo pre"
    job.post_env_script = "echo post"
    db_session.commit()

    with pytest.raises(TestJobExecutionError) as exc_info:
        test_execution.execute_env_set(
            db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
        )

    assert exc_info.value.code == "job_cancelled"


def test_run_case_cancel_marks_not_executed(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cancel detected after command → case marked not_executed, no exception."""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1", username="root", password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    scripts: list[str] = []

    def fake_run_control_command(*, script: str, **_: object) -> RemoteCommandResult:
        scripts.append(script)
        return RemoteCommandResult(returncode=1, stdout="", stderr="killed")

    monkeypatch.setattr(
        mugen_runner, "run_control_command",
        fake_run_control_command,
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
            return False

    monkeypatch.setattr(mugen_runner, "HangDetector", lambda **_: FakeDetector())

    mugen_runner.run_case(
        db_session, job=job, control=control, case_run=case_run,
        cancel_check=lambda: True,
    )

    assert case_run.status == TestCaseRunStatus.NOT_EXECUTED.value
    assert "pkill -f mugen.sh || true" in scripts


def test_run_case_soft_cancel_event_marks_not_executed_and_raises(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cancel_event 被外部（如 Soft 或 job 级取消）set → run_control_command
    返回 cancelled=True 且无 DB hit / 无 hang → 本 case 收敛为 not_executed,
    抛 job_cancelled 让主线程独占终态决定权(Soft 会覆盖成 task_timeout,
    DB cancel 会覆盖成 cancelled)。
    """
    import threading

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1", username="root", password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )
    cancel_event = threading.Event()

    def _fake_run(**kwargs: object) -> RemoteCommandResult:
        # 模拟 run_process 2s 内看到附加的 job 级取消信号后 kill sshpass 返回。
        if cancel_event in kwargs.get("cancel_events", ()):
            cancel_event.set()
            return RemoteCommandResult(
                returncode=None, stdout="", stderr="", cancelled=True
            )
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    class FakeDetector:
        @staticmethod
        def start() -> None:
            pass

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return False

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(mugen_runner, "run_control_command", _fake_run)
    monkeypatch.setattr(mugen_runner, "HangDetector", lambda **_: FakeDetector())

    with pytest.raises(TestJobExecutionError) as exc_info:
        mugen_runner.run_case(
            db_session,
            job=job,
            control=control,
            case_run=case_run,
            cancel_check=lambda: False,
            cancel_event=cancel_event,
        )

    assert exc_info.value.code == "job_cancelled"
    # 与 DB cancel 语义一致:被终止的 case 标 not_executed,不留在 RUNNING
    assert case_run.status == TestCaseRunStatus.NOT_EXECUTED.value


def test_run_case_hang_does_not_cancel_the_test_job(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HangDetector 只中断当前 case，不能取消整个 TestJob。"""
    import threading

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = SimpleNamespace(
        ip="1.1.1.1", username="root", password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )
    cancel_event = threading.Event()
    captured_on_hung: list = []

    class FakeDetector:
        def __init__(self, *, check_fn, interval=30.0, max_failures=5, on_hung=None, **_extra):  # noqa: ANN001
            captured_on_hung.append(on_hung)

        @staticmethod
        def start() -> None:
            # 模拟达到 max_failures → 触发 on_hung(真实 detector 会自己调)
            if captured_on_hung and captured_on_hung[0] is not None:
                captured_on_hung[0]()

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return True

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner, "run_control_command",
        lambda **_: RemoteCommandResult(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(mugen_runner, "HangDetector", lambda **kw: FakeDetector(**kw))
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(
            db_session,
            job=job,
            control=control,
            case_run=case_run,
            cancel_event=cancel_event,
        )

    assert captured_on_hung and captured_on_hung[0] is not None
    assert not cancel_event.is_set()


def test_map_job_status_cancelled() -> None:
    """_map_job_status maps CANCELLED to 'cancelled'."""
    from app.modules.pipelines.framework_executors.mugen import _map_job_status
    from app.modules.test_management.models import TestJobStatus

    assert _map_job_status(TestJobStatus.CANCELLED.value) == "cancelled"


# ---------- DirectRunPipelineStrategy + registry dispatch ----------


def _seed_pipeline_type(db, *, name, strategy_kind, framework="mugen"):
    pt = PipelineType(
        name=name,
        display_name=name,
        strategy_kind=strategy_kind,
        test_framework=framework,
        is_system=True,
        default_config={},
    )
    db.add(pt)
    db.flush()
    return pt


def _make_release_config(
    db,
    *,
    suites,
    versions,
    archs,
    case_names_map=None,
    kernel_variant=None,
    kernel_rpm_url=None,
    physical_enabled=None,
):
    """release config：config_data.case_selections（每个 suite → {suite_name, case_names}）。

    case_names_map 可按 suite 给定选中 case 名；未给定的 suite 用空列表（等价全选）。
    """
    case_selections = [
        {"suite_name": s, "case_names": (case_names_map or {}).get(s, [])}
        for s in suites
    ]
    config_data = {"case_selections": case_selections}
    if physical_enabled is not None:
        config_data["release_physical_enabled"] = physical_enabled
    if kernel_variant:
        config_data["kernel_variant"] = kernel_variant
    if kernel_rpm_url:
        config_data["kernel_rpm_url"] = kernel_rpm_url
    config = PipelineConfig(
        name="release-cfg",
        pipeline_type="release",
        versions=versions,
        archs=archs,
        config_data=config_data,
        dist="openEuler",
        image_round="round-9",
    )
    db.add(config)
    db.flush()
    return config


def test_direct_run_strategy_creates_runjob_per_arch(
    db_session: Session,
) -> None:
    """release RunJob 形状：每架构一个 RunJob（全部选中 suite 的 case 共一套环境）。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    config = _make_release_config(
        db_session,
        suites=["smoke", "ltp"],
        versions=["24.03-LTS-SP3"],
        archs=["aarch64", "x86_64"],
    )
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64", "x86_64"],
    )
    db_session.add(execution)
    db_session.flush()

    strategy = get_pipeline_strategy(db_session, "release")
    run_jobs = strategy.plan_run_jobs(
        db_session,
        config=config,
        execution=execution,
        versions=["24.03-LTS-SP3"],
        archs=["aarch64", "x86_64"],
        triggered_by="admin",
    )

    # 1 version × 2 archs = 2 RunJobs（per-arch；跨 suite 全部 case 共一套环境）
    assert len(run_jobs) == 2
    assert {rj.arch for rj in run_jobs} == {"aarch64", "x86_64"}

    # 1 version → 1 PipelineRun
    runs = list(
        db_session.execute(select(PipelineRun).where(PipelineRun.execution_id == execution.id))
        .scalars()
        .all()
    )
    assert len(runs) == 1

    # All RunJobs have env_type=None (no split for direct_run)
    assert all(rj.env_type is None for rj in run_jobs)

    # All RunJobs point to the single release template（跨 suite 共一个模板）
    template_ids = {rj.module_template_id for rj in run_jobs}
    assert len(template_ids) == 1
    template = db_session.get(TestModuleTemplate, next(iter(template_ids)))
    assert template.name == "release"
    assert template.pipeline_type == "release"
    assert template.post_env_script  # 默认 post_env 非空（日志拷贝）


def test_direct_run_strategy_idempotent_on_template(db_session: Session) -> None:
    """Re-triggering release should reuse the single release template, not duplicate."""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    config = _make_release_config(db_session, suites=["smoke"], versions=["v1"], archs=["x86_64"])
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution)
    db_session.flush()

    strategy = get_pipeline_strategy(db_session, "release")
    strategy.plan_run_jobs(
        db_session,
        config=config,
        execution=execution,
        versions=["v1"],
        archs=["x86_64"],
    )

    templates_after_first = list(
        db_session.execute(
            select(TestModuleTemplate).where(TestModuleTemplate.name == "release")
        )
        .scalars()
        .all()
    )
    assert len(templates_after_first) == 1

    # Second trigger should reuse the same template
    execution2 = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution2)
    db_session.flush()
    strategy.plan_run_jobs(
        db_session,
        config=config,
        execution=execution2,
        versions=["v1"],
        archs=["x86_64"],
    )

    templates_after_second = list(
        db_session.execute(
            select(TestModuleTemplate).where(TestModuleTemplate.name == "release")
        )
        .scalars()
        .all()
    )
    assert len(templates_after_second) == 1  # No duplication


def test_release_builder_selects_cases_and_snapshots_kernel_extras(
    db_session: Session,
) -> None:
    """release (direct_run)：case 级选择 + node_num=max + 默认 post_env + 内核参数快照。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_a", node_num=1)
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_b", node_num=1)
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_c", node_num=2)
    config = _make_release_config(
        db_session,
        suites=["smoke"],
        versions=["24.03-LTS-SP3"],
        archs=["x86_64"],
        case_names_map={"smoke": ["oe_test_a", "oe_test_c"]},
        kernel_variant="26.09-with-kernel-6.18",
    )
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
        versions=["24.03-LTS-SP3"],
        archs=["x86_64"],
    )
    db_session.add(execution)
    db_session.flush()

    strategy = get_pipeline_strategy(db_session, "release")
    run_jobs = strategy.plan_run_jobs(
        db_session,
        config=config,
        execution=execution,
        versions=["24.03-LTS-SP3"],
        archs=["x86_64"],
        triggered_by="admin",
    )
    assert len(run_jobs) == 1  # 1 suite × 1 arch
    run_job = run_jobs[0]
    template = db_session.get(TestModuleTemplate, run_job.module_template_id)

    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version="24.03-LTS-SP3",
        actor_user_id="admin",
    )

    # case selection: only the two selected cases (not oe_test_b)
    assert {cr.case_name for cr in job.case_runs} == {"oe_test_a", "oe_test_c"}
    # env_set node_num = max(selected cases' node_num) = 2
    assert len(job.env_sets) == 1
    assert job.env_sets[0].node_num == 2
    # default post_env_script non-empty (log copy)
    assert job.post_env_script and "${OET_PATH}" in job.post_env_script
    # kernel variant snapshotted into pipeline_extras
    assert job.pipeline_extras == {"kernel_variant": "26.09-with-kernel-6.18"}


def test_release_builder_empty_case_names_selects_all(db_session: Session) -> None:
    """case_names 空列表等价全选（spec §9.1）。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_a")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_b")
    config = _make_release_config(
        db_session, suites=["smoke"], versions=["v1"], archs=["x86_64"]
    )  # case_names_map omitted → smoke gets [] → all
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution)
    db_session.flush()
    strategy = get_pipeline_strategy(db_session, "release")
    run_jobs = strategy.plan_run_jobs(
        db_session, config=config, execution=execution,
        versions=["v1"], archs=["x86_64"], triggered_by="admin",
    )
    template = db_session.get(TestModuleTemplate, run_jobs[0].module_template_id)
    job = build_test_job_for_run_job(
        db_session, run_job=run_jobs[0], config=config, template=template,
        version="v1", actor_user_id="admin",
    )
    assert {cr.case_name for cr in job.case_runs} == {"oe_test_a", "oe_test_b"}
    assert job.pipeline_extras is None  # no kernel params → None


def test_release_builder_gathers_cases_across_suites_into_one_env(
    db_session: Session,
) -> None:
    """每架构一套环境：多个 suite 的选中 case 汇总进同一个 TestJob/env_set。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_smoke_a", node_num=1)
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_smoke_b", node_num=1)
    _seed_mugen_case(db_session, suite_name="ltp", case_name="oe_test_ltp", node_num=2)
    config = _make_release_config(
        db_session,
        suites=["smoke", "ltp"],
        versions=["v1"],
        archs=["x86_64"],
        case_names_map={"smoke": ["oe_test_smoke_a"], "ltp": []},  # smoke 子集 + ltp 全选
    )
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution)
    db_session.flush()
    strategy = get_pipeline_strategy(db_session, "release")
    run_jobs = strategy.plan_run_jobs(
        db_session, config=config, execution=execution,
        versions=["v1"], archs=["x86_64"], triggered_by="admin",
    )
    assert len(run_jobs) == 1  # 1 arch → 1 RunJob（跨 suite 全部 case 共一套环境）
    template = db_session.get(TestModuleTemplate, run_jobs[0].module_template_id)
    job = build_test_job_for_run_job(
        db_session, run_job=run_jobs[0], config=config, template=template,
        version="v1", actor_user_id="admin",
    )
    # 跨 suite 汇总：smoke 选中 oe_test_smoke_a（非 b）+ ltp 全选 oe_test_ltp
    assert {cr.case_name for cr in job.case_runs} == {"oe_test_smoke_a", "oe_test_ltp"}
    assert {cr.suite_name for cr in job.case_runs} == {"smoke", "ltp"}
    # 单 env_set，node_num = max(全部选中 case node_num) = max(1, 2) = 2
    assert len(job.env_sets) == 1
    assert job.env_sets[0].node_num == 2


def test_release_builder_physical_toggle_off_skips_as_not_executed(
    db_session: Session,
) -> None:
    """release 全量跑（物理开关关）：物理机用例跳过为物理 NOT_EXECUTED 环境集呈现。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_smoke_a", node_num=1)
    _seed_mugen_case(
        db_session,
        suite_name="smoke",
        case_name="oe_test_smoke_phys",
        env_type="physical",
        node_num=1,
    )
    _seed_mugen_case(db_session, suite_name="ltp", case_name="oe_test_ltp", node_num=2)
    config = _make_release_config(
        db_session,
        suites=["smoke", "ltp"],
        versions=["v1"],
        archs=["x86_64"],
        case_names_map={"smoke": [], "ltp": []},  # 全选
        physical_enabled=False,
    )
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution)
    db_session.flush()
    strategy = get_pipeline_strategy(db_session, "release")
    run_jobs = strategy.plan_run_jobs(
        db_session, config=config, execution=execution,
        versions=["v1"], archs=["x86_64"], triggered_by="admin",
    )
    template = db_session.get(TestModuleTemplate, run_jobs[0].module_template_id)
    assert template.env_type == "both"  # release 模板升级为 both
    job = build_test_job_for_run_job(
        db_session, run_job=run_jobs[0], config=config, template=template,
        version="v1", actor_user_id="admin",
    )
    # VM 环境集：仅 vm 用例（物理用例不进 VM 环境）
    vm_sets = [es for es in job.env_sets if es.env_type == "vm"]
    assert len(vm_sets) == 1
    vm_case_runs = [
        cr for cr in job.case_runs if cr.env_set_id == vm_sets[0].id
    ]
    assert {cr.case_name for cr in vm_case_runs} == {"oe_test_smoke_a", "oe_test_ltp"}
    # 物理用例：独立 NOT_EXECUTED 物理环境集（可见的跳过，不建节点）
    phys_sets = [es for es in job.env_sets if es.env_type == "physical"]
    assert len(phys_sets) == 1
    assert phys_sets[0].node_num == 0
    assert phys_sets[0].status == "not_executed"
    phys_case_runs = [
        cr for cr in job.case_runs if cr.env_set_id == phys_sets[0].id
    ]
    assert {cr.case_name for cr in phys_case_runs} == {"oe_test_smoke_phys"}
    assert {cr.status for cr in phys_case_runs} == {"not_executed"}


def test_release_builder_physical_toggle_on_creates_executable_env(
    db_session: Session,
) -> None:
    """release 全量跑（物理开关开）：物理用例进可执行物理环境集（建节点）。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    _seed_mugen_case(db_session, suite_name="smoke", case_name="oe_test_smoke_a", node_num=1)
    _seed_mugen_case(
        db_session,
        suite_name="smoke",
        case_name="oe_test_smoke_phys",
        env_type="physical",
        node_num=2,
    )
    config = _make_release_config(
        db_session,
        suites=["smoke"],
        versions=["v1"],
        archs=["x86_64"],
        case_names_map={"smoke": []},  # 全选
        physical_enabled=True,
    )
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution)
    db_session.flush()
    strategy = get_pipeline_strategy(db_session, "release")
    run_jobs = strategy.plan_run_jobs(
        db_session, config=config, execution=execution,
        versions=["v1"], archs=["x86_64"], triggered_by="admin",
    )
    template = db_session.get(TestModuleTemplate, run_jobs[0].module_template_id)
    job = build_test_job_for_run_job(
        db_session, run_job=run_jobs[0], config=config, template=template,
        version="v1", actor_user_id="admin",
    )
    # vm 用例与物理用例各一个环境集
    assert len(job.env_sets) == 2
    vm_sets = [es for es in job.env_sets if es.env_type == "vm"]
    phys_sets = [es for es in job.env_sets if es.env_type == "physical"]
    assert len(vm_sets) == 1 and len(phys_sets) == 1
    # 物理环境集可执行：节点数 = max(物理用例 node_num) = 2，状态非 NOT_EXECUTED
    assert phys_sets[0].node_num == 2
    assert phys_sets[0].status != "not_executed"
    assert len(phys_sets[0].nodes) == 2
    phys_case_runs = [
        cr for cr in job.case_runs if cr.env_set_id == phys_sets[0].id
    ]
    assert {cr.case_name for cr in phys_case_runs} == {"oe_test_smoke_phys"}


def test_release_plan_run_jobs_rejects_multi_version(db_session: Session) -> None:
    """release 为单版本配置；plan_run_jobs 对多版本触发级覆盖 raise（defense-in-depth）。"""
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    config = _make_release_config(
        db_session, suites=["smoke"], versions=["v1"], archs=["x86_64"]
    )
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["v1"], archs=["x86_64"]
    )
    db_session.add(execution)
    db_session.flush()
    strategy = get_pipeline_strategy(db_session, "release")
    with pytest.raises(ValueError, match="单版本"):
        strategy.plan_run_jobs(
            db_session, config=config, execution=execution,
            versions=["v1", "v2"], archs=["x86_64"], triggered_by="admin",
        )


def test_create_env_node_vm_passes_kernel_extras_to_vm_request(
    db_session: Session,
    monkeypatch,
) -> None:
    """create_env_node_vm 从 job.pipeline_extras 读内核参数透传 VMRequestCreate（release）。

    update 的 job.pipeline_extras 为 None → 透传 None，不换内核（非干扰）。
    """
    from app.modules.test_management.envs import vm as env_vm
    from app.modules.users.models import User

    captured: dict = {}

    def fake_create_vm_request(db, *, actor, payload):  # noqa: ANN001
        captured["payload"] = payload
        return SimpleNamespace(id="fake-req-id")

    monkeypatch.setattr(env_vm, "create_vm_request", fake_create_vm_request)
    monkeypatch.setattr(env_vm, "process_vm_request", lambda *a, **k: None)

    user = User(id="user-1", username="u", role="ADMIN", password_hash="x")
    db_session.add(user)
    db_session.flush()
    job = TestJob(
        creator_user_id="user-1",
        name="release-job",
        status="pending",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-9",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
        keep_failed_env=False,
        keep_env=True,
        pre_env_script="",
        rerun_env_script="",
        post_env_script="",
        result_parser="mugen_results",
        update_packages=[],
        pipeline_extras={"kernel_variant": "26.09-with-kernel-6.18"},
    )
    db_session.add(job)
    db_session.flush()
    env_set = TestEnvSet(
        job_id=job.id,
        set_index=1,
        status=TestEnvSetStatus.RUNNING.value,
        node_num=1,
        env_type="vm",
        add_disk_num=0,
        add_nic_num=0,
    )
    db_session.add(env_set)
    db_session.flush()
    node = TestEnvNode(
        env_set_id=env_set.id,
        node_index=1,
        role="control",
        status=TestEnvNodeStatus.CREATING.value,
    )
    db_session.add(node)
    db_session.flush()

    # 函数在捕获 payload 后会因无真实 VMRequest 行而 raise，但 payload 已捕获。
    with pytest.raises(TestJobExecutionError):
        env_vm.create_env_node_vm(
            db_session, job=job, env_set=env_set, node=node, actor=user
        )

    payload = captured["payload"]
    assert payload.kernel_variant == "26.09-with-kernel-6.18"
    assert payload.kernel_rpm_url is None


def test_get_pipeline_strategy_dispatches_by_strategy_kind(
    db_session: Session,
) -> None:
    _seed_pipeline_type(db_session, name="update", strategy_kind="update_strategy")
    _seed_pipeline_type(db_session, name="release", strategy_kind="direct_run")
    _seed_pipeline_type(db_session, name="smoke", strategy_kind="direct_run")

    from app.modules.pipelines.pipeline_strategies.direct_run import (
        DirectRunPipelineStrategy,
    )
    from app.modules.pipelines.pipeline_strategies.update import (
        UpdatePipelineStrategy,
    )

    assert isinstance(get_pipeline_strategy(db_session, "update"), UpdatePipelineStrategy)
    assert isinstance(get_pipeline_strategy(db_session, "release"), DirectRunPipelineStrategy)
    # Different pipeline_type names with same strategy_kind return same strategy class
    assert isinstance(get_pipeline_strategy(db_session, "smoke"), DirectRunPipelineStrategy)


def test_get_pipeline_strategy_unknown_type_raises(db_session: Session) -> None:
    with pytest.raises(ValueError, match="unknown pipeline_type: nope"):
        get_pipeline_strategy(db_session, "nope")


def test_get_pipeline_strategy_unknown_strategy_kind_raises(
    db_session: Session,
) -> None:
    _seed_pipeline_type(db_session, name="weird", strategy_kind="some_future_kind")
    with pytest.raises(ValueError, match="unknown strategy_kind"):
        get_pipeline_strategy(db_session, "weird")


def _seed_64k_job(db, *, os_version: str):
    """建 job + env_set + node + 2 case_run，用于测试未转测状态收敛。"""
    from app.modules.test_management.models import utc_now

    job = TestJob(
        creator_user_id="admin",
        name="tj-64k",
        status="running",
        framework="mugen",
        env_type=TestEnvType.VM.value,
        dist="openEuler",
        os_version=os_version,
        image_round="round-9",
        arch="aarch64",
        mugen_commit_sha="abc",
        env_set_num=1,
        keep_env=True,
        created_at=utc_now(),
    )
    db.add(job)
    db.flush()
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db.add(env_set)
    db.flush()
    db.add(
        TestEnvNode(
            env_set_id=env_set.id,
            node_index=0,
            role="control",
            status=TestEnvNodeStatus.CREATING.value,
        )
    )
    for suite, case in [("s1", "c1"), ("s2", "c2")]:
        db.add(
            TestCaseRun(
                job_id=job.id,
                env_set_id=env_set.id,
                suite_name=suite,
                case_name=case,
                status="pending",
            )
        )
    db.commit()
    return job, env_set


def test_mark_env_set_not_executed_is_scoped_to_current_env_set(
    db_session: Session,
) -> None:
    """结构化未转测只收敛当前 EnvSet，不读取全局任务事件。"""
    from app.modules.test_management.execution import _mark_env_set_not_executed

    _job, env_set = _seed_64k_job(db_session, os_version="openEuler-24.03-LTS-SP4-64k")
    _, other_env_set = _seed_64k_job(db_session, os_version="openEuler-24.03-LTS-SP4-64k")

    _mark_env_set_not_executed(db_session, env_set=env_set)

    cases = (
        db_session.execute(select(TestCaseRun).where(TestCaseRun.env_set_id == env_set.id))
        .scalars()
        .all()
    )
    assert all(c.status == TestCaseRunStatus.NOT_EXECUTED.value for c in cases), [
        c.status for c in cases
    ]
    db_session.refresh(env_set)
    assert env_set.status == TestEnvSetStatus.NOT_EXECUTED.value
    assert all(node.status == TestEnvNodeStatus.NOT_EXECUTED.value for node in env_set.nodes)
    assert other_env_set.status == TestEnvSetStatus.PENDING.value


def test_execute_env_set_stops_before_prepare_when_64k_is_not_transferred(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """环境创建返回未转测时，直接收敛状态且不进入测试准备。"""
    from app.modules.test_management import execution as test_execution

    _job, env_set = _seed_64k_job(
        db_session,
        os_version="openEuler-24.03-LTS-SP4-64k",
    )
    monkeypatch.setattr(test_execution, "create_env_node_vm", lambda *_, **__: False)
    monkeypatch.setattr(
        test_execution,
        "prepare_env",
        lambda *_, **__: pytest.fail("not-transferred environment must not be prepared"),
    )

    result = test_execution.execute_env_set(
        db_session,
        job=_job,
        env_set=env_set,
        actor=SimpleNamespace(id="admin"),
    )

    assert result == (False, False)
    assert env_set.status == TestEnvSetStatus.NOT_EXECUTED.value
    assert all(
        case.status == TestCaseRunStatus.NOT_EXECUTED.value for case in env_set.case_runs
    )


def _make_update_config(
    db,
    *,
    versions,
    archs,
    template_ids=None,
):
    _seed_pipeline_type(db, name="update", strategy_kind="update_strategy")
    config = PipelineConfig(
        name="update-cfg",
        pipeline_type="update",
        versions=versions,
        archs=archs,
        config_data={"module_template_ids": template_ids or []},
        dist="openEuler",
        image_round="",
    )
    db.add(config)
    db.flush()
    return config


def _make_template(db, *, name="t", env_type="vm"):
    tmpl = TestModuleTemplate(
        name=name,
        display_name=name,
        suite_name="s",
        pipeline_type="update",
        env_set_num=1,
        node_num=1,
        case_filter="none",
        env_type=env_type,
        skip_packages=[],
        pre_env_script="",
        post_env_script="",
        mugen_exec_command=None,
        result_parser="mugen_results",
        test_framework="mugen",
    )
    db.add(tmpl)
    db.flush()
    return tmpl


def test_update_strategy_skips_64k_x86_64(
    db_session: Session,
) -> None:
    """-64k 版本 × x86_64 架构 → 不创建 RunJob。"""
    from app.modules.pipelines.pipeline_strategies.update import (
        UpdatePipelineStrategy,
    )

    tmpl = _make_template(db_session)
    config = _make_update_config(
        db_session,
        versions=["openEuler-24.03-LTS-SP4", "openEuler-24.03-LTS-SP4-64k"],
        archs=["aarch64", "x86_64"],
        template_ids=[tmpl.id],
    )
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
    )
    db_session.add(execution)
    db_session.flush()

    strategy = UpdatePipelineStrategy()
    run_jobs = strategy.plan_run_jobs(
        db_session,
        config=config,
        execution=execution,
        versions=config.versions,
        archs=config.archs,
    )

    # 2403sp4 × aarch64 + 2403sp4 × x86_64 + 2403sp4-64k × aarch64 = 3
    # 2403sp4-64k × x86_64 should be skipped
    assert len(run_jobs) == 3, [rj.arch for rj in run_jobs]
    # RunJob has no version field; verify via the associated PipelineRun.
    run_ids = {rj.pipeline_run_id for rj in run_jobs}
    runs = (
        db_session.execute(select(PipelineRun).where(PipelineRun.id.in_(run_ids))).scalars().all()
    )
    run_by_version = {r.version: r for r in runs}
    # Two PipelineRuns: one for 2403sp4, one for 2403sp4-64k
    assert len(runs) == 2
    # 2403sp4 has 2 RunJobs (aarch64 + x86_64)
    sp4_id = run_by_version["openEuler-24.03-LTS-SP4"].id
    sp4_jobs = [rj for rj in run_jobs if rj.pipeline_run_id == sp4_id]
    assert len(sp4_jobs) == 2
    assert {rj.arch for rj in sp4_jobs} == {"aarch64", "x86_64"}
    # 2403sp4-64k has 1 RunJob (aarch64 only)
    k64k_id = run_by_version["openEuler-24.03-LTS-SP4-64k"].id
    k64k_jobs = [rj for rj in run_jobs if rj.pipeline_run_id == k64k_id]
    assert len(k64k_jobs) == 1
    assert k64k_jobs[0].arch == "aarch64"


def test_update_strategy_non_64k_creates_all_combinations(
    db_session: Session,
) -> None:
    """非 -64k 版本 → 全部版本×架构组合都创建。"""
    from app.modules.pipelines.pipeline_strategies.update import (
        UpdatePipelineStrategy,
    )

    tmpl = _make_template(db_session)
    config = _make_update_config(
        db_session,
        versions=["openEuler-22.03-LTS-SP4"],
        archs=["aarch64", "x86_64"],
        template_ids=[tmpl.id],
    )
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
    )
    db_session.add(execution)
    db_session.flush()

    strategy = UpdatePipelineStrategy()
    run_jobs = strategy.plan_run_jobs(
        db_session,
        config=config,
        execution=execution,
        versions=config.versions,
        archs=config.archs,
    )

    assert len(run_jobs) == 2


def _make_job_for_runner(
    db_session: Session,
    *,
    mugen_exec_command: str | None = None,
    pre_env_script: str | None = None,
    post_env_script: str | None = None,
) -> TestJob:
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
        mugen_exec_command=mugen_exec_command,
        pre_env_script=pre_env_script,
        post_env_script=post_env_script,
    )
    db_session.add(job)
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    db_session.add(env_set)
    db_session.commit()
    return job


def _ok_result() -> RemoteCommandResult:
    return RemoteCommandResult(returncode=0, stdout="", stderr="")


def _event_phases(db_session: Session, job_id: int) -> list[str]:
    rows_rows = (
        db_session.execute(
            select(TaskEvent).where(TaskEvent.subject_id == str(job_id))
        ).scalars().all()
    )
    return [
        e.phase
        for e in rows_rows
    ]


def test_prepare_env_records_ssh_ready_done(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """prepare_env 成功后记 ssh_ready_done。"""
    job = _make_job_for_runner(db_session, mugen_exec_command="docker exec ...")
    control = SimpleNamespace(
        ip="1.1.1.1", username="root", password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )
    monkeypatch.setattr(mugen_runner, "wait_for_ssh_ready", lambda *a, **kw: None)
    monkeypatch.setattr(mugen_runner, "write_control_file", lambda **kw: None)
    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **kw: _ok_result())

    mugen_runner.prepare_env(
        db_session, job=job, env_set=job.env_sets[0], control=control, peer=None
    )

    phases = _event_phases(db_session, job.id)
    assert "ssh_ready" in phases
    assert "ssh_ready_done" in phases


def test_prepare_mugen_records_done(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """prepare_mugen 成功后记 mugen_prepare_done。"""
    job = _make_job_for_runner(db_session)
    control = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **kw: _ok_result())
    monkeypatch.setattr(mugen_runner, "job_step_timeout", lambda *a, **kw: 60)

    mugen_runner.prepare_mugen(db_session, job=job, control=control)

    phases = _event_phases(db_session, job.id)
    assert "mugen_prepare" in phases
    assert "mugen_prepare_done" in phases


def test_configure_mugen_node_records_done(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """configure_mugen_node 成功后记 mugen_config_done。"""
    job = _make_job_for_runner(db_session)
    control = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    node = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **kw: _ok_result())
    monkeypatch.setattr(mugen_runner, "job_step_timeout", lambda *a, **kw: 120)
    monkeypatch.setattr("time.sleep", lambda *_: None)

    mugen_runner.configure_mugen_node(
        db_session, job=job, control=control, node=node, role="control"
    )

    phases = _event_phases(db_session, job.id)
    assert "mugen_config" in phases
    assert "mugen_config_done" in phases


def test_configure_mugen_node_raises_job_cancelled_when_result_cancelled(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """configure_mugen_node:run_control_command 返回 cancelled=True 或
    cancel_event 已 set 时立即抛 job_cancelled,不重试、不 sleep。
    """
    import threading

    job = _make_job_for_runner(db_session)
    control = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    node = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    cancel_event = threading.Event()

    def _fake_run_control(**kwargs):
        cancel_event.set()
        return RemoteCommandResult(returncode=None, stdout="", stderr="", cancelled=True)

    sleeps: list[float] = []
    monkeypatch.setattr(mugen_runner, "run_control_command", _fake_run_control)
    monkeypatch.setattr(mugen_runner, "job_step_timeout", lambda *a, **kw: 120)
    monkeypatch.setattr(mugen_runner.time, "sleep", sleeps.append)

    with pytest.raises(TestJobExecutionError) as exc_info:
        mugen_runner.configure_mugen_node(
            db_session,
            job=job,
            control=control,
            node=node,
            role="control",
            cancel_event=cancel_event,
        )

    assert exc_info.value.code == "job_cancelled"
    assert sleeps == []


def test_run_hook_records_done(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_hook 成功后记 {phase}_done。"""
    job = _make_job_for_runner(db_session, pre_env_script="echo hi", post_env_script="echo bye")
    control = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **kw: _ok_result())
    monkeypatch.setattr(mugen_runner, "job_step_timeout", lambda *a, **kw: 60)

    mugen_runner.run_hook(
        db_session, job=job, control=control, directory="/tmp",
        script_name="pre_env.sh", phase="pre_env",
    )

    phases = _event_phases(db_session, job.id)
    assert "pre_env" in phases
    assert "pre_env_done" in phases


# ---------- VM 带外判活与宿主机恢复（ADR 0046） ----------


def _vm_control_with_host(
    db: Session, *, with_channel: bool = True, vm_name: str = "vm-1"
) -> SimpleNamespace:
    """构造带真实 Resource/VirtualResourceSpec 的 VM control。

    回归锁必须用真实 ORM 形态：宿主信息在 virtual_spec 上而不是 Resource 上。
    """
    from uuid import uuid4

    from app.modules.resources.models import VirtualResourceSpec

    vm_resource = Resource(
        resource_code=f"vm-{uuid4().hex[:8]}",
        resource_type="virtual",
        ssh_username="root",
        ssh_password_ciphertext="cipher",
        primary_ip="10.0.0.2",
    )
    db.add(vm_resource)
    db.flush()
    if with_channel:
        host = Resource(
            resource_code=f"host-{uuid4().hex[:8]}",
            resource_type="physical",
            ssh_username="root",
            ssh_password_ciphertext="cipher",
            primary_ip="10.0.0.1",
        )
        db.add(host)
        db.flush()
        vm_resource.virtual_spec = VirtualResourceSpec(
            vm_name=vm_name, host_resource_id=host.id
        )
    else:
        vm_resource.virtual_spec = VirtualResourceSpec(vm_name=vm_name, host_resource_id=None)
    db.commit()
    return SimpleNamespace(ip="10.0.0.2", username="root", password="p", resource=vm_resource)


def testvm_host_channel_resolves_from_virtual_spec(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """回归锁：宿主通道从 virtual_spec 解析——修复前 getattr(resource,...) 恒 None，
    VM console 取证与带外判活从未生效（SimpleNamespace 假对象掩盖了该缺陷）。
    """
    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    control = _vm_control_with_host(db_session)
    assert mugen_runner.vm_host_channel(db_session, control) == ("10.0.0.1", "vm-1", "/test-key")

    # 无宿主引用
    control_no_host = _vm_control_with_host(db_session, with_channel=False)
    assert mugen_runner.vm_host_channel(db_session, control_no_host) is None

    # 物理机不走 VM 通道
    assert mugen_runner.vm_host_channel(db_session, _bmc_control()) is None


def test_capture_console_vm_with_real_resource_uses_host_channel(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """回归锁（修复）：真实 VM Resource 挂死取证走宿主机 virsh console 分支。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    captured: dict[str, object] = {}
    stores: list[dict] = []

    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(
            vm_host_ssh_key_path="/test-key", pipeline_log_dir="/tmp/kronos-test-logs"
        ),
    )

    def fake_capture(*, host_ip, vm_name, ssh_key_path):
        captured.update(host_ip=host_ip, vm_name=vm_name, ssh_key_path=ssh_key_path)
        return "=== virsh domstate ===\nrunning"

    monkeypatch.setattr(mugen_runner, "capture_vm_console_output", fake_capture)

    class FakeCollector:
        def __init__(self, *, base_dir):  # noqa: ANN001
            pass

        @staticmethod
        def store_artifact(**kw):  # noqa: ANN003
            stores.append(kw)

    monkeypatch.setattr(mugen_runner, "LogCollector", FakeCollector)

    _capture_and_store_console(
        db_session, job=job, control=control, case_run=case_run
    )

    assert captured == {"host_ip": "10.0.0.1", "vm_name": "vm-1", "ssh_key_path": "/test-key"}
    assert stores and stores[0]["artifact_type"] == "console_diagnostic"


def test_run_case_vm_with_host_channel_builds_domstate_gate(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VM 有宿主通道 → HangDetector 拿到 domstate 确认门；无通道维持无门。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    captured: dict[str, object] = {}

    class FakeDetector:
        def __init__(self, **kw: object) -> None:
            captured.update(kw)

        @staticmethod
        def start() -> None:
            pass

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return True

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(mugen_runner, "HangDetector", FakeDetector)
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert captured.get("confirm_fn") is not None
    assert captured.get("on_watch_start") is not None
    assert captured.get("on_recovered") is not None


def test_run_case_vm_domstate_alive_watches_and_selfheals(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sssd 场景回放：domstate 活着 → 观察模式 → SSH 恢复 → 用例拿回真实结果。"""
    import threading

    import app.modules.test_management.hang_detector as hang_detector_module

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    events: list[tuple[str | None, str | None]] = []
    artifacts: list[str | None] = []
    recovered_event = threading.Event()

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(mugen_runner, "vm_domstate_alive", lambda **_kw: True)
    monkeypatch.setattr(mugen_runner, "capture_vm_console_output", lambda **_kw: "console")
    monkeypatch.setattr(
        mugen_runner,
        "_record_hang_watch_event",
        lambda _job_id, **kw: (
            events.append((kw.get("phase"), kw.get("message"))),
            recovered_event.set() if kw.get("phase") == "hang_recovered" else None,
        ),
    )
    monkeypatch.setattr(
        mugen_runner,
        "_store_hang_watch_artifact",
        lambda **kw: artifacts.append(kw.get("artifact_name")),
    )
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: (
            recovered_event.wait(timeout=5),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        )[1],
    )

    probe_count = [0]

    def fake_ssh_alive(_control: object, _stats: object = None) -> bool:
        probe_count[0] += 1
        return probe_count[0] > 5

    monkeypatch.setattr(mugen_runner, "_ssh_alive", fake_ssh_alive)
    real_hang_detector = mugen_runner.HangDetector

    def fast_detector(**kw: object) -> object:
        return real_hang_detector(interval=0.02, max_failures=3, **kw)

    monkeypatch.setattr(mugen_runner, "HangDetector", fast_detector)
    monkeypatch.setattr(mugen_runner, "_parse_and_store_subcases", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "_per_case_collect_log", lambda *_, **__: None)
    monkeypatch.setattr(hang_detector_module, "WATCH_TIMEOUT_SECONDS", 5.0)

    mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert recovered_event.wait(timeout=1)
    phases = [phase for phase, _ in events]
    assert "hang_watch" in phases
    assert "hang_recovered" in phases
    # watch-entry 事件注明宿主机 domstate 活着
    assert any(message and "VM 运行中" in message for _, message in events)
    assert artifacts == [f"console-{case_run.suite_name}-{case_run.case_name}-watch-entry.log"]
    assert case_run.status == TestCaseRunStatus.PASSED.value


def test_run_case_vm_domstate_shutoff_deadline_declares_hang(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """domstate shut off → 锚定关机宽限，到点判死：vm_hang + detail 含关机证据。"""
    import app.modules.test_management.hang_detector as hang_detector_module

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    events: list[tuple[str | None, str | None]] = []

    monkeypatch.setattr(
        mugen_runner,
        "record_test_job_event",
        lambda _db, **kw: events.append((kw.get("phase"), kw.get("message"))),
    )
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(mugen_runner, "vm_domstate_alive", lambda **_kw: False)
    monkeypatch.setattr(mugen_runner, "capture_vm_console_output", lambda **_kw: "console")
    monkeypatch.setattr(
        mugen_runner,
        "_record_hang_watch_event",
        lambda _job_id, **kw: events.append((kw.get("phase"), kw.get("message"))),
    )
    monkeypatch.setattr(mugen_runner, "_store_hang_watch_artifact", lambda **_kw: None)

    def fake_run_control(**kw: object) -> object:
        cancel_event = kw.get("cancel_event")
        if cancel_event is not None:
            cancel_event.wait(timeout=5)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", fake_run_control)
    monkeypatch.setattr(
        mugen_runner,
        "_ssh_alive",
        lambda _control, _stats=None: False,
    )
    real_hang_detector = mugen_runner.HangDetector

    def fast_detector(**kw: object) -> object:
        return real_hang_detector(interval=0.02, max_failures=2, **kw)

    monkeypatch.setattr(mugen_runner, "HangDetector", fast_detector)
    monkeypatch.setattr(mugen_runner, "_capture_and_store_console", lambda *_, **__: None)
    monkeypatch.setattr(hang_detector_module, "WATCH_POWER_OFF_DEADLINE_SECONDS", 0.15)

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(db_session, job=job, control=control, case_run=case_run)

    assert case_run.status == TestCaseRunStatus.ERROR.value
    # 首查关机也进观察模式，watch-entry 事件注明 VM 已关机
    assert any(
        message and "VM 已关机" in message and "观察模式" in message for _, message in events
    )
    assert any(
        message and "已关机" in message and "10 分钟内 SSH 未恢复" in message
        for _, message in events
    )
    # 判死 detail 注明宿主机关机证据
    assert any(
        message and "宿主机报告 VM" in message and "已关机" in message
        for phase, message in events
        if phase == "case_error"
    )


def test_try_vm_recovery_no_channel_returns_false(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """无宿主通道（物理机/未配置）：不尝试恢复、不写事件，回退原熔断。"""
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    events: list[str | None] = []
    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("phase"))
    )

    assert (
        mugen_runner.try_vm_recovery(
            db_session, job=job, control=_bmc_control(), cancel_event=None
        )
        is False
    )
    assert events == []


def test_try_vm_recovery_reset_and_ssh_back_returns_true(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ebtables 场景回放：console 取证 → 硬复位 → SSH 恢复 → True，事件留痕。"""
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    events: list[str | None] = []
    artifacts: list[str | None] = []
    order: list[str] = []

    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("phase"))
    )
    monkeypatch.setattr(
        mugen_runner,
        "capture_vm_console_output",
        lambda **_kw: (order.append("capture"), "console output")[1],
    )
    monkeypatch.setattr(
        mugen_runner,
        "_store_hang_watch_artifact",
        lambda **kw: artifacts.append(kw.get("artifact_name")),
    )
    monkeypatch.setattr(
        mugen_runner,
        "vm_hard_reset",
        lambda **_kw: (order.append("reset"), True)[1],
    )
    monkeypatch.setattr(
        mugen_runner,
        "_ssh_alive",
        lambda _control, _stats=None: (order.append("ssh"), True)[1],
    )

    assert (
        mugen_runner.try_vm_recovery(db_session, job=job, control=control, cancel_event=None)
        is True
    )
    assert events == ["vm_recovery_started", "vm_recovered"]
    assert order == ["capture", "reset", "ssh"]
    assert artifacts == ["console-recovery.log"]


def test_sync_vm_disks_best_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sync 契约：下发 sync 命令且绝不抛异常（SSH 已死是杀手用例的预期场景）。"""
    control = SimpleNamespace(ip="1.1.1.1", username="root", password="p")
    recorded: list[dict] = []

    def ok_command(**kwargs):
        recorded.append(kwargs)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", ok_command)
    mugen_runner.sync_vm_disks(control)
    assert recorded[0]["script"] == "sync"
    assert recorded[0]["control"] is control

    # SSH 已死（杀手用例场景）：吞掉异常，交给下轮探针恢复接管
    def dead_ssh(**_kwargs):
        raise RuntimeError("ssh dead")

    monkeypatch.setattr(mugen_runner, "run_control_command", dead_ssh)
    mugen_runner.sync_vm_disks(control)  # 不抛即通过


def test_execute_env_set_syncs_at_boundaries(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """job 10238 场景：环境就绪 sync 1 次 + 每个正常返回的用例后各 1 次；
    异常用例（SSH 已死）不 sync——sync 失败无意义。
    """
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.remote import RemoteCommandError

    _patch_env_set_basics(monkeypatch, test_execution)
    _patch_probe_gate(monkeypatch, test_execution, refused=False)

    order: list[str] = []

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        order.append(f"case:{case_run.case_name}")
        if case_run.case_name == "c1":  # 中间用例杀 sshd：SSH 已死不 sync
            case_run.status = TestCaseRunStatus.ERROR.value
            raise RemoteCommandError("ssh refused")
        case_run.status = TestCaseRunStatus.PASSED.value

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)
    monkeypatch.setattr(
        test_execution, "sync_vm_disks", lambda control: order.append("sync")
    )

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=3)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert order == [
        "sync",           # 环境就绪（部署/pre_env 产物落盘）
        "case:c0",
        "sync",           # 用例完成后
        "case:c1",        # 异常用例：不 sync
        "case:c2",
        "sync",
    ]


def test_execute_env_set_no_sync_without_host_channel(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """物理机/无宿主通道 VM 不会被硬复位，不付同步开销。"""
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)
    monkeypatch.setattr(test_execution, "vm_host_channel", lambda *_: None)

    sync_calls: list[object] = []
    monkeypatch.setattr(
        test_execution, "sync_vm_disks", lambda control: sync_calls.append(1)
    )
    monkeypatch.setattr(
        test_execution,
        "run_case",
        lambda _db, *, job, control, case_run, **_kw: setattr(
            case_run, "status", TestCaseRunStatus.PASSED.value
        ),
    )

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=2)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert sync_calls == []
    for case_run in case_runs:
        assert case_run.status == TestCaseRunStatus.PASSED.value


def test_try_vm_recovery_probe_trigger_message(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """trigger=probe 的事件文案注明探针来源，与熔断触发区分。"""
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    messages: list[str] = []

    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(
        mugen_runner,
        "record_test_job_event",
        lambda _db, **kw: messages.append(kw.get("message", "")),
    )
    monkeypatch.setattr(mugen_runner, "capture_vm_console_output", lambda **_kw: "console")
    monkeypatch.setattr(mugen_runner, "_store_hang_watch_artifact", lambda **_kw: None)
    monkeypatch.setattr(mugen_runner, "vm_hard_reset", lambda **_kw: False)

    assert (
        mugen_runner.try_vm_recovery(
            db_session,
            job=job,
            control=control,
            cancel_event=None,
            trigger="probe",
        )
        is False
    )
    assert len(messages) == 2
    assert "连接拒绝" in messages[0]
    assert "熔断" not in messages[0]


def test_try_vm_recovery_ssh_never_back_returns_false(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """复位成功但 SSH 不回：预算耗尽 → False + vm_recovery_failed。"""
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    events: list[str | None] = []

    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("phase"))
    )
    monkeypatch.setattr(mugen_runner, "capture_vm_console_output", lambda **_kw: "console")
    monkeypatch.setattr(mugen_runner, "_store_hang_watch_artifact", lambda **_kw: None)
    monkeypatch.setattr(mugen_runner, "vm_hard_reset", lambda **_kw: True)
    monkeypatch.setattr(mugen_runner, "_ssh_alive", lambda _control, _stats=None: False)
    monkeypatch.setattr(mugen_runner, "SSH_READY_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(mugen_runner, "SSH_READY_RETRY_INTERVAL_SECONDS", 0.01)

    assert (
        mugen_runner.try_vm_recovery(db_session, job=job, control=control, cancel_event=None)
        is False
    )
    assert events == ["vm_recovery_started", "vm_recovery_failed"]


def test_try_vm_recovery_reset_fails_skips_ssh_wait(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """复位无效（仍 shut off）：不进入 SSH 等待，直接失败。"""
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    control = _vm_control_with_host(db_session)
    events: list[str | None] = []

    monkeypatch.setattr(
        mugen_runner,
        "get_settings",
        lambda: SimpleNamespace(vm_host_ssh_key_path="/test-key"),
    )
    monkeypatch.setattr(
        mugen_runner, "record_test_job_event", lambda _db, **kw: events.append(kw.get("phase"))
    )
    monkeypatch.setattr(mugen_runner, "capture_vm_console_output", lambda **_kw: "console")
    monkeypatch.setattr(mugen_runner, "_store_hang_watch_artifact", lambda **_kw: None)
    monkeypatch.setattr(mugen_runner, "vm_hard_reset", lambda **_kw: False)

    def unexpected_alive(_control: object, _stats: object = None) -> bool:
        raise AssertionError("reset failed; SSH wait must be skipped")

    monkeypatch.setattr(mugen_runner, "_ssh_alive", unexpected_alive)

    assert (
        mugen_runner.try_vm_recovery(db_session, job=job, control=control, cancel_event=None)
        is False
    )
    assert events == ["vm_recovery_started", "vm_recovery_failed"]


def test_execute_env_set_breaker_recovers_and_continues(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3 连击触发熔断前先试宿主机恢复：成功 → 计数清零继续，恢复只一次。"""
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.remote import RemoteCommandError

    _patch_env_set_basics(monkeypatch, test_execution)

    outcomes: list[Exception | None] = [
        RemoteCommandError("ssh failed"),
        RemoteCommandError("ssh failed"),
        RemoteCommandError("ssh failed"),
        None,
        None,
    ]
    recovery_calls: list[object] = []

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        outcome = outcomes.pop(0)
        if outcome is not None:
            case_run.status = TestCaseRunStatus.ERROR.value
            raise outcome
        case_run.status = TestCaseRunStatus.PASSED.value

    def fake_recovery(db, *, job, control, cancel_event=None):
        recovery_calls.append(control)
        return True

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)
    monkeypatch.setattr(test_execution, "try_vm_recovery", fake_recovery)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=5)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    assert len(recovery_calls) == 1
    for i in range(3):
        assert case_runs[i].status == TestCaseRunStatus.ERROR.value
    for i in (3, 4):
        assert case_runs[i].status == TestCaseRunStatus.PASSED.value


def test_execute_env_set_recovery_once_then_breaker(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """恢复预算每 env_set 一次：再次连击不再恢复，剩余用例批量标 error。"""
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.remote import RemoteCommandError

    _patch_env_set_basics(monkeypatch, test_execution)

    err = RemoteCommandError("ssh failed")
    outcomes: list[Exception | None] = [err, err, err, None, err, err, err]
    recovery_calls: list[object] = []

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        outcome = outcomes.pop(0)
        if outcome is not None:
            case_run.status = TestCaseRunStatus.ERROR.value
            raise outcome
        case_run.status = TestCaseRunStatus.PASSED.value

    def fake_recovery(db, *, job, control, cancel_event=None):
        recovery_calls.append(control)
        return True

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)
    monkeypatch.setattr(test_execution, "try_vm_recovery", fake_recovery)

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=8)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    assert len(recovery_calls) == 1
    # 第一次熔断被恢复救回：case 3 正常执行；第二次熔断不再恢复，case 7 批量标错
    for i in (0, 1, 2, 4, 5, 6, 7):
        assert case_runs[i].status == TestCaseRunStatus.ERROR.value
    assert case_runs[3].status == TestCaseRunStatus.PASSED.value


def test_execute_env_set_recovery_failure_marks_remaining(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """恢复失败（无通道/复位无效/SSH 未回）：维持原熔断批量标 error。"""
    from app.modules.test_management import execution as test_execution

    _patch_env_set_basics(monkeypatch, test_execution)

    def fake_run_case(db, *, job, control, case_run, **kwargs):
        case_run.status = TestCaseRunStatus.ERROR.value
        raise EnvSetHangError("hang")

    monkeypatch.setattr(test_execution, "run_case", fake_run_case)
    monkeypatch.setattr(
        test_execution, "try_vm_recovery", lambda *_, **__: False
    )

    job, env_set, case_runs = _make_job_with_env_set_and_cases(db_session, num_cases=5)
    db_session.add(TestEnvNode(env_set=env_set, node_index=0, role="control"))
    db_session.commit()

    has_failure, has_error = test_execution.execute_env_set(
        db_session, job=job, env_set=env_set, actor=SimpleNamespace(id="admin")
    )
    assert has_error is True
    for i in range(5):
        assert case_runs[i].status == TestCaseRunStatus.ERROR.value


def _patch_probe_gate(monkeypatch, test_execution, *, refused: bool) -> list[dict]:
    """打开探针门（通道存在）并固定探活结果，返回恢复调用记录。

    一并 no-op 掉 sync（假通道下真实 sync 会 SSH 1.1.1.1 超时）；
    需要观察 sync 行为的测试自行再覆盖。
    """
    monkeypatch.setattr(
        test_execution, "vm_host_channel", lambda *_: ("10.0.0.1", "vm-1", "/test-key")
    )
    monkeypatch.setattr(test_execution, "ssh_connect_refused", lambda _control: refused)
    monkeypatch.setattr(test_execution, "sync_vm_disks", lambda _control: None)
    calls: list[dict] = []
    monkeypatch.setattr(
        test_execution,
        "try_vm_recovery",
        lambda _db, *, job, control, cancel_event=None, **kw: (
            calls.append({**kw, "control": control}),
            True,
        )[1],
    )
    return calls
