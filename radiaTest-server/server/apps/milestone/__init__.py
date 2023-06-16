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

from .routes import (
    OrgMilestoneEventV1,
    GroupMilestoneEventV1,
    MilestoneEventV2,
    MilestoneItemEventV2,
    MilestonePreciseEvent,
    GiteeMilestoneEventV2,
    SyncMilestoneItemEventV2,
    MilestoneItemStateEventV2,
    MilestoneIssueRateEvent,
    GenerateTestReportEvent,
    TestReportEvent,
    TestReportFileEvent,
    MilestoneGantt,
)


def init_api(api: Api):
    api.add_resource(MilestoneEventV2, "/api/v2/milestone", "/api/v2/ws/<string:workspace>/milestone")
    api.add_resource(MilestoneItemEventV2, "/api/v2/milestone/<int:milestone_id>")
    api.add_resource(MilestoneItemStateEventV2, "/api/v2/milestone/<int:milestone_id>/state")
    api.add_resource(OrgMilestoneEventV1, "/api/v1/org/<int:org_id>/milestone")
    api.add_resource(GroupMilestoneEventV1, "/api/v1/group/<int:group_id>/milestone")
    api.add_resource(MilestonePreciseEvent, "/api/v1/milestone/preciseget")
    api.add_resource(
        MilestoneIssueRateEvent,
        "/api/v2/milestone/<int:milestone_id>/issue-rate",
    )
    api.add_resource(GiteeMilestoneEventV2, "/api/v2/gitee-milestone")
    api.add_resource(SyncMilestoneItemEventV2, "/api/v2/milestone/<int:milestone_id>/sync")
    api.add_resource(GenerateTestReportEvent, "/api/v2/milestone/<int:milestone_id>/generate-test-report")
    api.add_resource(TestReportFileEvent, "/api/v2/milestone/<int:milestone_id>/test-report-file")
    api.add_resource(TestReportEvent, "/api/v2/milestone/<int:milestone_id>/test-report")
    api.add_resource(
        MilestoneGantt,
        "/api/v2/milestone/gantt"
    )
