# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""逐 case 日志原子上传测试（ADR 0048）：上下文、幂等落位、状态门控、补拉及 executor 注入。"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.test_management.frameworks import mugen_runner
from app.modules.test_management.models import (
    TestCaseRun,
    TestCaseRunStatus,
    TestEnvSet,
    TestJob,
)
from app.modules.test_management.remote import RemoteCommandResult
from app.modules.users.service import create_user


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


def _make_run_job(
    db: Session,
    *,
    template: TestModuleTemplate,
    arch: str = "x86_64",
):
    config = PipelineConfig(
        name="cfg",
        pipeline_type="update",
        versions=["24.03-LTS-SP3"],
        archs=[arch],
        config_data={
            "module_template_ids": [template.id],
            "repo_base_url": "http://example/repo",
        },
        dist="openEuler",
        image_round="round-9",
    )
    db.add(config)
    db.flush()
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=["24.03-LTS-SP3"], archs=[arch]
    )
    db.add(execution)
    db.flush()
    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version="24.03-LTS-SP3",
        status="pending",
        triggered_by="admin",
    )
    db.add(run)
    db.flush()
    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch=arch,
        status="pending",
    )
    db.add(run_job)
    db.flush()
    return config, execution, run, run_job


def _make_job_with_case_run(db: Session, *, result_parser: str | None = "none"):
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


def _make_control() -> SimpleNamespace:
    return SimpleNamespace(
        ip="1.1.1.1",
        username="root",
        password="p",
        resource=SimpleNamespace(host_resource_id=None),
    )


# ---------- 上下文注册表 ----------


def test_case_log_context_registry_roundtrip() -> None:
    from app.modules.test_management.case_log_context import (
        CaseLogContext,
        get_case_log_context,
        pop_case_log_context,
        set_case_log_context,
    )

    ctx = CaseLogContext(
        run_id="run-1", module_name="pkgcmd", arch="x86_64", run_job_id="rj-1"
    )
    assert get_case_log_context(9999) is None
    set_case_log_context(9999, ctx)
    assert get_case_log_context(9999) is ctx
    assert pop_case_log_context(9999) is ctx
    assert get_case_log_context(9999) is None
    # pop 不存在的 job 不抛
    assert pop_case_log_context(9999) is None


def test_process_test_job_registers_and_pops_case_log_context(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """process_test_job 持有上下文期间 env_set 线程可读取，结束后注销。"""
    from app.modules.test_management import execution as test_execution
    from app.modules.test_management.case_log_context import (
        CaseLogContext,
        get_case_log_context,
    )
    from app.modules.users.models import UserRole

    actor = create_user(
        db_session, username="ctxjob", password="test-pass", role=UserRole.TE
    )
    job = TestJob(
        creator_user_id=actor.id,
        name="ctx",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="v",
        image_round="",
        arch="x86_64",
        mugen_commit_sha="abc",
        env_set_num=1,
    )
    job.env_sets.append(TestEnvSet(set_index=1, node_num=1))
    db_session.add(job)
    db_session.commit()

    captured: dict[str, object] = {}

    def fake_thread(job_id: int, env_set_id: str, actor_id: str, cancel_event) -> object:
        captured["ctx"] = get_case_log_context(job_id)
        return SimpleNamespace(
            env_set_id=env_set_id, has_failure=False, has_error=False
        )

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(test_execution, "_run_env_set_thread", fake_thread)

    ctx = CaseLogContext(
        run_id="run-1", module_name="pkgcmd", arch="x86_64", run_job_id="rj-1"
    )
    test_execution.process_test_job(job.id, case_log_context=ctx)

    assert captured["ctx"] is ctx
    assert get_case_log_context(job.id) is None
    db_session.refresh(job)
    assert job.status == "succeeded"


# ---------- upload_case_logs ----------


def _register_ctx(job_id: int) -> None:
    from app.modules.test_management.case_log_context import (
        CaseLogContext,
        set_case_log_context,
    )

    set_case_log_context(
        job_id,
        CaseLogContext(
            run_id="run-1", module_name="pkgcmd", arch="x86_64", run_job_id="rj-1"
        ),
    )


_REMOTE_PIECE_PATHS = [
    "/opt/mugen/logs/s/c",
    "/opt/mugen/results/s/succeed/c",
    "/opt/mugen/results/s/failed/c",
    "/opt/mugen/results/s/skipped/c",
]


def _stub_remote_probe(
    monkeypatch: pytest.MonkeyPatch, existing: list[str]
) -> None:
    """模拟控制节点上的远端路径探测，existing 即真实存在的目录列表。"""
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, control, script, timeout_seconds, **kwargs: RemoteCommandResult(
            returncode=0, stdout="\n".join(existing), stderr=""
        ),
    )


