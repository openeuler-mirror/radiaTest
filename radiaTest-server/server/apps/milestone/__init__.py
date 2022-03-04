from flask_restful import Api

from .routes import MilestoneEvent, PreciseGet, GiteeIssues, MilestoneEventItem


def init_api(api: Api):
    api.add_resource(MilestoneEvent, "/api/v1/milestone")
    api.add_resource(MilestoneEventItem, "/api/v1/milestone/<int:milestone_id>")
    api.add_resource(PreciseGet, "/api/v1/milestone/preciseget")
    api.add_resource(GiteeIssues, "/api/v1/milestone/issues")