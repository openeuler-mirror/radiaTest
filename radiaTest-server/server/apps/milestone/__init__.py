from flask_restful import Api

from .routes import (
    GiteeIssuesV1,
    GiteeIssuesV2,
    OrgMilestoneEventV1,
    GroupMilestoneEventV1,
    MilestoneEventV2,
    MilestoneItemEventV2,
    MilestonePreciseEvent,
    GiteeIssuesTypeV2,
    GiteeIssuesStateV2,
    GiteeIssuesItemV2,
    GiteeIssuesStatisticsByMilestone,
    UpdateGiteeIssuesStatistics,
    GiteeMilestoneEventV2,
    SyncMilestoneItemEventV2,
    MilestoneItemStateEventV2,
    UpdateGiteeIssuesTypeState,
    UpdateMilestoneIssueRateByField,
    GenerateTestReportEvent,
    TestReportEvent,
    TestReportFileEvent,
)


def init_api(api: Api):
    api.add_resource(MilestoneEventV2, "/api/v2/milestone")
    api.add_resource(MilestoneItemEventV2, "/api/v2/milestone/<int:milestone_id>")
    api.add_resource(MilestoneItemStateEventV2, "/api/v2/milestone/<int:milestone_id>/state")
    api.add_resource(OrgMilestoneEventV1, "/api/v1/org/<int:org_id>/milestone")
    api.add_resource(GroupMilestoneEventV1, "/api/v1/group/<int:group_id>/milestone")
    api.add_resource(GiteeIssuesV1, "/api/v1/milestone/issues")
    api.add_resource(GiteeIssuesV2, "/api/v2/milestone/issues")
    api.add_resource(GiteeIssuesItemV2, "/api/v2/milestone/issues/<int:issue_id>")
    api.add_resource(GiteeIssuesTypeV2, "/api/v2/milestone/issue_types")
    api.add_resource(GiteeIssuesStateV2, "/api/v2/milestone/issue_states")
    api.add_resource(MilestonePreciseEvent, "/api/v1/milestone/preciseget")
    api.add_resource(
        GiteeIssuesStatisticsByMilestone,
        "/api/v2/milestone/<int:milestone_id>/issues-statistics",
    )
    api.add_resource(
        UpdateMilestoneIssueRateByField,
        "/api/v2/milestone/<int:milestone_id>/issue-rate",
    )
    api.add_resource(UpdateGiteeIssuesStatistics, "/api/v2/issues/statistics")
    api.add_resource(UpdateGiteeIssuesTypeState, "/api/v2/issues/type-state")
    api.add_resource(GiteeMilestoneEventV2, "/api/v2/gitee-milestone")
    api.add_resource(SyncMilestoneItemEventV2, "/api/v2/milestone/<int:milestone_id>/sync")
    api.add_resource(GenerateTestReportEvent, "/api/v2/milestone/<int:milestone_id>/generate-test-report")
    api.add_resource(TestReportFileEvent, "/api/v2/milestone/<int:milestone_id>/test-report-file")
    api.add_resource(TestReportEvent, "/api/v2/milestone/<int:milestone_id>/test-report")
