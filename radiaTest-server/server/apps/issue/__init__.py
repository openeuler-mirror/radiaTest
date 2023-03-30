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

from flask_restful import Api

from server.apps.issue.routes import (
    GiteeIssuesType,
    GiteeIssuesState,
    GiteeIssuesItem,
    GiteeIssuesV5,
    GiteeIssuesV8,
    UpdateGiteeIssuesTypeState,
    IssueEvent,
    IssueItemEvent,
    GiteeProjectEvent,
)


def init_api(api: Api):
    api.add_resource(IssueEvent, "/api/v1/issues")
    api.add_resource(IssueItemEvent, "/api/v1/issues/<int:issue_id>")
    api.add_resource(GiteeIssuesType, "/api/v1/issue-types")
    api.add_resource(GiteeIssuesState, "/api/v1/issue-states")
    api.add_resource(GiteeProjectEvent, "/api/v1/gitee-project")
    api.add_resource(GiteeIssuesV5, "/api/v1/gitee-issues")
    api.add_resource(GiteeIssuesV8, "/api/v2/gitee-issues")
    api.add_resource(GiteeIssuesItem, "/api/v1/gitee-issues/<int:gitee_issue_id>")
    api.add_resource(UpdateGiteeIssuesTypeState, "/api/v2/issues/type-state")

