# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import errno
import fcntl
import hashlib
import os
import shutil
import time
import unicodedata
from collections.abc import AsyncIterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import anyio

from app.core.config import get_settings

# ISO 上传存储的安全与清理阈值。上传是信任边界：必须校验文件名、大小、
# 容量，且全程加排他锁防并发写入竞争。详见 ISOStorage.store。
MAX_ISO_BYTES = 20 * 1024**3
MIN_FREE_BYTES = 10 * 1024**3
MAX_USED_PERCENT = 90
PART_MAX_AGE_SECONDS = 24 * 60 * 60
ISO_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


class ISOStorageError(Exception):
    """ISO 存储相关错误的基类。"""


class ISOValidationError(ISOStorageError):
    """上传校验失败(文件名非法、大小不符、超长等)，对应 400。"""


class ISOTooLargeError(ISOStorageError):
    """ISO 超过 MAX_ISO_BYTES(20GB)，对应 413。"""


class ISOInsufficientStorageError(ISOStorageError):
    """上传后会突破 MIN_FREE_BYTES 或 MAX_USED_PERCENT，对应 507。"""


class ISOStorageUnavailableError(ISOStorageError):
    """存储目录不可用或底层 IO 失败，对应 503。"""


@dataclass(frozen=True)
class StoredISO:
    """上传完成后返回的存储句柄：以 SHA-256 命名的最终下载路径。"""

    sha256: str
    size_bytes: int
    download_path: str


class ISOStorage:
    """本地 ISO 流式上传存储。

    不变量：.part 临时文件先写后原子 rename 为 <sha256>.iso；同一内容
    重复上传时复用已存文件并刷新 mtime。上传全程持 .upload.lock 排他锁，
    串行化所有上传，避免清理与写入竞态。
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    async def store(
        self,
        *,
        filename: str,
        content_length: int,
        chunks: AsyncIterable[bytes],
    ) -> StoredISO:
        """流式接收 ISO 并落盘，返回下载句柄。

        顺序：校验文件名/大小 → 建目录 → 加上传锁 → 清理过期文件 →
        容量预检 → 边写边算 SHA-256 → 校验实际大小 → 原子命名。
        任何异常都删 .part 临时文件并释放锁，避免残留。
        """
        validate_iso_filename(filename)
        validate_content_length(content_length)
        part_path = self.root / f".{uuid4().hex}.part"
        digest = hashlib.sha256()
        received = 0
        upload_lock: BinaryIO | None = None

        try:
            self._ensure_root()
            upload_lock = await anyio.to_thread.run_sync(self._acquire_upload_lock)
            self._cleanup_expired()
            self._ensure_capacity(content_length)
            output = await anyio.open_file(part_path, "xb")
            async with output:
                await anyio.to_thread.run_sync(os.chmod, part_path, 0o600)
                async for chunk in chunks:
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > content_length:
                        raise ISOValidationError(
                            "received ISO data exceeds Content-Length"
                        )
                    if received > MAX_ISO_BYTES:
                        raise ISOTooLargeError("ISO cannot exceed 20 GB")
                    digest.update(chunk)
                    await output.write(chunk)
                await output.flush()

            if received != content_length:
                raise ISOValidationError("received ISO size does not match Content-Length")

            sha256 = digest.hexdigest()
            final_path = self.root / f"{sha256}.iso"
            if final_path.exists():
                if final_path.is_symlink() or not final_path.is_file():
                    raise ISOStorageUnavailableError("stored ISO path is not a regular file")
                _remove_partial_file(part_path)
                os.utime(final_path, follow_symlinks=False)
            else:
                os.replace(part_path, final_path)
                os.chmod(final_path, 0o644)

            return StoredISO(
                sha256=sha256,
                size_bytes=received,
                download_path=f"/vm-iso/{sha256}.iso",
            )
        except OSError as exc:
            _remove_partial_file(part_path)
            if exc.errno == errno.ENOSPC:
                raise ISOInsufficientStorageError("insufficient ISO storage") from exc
            raise ISOStorageUnavailableError("failed to store ISO") from exc
        except BaseException:
            _remove_partial_file(part_path)
            raise
        finally:
            if upload_lock is not None:
                fcntl.flock(upload_lock.fileno(), fcntl.LOCK_UN)
                upload_lock.close()

    def _ensure_root(self) -> None:
        if not self.root.is_dir() or self.root.is_symlink():
            raise ISOStorageUnavailableError("ISO upload directory is unavailable")

    def _acquire_upload_lock(self) -> BinaryIO:
        lock_file = (self.root / ".upload.lock").open("a+b")
        try:
            os.fchmod(lock_file.fileno(), 0o600)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except BaseException:
            lock_file.close()
            raise
        return lock_file

    def _ensure_capacity(self, content_length: int) -> None:
        """
        容量预检：上传后剩余 < MIN_FREE_BYTES 或使用率 ≥ MAX_USED_PERCENT 则拒绝，
        避免单个 ISO 写爆 /data 分区。
        """
        usage = shutil.disk_usage(self.root)
        projected_free = usage.free - content_length
        projected_used_percent = (usage.used + content_length) * 100 / usage.total
        if (
            projected_free < MIN_FREE_BYTES
            or projected_used_percent >= MAX_USED_PERCENT
        ):
            raise ISOInsufficientStorageError(
                "ISO upload would exceed storage safety limits"
            )

    def _cleanup_expired(self) -> None:
        """
        上传时顺手清理过期文件：.iso 超 30 天、.part 超 24 小时。
        不碰符号链接和非常规文件，避免误删。无 cron，由后续上传触发。
        """
        cutoff_by_suffix = {
            ".iso": time.time() - ISO_MAX_AGE_SECONDS,
            ".part": time.time() - PART_MAX_AGE_SECONDS,
        }
        for path in self.root.iterdir():
            cutoff = cutoff_by_suffix.get(path.suffix)
            if cutoff is None or path.is_symlink() or not path.is_file():
                continue
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except FileNotFoundError:
                continue


def validate_iso_filename(filename: str) -> None:
    """
    文件名安全校验(信任边界)：禁止路径分隔符、控制字符，限长 255，
    必须 .iso 后缀。防止路径穿越和非法文件名。
    """
    if not filename or len(filename) > 255:
        raise ISOValidationError("ISO filename must be 1 to 255 characters")
    if "/" in filename or "\\" in filename:
        raise ISOValidationError("ISO filename cannot contain path separators")
    if any(unicodedata.category(char).startswith("C") for char in filename):
        raise ISOValidationError("ISO filename cannot contain control characters")
    if not filename.lower().endswith(".iso"):
        raise ISOValidationError("ISO filename must end with .iso")


def validate_content_length(content_length: int) -> None:
    if content_length <= 0:
        raise ISOValidationError("Content-Length must be positive")
    if content_length > MAX_ISO_BYTES:
        raise ISOTooLargeError("ISO cannot exceed 20 GB")


def _remove_partial_file(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def get_iso_storage() -> ISOStorage:
    return ISOStorage(Path(get_settings().vm_iso_upload_dir))
