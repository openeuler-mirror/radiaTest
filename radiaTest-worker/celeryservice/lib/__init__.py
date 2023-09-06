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

from datetime import datetime


class TaskHandlerBase:
    def __init__(self, logger):
        self.start_time = datetime.now()
        self.running_time = 0
        self.logger = logger

    def next_period(self):
        _current_time = datetime.now()
        self.running_time = (_current_time - self.start_time).seconds*1000 + (_current_time - self.start_time).microseconds/1000


class AuthTaskHandler(TaskHandlerBase):
    def __init__(self, logger, auth):
        self.auth = auth
        super().__init__(logger)


        