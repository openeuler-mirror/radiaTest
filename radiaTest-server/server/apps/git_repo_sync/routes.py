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

from flask import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from celeryservice.tasks import load_scripts
from server import casbin_enforcer, redis_client
from server.utils.response_util import RET
from server.utils.auth_util import auth
from server.utils.db import Insert
from server.utils.response_util import response_collect
from server.model.celerytask import CeleryTask
from server.model.framework import GitRepo

class GitRepoItemSyncEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
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
        
        if not repo.framework.adaptive:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=f"{repo.framework.name} is not adapted, the testcase repo could not be resolved"
            )

        if redis_client.get(f"loading_repo#{repo.id}_{repo.git_url}@{repo.branch}"):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"locked: repo#{repo.id} from {repo.git_url}@{repo.branch} has been loading"
            )

        _task = load_scripts.delay(
            repo.id,
            repo.name,
            repo.git_url,
            repo.branch,
            repo.framework.name,
        )
        celerytask = {
            "tid": _task.task_id,
            "status": "PENDING",
            "object_type": "scripts_load",
            "description": f"from {repo.git_url} on branch {repo.branch}",
        }

        _ = Insert(CeleryTask, celerytask).single(CeleryTask, "/celerytask")

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )