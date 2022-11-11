from flask_restful import Api

from .routes import RequirementOrgEvent
from .routes import RequirementEvent
from .routes import RequirementItemEvent
from .routes import RequirementItemAcceptEvent
from .routes import RequirementItemGroupAcceptEvent
from .routes import RequirementItemRejectEvent
from .routes import RequirementItemValidateEvent
from .routes import RequirementItemAttachmentEvent
from .routes import RequirementItemAttachmentDownload
from .routes import RequirementItemAttachmentLock
from .routes import RequirementItemProgressEvent
from .routes import RequirementItemRewardEvent
from .routes import RequirementItemAttributorEvent
from .routes import RequirementItemPackagesEvent
from .routes import RequirementPackageItemValidateEvent
from .routes import RequirementPackageItemTaskEvent


def init_api(api: Api):
    api.add_resource(RequirementOrgEvent, "/api/v1/requirement/org/<int:org_id>")
    api.add_resource(RequirementEvent, "/api/v1/requirement")
    api.add_resource(RequirementItemEvent, "/api/v1/requirement/<int:requirement_id>")
    api.add_resource(
        RequirementItemAcceptEvent, 
        "/api/v1/requirement/<int:requirement_id>/accept"
    )
    api.add_resource(
        RequirementItemGroupAcceptEvent, 
        "/api/v1/requirement/<int:requirement_id>/group/<int:group_id>/accept"
    )
    api.add_resource(RequirementItemRejectEvent, "/api/v1/requirement/<int:requirement_id>/reject")
    api.add_resource(RequirementItemValidateEvent, "/api/v1/requirement/<int:requirement_id>/validate")
    api.add_resource(RequirementItemAttachmentEvent, "/api/v1/requirement/<int:requirement_id>/attachment")
    api.add_resource(RequirementItemAttachmentDownload, "/api/v1/requirement/<int:requirement_id>/attachment/download")
    api.add_resource(RequirementItemAttachmentLock, "/api/v1/requirement/<int:requirement_id>/attachment/lock")
    api.add_resource(
        RequirementItemProgressEvent, 
        "/api/v1/requirement/<int:requirement_id>/progress",
        "/api/v1/requirement/<int:requirement_id>/progress/<int:progress_id>"
    )
    api.add_resource(RequirementItemRewardEvent, "/api/v1/requirement/<int:requirement_id>/reward")
    api.add_resource(RequirementItemAttributorEvent, "/api/v1/requirement/<int:requirement_id>/attributor")
    api.add_resource(RequirementItemPackagesEvent, "/api/v1/requirement/<int:requirement_id>/package")
    api.add_resource(
        RequirementPackageItemValidateEvent, 
        "/api/v1/requirement/<int:requirement_id>/package/<package_id>/validate",
        "/api/v1/requirement/<int:requirement_id>/package/<package_id>/set-validator/<int:user_id>"
    )
    api.add_resource(
        RequirementPackageItemTaskEvent,
        "/api/v1/requirement/<int:requirement_id>/package/<package_id>/task"
    )