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
    Status,
    StatusOrder,
    Task,
    TaskItem,
    ParticipantItem,
    Cases,
    Family,
    TaskStatistics,
)
from .routes import (
    Comment,
    Participants,
    RecycleBin,
    Tag,
    FamilyItem,
    Report,
    TaskMilestones,
    CasesResult,
    ExecutorItem,
    TaskPercentage,
    TaskGantt,
)
from .routes import (
    TaskMilestonesCases,
    TaskExecute,
    TaskList,
    CaseTask,
    TaskFrame,
    MilestoneTaskProgress,
    CaseNodeTaskProgress,
    SubTaskProgress
)
from .routes import (
    TaskDistributeTemplate,
    DistributeType,
    DistributeCaseByTemplate,
    MileStoneTask,
)


def init_api(api: Api):
    api.add_resource(
        Status,
        "/api/v1/task/status",
        "/api/v1/task/status/<int:status_id>",
        endpoint="task_status",
    )
    api.add_resource(
        StatusOrder, "/api/v1/task/status/order", endpoint="task_status_order"
    )
    api.add_resource(Task, "/api/v1/tasks", "/api/v1/ws/<string:workspace>/tasks", endpoint="task")
    api.add_resource(TaskItem, "/api/v1/tasks/<int:task_id>", endpoint="task_item")
    api.add_resource(
        ParticipantItem,
        "/api/v1/tasks/<int:task_id>/participants",
        endpoint="task_participant_item",
    )
    api.add_resource(
        Participants, "/api/v1/tasks/participants", endpoint="task_participant"
    )
    api.add_resource(
        ExecutorItem,
        "/api/v1/tasks/<int:task_id>/executor",
        endpoint="task_executor_item",
    )
    api.add_resource(
        Comment, "/api/v1/tasks/<int:task_id>/comment", endpoint="task_comment"
    )
    api.add_resource(
        TaskPercentage,
        "/api/v1/tasks/<int:task_id>/percentage"
    )
    api.add_resource(
        TaskGantt,
        "/api/v1/tasks/gantt"
    )
    api.add_resource(
        RecycleBin, "/api/v1/tasks/recycle-bin", endpoint="task_recycle_bin"
    )
    api.add_resource(Tag, "/api/v1/tasks/tags", endpoint="task_tag")
    api.add_resource(
        FamilyItem, "/api/v1/tasks/<int:task_id>/family", endpoint="task_family_item"
    )
    api.add_resource(Family, "/api/v1/tasks/family", endpoint="task_family")
    api.add_resource(
        Report, "/api/v1/tasks/<int:task_id>/reports", endpoint="task_report"
    )
    api.add_resource(
        Cases,
        "/api/v1/tasks/<int:task_id>/milestones/<int:milestone_id>/cases",
        "/api/v1/tasks/<int:task_id>/cases",
        endpoint="task_cases",
    )
    api.add_resource(
        CasesResult,
        "/api/v1/tasks/<int:task_id>/cases/result",
        endpoint="task_cases_result",
    )
    api.add_resource(
        TaskStatistics, "/api/v1/task/count/total", endpoint="task_statistics"
    )
    api.add_resource(
        TaskMilestones,
        "/api/v1/task/milestones/<int:taskmilestone_id>",
        endpoint="task_milestones",
    )
    api.add_resource(
        TaskMilestonesCases,
        "/api/v1/task/<int:task_id>/milestones/<int:taskmilestone_id>/cases/<int:case_id>",
        endpoint="task_milestone_cases",
    )
    api.add_resource(TaskExecute, "/api/v1/tasks/execute", endpoint="out_task")
    api.add_resource(
        TaskDistributeTemplate,
        "/api/v1/tasks/distribute-templates",
        "/api/v1/tasks/distribute-templates/<int:template_id>",
        endpoint="distribute-templates",
    )
    api.add_resource(
        DistributeType,
        "/api/v1/tasks/distribute-templates/<int:template_id>/types",
        "/api/v1/tasks/distribute-templates/suites",
        "/api/v1/tasks/distribute-templates/types/<int:type_id>",
        endpoint="distribute_template_type",
    )
    api.add_resource(
        DistributeCaseByTemplate,
        "/api/v1/tasks/<int:task_id>/distribute-templates/<int:template_id>",
        endpoint="distribute_case_by_template",
    )
    api.add_resource(TaskList, "/api/v1/tasks/list", endpoint="task_list")
    api.add_resource(CaseTask, "/api/v1/case/<int:case_id>/task")
    api.add_resource(TaskFrame, "/api/v1/task/frame")
    api.add_resource(MileStoneTask, "/api/v1/milestone/<int:milestone_id>/tasks")

    api.add_resource(
        MilestoneTaskProgress,
        "/api/v1/milestone/<int:milestone_id>/task-progress"
    )
    api.add_resource(
        CaseNodeTaskProgress,
        "/api/v1/milestone/<int:milestone_id>/task-progress/case-node/<int:case_node_id>"
    )
    api.add_resource(
        SubTaskProgress,
        "/api/v1/milestone/<int:milestone_id>/task-progress/task/<int:task_id>"
    )
