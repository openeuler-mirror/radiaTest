# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""pxe-install.sh 宿主脚本行为测试：引导文件下载失败必须显式报错。

背景：prod 曾因镜像登记指向返回 403 的 URL，脚本里 wget 错误被
``2>/dev/null || true`` 静默吞掉，最终报出误导性的
"vmlinuz not found"。用本地 HTTP 桩服务验证：
- EFI/pxeboot 下载失败时报 sync_failed 且消息带原始 URL；
- 200 空文件不被当作有效 EFI；
- 下载成功时引导文件完整落盘（DHCP 绑定段用 KRONOS_DHCP_CONF 隔离）。
"""

import base64
import io
import json
import os
import shutil
import subprocess
import threading
from collections.abc import Callable
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("wget", path="/usr/bin:/bin") is None,
    reason="pxe-install.sh 的引导文件下载依赖宿主 wget",
)


SCRIPT = (
    Path(__file__).parents[1] / "app" / "modules" / "vms" / "host_scripts" / "pxe-install.sh"
)

TARGET_IP = "172.168.199.10"
TARGET_MAC = "aa:bb:cc:dd:ee:ff"

PXEBOOT_LISTING = (
    '<html><body><a href="vmlinuz">vmlinuz</a><a href="initrd.img">initrd.img</a></body></html>'
)


class _StubHandler(SimpleHTTPRequestHandler):
    """按 routes 前缀表返回 (status, body)；未命中返回 404。"""

    routes: list[tuple[str, int, bytes]] = []

    def send_head(self) -> io.BytesIO | None:
        """生成响应头并返回响应体流；标准库的 GET 处理直接复用，见下方说明。

        BaseHTTPRequestHandler 按 "do_" + 大写的 HTTP 方法名分派，标识符无法写成
        snake_case（G.NAM.01），因此不改写该方法名，而是覆写它调用的 send_head。
        """
        path = self.path.replace("//", "/")
        for prefix, status, body in type(self).routes:
            if path.startswith(prefix):
                self.send_response(status)
                # wget 只从 text/html 响应解析链接递归下载，目录列表必须用 text/html
                # （与 Apache autoindex 一致）；文件用 octet-stream。
                ctype = "text/html" if path.endswith("/") else "application/octet-stream"
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return io.BytesIO(body)
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    @staticmethod
    def log_message(*args: object) -> None:
        pass


@pytest.fixture()
def stub_server() -> Callable[[list[tuple[str, int, bytes]]], str]:
    servers: list[ThreadingHTTPServer] = []

    def _start(routes: list[tuple[str, int, bytes]]) -> str:
        handler = type("_Handler", (_StubHandler,), {"routes": routes})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        servers.append(server)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return f"http://127.0.0.1:{server.server_port}"

    yield _start
    for server in servers:
        server.shutdown()
        server.server_close()


def _official_routes() -> list[tuple[str, int, bytes]]:
    # 顺序敏感：文件前缀必须排在目录列表前缀之前（startswith 匹配）。
    return [
        ("/OS/x86_64/EFI/BOOT/grubx64.efi", 200, b"grub-efi-binary"),
        ("/OS/x86_64/images/pxeboot/vmlinuz", 200, b"vmlinuz-data"),
        ("/OS/x86_64/images/pxeboot/initrd.img", 200, b"initrd-data"),
        ("/OS/x86_64/images/pxeboot/", 200, PXEBOOT_LISTING.encode()),
    ]


def _run_script(tmp_path: Path, base: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "target_mac": TARGET_MAC,
        "target_ip": TARGET_IP,
        "efi_url": f"{base}/OS/x86_64/EFI/BOOT/grubx64.efi",
        "repo_url": f"{base}/OS/x86_64",
        "arch": "x86_64",
        "os_name": "openEuler-24.03-LTS-SP1",
        "tftp_root": str(tmp_path / "tftpboot"),
        "httpd_root": str(tmp_path / "www"),
        "httpd_prefix": "http://stub.invalid:9400",
        "nics": [TARGET_MAC],
    }
    dhcp_conf = tmp_path / "dhcpd.conf"
    dhcp_conf.write_text("# stub dhcpd.conf\n")
    env = os.environ | {
        "KRONOS_PAYLOAD_B64": base64.b64encode(json.dumps(payload).encode()).decode(),
        # 隔离 DHCP 段：systemctl restart dhcpd 在测试机必然失败 → bind_failed，
        # 但 sync 段产物已完整落盘，且绝不触碰 /etc/dhcp/dhcpd.conf。
        "KRONOS_DHCP_CONF": str(dhcp_conf),
        # 生产走 SSH 用系统 python(3.11，带 crypt)；本地把 PATH 收敛到 /usr/bin，
        # 避免 uv venv 的 3.13(无 crypt) 让 ks 段崩溃。
        "PATH": "/usr/bin:/bin",
    }
    return subprocess.run(
        ["/bin/bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60
    )


def _error_result(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.returncode != 0
    result = json.loads(proc.stdout)
    assert result["status"] == "error"
    return result


def test_efi_download_failure_reports_url(stub_server, tmp_path) -> None:
    base = stub_server([("/OS/x86_64/EFI/BOOT/grubx64.efi", 403, b"forbidden")])
    proc = _run_script(tmp_path, base)

    result = _error_result(proc)
    assert result["error_code"] == "sync_failed"
    assert "grubx64.efi" in result["error_message"]
    assert "vmlinuz not found" not in result["error_message"]


def test_pxeboot_download_failure_reports_url(stub_server, tmp_path) -> None:
    base = stub_server([("/OS/x86_64/EFI/BOOT/grubx64.efi", 200, b"grub-efi-binary")])
    proc = _run_script(tmp_path, base)

    result = _error_result(proc)
    assert result["error_code"] == "sync_failed"
    assert "images/pxeboot" in result["error_message"]
    assert "vmlinuz not found" not in result["error_message"]


def test_empty_efi_is_rejected(stub_server, tmp_path) -> None:
    base = stub_server([("/OS/x86_64/EFI/BOOT/grubx64.efi", 200, b"")])
    proc = _run_script(tmp_path, base)

    result = _error_result(proc)
    assert result["error_code"] == "sync_failed"
    assert "EFI file is empty" in result["error_message"]


def test_successful_download_syncs_boot_files(stub_server, tmp_path) -> None:
    base = stub_server(_official_routes())
    proc = _run_script(tmp_path, base)

    pxeboot_dir = tmp_path / "tftpboot" / "radia_test" / TARGET_IP / "pxeboot"
    assert (pxeboot_dir / "vmlinuz").read_bytes() == b"vmlinuz-data"
    assert (pxeboot_dir / "initrd.img").read_bytes() == b"initrd-data"
    efi_path = tmp_path / "tftpboot" / "radia_test" / TARGET_IP / "grubx64.efi"
    assert efi_path.read_bytes() == b"grub-efi-binary"
    grub_cfg = (tmp_path / "tftpboot" / "radia_test" / TARGET_IP / "grub.cfg").read_text()
    assert "pxeboot/vmlinuz" in grub_cfg
    ks_path = tmp_path / "www" / "ks" / "radia_test" / f"{TARGET_IP}.ks"
    assert f"url --url={base}/OS/x86_64" in ks_path.read_text()
    # 证明流程走完 sync 段、到达 DHCP 绑定段（绑定结果与本测试无关）。
    assert "开始绑定 DHCP" in proc.stderr