def test_upload_case_logs_lands_logs_and_results_atomically(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logs 目录与 results 桶按最终布局落位，pkg_folder artifact 幂等登记。"""
    from app.modules.test_management.case_log_context import pop_case_log_context
    from app.modules.test_management.models import TestLogArtifact

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    _stub_remote_probe(monkeypatch, _REMOTE_PIECE_PATHS)

    scp_calls: list[str] = []

    def fake_scp_directory(
        *, target, remote_path, local_dir, timeout_seconds=300,
        verify_host_key=True,
    ) -> bool:
        scp_calls.append(remote_path)
        local = Path(local_dir)
        local.mkdir(parents=True, exist_ok=True)
        name = Path(remote_path).name
        (local / name).mkdir()
        (local / name / "run.log").write_text("log content", encoding="utf-8")
        return True

    monkeypatch.setattr(mugen_runner, "scp_directory", fake_scp_directory)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1"
    assert (base / "logs" / "s" / "c" / "run.log").read_text(encoding="utf-8") == (
        "log content"
    )
    assert (base / "results" / "s" / "succeed" / "c" / "run.log").exists()
    # 临时目录不残留
    leftovers = [p for p in base.parent.rglob(".tmp-*")]
    assert leftovers == []

    artifacts = list(
        db_session.execute(
            select(TestLogArtifact).where(TestLogArtifact.job_id == job.id)
        ).scalars()
    )
    by_name = {a.artifact_name: a for a in artifacts}
    assert set(by_name) == {"logs", "results"}
    assert by_name["logs"].artifact_type == "pkg_folder"
    assert by_name["logs"].pipeline_run_id == "run-1"
    assert by_name["logs"].storage_path == str(base / "logs")
    assert pop_case_log_context(job.id) is not None


def test_upload_case_logs_skips_existing_case_and_artifact(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """目标 case 目录已存在时跳过 scp；artifact 不重复登记。"""
    from app.modules.test_management.models import TestLogArtifact

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1"
    (base / "logs" / "s" / "c").mkdir(parents=True)

    scp_calls: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "scp_directory",
        lambda **kwargs: (scp_calls.append(kwargs["remote_path"]), True)[1],
    )

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    assert scp_calls == []
    artifacts = list(
        db_session.execute(
            select(TestLogArtifact).where(TestLogArtifact.job_id == job.id)
        ).scalars()
    )
    assert artifacts == []


def test_upload_case_logs_docker_stages_via_docker_cp(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """docker 模块先 docker cp 到宿主机 staging，再从 staging scp。"""
    from app.modules.test_management.case_log_context import pop_case_log_context

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    job.mugen_exec_command = (
        "docker exec openEuler_test bash /home/mugen/mugen.sh -f {suite} -r {case} -x"
    )
    db_session.commit()
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    scripts: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, control, script, timeout_seconds, **kwargs: (
            scripts.append(script),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        )[1],
    )
    scp_calls: list[str] = []

    def fake_scp_directory(
        *, target, remote_path, local_dir, timeout_seconds=300,
        verify_host_key=True,
    ) -> bool:
        scp_calls.append(remote_path)
        # staging 目录整体拉回：{stage}/{case_run.id}/logs/{suite}/{case}/...
        stage_local = Path(local_dir) / case_run.id
        (stage_local / "logs" / "s" / "c").mkdir(parents=True)
        (stage_local / "results" / "s" / "failed" / "c").mkdir(parents=True)
        (stage_local / "logs" / "s" / "c" / "run.log").write_text(
            "docker log", encoding="utf-8"
        )
        (stage_local / "results" / "s" / "failed" / "c" / "run.log").write_text(
            "bucket", encoding="utf-8"
        )
        return True

    monkeypatch.setattr(mugen_runner, "scp_directory", fake_scp_directory)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    # docker cp 脚本包含容器内路径与 staging
    assert any("docker cp openEuler_test:/home/mugen/logs/s/c" in s for s in scripts)
    assert any("docker cp openEuler_test:/home/mugen/results/s/failed/c" in s for s in scripts)
    assert len(scp_calls) == 1
    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1"
    assert (base / "logs" / "s" / "c" / "run.log").read_text(encoding="utf-8") == (
        "docker log"
    )
    assert (base / "results" / "s" / "failed" / "c" / "run.log").exists()
    assert pop_case_log_context(job.id) is not None


def test_upload_case_logs_missing_buckets_are_skipped_not_fatal(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mugen 逐 case 覆盖 results：缺失桶（探测不存在）直接跳过，不算失败。"""
    from app.modules.test_management.models import TestLogArtifact

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    # 真实布局：case 只落在 logs + succeed 桶，failed/skipped 桶远端不存在。
    _stub_remote_probe(monkeypatch, _REMOTE_PIECE_PATHS[:2])

    scp_calls: list[str] = []

    def fake_scp_directory(
        *, target, remote_path, local_dir, timeout_seconds=300,
        verify_host_key=True,
    ) -> bool:
        scp_calls.append(remote_path)
        local = Path(local_dir)
        local.mkdir(parents=True, exist_ok=True)
        (local / Path(remote_path).name).mkdir()
        (local / Path(remote_path).name / "run.log").write_text("log", encoding="utf-8")
        return True

    monkeypatch.setattr(mugen_runner, "scp_directory", fake_scp_directory)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    assert sorted(scp_calls) == sorted(_REMOTE_PIECE_PATHS[:2])
    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1"
    assert (base / "logs" / "s" / "c" / "run.log").exists()
    assert (base / "results" / "s" / "succeed" / "c" / "run.log").exists()
    assert not (base / "results" / "s" / "failed").exists()
    assert not (base / "results" / "s" / "skipped").exists()
    artifacts = list(
        db_session.execute(
            select(TestLogArtifact).where(TestLogArtifact.job_id == job.id)
        ).scalars()
    )
    assert {a.artifact_name for a in artifacts} == {"logs", "results"}
    from app.modules.test_management.case_log_context import pop_case_log_context

    assert pop_case_log_context(job.id) is not None


def test_upload_case_logs_partial_scp_failure_lands_nothing(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """已暂存 piece 之后任一 piece scp 失败：整 case 不落位，等待结束补拉兜底。"""
    from app.modules.test_management.models import TestLogArtifact

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    # 真实布局：logs 与 succeed 桶存在；logs 暂存成功后 succeed 桶 scp 失败。
    _stub_remote_probe(monkeypatch, _REMOTE_PIECE_PATHS[:2])

    scp_calls: list[str] = []

    def fake_scp_directory(
        *, target, remote_path, local_dir, timeout_seconds=300,
        verify_host_key=True,
    ) -> bool:
        scp_calls.append(remote_path)
        if len(scp_calls) == 2:
            return False
        local = Path(local_dir)
        local.mkdir(parents=True, exist_ok=True)
        (local / Path(remote_path).name).mkdir()
        return True

    monkeypatch.setattr(mugen_runner, "scp_directory", fake_scp_directory)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1"
    assert not (base / "logs").exists()
    assert not (base / "results").exists()
    artifacts = list(
        db_session.execute(
            select(TestLogArtifact).where(TestLogArtifact.job_id == job.id)
        ).scalars()
    )
    assert artifacts == []
    from app.modules.test_management.case_log_context import pop_case_log_context

    assert pop_case_log_context(job.id) is not None


def test_upload_case_logs_docker_cleans_remote_staging(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """docker staging scp 完成后清理测试机目录，keep_env 机器长期复用不残留。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    job.mugen_exec_command = (
        "docker exec openEuler_test bash /home/mugen/mugen.sh -f {suite} -r {case} -x"
    )
    db_session.commit()
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    scripts: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, control, script, timeout_seconds, **kwargs: (
            scripts.append(script),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        )[1],
    )
    monkeypatch.setattr(mugen_runner, "scp_directory", lambda **kwargs: True)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    assert f"rm -rf /tmp/kronos-case-upload/{case_run.id}" in scripts
    from app.modules.test_management.case_log_context import pop_case_log_context

    assert pop_case_log_context(job.id) is not None


def test_upload_case_logs_docker_cleans_remote_staging_on_scp_failure(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """scp 失败/抛异常时远端 staging 清理同样必须执行（finally 语义）。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    job.mugen_exec_command = (
        "docker exec openEuler_test bash /home/mugen/mugen.sh -f {suite} -r {case} -x"
    )
    db_session.commit()
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    scripts: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda *, control, script, timeout_seconds, **kwargs: (
            scripts.append(script),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        )[1],
    )

    def failing_scp_directory(**kwargs) -> bool:
        raise RuntimeError("scp transport broken")

    monkeypatch.setattr(mugen_runner, "scp_directory", failing_scp_directory)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    assert f"rm -rf /tmp/kronos-case-upload/{case_run.id}" in scripts
    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1"
    assert not (base / "logs").exists()
    from app.modules.test_management.case_log_context import pop_case_log_context

    assert pop_case_log_context(job.id) is not None


def test_upload_case_logs_without_context_is_noop(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """无 pipeline 上下文（遗留独立任务入口）直接跳过，不触发 scp。"""
    from app.modules.test_management.case_log_context import pop_case_log_context

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    # 全局注册表按 job_id 键控，先弹出其他测试可能残留的同 id 上下文。
    pop_case_log_context(job.id)

    scp_calls: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "scp_directory",
        lambda **kwargs: (scp_calls.append(kwargs["remote_path"]), True)[1],
    )

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    assert scp_calls == []
    assert not (tmp_path / "run-1").exists()


def test_upload_case_logs_multi_env_naming(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """multi_env 时落位到 env-{N} 子目录，artifact 命名 env{N}- 前缀。"""
    from app.modules.test_management.models import TestLogArtifact

    job, env_set, case_run = _make_job_with_case_run(db_session)
    env_set2 = TestEnvSet(
        job=job, set_index=2, node_num=1, add_disk_num=0, add_nic_num=0
    )
    db_session.add(env_set2)
    db_session.flush()
    case_run.env_set = env_set2
    db_session.flush()
    _register_ctx(job.id)

    monkeypatch.setattr(
        mugen_runner, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    _stub_remote_probe(monkeypatch, _REMOTE_PIECE_PATHS)

    def fake_scp_directory(
        *, target, remote_path, local_dir, timeout_seconds=300,
        verify_host_key=True,
    ) -> bool:
        local = Path(local_dir)
        local.mkdir(parents=True, exist_ok=True)
        (local / Path(remote_path).name).mkdir()
        (local / Path(remote_path).name / "run.log").write_text("log", encoding="utf-8")
        return True

    monkeypatch.setattr(mugen_runner, "scp_directory", fake_scp_directory)

    mugen_runner.upload_case_logs(
        db_session, job=job, control=_make_control(), case_run=case_run
    )

    base = tmp_path / "run-1" / "pkgcmd" / "x86_64" / "rj-1" / "env-2"
    assert (base / "logs" / "s" / "c" / "run.log").read_text(encoding="utf-8") == "log"
    assert (base / "results" / "s" / "succeed" / "c" / "run.log").exists()
    artifacts = list(
        db_session.execute(
            select(TestLogArtifact).where(TestLogArtifact.job_id == job.id)
        ).scalars()
    )
    assert {a.artifact_name for a in artifacts} == {"env2-logs", "env2-results"}
    from app.modules.test_management.case_log_context import pop_case_log_context

    assert pop_case_log_context(job.id) is not None


# ---------- run_case 集成 ----------


def _stub_run_case_env(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_run_case_uploads_case_logs_after_normal_completion(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """正常收敛（passed）后触发逐 case 上传。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _stub_run_case_env(monkeypatch)
    monkeypatch.setattr(
        mugen_runner, "_ssh_read_file", lambda _control, _path: "foo 1 TPASS\n"
    )

    uploads: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "upload_case_logs",
        lambda db, *, job, control, case_run: uploads.append(case_run.id),
    )

    mugen_runner.run_case(db_session, job=job, control=_make_control(), case_run=case_run)

    assert case_run.status == TestCaseRunStatus.PASSED.value
    assert uploads == [case_run.id]


def test_run_case_hang_does_not_upload_case_logs(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """挂死路径不上传（机器不可达，console 取证兜底）。"""
    from app.modules.test_management.errors import EnvSetHangError

    job, _env_set, case_run = _make_job_with_case_run(db_session)
    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "write_remote_file", lambda **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(returncode=0, stdout="", stderr=""),
    )

    class HungDetector:
        @staticmethod
        def start() -> None:
            pass

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return True

    monkeypatch.setattr(mugen_runner, "HangDetector", lambda **_: HungDetector())
    monkeypatch.setattr(
        mugen_runner,
        "_capture_and_store_console",
        lambda *_, **__: None,
    )

    uploads: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "upload_case_logs",
        lambda db, *, job, control, case_run: uploads.append(case_run.id),
    )

    with pytest.raises(EnvSetHangError):
        mugen_runner.run_case(
            db_session, job=job, control=_make_control(), case_run=case_run
        )

    assert uploads == []


def test_run_case_timeout_uploads_case_logs(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """timeout(exit 124) 收敛路径同样触发逐 case 上传。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _stub_run_case_env(monkeypatch)
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(returncode=124, stdout="", stderr=""),
    )

    uploads: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "upload_case_logs",
        lambda db, *, job, control, case_run: uploads.append(case_run.id),
    )

    mugen_runner.run_case(db_session, job=job, control=_make_control(), case_run=case_run)

    assert case_run.status == TestCaseRunStatus.TIMEOUT.value
    assert uploads == [case_run.id]


def test_run_case_skipped_uploads_case_logs(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """skipped 收敛路径同样触发逐 case 上传。"""
    job, _env_set, case_run = _make_job_with_case_run(db_session)
    _stub_run_case_env(monkeypatch)

    def fake_run_control_command(
        *, control, script, timeout_seconds, **kwargs
    ) -> RemoteCommandResult:
        if "skipped/" in script:
            return RemoteCommandResult(returncode=0, stdout="c\n", stderr="")
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", fake_run_control_command)

    uploads: list[str] = []
    monkeypatch.setattr(
        mugen_runner,
        "upload_case_logs",
        lambda db, *, job, control, case_run: uploads.append(case_run.id),
    )

    mugen_runner.run_case(db_session, job=job, control=_make_control(), case_run=case_run)

    assert case_run.status == TestCaseRunStatus.SKIPPED.value
    assert uploads == [case_run.id]


# ---------- 结束补拉（_self_collect_logs 补漏式） ----------


def test_self_collect_logs_refetches_dir_when_artifact_exists(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """目录 artifact 已存在（逐 case 上传建过）时仍重拉全量补漏，不重复登记。"""
    from app.modules.pipelines import tasks as pipeline_tasks
    from app.modules.test_management.models import TestLogArtifact

    template = TestModuleTemplate(name="pkgcmd", display_name="P", suite_name="s")
    db_session.add(template)
    db_session.flush()
    _config, _execution, run, run_job = _make_run_job(db_session, template=template)
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    run_job.test_job_id = job.id
    db_session.commit()

    base = tmp_path / run.id / template.name / run_job.arch / run_job.id
    (base / "logs").mkdir(parents=True)
    (base / "logs" / "pre.log").write_text("pre", encoding="utf-8")
    db_session.add(
        TestLogArtifact(
            pipeline_run_id=run.id,
            job_id=job.id,
            module=template.name,
            arch=run_job.arch,
            artifact_type="pkg_folder",
            artifact_name="logs",
            storage_path=str(base / "logs"),
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        pipeline_tasks, "get_settings", lambda: SimpleNamespace(pipeline_log_dir=str(tmp_path))
    )
    monkeypatch.setattr(
        pipeline_tasks,
        "_control_node_ssh_targets",
        lambda db, job: [
            {"ip": "1.1.1.1", "username": "root", "password": "p", "env_set_index": 1}
        ],
    )
    monkeypatch.setattr(
        pipeline_tasks,
        "run_ssh_command",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="logs/\n"),
    )

    scp_calls: list[tuple[str, str]] = []

    def fake_scp_directory(
        *, target, remote_path, local_dir, timeout_seconds=300,
        verify_host_key=True,
    ) -> bool:
        scp_calls.append((remote_path, str(local_dir)))
        landed = Path(local_dir) / "logs"
        landed.mkdir(parents=True, exist_ok=True)
        (landed / "gap.log").write_text("gap", encoding="utf-8")
        (landed / "pre.log").write_text("pre", encoding="utf-8")
        return True

    monkeypatch.setattr(pipeline_tasks, "scp_directory", fake_scp_directory)
    monkeypatch.setattr(
        pipeline_tasks, "SessionLocal", lambda: nullcontext(db_session)
    )

    pipeline_tasks.collect_pipeline_logs_task.run(run_job.id)

    assert len(scp_calls) == 1
    # 补漏文件与既有文件合并共存
    assert (base / "logs" / "gap.log").read_text(encoding="utf-8") == "gap"
    assert (base / "logs" / "pre.log").read_text(encoding="utf-8") == "pre"
    # artifact 不重复登记
    logs_artifacts = list(
        db_session.execute(
            select(TestLogArtifact).where(
                TestLogArtifact.job_id == job.id,
                TestLogArtifact.artifact_name == "logs",
            )
        ).scalars()
    )
    assert len(logs_artifacts) == 1
    assert logs_artifacts[0].storage_path == str(base / "logs")


# ---------- executor 注入 ----------


def test_mugen_executor_injects_case_log_context(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.pipelines.framework_executors import mugen as mugen_executor
    from app.modules.test_management.case_log_context import CaseLogContext

    template = TestModuleTemplate(name="pkgcmd", display_name="P", suite_name="s")
    db_session.add(template)
    db_session.flush()
    config, _execution, run, run_job = _make_run_job(db_session, template=template)
    job, _env_set, _case_run = _make_job_with_case_run(db_session)
    job.status = "pending"
    db_session.commit()

    monkeypatch.setattr(
        mugen_executor,
        "build_test_job_for_run_job",
        lambda db, **kwargs: job,
    )
    captured: dict[str, object] = {}

    def fake_process_test_job(job_id: int, case_log_context=None) -> None:
        captured["job_id"] = job_id
        captured["ctx"] = case_log_context
        job.status = "succeeded"
        # 真实 process_test_job 在独立 session 提交终态；fake 需同样提交，
        # 否则 executor 的 db.refresh(job) 会丢弃未提交的 dirty 状态。
        db_session.commit()

    monkeypatch.setattr(mugen_executor, "process_test_job", fake_process_test_job)

    terminal = mugen_executor.MugenFrameworkExecutor().prepare_and_execute(
        db_session, run_job=run_job, config=config, actor_user_id="admin"
    )

    assert terminal == "succeeded"
    assert captured["job_id"] == job.id
    ctx = captured["ctx"]
    assert isinstance(ctx, CaseLogContext)
    assert ctx.run_id == run.id
    assert ctx.run_job_id == run_job.id
    assert ctx.module_name == template.name
    assert ctx.arch == run_job.arch
