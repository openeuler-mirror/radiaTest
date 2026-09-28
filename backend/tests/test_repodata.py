# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import gzip
from io import BytesIO
from unittest.mock import patch

from app.modules.pipelines.repodata import fetch_service_packages, fetch_update_packages

REPOMD_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <revision>1700000000</revision>
  <data type="primary">
    <location href="repodata/abc123-primary.xml.gz" />
    <checksum type="sha256">abc123</checksum>
  </data>
</repomd>
"""

PRIMARY_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<metadata xmlns="http://linux.duke.edu/metadata/common">
  <package type="src">
    <name>bash</name>
    <arch>src</arch>
  </package>
  <package type="src">
    <name>curl</name>
    <arch>src</arch>
  </package>
  <package type="rpm">
    <name>bash</name>
    <arch>aarch64</arch>
  </package>
  <package type="src">
    <name>kernel</name>
    <arch>src</arch>
  </package>
</metadata>
"""

UPDATE_JSON = b'{"update": [{"dir": "update_20240101"}]}'


def _make_mock_urlopen(*responses: bytes):
    """Create a mock urlopen that returns responses in order."""
    iterators = [iter([BytesIO(r)]) for r in responses]

    def mock_urlopen(url, timeout=10):
        for i, resp in enumerate(iterators):
            if str(url).endswith(repomd_url_suffixes[i]):
                return resp
        return BytesIO(b"")

    repomd_url_suffixes = ["update.json", "repomd.xml", "primary.xml.gz"]
    
    def smart_mock(url, timeout=10):
        url_str = str(url)
        if "update.json" in url_str:
            return BytesIO(UPDATE_JSON)
        if "repomd.xml" in url_str:
            return BytesIO(REPOMD_XML)
        if "primary.xml.gz" in url_str:
            return BytesIO(gzip.compress(PRIMARY_XML))
        raise ValueError(f"unexpected url: {url}")

    return smart_mock


def test_fetch_update_packages_returns_source_package_names() -> None:
    mock = _make_mock_urlopen(UPDATE_JSON, REPOMD_XML, PRIMARY_XML)
    with patch("app.modules.pipelines.repodata.urlopen", side_effect=mock):
        packages = fetch_update_packages(
            repo_base_url="http://example.com/repo.openeuler.org",
            version="24.03-LTS-SP3",
        )

    assert "bash" in packages
    assert "curl" in packages
    assert "kernel" in packages
    assert len(packages) == 3


def test_fetch_update_packages_deduplicates() -> None:
    primary_with_dupes = b"""<?xml version="1.0"?>
<metadata xmlns="http://linux.duke.edu/metadata/common">
  <package type="src"><name>bash</name><arch>src</arch></package>
  <package type="src"><name>bash</name><arch>src</arch></package>
  <package type="src"><name>curl</name><arch>src</arch></package>
</metadata>
"""

    def mock(url, timeout=10):
        url_str = str(url)
        if "update.json" in url_str:
            return BytesIO(UPDATE_JSON)
        if "repomd.xml" in url_str:
            return BytesIO(REPOMD_XML)
        if "primary.xml.gz" in url_str:
            return BytesIO(gzip.compress(primary_with_dupes))
        raise ValueError(f"unexpected: {url}")

    with patch("app.modules.pipelines.repodata.urlopen", side_effect=mock):
        packages = fetch_update_packages(
            repo_base_url="http://example.com/repo.openeuler.org",
            version="24.03-LTS-SP3",
        )

    assert len(packages) == 2
    assert set(packages) == {"bash", "curl"}


FILELISTS_REPOMD_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <revision>1700000000</revision>
  <data type="filelists">
    <location href="repodata/abc-filelists.xml.gz" />
    <checksum type="sha256">abc</checksum>
  </data>
</repomd>
"""

FILELISTS_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<filelists xmlns="http://linux.duke.edu/metadata/filelists">
  <package pkgid="1" name="openssh" arch="aarch64">
    <version epoch="0" ver="8" rel="1"/>
    <file>/usr/bin/ssh</file>
    <file>/lib/systemd/system/sshd.service</file>
    <file>/usr/lib/systemd/system/sshd.socket</file>
  </package>
  <package pkgid="2" name="systemd" arch="aarch64">
    <version epoch="0" ver="250" rel="1"/>
    <file>/lib/systemd/system/network.target</file>
    <file>/usr/bin/systemctl</file>
  </package>
  <package pkgid="3" name="bash" arch="aarch64">
    <version epoch="0" ver="5" rel="1"/>
    <file>/usr/bin/bash</file>
  </package>
</filelists>
"""


def test_fetch_service_packages_extracts_systemd_units() -> None:

    def mock(url, timeout=10):
        url_str = str(url)
        if "update.json" in url_str:
            return BytesIO(UPDATE_JSON)
        if "repomd.xml" in url_str:
            return BytesIO(FILELISTS_REPOMD_XML)
        if "filelists.xml.gz" in url_str:
            return BytesIO(gzip.compress(FILELISTS_XML))
        raise ValueError(f"unexpected: {url}")

    with patch("app.modules.pipelines.repodata.urlopen", side_effect=mock):
        services = fetch_service_packages(
            repo_base_url="http://example.com/repo.openeuler.org",
            version="24.03-LTS-SP3",
            arch="aarch64",
        )

    svc_set = set(services)
    assert ("openssh", "sshd", "service") in svc_set
    assert ("openssh", "sshd", "socket") in svc_set
    assert ("systemd", "network", "target") in svc_set
    # bash has no systemd files — should not appear
    assert not any(s[0] == "bash" for s in services)
