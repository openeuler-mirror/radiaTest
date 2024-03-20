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

class ProfileMap(object):
    @staticmethod
    def gitee_user(oauth_user):
        return {
            "user_id": "gitee_" + str(oauth_user.get("id")),
            "user_login": oauth_user.get("login"),
            "user_name": oauth_user.get("name"),
            "avatar_url": oauth_user.get("avatar_url")
        }

    @staticmethod
    def oneid_user(oauth_user):
        return {
            "user_id": "oneid_" + str(oauth_user.get("sub")),
            "user_login": oauth_user.get("username"),
            "user_name": oauth_user.get("username"),
            "avatar_url": oauth_user.get("picture")
        }

    gitee = gitee_user
    oneid = oneid_user
