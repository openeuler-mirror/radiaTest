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

from server.model.framework import GitRepo
from server.utils.response_util import RET


class GitRepoHandler:
    @staticmethod
    def get_git_repo(query, filter_params: list):
        if query.name:
            filter_params.append(
                GitRepo.name.like(f'%{query.name}%')
            )
        if query.git_url:
            filter_params.append(
                GitRepo.git_url.like(f'%{query.git_url}%')
            )
        if query.branch:
            filter_params.append(
                GitRepo.branch.like(f'%{query.branch}%')
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