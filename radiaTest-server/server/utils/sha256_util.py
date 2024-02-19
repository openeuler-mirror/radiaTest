# copyright (c) [2024] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
import uuid
import hmac
import hashlib
import base64


class Hmacsha256:
    """
    Hmacsha256 provide a set of encryption methods.

    Using it can ensure the security of information.
    """
    def __init__(self, key=None):
        if not key:
            self.key = str(uuid.uuid4())
        else:
            self.key = str(key)

    def encrypt(self, string_to_sign):
        """Hmacsha256 encryption method.
        :param string_to_sign： string, Encrypted Content
        :return:
          - string, The results of information encryption
        """
        key = self.key.encode('utf-8')
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(key, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign


