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
import os
from pathlib import Path

import pytest

from server.utils.config_util import loads_app_yaml, loads_config_ini

INI_PATH = Path("/etc/radiaTest/server.ini")


class FakeApp:
    def __init__(self, config):
        self.config = config


@pytest.fixture
def server_ini_guard():
    INI_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup = INI_PATH.read_bytes() if INI_PATH.exists() else None
    yield
    if backup is not None:
        INI_PATH.write_bytes(backup)
    elif INI_PATH.exists():
        os.remove(INI_PATH)


def _write_ini(content):
    INI_PATH.parent.mkdir(parents=True, exist_ok=True)
    INI_PATH.write_text(content, encoding="utf-8")


def test_loads_config_ini_parses_and_cleans(server_ini_guard):
    _write_ini("[server]\nport = 8082\nname = radiaTest\n")
    config = loads_config_ini()
    assert config["PORT"] == 8082
    assert config["NAME"] == "radiaTest"
    assert not INI_PATH.exists()


def test_loads_config_ini_keeps_string_value(server_ini_guard):
    _write_ini("[server]\ndebug = True\n")
    config = loads_config_ini()
    assert config["DEBUG"] == "True"


def test_loads_config_ini_without_file(server_ini_guard):
    if INI_PATH.exists():
        os.remove(INI_PATH)
    assert loads_config_ini() == {}


def test_loads_app_yaml_loads_and_cleans(tmp_path):
    yaml_path = tmp_path / "app.yaml"
    yaml_path.write_text(
        "- appid: xxx\n  name: test\n  secret: sss\n", encoding="utf-8"
    )
    app = FakeApp({"YAML_PATH": str(yaml_path)})
    loads_app_yaml(app)
    assert app.config["APP"] == [{"appid": "xxx", "name": "test", "secret": "sss"}]
    assert not yaml_path.exists()


def test_loads_app_yaml_without_file(tmp_path):
    app = FakeApp({"YAML_PATH": str(tmp_path / "not_exist.yaml")})
    loads_app_yaml(app)
    assert "APP" not in app.config
