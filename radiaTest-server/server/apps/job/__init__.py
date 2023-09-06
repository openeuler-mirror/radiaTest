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

from flask_restful import Api

from .routes import JobItemChildren, LogEvent
from .routes import JobItemEvent
from .routes import JobEvent
from .routes import AnalyzedEvent
from .routes import AnalyzedItemEvent
from .routes import AnalyzedRecords
from .routes import AnalyzedLogs
from .routes import RunSuiteEvent
from .routes import RunTemplateEvent
from .routes import PreciseAnalyzedEvent


def init_api(api: Api):
    api.add_resource(JobEvent, "/api/v1/ws/<string:workspace>/job")
    api.add_resource(JobItemEvent, "/api/v1/job/<int:job_id>")
    api.add_resource(JobItemChildren, "/api/v1/job/<int:job_id>/children")
    api.add_resource(AnalyzedEvent, "/api/v1/analyzed")
    api.add_resource(AnalyzedItemEvent, "/api/v1/analyzed/<int:analyzed_id>")
    api.add_resource(AnalyzedRecords, "/api/v1/analyzed/records")
    api.add_resource(AnalyzedLogs, "/api/v1/analyzed/<int:analyzed_id>/logs")
    api.add_resource(RunSuiteEvent, "/api/v1/job/suite")
    api.add_resource(RunTemplateEvent, "/api/v1/job/template")
    api.add_resource(PreciseAnalyzedEvent, "/api/v1/analyzed/preciseget")
    api.add_resource(LogEvent, "/api/v1/log")
