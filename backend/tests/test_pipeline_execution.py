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
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.leases.models import ResourceLease
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
)
from app.modules.resources.models import Resource, ResourceType
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import (
    MugenCase,
    TestCaseRun,
    TestCaseRunDetail,
    TestCaseRunStatus,
    TestEnvNode,
    TestEnvSet,
    TestEnvSetStatus,
    TestJob,
)
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
