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
import sys
import types
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# server/__init__.py 依赖 MySQL/Redis/Casbin 等完整运行环境才能引导，
# 单元测试只需被测模块本身，这里注册一个轻量包替身跳过应用引导，
# server.* 子模块仍按真实源码加载
if "server" not in sys.modules:
    server_pkg = types.ModuleType("server")
    server_pkg.__path__ = [str(BASE_DIR / "server")]
    sys.modules["server"] = server_pkg
