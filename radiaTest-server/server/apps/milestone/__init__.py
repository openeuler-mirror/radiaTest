from flask_restful import Api

from .routes import (
    GiteeIssuesV1, 
    GiteeIssuesV2, 
    MilestoneEventV1, 
    MilestoneEventV2, 
    MilestoneItemChangeStateV2, 
    MilestoneItemEventV1, 
    MilestoneItemEventV2, 
    MilestonePreciseEvent, 
    GiteeIssuesTypeV2
)


def init_api(api: Api):
    api.add_resource(MilestoneEventV1, "/api/v1/milestone")
    api.add_resource(MilestoneEventV2, "/api/v2/milestone")
    api.add_resource(MilestoneItemEventV1, "/api/v1/milestone/<int:milestone_id>")
    api.add_resource(MilestoneItemEventV2, "/api/v2/milestone/<int:milestone_id>")
    api.add_resource(GiteeIssuesV1, "/api/v1/milestone/issues")
    api.add_resource(GiteeIssuesV2, "/api/v2/milestone/issues")
    api.add_resource(GiteeIssuesTypeV2, "/api/v2/milestone/issue_types")
    api.add_resource(MilestonePreciseEvent, "/api/v1/milestone/preciseget")
    api.add_resource(MilestoneItemChangeStateV2, "/api/v2/milestone/<int:milestone_id>/change_state")