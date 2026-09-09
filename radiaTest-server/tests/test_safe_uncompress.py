# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    : 2026/09/09
# @License : Mulan PSL v2
#####################################
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from server.utils.safe_uncompress import SafeUncompress


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            zf.writestr(info, content)


def make_tar(path, entries):
    with tarfile.open(path, "w") as tf:
        for name, content in entries:
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_get_encoding_str_ascii_passthrough():
    assert SafeUncompress.get_encoding_str("plain") == "plain"


def test_get_encoding_str_utf8_fallback():
    assert SafeUncompress.get_encoding_str("中文") == "中文"


def test_is_safe_path_accepts_inner_path(tmp_path):
    basedir = tmp_path / "extract"
    assert SafeUncompress.is_safe_path(basedir, "inner/file.txt") is True


def test_is_safe_path_rejects_traversal(tmp_path):
    basedir = tmp_path / "extract"
    assert SafeUncompress.is_safe_path(basedir, "../../../../etc/passwd") is False


def test_uncompress_zip_extracts_files(tmp_path):
    zip_path = tmp_path / "pack.zip"
    make_zip(zip_path, [("dir/a.txt", "A"), ("dir/b.txt", "B")])
    dist = tmp_path / "out"
    dist.mkdir()
    SafeUncompress("zip", zip_path).uncompress(dist)
    assert (dist / "dir" / "a.txt").read_text(encoding="utf-8") == "A"
    assert (dist / "dir" / "b.txt").read_text(encoding="utf-8") == "B"


def test_uncompress_zip_skips_macos_cache(tmp_path):
    zip_path = tmp_path / "pack.zip"
    make_zip(
        zip_path,
        [("dir/a.txt", "A"), ("__MACOSX/dir/._a.txt", "cache")],
    )
    dist = tmp_path / "out"
    dist.mkdir()
    SafeUncompress("zip", zip_path).uncompress(dist)
    assert (dist / "dir" / "a.txt").exists()
    assert not (dist / "__MACOSX").exists()


def test_uncompress_zip_rejects_too_many_files(tmp_path):
    zip_path = tmp_path / "pack.zip"
    make_zip(zip_path, [(f"f{i}.txt", "x") for i in range(4)])
    dist = tmp_path / "out"
    dist.mkdir()
    handler = SafeUncompress("zip", zip_path)
    handler.max_number = 2
    with pytest.raises(RuntimeError, match="files too many"):
        handler.uncompress(dist)


def test_uncompress_zip_rejects_oversize(tmp_path):
    zip_path = tmp_path / "pack.zip"
    make_zip(zip_path, [("big.txt", "x" * 32)])
    dist = tmp_path / "out"
    dist.mkdir()
    handler = SafeUncompress("zip", zip_path)
    handler.max_total_size = 8
    with pytest.raises(RuntimeError, match="size too big"):
        handler.uncompress(dist)


def test_uncompress_zip_skips_deep_path(tmp_path):
    zip_path = tmp_path / "pack.zip"
    deep_name = "/".join(f"d{i}" for i in range(21)) + "/deep.txt"
    make_zip(zip_path, [("ok.txt", "O"), (deep_name, "D")])
    dist = tmp_path / "out"
    dist.mkdir()
    SafeUncompress("zip", zip_path).uncompress(dist)
    assert (dist / "ok.txt").exists()
    assert not (dist / "d0").exists()


def test_uncompress_tar_extracts_files(tmp_path):
    tar_path = tmp_path / "pack.tar"
    make_tar(tar_path, [("dir/f.txt", "hello")])
    dist = tmp_path / "out"
    dist.mkdir()
    SafeUncompress("tar", tar_path).uncompress(dist)
    assert (dist / "dir" / "f.txt").read_text(encoding="utf-8") == "hello"


def test_uncompress_dispatches_by_filetype(tmp_path):
    tar_path = tmp_path / "pack.tar"
    make_tar(tar_path, [("f.txt", "T")])
    dist = tmp_path / "out"
    dist.mkdir()
    SafeUncompress("any", tar_path).uncompress(dist)
    assert (dist / "f.txt").read_text(encoding="utf-8") == "T"
