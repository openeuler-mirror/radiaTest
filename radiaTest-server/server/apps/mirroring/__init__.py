from flask_restful import Api

from .routes import IMirroringEvent
from .routes import PreciseGetIMirroring
from .routes import QMirroringEvent
from .routes import PreciseGetQMirroring
from .routes import RepoEvent
from .routes import IMirroringItemEvent
from .routes import QMirroringItemEvent


def init_api(api: Api):
    api.add_resource(IMirroringEvent, "/api/v1/imirroring")
    api.add_resource(PreciseGetIMirroring, "/api/v1/imirroring/preciseget")
    api.add_resource(QMirroringEvent, "/api/v1/qmirroring")
    api.add_resource(PreciseGetQMirroring, "/api/v1/qmirroring/preciseget")
    api.add_resource(RepoEvent, "/api/v1/repo")
    api.add_resource(IMirroringItemEvent, "/api/v1/imirroring/<int:i_mirroring_id>")
    api.add_resource(QMirroringItemEvent, "/api/v1/qmirroring/<int:q_mirroring_id>")