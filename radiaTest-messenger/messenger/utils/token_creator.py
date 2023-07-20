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

import os
import abc
import re


class TokenCreator:
    def __init__(self):
        self.file_path = os.path.abspath(__file__)

    @abc.abstractmethod
    def start(self):
        pass


class VncTokenCreator(TokenCreator):
    def __init__(self, ip, vnc_port):
        super().__init__()
        self.ip = ip
        if vnc_port is not None:
            self.vnc_port = str(int(vnc_port) + 5900)
        
        self.token = ip.replace(".", "-") + "-" + self.vnc_port
        self.target_path = (
            re.match(".*/messenger/", self.file_path).group() + "config/vnc_tokens/"
        )

    def start(self):
        if os.path.isdir(self.target_path) and self.vnc_port:
            with open(self.target_path + self.token, "w") as f:
                f.write(self.token + ": " + self.ip + ":" + self.vnc_port)
            return self.token
        else:
            return ""
    
    def end(self):
        if os.path.isfile(self.target_path + self.token):
            os.remove(self.target_path + self.token)
