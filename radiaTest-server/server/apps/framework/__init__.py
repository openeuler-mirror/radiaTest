# Copyright (c) [2021] Huawei Technologies Co.,Ltd.ALL rights reserved.
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

from flask_restful import Api

from .routes import FrameworkEvent, FrameworkItemEvent, GitRepoEvent, GitRepoItemEvent


def init_api(api: Api):
    api.add_resource(FrameworkEvent, "/api/v1/framework")
    api.add_resource(FrameworkItemEvent, "/api/v1/framework/<int:framework_id>")
    api.add_resource(GitRepoEvent, "/api/v1/git_repo")
    api.add_resource(GitRepoItemEvent, "/api/v1/git_repo/<int:git_repo_id>")
