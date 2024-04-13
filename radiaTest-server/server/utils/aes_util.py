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

from Crypto.Cipher import AES
import base64
from flask import current_app


class FileAES:
    def __init__(self):
        aes_key = str(current_app.config.get("AES_KEY"))
        self.key = base64.b64decode(aes_key.encode("utf-8"))
        self.mode = AES.MODE_GCM

    def encrypt(self, text):
        file_aes = AES.new(self.key, self.mode)
        text = text.encode('utf-8')
        en_text, tag = file_aes.encrypt_and_digest(text)
        nonce = file_aes.nonce
        encrypted_text = base64.b64encode(en_text).decode('utf-8')
        tag = base64.b64encode(tag).decode('utf-8')
        nonce = base64.b64encode(nonce).decode('utf-8')
        return encrypted_text, tag, nonce

    def decrypt(self, encrypted_text, tag, nonce):
        file_aes = AES.new(self.key, self.mode, nonce=base64.b64decode(nonce.encode('utf-8')))
        tag = base64.b64decode(tag.encode('utf-8'))
        encrypted_text = base64.b64decode(encrypted_text.encode('utf-8'))
        decrypted_text = file_aes.decrypt_and_verify(encrypted_text, tag)
        return decrypted_text.decode('utf-8')
