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
# Date : 2023/3/20 14:00:00
# License : Mulan PSL v2
#####################################
# 测试设计(Strategy)相关接口的init层

from flask_restful import Api

from server.apps.strategy.routes import (
    FeatureSetEvent,
    FeatureSetItemEvent,
    ProductFeatureEvent,
    StrategyImportEvent,
    StrategyExportEvent, 
    StrategyCommitEvent,
    StrategyItemEvent,
    StrategyRelateEvent,
    StrategySubmmitEvent,
    StrategyCommitReductEvent,
    StrategyTemplateEvent,
    StrategyTemplateItemEvent,
    StrategyTemplateApplyEvent,
    ProductInheritFeatureEvent,
    StrategyCommitStageEvent,
    StrategyCommitItemEvent,

)


def init_api(api: Api):
    api.add_resource(
        FeatureSetEvent,
        "/api/v1/feature", 
        methods=["Post", "get"]
    ) 
    api.add_resource(
        FeatureSetItemEvent,
        "/api/v1/feature/<int:feature_id>", 
        methods=["GET", "Put", "Delete"]
    )
    api.add_resource(
        ProductInheritFeatureEvent, 
        "/api/v1/product/<int:product_id>/inherit-feature", 
        methods=["POST"]
    )
    api.add_resource(
        ProductFeatureEvent,
        "/api/v1/product/<int:product_id>/feature", 
        methods=["GET"]
    )
    api.add_resource(
        StrategyCommitEvent,
        "/api/v1/product-feature/<int:product_feature_id>/strategy", 
        methods=["GET", "Post"]
    )
    api.add_resource(
        StrategyItemEvent,
        "/api/v1/strategy/<int:strategy_id>",
        methods=["GET", "Delete"]
    )
    api.add_resource(
        StrategyRelateEvent,
        "/api/v1/product/<int:product_id>/relate",
        methods=["Post"]
    )
    api.add_resource(
        StrategySubmmitEvent,
        "/api/v1/strategy/<int:strategy_id>/submmit",
        methods=["Post"]
    )
    api.add_resource(
        StrategyCommitItemEvent,
        "/api/v1/product-feature/<int:product_feature_id>/strategy-commit",
        methods=["Get"]
    )
    api.add_resource(
        StrategyCommitStageEvent,
        "/api/v1/strategy/<int:strategy_id>/strategy-commit/stage",
        methods=["Post"]
    )
    api.add_resource(
        StrategyCommitReductEvent,
        "/api/v1/strategy/<int:strategy_id>/reduct",
        methods=["Delete"]
    )
    api.add_resource(
        StrategyTemplateEvent,
        "/api/v1/strategy-template",
        methods=["GET", "Post"]
    )
    api.add_resource(
        StrategyTemplateItemEvent,
        "/api/v1/strategy-template/<int:strategy_template_id>",
        methods=["GET", "Put", "Delete"]
    )
    api.add_resource(
        StrategyTemplateApplyEvent,
        "/api/v1/strategy-template/<int:strategy_template_id>/apply/product-feature/<int:product_feature_id>",
        methods=["Post"]
    )
    