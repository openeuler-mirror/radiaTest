# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : MDS_ZHR
# email : 331884949@qq.com
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 基线模板(Baseline_template)相关接口的init层

from flask_restful import Api

from server.apps.baseline_template.routes import (
    BaselineTemplateEvent,
    BaselineTemplateItemEvent,
    BaselineTemplateInheritEvent,
    BaseNodeEvent,
    BaseNodeItemEvent,
    BaselineTemplateCleanItemEvent,
    BaselineTemplateApplyItemEvent,
)


def init_api(api: Api):
    api.add_resource(
        BaselineTemplateEvent, 
        "/api/v1/baseline-template", 
        "/api/v1/ws/<string:workspace>/baseline-template",
        methods=["POST", "GET"]
    )
    api.add_resource(
        BaselineTemplateItemEvent, 
        "/api/v1/baseline-template/<int:baseline_template_id>", 
        methods=["GET", "PUT", "DELETE"]
    )
    api.add_resource(
        BaselineTemplateInheritEvent, 
        "/api/v1/baseline-template/<int:baseline_template_id>/inherit/<int:inherit_baseline_template_id>",
        methods=["POST"]
    )
    api.add_resource(
        BaselineTemplateCleanItemEvent, 
        "/api/v1/baseline-template/<int:baseline_template_id>/clean",
        methods=["DELETE"]
    )   
    api.add_resource(
        BaseNodeEvent, 
        "/api/v1/baseline-template/<int:baseline_template_id>/base-node",
        methods=["POST", "GET"]
    )
    api.add_resource(
        BaseNodeItemEvent, 
        "/api/v1/base-node/<int:base_node_id>",
        methods=["GET", "PUT", "DELETE"]
    )
    api.add_resource(
        BaselineTemplateApplyItemEvent, 
        "/api/v1/case-node/<int:case_node_id>/apply/baseline-template/<int:baseline_template_id>",
        methods=["POST"]
    )
