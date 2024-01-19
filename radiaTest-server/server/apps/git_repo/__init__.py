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

from flask_restful import Api

from .routes import (
    GitRepoEvent, 
    GitRepoItemEvent, 
    GitRepoScopedEvent,
    GitRepoItemSyncEvent,
)


def init_api(api: Api):
    api.add_resource(GitRepoEvent, "/api/v1/git-repo", "/api/v1/ws/<string:workspace>/git-repo")
    api.add_resource(GitRepoScopedEvent, "/api/v1/git-repo/scoped")
    api.add_resource(GitRepoItemEvent, "/api/v1/git-repo/<int:git_repo_id>")
    api.add_resource(GitRepoItemSyncEvent, "/api/v1/git-repo/<int:git_repo_id>/sync")
