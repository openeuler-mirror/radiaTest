from flask import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import RET
from server.utils.response_util import response_collect
from server.model.framework import Framework, GitRepo
from server.utils.db import Insert, Delete, Edit, Select
from server.schema.framework import FrameworkBase, FrameworkQuery, GitRepoBase, GitRepoQuery


# TODO 权限归属基表加入后的改动
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
        filter_params = []
        if query.name:
            filter_params.append(
                Framework.name.like(f'%{query.name}%')
            )
        if query.url:
            filter_params.append(
                Framework.url.like(f'%{query.url}%')
            )
        if query.adaptive:
            filter_params.append(
                Framework.adaptive == query.adaptive
            )
        
        frameworks = Framework.query.filter(*filter_params).all()
        if not frameworks:
            return jsonify(error_code=RET.OK, error_msg="OK", data=[])


        return jsonify(
            error_code=RET.OK, 
            error_msg="OK", 
            data=[
                _framework.to_json() for _framework in frameworks
            ]
        )


class FrameworkItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def delete(self, framework_id):
        return Delete(Framework, {"id": framework_id}).single(Framework, "/framework")
    
    @auth.login_required
    @response_collect
    @validate()
    def put(self, framework_id, body: FrameworkQuery):
        _body = {
            **body.__dict__,
            "id": framework_id,
        }

        return Edit(Framework, _body).single(Framework, "/framework")

    @auth.login_required
    @response_collect
    @validate()
    def get(self, framework_id):
        framework = Framework.query.filter_by(id=framework_id).first()
        if not framework:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the framework does not exist"
            )
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=framework.to_json()
        )


# TODO 权限归属基表加入后的改动
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
        filter_params = []
        if query.name:
            filter_params.append(
                GitRepo.name.like(f'%{query.name}%')
            )
        if query.git_url:
            filter_params.append(
                GitRepo.git_url.like(f'%{query.git_url}%')
            )
        if query.sync_rule:
            filter_params.append(
                GitRepo.sync_rule == query.sync_rule
            )
        if query.framework_id:
            filter_params.append(
                GitRepo.framework_id == query.framework_id
            )
        
        
        git_repos = GitRepo.query.filter(*filter_params).all()
        if not git_repos:
            return jsonify(error_code=RET.OK, error_msg="OK", data=[])


        return jsonify(
            error_code=RET.OK, 
            error_msg="OK", 
            data=[
                _git_repo.to_json() for _git_repo in git_repos
            ]
        )


class GitRepoItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def delete(self, git_repo_id):
        return Delete(GitRepo, {"id": git_repo_id}).single(GitRepo, "/git_repo")
    
    @auth.login_required
    @response_collect
    @validate()
    def put(self, git_repo_id, body: GitRepoQuery):
        _body = {
            **body.__dict__,
            "id": git_repo_id,
        }

        return Edit(GitRepo, _body).single(GitRepo, "/git_repo")

    @auth.login_required
    @response_collect
    def get(self, git_repo_id):
        git_repo = GitRepo.query.filter_by(id=git_repo_id).first()
        if not git_repo:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the git repo does not exist"
            )
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=git_repo.to_json()
        )