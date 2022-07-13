from flask import Flask
from flask_restful import Api
from .user.routes import gitee
from . import user
from . import administrator
from . import group
from . import organization
from . import message
from . import task
from . import job
from . import milestone
from . import mirroring
from . import pmachine
from . import product
from . import template
from . import testcase
from . import vmachine
from . import external
from . import framework
from . import permission
from . import celerytask
from . import qualityboard


def init_api(app: Flask):
    app.register_blueprint(gitee)
    api = Api(app)
    administrator.init_api(api)
    user.init_api(api)
    group.init_api(api)
    organization.init_api(api)
    message.init_api(api)
    task.init_api(api)
    job.init_api(api)
    milestone.init_api(api)
    mirroring.init_api(api)
    pmachine.init_api(api)
    product.init_api(api)
    template.init_api(api)
    testcase.init_api(api)
    vmachine.init_api(api)
    external.init_api(api)
    framework.init_api(api)
    permission.init_api(api)
    celerytask.init_api(api)
    qualityboard.init_api(api)
