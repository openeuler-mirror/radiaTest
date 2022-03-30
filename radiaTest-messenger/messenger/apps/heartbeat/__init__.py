from flask_restful import Api

from .routes import HeartbeatEvent


def init_api(api: Api):
    api.add_resource(HeartbeatEvent, "/api/v1/heartbeat")
