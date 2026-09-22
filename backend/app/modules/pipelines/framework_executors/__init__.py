# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Framework executor(Seam 2: test_framework)。每个 executor 定义如何为一个
测试框架构建执行单元 + 运行 + 解析结果。pipeline 框架循环经 registry 分派。
mugen 是首个实现；非 mugen 框架在此插拔。
"""

from __future__ import annotations

from .mugen import MugenFrameworkExecutor

__all__ = ["MugenFrameworkExecutor"]
