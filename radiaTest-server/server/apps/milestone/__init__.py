from flask_restful import Api

from .routes import (
    GiteeIssuesV1, 
    GiteeIssuesV2, 
    MilestoneEventV2, 
    MilestoneItemEventV2, 
    MilestonePreciseEvent, 
    GiteeIssuesTypeV2,
    GiteeIssuesItemV2
)

def init_api(api: Api):
    api.add_resource(MilestoneEventV2, "/api/v2/milestone")
    api.add_resource(MilestoneItemEventV2, "/api/v2/milestone/<int:milestone_id>")
    api.add_resource(GiteeIssuesV1, "/api/v1/milestone/issues")
    api.add_resource(GiteeIssuesV2, "/api/v2/milestone/issues")
    api.add_resource(GiteeIssuesItemV2, "/api/v2/milestone/issues/<int:issue_id>")
    api.add_resource(GiteeIssuesTypeV2, "/api/v2/milestone/issue_types")
    api.add_resource(MilestonePreciseEvent, "/api/v1/milestone/preciseget")
