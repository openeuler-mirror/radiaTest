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

from flask import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import RET
from server.utils.response_util import response_collect
from server.model.framework import Framework, GitRepo
from server.utils.db import Insert, Delete, Edit, Select
from server.schema.framework import FrameworkBase, FrameworkQuery, GitRepoBase, GitRepoQuery
from server.utils.resource_utils import ResourceManager
from server.utils.permission_utils import GetAllByPermission
from server import casbin_enforcer


class FrameworkEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: FrameworkBase):
        return ResourceManager("framework").add("api_infos.yaml", body.__dict__)

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: FrameworkQuery):
        filter_params = GetAllByPermission(Framework).get_filter()
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
    @casbin_enforcer.enforcer
    def delete(self, framework_id):
        return ResourceManager("framework").del_cascade_single(framework_id, GitRepo, [GitRepo.framework_id==framework_id], False)
    
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, framework_id, body: FrameworkQuery):
        _body = {
            **body.__dict__,
            "id": framework_id,
        }

        return Edit(Framework, _body).single(Framework, "/framework")

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
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


class GitRepoEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: GitRepoBase):
        return ResourceManager("git_repo").add("api_infos.yaml", body.__dict__)

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: GitRepoQuery):
        filter_params = GetAllByPermission(GitRepo).get_filter()
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
    @casbin_enforcer.enforcer
    def delete(self, git_repo_id):
        return ResourceManager("git_repo").del_single(git_repo_id)
    
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, git_repo_id, body: GitRepoQuery):
        _body = {
            **body.__dict__,
            "id": git_repo_id,
        }

        return Edit(GitRepo, _body).single(GitRepo, "/git_repo")

    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
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