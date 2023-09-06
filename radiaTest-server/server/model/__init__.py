# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
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

from server.model.base import BaseModel, PermissionBaseModel
from server.model.product import Product
from server.model.milestone import Milestone, TestReport
from server.model.mirroring import IMirroring, QMirroring, Repo
from server.model.pmachine import Pmachine, MachineGroup
from server.model.vmachine import Vmachine, Vdisk, Vnic
from server.model.testcase import Suite, Case, SuiteDocument, Commit
from server.model.template import Template
from server.model.job import Job, Analyzed, Logs
from server.model.framework import Framework, GitRepo
from server.model.permission import Role, Scope, ReUserRole, ReScopeRole
from server.model.celerytask import CeleryTask
from server.model.user import User
from server.model.group import Group, ReUserGroup
from server.model.organization import Organization, ReUserOrganization
from server.model.message import Message, MsgLevel, MsgType
from server.model.manualjob import ManualJob, ManualJobStep
from server.model.baselinetemplate import BaselineTemplate, BaseNode
from server.model.strategy import Strategy, StrategyCommit, StrategyTemplate
