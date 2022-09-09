from flask_restful import Api

from .routes import (
    FeatureListSummary,
    PackageListCompareEvent,
    PackageListEvent,
    QualityBoardEvent,
    QualityBoardItemEvent,
    QualityBoardDeleteVersionEvent,
    ATOverview,
    QualityDefendEvent,
    ChecklistEvent,
    ChecklistItem,
    ChecklistRoundsCountEvent,
    DailyBuildOverview,
    DailyBuildDetail,
    WeeklybuildHealthOverview,
    WeeklybuildHealthEvent,
    FeatureListEvent,
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
        ChecklistItem,
        "/api/v1/checklist/<int:checklist_id>",
    )
    api.add_resource(
        ChecklistEvent,
        "/api/v1/checklist",
    )
    api.add_resource(
        ChecklistRoundsCountEvent,
        "/api/v1/checklist/rounds-count/<int:product_id>",
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
        WeeklybuildHealthOverview,
        "/api/v1/qualityboard/<int:qualityboard_id>/weeklybuild-health",
    )
    api.add_resource(
        WeeklybuildHealthEvent,
        "/api/v1/weeklybuild/<int:weeklybuild_id>",
    )
    api.add_resource(
        FeatureListEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/feature-list"
    )
    api.add_resource(
        FeatureListSummary,
        "/api/v1/qualityboard/<int:qualityboard_id>/feature-list/summary"
    )
    api.add_resource(
        PackageListEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/milestone/<int:milestone_id>/pkg-list",
    )
    api.add_resource(
        PackageListCompareEvent,
        "/api/v1/qualityboard/<int:qualityboard_id>/milestone/<int:comparee_milestone_id>/with/<int:comparer_milestone_id>/pkg-compare"
    )
