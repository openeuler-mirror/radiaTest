from flask_restful import Api

from messenger.apps.at.routes import AtEvent


def init_api(api: Api):
    api.add_resource(AtEvent, "/api/v1/openeuler/at")
