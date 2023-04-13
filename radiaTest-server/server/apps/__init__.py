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
)


def init_api(app: Flask):
    app.register_blueprint(oauth)       # 注册登陆鉴权相关接口蓝图
    api = Api(app)
    administrator.init_api(api)         # 注册管理员相关接口URL
    user.init_api(api)                  # 注册用户相关接口URL
    group.init_api(api)                 # 注册用户组相关接口URL
    organization.init_api(api)          # 注册组织相关接口URL
    message.init_api(api)               # 注册消息通知相关接口URL
    task.init_api(api)                  # 注册任务相关接口URL
    job.init_api(api)                   # 注册测试执行相关接口URL
    milestone.init_api(api)             # 注册里程碑相关接口URL
    issue.init_api(api)                 # 注册问题单相关接口URL
    mirroring.init_api(api)             # 注册镜像信息相关接口URL
    pmachine.init_api(api)              # 注册物理机相关接口URL
    product.init_api(api)               # 注册产品版本相关接口URL
    template.init_api(api)              # 注册测试模板相关接口URL
    testcase.init_api(api)              # 注册测试用例相关接口URL
    vmachine.init_api(api)              # 注册虚拟机相关接口URL
    external.init_api(api)              # 注册外部接口URL
    framework.init_api(api)             # 注册测试框架相关接口URL
    permission.init_api(api)            # 注册权限相关接口URL
    celerytask.init_api(api)            # 注册内部并发框架调用相关接口URL
    qualityboard.init_api(api)          # 注册质量看板相关接口URL
    requirement.init_api(api)           # 注册需求中心相关接口URL
    manualjob.init_api(api)             # 注册手工用例执行相关接口URL
    baseline_template.init_api(api)     # 注册基线相关接口URL
    strategy.init_api(api)              # 注册测试策略相关接口URL
