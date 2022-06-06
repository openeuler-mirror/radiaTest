from flask import Flask
from flask_restful import Api
from . import job
from . import pmachine
from . import vmachine
from . import heartbeat
from . import certifi


def init_api(app: Flask):
    api = Api(app)
    job.init_api(api)
    pmachine.init_api(api)
    vmachine.init_api(api)
    heartbeat.init_api(api)
    certifi.init_api(api)
