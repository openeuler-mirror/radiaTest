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

from server.model import (
    Product,
    Milestone,
    Framework,
    GitRepo,
    BaselineTemplate,
    BaseNode,
    SuiteDocument
)


class TableAdapter:
    product = Product
    milestone = Milestone
    framework = Framework
    git_repo = GitRepo
    suite_document = SuiteDocument
    baseline_template = BaselineTemplate
    base_node = BaseNode
