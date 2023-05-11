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

from flask import Flask
from flask_restful import Api

from .user.routes import oauth
from . import (
    user,
    administrator,
    group,
    organization,
    message,
    task,
    job,
    milestone,
    mirroring,
    pmachine,
    product,
    template,
    testcase,
    vmachine,
    external,
    framework,
    permission,
    celerytask,
    qualityboard,
    requirement,
    manualjob,
    baseline_template,
    issue,
    strategy,
    git_repo,
)


def init_api(app: Flask):
    app.register_blueprint(oauth)       # 注册登陆鉴权相关接口蓝图
    api = Api(app)
    administrator.init_api(api)
    user.init_api(api)
    group.init_api(api)
    organization.init_api(api)
    message.init_api(api)
    task.init_api(api)
    job.init_api(api)
    milestone.init_api(api)
    issue.init_api(api)
    mirroring.init_api(api)
    pmachine.init_api(api)
    product.init_api(api)
    template.init_api(api)
    testcase.init_api(api)
    vmachine.init_api(api)
    external.init_api(api)
    framework.init_api(api)
    git_repo.init_api(api)
    permission.init_api(api)
    celerytask.init_api(api)
    qualityboard.init_api(api)
    requirement.init_api(api)
    manualjob.init_api(api)  # 手工测试任务(ManualJob)相关接口
    baseline_template.init_api(api)
    strategy.init_api(api)
