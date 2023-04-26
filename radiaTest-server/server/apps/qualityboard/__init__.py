# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
# @Date    :
# @License : Mulan PSL v2
#####################################

from flask_restful import Api

from .routes import (
    ChecklistResultEvent,
    FeatureSummary,
    PackageListCompareEvent,
    DailyBuildPackageListCompareEvent,
    DailyBuildPkgEvent,
    DailyPackagCompareResultExportEvent,
    RoundIssueEvent,
    RoundMilestoneEvent,
    SamePackageListCompareEvent,
    PackageListEvent,
    QualityBoardEvent,
    QualityBoardItemEvent,
    QualityBoardDeleteVersionEvent,
    ATOverview,
    QualityDefendEvent,
    DeselectChecklistItem,
    ChecklistEvent,
    ChecklistItem,
    ChecklistRoundsCountEvent,
    DailyBuildOverview,
    DailyBuildDetail,
    WeeklybuildHealthOverview,
    WeeklybuildHealthEvent,
    FeatureEvent,
    CheckItemEvent,
    CheckItemSingleEvent,
    QualityResultCompare,
    QualityResult,
    RoundEvent,
    RoundIssueRateEvent,
    RoundItemEvent,
    CompareRoundEvent,
    RpmCheckOverview,
    RpmCheckDetailEvent,
    PackagCompareResultExportEvent,
    SamePackagCompareResultExportEvent,
    RoundRepeatRpmEvent,
)


def init_api(api: Api):
    api.add_resource(QualityBoardEvent, "/api/v1/qualityboard")
    api.add_resource(
        QualityBoardItemEvent, "/api/v1/qualityboard/<int:qualityboard_id>"
    )
    api.add_resource(
        QualityBoardDeleteVersionEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/rollback",
    )
    api.add_resource(
        ATOverview,
        "/api/v1/qualityboard/<int:qualityboard_id>/at"
    )
    api.add_resource(
        QualityDefendEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/quality-defend"
    )
    api.add_resource(
        CheckItemSingleEvent,
        "/api/v1/checkitem/<int:checkitem_id>",
    )
    api.add_resource(
        CheckItemEvent,
        "/api/v1/checkitem",
    )
    api.add_resource(
        DeselectChecklistItem,
        "/api/v1/checklist/<int:checklist_id>/deselect",
    )
    api.add_resource(
        ChecklistItem,
        "/api/v1/checklist/<int:checklist_id>",
    )
    api.add_resource(
        ChecklistEvent,
        "/api/v1/checklist",
    )
    api.add_resource(
        ChecklistRoundsCountEvent,
        "/api/v1/checklist/rounds-count",
    )
    api.add_resource(
        DailyBuildOverview,
        "/api/v1/qualityboard/<int:qualityboard_id>/dailybuild",
    )
    api.add_resource(
        DailyBuildDetail,
        "/api/v1/dailybuild/<int:dailybuild_id>",
    )
    api.add_resource(
        RpmCheckOverview,
        "/api/v1/qualityboard/<int:qualityboard_id>/rpmcheck",
    )
    api.add_resource(
        RpmCheckDetailEvent,
        "/api/v1/rpmcheck",
    )
    api.add_resource(
        WeeklybuildHealthOverview,
        "/api/v1/qualityboard/<int:qualityboard_id>/weeklybuild-health",
    )
    api.add_resource(
        WeeklybuildHealthEvent,
        "/api/v1/weeklybuild/<int:weeklybuild_id>",
    )
    api.add_resource(
        FeatureEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/feature-list"
    )
    api.add_resource(
        FeatureSummary,
        "/api/v1/qualityboard/<int:qualityboard_id>/feature-list/summary"
    )
    api.add_resource(
        PackageListEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/round/<int:round_id>/pkg-list",
    )
    api.add_resource(
        PackageListCompareEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/round/<int:comparee_round_id>/with/<int:comparer_round_id>/pkg-compare"
    )
    api.add_resource(
        DailyBuildPackageListCompareEvent,
        "/api/v1/qualityboard/daily-build/with/round/<int:comparer_round_id>/pkg-compare"
    )
    api.add_resource(
        DailyPackagCompareResultExportEvent,
        "/api/v1/qualityboard/daily-build/with/round/<int:comparer_round_id>/pkg-compare-result-export"
    )
    api.add_resource(
        DailyBuildPkgEvent,
        "/api/v1/qualityboard/daily-build"
    )
    api.add_resource(
        SamePackageListCompareEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/round/<int:round_id>/pkg-compare"
    )
    api.add_resource(
        PackagCompareResultExportEvent,
        "/api/v1/round/<int:comparee_round_id>/with/<int:comparer_round_id>/pkg-compare-result-export"
    )
    api.add_resource(
        SamePackagCompareResultExportEvent,
        "/api/v1/round/<int:round_id>/pkg-compare-result-export"
    )
    api.add_resource(
        QualityResultCompare,
        "/api/v1/quality-compare"
    )
    api.add_resource(
        QualityResult,
        "/api/v1/quality-result/<int:milestone_id>"
    )
    api.add_resource(
        RoundEvent,
        "/api/v1/round"
    )
    api.add_resource(
        RoundItemEvent,
        "/api/v1/round/<int:round_id>"
    )
    api.add_resource(
        CompareRoundEvent,
        "/api/v1/round/<int:round_id>/compare-round"
    )
    api.add_resource(
        RoundMilestoneEvent,
        "/api/v1/round/<int:round_id>/bind-milestone"
    )
    api.add_resource(
        RoundIssueRateEvent,
        "/api/v1/round/<int:round_id>/issue-rate"
    )
    api.add_resource(
        RoundIssueEvent,
        "/api/v1/round/<int:round_id>/issues"
    )
    api.add_resource(
        ChecklistResultEvent,
        "/api/v1/round/<int:round_id>/checklist-result",
    )
    api.add_resource(
        RoundRepeatRpmEvent,
        "/api/v1/round/<int:round_id>/repeat-rpm"
    )
