from flask_restful import Api

from .routes import FrameworkEvent, FrameworkItemEvent, GitRepoEvent, GitRepoItemEvent


def init_api(api: Api):
    api.add_resource(FrameworkEvent, "/api/v1/framework")
    api.add_resource(FrameworkItemEvent, "/api/v1/framework/<int:framework_id>")
    api.add_resource(GitRepoEvent, "/api/v1/git_repo")
    api.add_resource(GitRepoItemEvent, "/api/v1/git_repo/<int:git_repo_id>")
