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

class ScopeKey(object):
    @staticmethod
    def gitee_scope(oauth_scope):
        return f"{oauth_scope}".replace(',', "%20")

    @staticmethod
    def oneid_scope(oauth_scope):
        return f"{oauth_scope}".replace(",", "%20") + "&state=random"

    gitee = gitee_scope
    oneid = oneid_scope
