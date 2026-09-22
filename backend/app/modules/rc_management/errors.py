# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rc_management 领域异常：由 router 统一映射为 APIError。"""


class RcManagementError(Exception):
    """rc_management 领域异常基类。"""


class VersionNotFoundError(RcManagementError):
    def __init__(self, version_id: str) -> None:
        super().__init__(f"版本 {version_id} 不存在")


class MilestoneNotFoundError(RcManagementError):
    def __init__(self, milestone_id: str) -> None:
        super().__init__(f"里程碑 {milestone_id} 不存在")


class CompareNotFoundError(RcManagementError):
    def __init__(self, compare_id: str) -> None:
        super().__init__(f"比对任务 {compare_id} 不存在")


class VersionHasMilestonesError(RcManagementError):
    def __init__(self, name: str) -> None:
        super().__init__(f"版本 {name} 下仍有里程碑，不可删除")


class MilestoneHasComparesError(RcManagementError):
    def __init__(self, name: str) -> None:
        super().__init__(f"里程碑 {name} 已有比对记录，不可删除")


class VersionDuplicateError(RcManagementError):
    def __init__(self, name: str) -> None:
        super().__init__(f"版本 {name} 已存在")


class MilestoneDuplicateError(RcManagementError):
    def __init__(self, name: str) -> None:
        super().__init__(f"里程碑 {name} 已存在")


class InvalidBuildUrlError(RcManagementError):
    def __init__(self, url: str) -> None:
        super().__init__(
            f"比对构建根 URL 无效：{url}，需形如 …/EBS-<product>/<round>/<kernel-variant>/"
        )


class CompareVersionMismatchError(RcManagementError):
    def __init__(self) -> None:
        super().__init__("比对的两个里程碑必须属于同一版本")


class CompareInProgressError(RcManagementError):
    def __init__(self, milestone: str) -> None:
        super().__init__(f"里程碑 {milestone} 已有进行中的比对，请稍后再试")


class MilestoneBuildUrlMissingError(RcManagementError):
    def __init__(self, name: str) -> None:
        super().__init__(f"里程碑 {name} 未登记比对构建根 URL，先在里程碑上补齐再比对")
