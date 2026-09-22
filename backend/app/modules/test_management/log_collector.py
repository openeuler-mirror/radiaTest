# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.test_management.models import TestLogArtifact


class LogCollector:
    """存储和读取 Test Job 日志 artifact。

    Pipeline 调用方可传 pipeline run ID 用于存储分组，但 artifact 记录归
    Test Job 所有，本类不解析 Pipeline 状态。
    """

    def __init__(self, *, base_dir: str) -> None:
        self._base_dir = base_dir

    def store_artifact(
        self,
        *,
        db: Session,
        job_id: int,
        module: str,
        arch: str,
        artifact_type: str,
        artifact_name: str,
        content: str | bytes,
        storage_scope: str | None = None,
        pipeline_run_id: str | None = None,
    ) -> TestLogArtifact:
        """持久化单个 artifact 及其归 Test Job 所有的元数据。"""
        scope = storage_scope or pipeline_run_id
        if scope is None:
            raise ValueError("storage_scope or pipeline_run_id is required")
        dir_path = Path(self._base_dir) / scope / module / arch
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / artifact_name

        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            file_path.write_text(content, encoding="utf-8")

        artifact = TestLogArtifact(
            pipeline_run_id=pipeline_run_id,
            job_id=job_id,
            module=module,
            arch=arch,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            storage_path=str(file_path),
        )
        db.add(artifact)
        db.flush()
        return artifact

    @staticmethod
    def store_dir_artifact(
        *,
        db: Session,
        job_id: int,
        module: str,
        arch: str,
        artifact_type: str,
        artifact_name: str,
        local_dir: str,
        pipeline_run_id: str | None = None,
    ) -> TestLogArtifact:
        """把一个已复制的目录登记为 Test Job 日志 artifact。"""
        artifact = TestLogArtifact(
            pipeline_run_id=pipeline_run_id,
            job_id=job_id,
            module=module,
            arch=arch,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            storage_path=local_dir,
        )
        db.add(artifact)
        db.flush()
        return artifact

    @staticmethod
    def store_file_artifact(
        *,
        db: Session,
        pipeline_run_id: str,
        job_id: int,
        module: str,
        arch: str,
        artifact_type: str,
        artifact_name: str,
        local_file: str,
    ) -> TestLogArtifact:
        """Register a pre-downloaded local file as a file artifact (full content on disk).

        Used by _self_collect_logs for log files downloaded via scp_file (no
        truncation, unlike the old cat-into-stdout approach capped at 16KB).
        local_file is the absolute path to the file on the worker.
        """
        artifact = TestLogArtifact(
            pipeline_run_id=pipeline_run_id,
            job_id=job_id,
            module=module,
            arch=arch,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            storage_path=local_file,
        )
        db.add(artifact)
        db.flush()
        return artifact

    @staticmethod
    def list_dir_files(artifact: TestLogArtifact) -> list[str]:
        """返回目录 artifact 内文件的相对路径列表。"""
        base = Path(artifact.storage_path)
        if not base.is_dir():
            return []
        return sorted(
            str(file_path.relative_to(base))
            for file_path in base.rglob("*")
            if file_path.is_file()
        )

    @staticmethod
    def read_dir_file(artifact: TestLogArtifact, file_name: str) -> str | None:
        """读取目录 artifact 中的文件，拒绝路径穿越(path traversal)。"""
        base = Path(artifact.storage_path).resolve()
        target = (base / file_name).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return None
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8", errors="replace")
