# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

import anyio
import pytest

from app.modules.vms import iso_storage
from app.modules.vms.iso_storage import (
    ISOInsufficientStorageError,
    ISOStorage,
    ISOStorageUnavailableError,
    ISOTooLargeError,
    ISOValidationError,
)

GIB = 1024**3


async def chunks(*values: bytes) -> AsyncIterator[bytes]:
    for value in values:
        yield value


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def ample_disk_space(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        iso_storage.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100 * GIB, used=10 * GIB, free=90 * GIB),
    )


@pytest.mark.anyio
async def test_store_streams_to_sha_named_file_and_deduplicates(tmp_path: Path) -> None:
    storage = ISOStorage(tmp_path)

    first = await storage.store(
        filename="openEuler.iso",
        content_length=6,
        chunks=chunks(b"abc", b"123"),
    )
    second = await storage.store(
        filename="same-content.ISO",
        content_length=6,
        chunks=chunks(b"abc123"),
    )

    assert first == second
    assert first.download_path == f"/vm-iso/{first.sha256}.iso"
    assert (tmp_path / f"{first.sha256}.iso").read_bytes() == b"abc123"
    assert list(tmp_path.glob("*.iso")) == [tmp_path / f"{first.sha256}.iso"]
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "filename",
    ["", "image.qcow2", "../image.iso", "dir/image.iso", "bad\nname.iso"],
)
async def test_store_rejects_untrusted_filenames(tmp_path: Path, filename: str) -> None:
    with pytest.raises(ISOValidationError):
        await ISOStorage(tmp_path).store(
            filename=filename,
            content_length=1,
            chunks=chunks(b"x"),
        )


@pytest.mark.anyio
async def test_store_removes_partial_file_when_body_is_truncated(tmp_path: Path) -> None:
    with pytest.raises(ISOValidationError, match="does not match"):
        await ISOStorage(tmp_path).store(
            filename="image.iso",
            content_length=2,
            chunks=chunks(b"x"),
        )

    assert not list(tmp_path.glob("*.part"))
    assert not list(tmp_path.glob("*.iso"))


@pytest.mark.anyio
async def test_store_rejects_size_and_capacity_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ISOTooLargeError):
        await ISOStorage(tmp_path).store(
            filename="image.iso",
            content_length=iso_storage.MAX_ISO_BYTES + 1,
            chunks=chunks(),
        )

    monkeypatch.setattr(
        iso_storage.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100 * GIB, used=89 * GIB, free=11 * GIB),
    )
    with pytest.raises(ISOInsufficientStorageError):
        await ISOStorage(tmp_path).store(
            filename="image.iso",
            content_length=2 * GIB,
            chunks=chunks(),
        )


@pytest.mark.anyio
async def test_store_lazily_removes_only_expired_upload_files(tmp_path: Path) -> None:
    old_part = tmp_path / ".old.part"
    old_iso = tmp_path / f"{'a' * 64}.iso"
    fresh_iso = tmp_path / f"{'b' * 64}.iso"
    unrelated = tmp_path / "keep.txt"
    for path in (old_part, old_iso, fresh_iso, unrelated):
        path.write_bytes(b"x")
    old = time.time() - iso_storage.ISO_MAX_AGE_SECONDS - 1
    os.utime(old_part, (old, old))
    os.utime(old_iso, (old, old))

    await ISOStorage(tmp_path).store(
        filename="new.iso",
        content_length=1,
        chunks=chunks(b"n"),
    )

    assert not old_part.exists()
    assert not old_iso.exists()
    assert fresh_iso.exists()
    assert unrelated.exists()


@pytest.mark.anyio
async def test_store_requires_prepared_non_symlink_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ISOStorageUnavailableError):
        await ISOStorage(missing).store(
            filename="image.iso",
            content_length=1,
            chunks=chunks(b"x"),
        )

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ISOStorageUnavailableError):
        await ISOStorage(link).store(
            filename="image.iso",
            content_length=1,
            chunks=chunks(b"x"),
        )


@pytest.mark.anyio
async def test_store_hides_storage_io_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        iso_storage.shutil,
        "disk_usage",
        lambda _path: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    with pytest.raises(ISOStorageUnavailableError, match="failed to store"):
        await ISOStorage(tmp_path).store(
            filename="image.iso",
            content_length=1,
            chunks=chunks(b"x"),
        )


@pytest.mark.anyio
async def test_store_serializes_capacity_check_and_upload(tmp_path: Path) -> None:
    first_started = anyio.Event()
    release_first = anyio.Event()
    second_started = anyio.Event()

    async def first_chunks() -> AsyncIterator[bytes]:
        first_started.set()
        yield b"a"
        await release_first.wait()
        yield b"b"

    async def second_chunks() -> AsyncIterator[bytes]:
        second_started.set()
        yield b"c"

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(
            lambda: ISOStorage(tmp_path).store(
                filename="first.iso",
                content_length=2,
                chunks=first_chunks(),
            )
        )
        await first_started.wait()
        task_group.start_soon(
            lambda: ISOStorage(tmp_path).store(
                filename="second.iso",
                content_length=1,
                chunks=second_chunks(),
            )
        )
        await anyio.sleep(0.05)
        assert not second_started.is_set()
        release_first.set()

    assert second_started.is_set()
