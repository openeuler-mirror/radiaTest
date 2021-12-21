from flask_restful import Api

from .routes import IMirroringEvent
from .routes import PreciseGetIMirroring
from .routes import QMirroringEvent
from .routes import PreciseGetQMirroring
from .routes import RepoEvent


def init_api(api: Api):
    api.add_resource(IMirroringEvent, "/api/v1/imirroring")
    api.add_resource(PreciseGetIMirroring, "/api/v1/imirroring/preciseget")
    api.add_resource(QMirroringEvent, "/api/v1/qmirroring")
    api.add_resource(PreciseGetQMirroring, "/api/v1/qmirroring/preciseget")
    api.add_resource(RepoEvent, "/api/v1/repo")