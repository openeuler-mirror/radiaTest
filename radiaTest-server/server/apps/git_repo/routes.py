# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang
# @email   : ethanzhang55@outlook.com
# @Date    : 
# @License : Mulan PSL v2


#####################################

from flask import jsonify, g
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer, redis_client, swagger_adapt
from server.utils.response_util import RET, workspace_error_collect
from server.utils.auth_util import auth
from server.utils.db import Insert, Edit
from server.utils.response_util import response_collect
from server.model.celerytask import CeleryTask
from server.model.framework import GitRepo
from server.schema.framework import GitRepoBase, GitRepoQuery, GitRepoScopedQuery
from server.apps.git_repo.handlers import GitRepoHandler
from server.utils.resource_utils import ResourceManager
from server.utils.permission_utils import GetAllByPermission


def get_git_repo_tag():
    return {
        "name": "测试框架git_repo",
        "description": "测试框架git_repo相关接口",
    }


class GitRepoScopedEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoScopedEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "查询git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": GitRepoScopedQuery,   # 当前接口查询参数schema校验器
    })
    def get(self, query: GitRepoScopedQuery):
        filter_params = [
            GitRepo.permission_type == query.type
        ]
        if query.type == "group":
            filter_params.append(GitRepo.group_id == query.group_id)
        elif query.type == "org":
            filter_params.append(GitRepo.org_id == query.org_id)

        return GitRepoHandler.get_git_repo(query, filter_params)


class GitRepoEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "添加git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": GitRepoBase,   # 当前接口查询参数schema校验器
    })
    def post(self, body: GitRepoBase):
        return ResourceManager("git_repo").add_v2("framework/api_infos.yaml", body.__dict__)

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "查询指定工作区下git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": GitRepoQuery,   # 当前接口查询参数schema校验器
    })
    def get(self, workspace: str, query: GitRepoQuery):
        filter_params = GetAllByPermission(GitRepo, workspace).get_filter()
        return GitRepoHandler.get_git_repo(query, filter_params)


class GitRepoItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "删除git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, git_repo_id):
        return ResourceManager("git_repo").del_single(git_repo_id)

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "修改git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": GitRepoQuery,   # 当前接口查询参数schema校验器
    })
    def put(self, git_repo_id, body: GitRepoQuery):
        _body = {
            **body.__dict__,
            "id": git_repo_id,
        }

        return Edit(GitRepo, _body).single(GitRepo, "/git_repo")

    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "通过git_repo_id获取git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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


class GitRepoItemSyncEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_git_repo_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GitRepoItemSyncEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_git_repo_tag(),  # 当前接口所对应的标签
        "summary": "同步指定git_repo",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, git_repo_id):
        """
        trigger 'read git repo' celery worker
        Args:
            git_repo_id(int): ID of the repo to sync
        Returns:
            Response: error_code(int), error_msg(str)
        """
        repo = GitRepo.query.filter_by(id=git_repo_id).first()
        if not repo or not repo.sync_rule:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"repo #{git_repo_id} does not exist or not allow to resolve"
            )
        
        if not repo.adaptive:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=f"{repo.framework.name} is not adapted, the testcase repo could not be resolved"
            )

        if redis_client.get(f"loading_repo#{repo.id}_{repo.git_url}@{repo.branch}"):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"locked: repo#{repo.id} from {repo.git_url}@{repo.branch} has been loading"
            )

        from celeryservice.tasks import load_scripts
        _task = load_scripts.delay(
            repo.id,
            repo.name,
            repo.git_url,
            repo.branch,
        )
        celerytask = {
            "tid": _task.task_id,
            "status": "PENDING",
            "object_type": "scripts_load",
            "description": f"from {repo.git_url} on branch {repo.branch}",
            "user_id": g.user_id,
        }

        _ = Insert(CeleryTask, celerytask).single(CeleryTask, "/celerytask")

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )