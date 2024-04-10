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

from .routes import (
    PreciseProductEvent,
    ProductEvent,
    ProductEventItem,
    UpdateProductIssueRate,
    ProductTestReportEvent,
)


def init_api(api: Api):
    api.add_resource(
        ProductEvent, 
        "/api/v1/product", 
        "/api/v1/ws/<string:workspace>/product"
    )
    api.add_resource(
        PreciseProductEvent,
        "/api/v1/product/preciseget",
        "/api/v1/ws/<string:workspace>/product/preciseget"
    )
    api.add_resource(ProductEventItem, "/api/v1/product/<int:product_id>")
    api.add_resource(
        UpdateProductIssueRate,
        "/api/v1/product/<int:product_id>/issue-rate"
    )
    api.add_resource(ProductTestReportEvent, "/api/v1/product/<int:product_id>/test-report")
