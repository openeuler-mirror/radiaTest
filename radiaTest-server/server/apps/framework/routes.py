from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.model.framework import Framework, GitRepo
from server.utils.db import Insert, Delete, Edit, Select
from server.schema.framework import FrameworkBase, FrameworkQuery, GitRepoBase, GitRepoQuery


# TODO 考慮有歸屬基表後的變動（如篩選條件）
class FrameworkEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: FrameworkBase):
        return Insert(Framework, body.__dict__).single(Framework, '/framework')

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: FrameworkQuery):
        body = query.__dict__
        return Select(Framework, body).fuzz()


class FrameworkItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def delete(self, framework_id):
        return Delete(Framework, {"id": framework_id}).single(Framework, "/framework")
    
    @auth.login_required
    @response_collect
    @validate()
    def post(self, framework_id, body: FrameworkQuery):
        _body = {
            **body.__dict__,
            "id": framework_id,
        }

        return Edit(Framework, _body).single(Framework, "/framework")


# TODO 考慮有歸屬基表後的變動（如篩選條件）
class GitRepoEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: GitRepoBase):
        return Insert(GitRepo, body.__dict__).single(GitRepo, '/git_repo')

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: GitRepoQuery):
        body = query.__dict__
        return Select(GitRepo, body).fuzz()


class GitRepoItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def delete(self, git_repo_id):
        return Delete(GitRepo, {"id": git_repo_id}).single(GitRepo, "/git_repo")
    
    @auth.login_required
    @response_collect
    @validate()
    def post(self, git_repo_id, body: GitRepoQuery):
        _body = {
            **body.__dict__,
            "id": git_repo_id,
        }

        return Edit(GitRepo, _body).single(GitRepo, "/git_repo")