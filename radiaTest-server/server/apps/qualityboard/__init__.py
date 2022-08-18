from flask_restful import Api

from .routes import (
    QualityBoardEvent,
    QualityBoardItemEvent,
    QualityBoardDeleteVersionEvent,
    ATOverview,
    QualityDefendEvent,
    ChecklistEvent,
    ChecklistItem
)


def init_api(api: Api):
    api.add_resource(QualityBoardEvent, "/api/v1/qualityboard")
    api.add_resource(
        QualityBoardItemEvent, "/api/v1/qualityboard/<int:qualityboard_id>"
    )
    api.add_resource(
        QualityBoardDeleteVersionEvent,
        "/api/v1/qualityboard/rollback/<int:qualityboard_id>",
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