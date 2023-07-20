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

import base64
from Crypto.Cipher import AES
from flask import current_app


class FileAES:
    def __init__(self):
        self.key = current_app.config.get('AES_KEY').encode('utf-8')
        self.mode = AES.MODE_ECB

    def encrypt(self, text):
        """加密函数"""
        file_aes = AES.new(self.key, self.mode)
        text = text.encode('utf-8')
        while len(text) % 16 != 0:
            text += b'\x00'
        en_text = file_aes.encrypt(text)
        return str(base64.b64encode(en_text), encoding='utf-8')

    def decrypt(self, text):
        """解密函数"""
        file_aes = AES.new(self.key, self.mode)
        text = bytes(text, encoding='utf-8')
        text = base64.b64decode(text)
        de_text = file_aes.decrypt(text)
        return_text = str(de_text, encoding='utf-8').strip(b'\x00'.decode())
        return return_text
