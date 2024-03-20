# Copyright 2024 Ethan-Zhang.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Original code modified by Ethan-Zhang <ethanzhang55@outlook.com>
#
# Copyright 2017 The casbin Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import jwt
from server.utils.aes_util import FileAES


class UnSupportedAuthType(Exception):
    status_code = 501

    def __init__(self, message, status_code=None, payload=None, errors=None):
        super().__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.errors = errors

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        if self.errors is not None:
            rv["errors"] = self.errors
        return rv


def authorization_decoder(config, auth_str: str):
    """
    Authorization token decoder based on type. This will decode the token and
    only return the owner
    Args:
        config: app.config object
        auth_str: Authorization string should be in "<type> <token>" format
    Returns:
        decoded owner from token
    """

    _type, _token = auth_str.split()

    if _type == "JWT":
        """return only the identity， depends on JWT 2.x"""
        try:
            decode_payload = FileAES().decrypt(_token.split('.')[1])
        except UnicodeDecodeError as e:
            raise UnSupportedAuthType(
                f"{_token} is not in valid encripted coding, cause error {e}"
            ) from e
        token = _token.replace(_token.split('.')[1], decode_payload)

        decoded_jwt = jwt.decode(
            token,
            config.get("TOKEN_SECRET_KEY"),
            algorithms=["HS512", "HS384", "HS256"],
        )
        return str(decoded_jwt.get("user_id", ""))
    else:
        raise UnSupportedAuthType("%s Authorization is not supported" % _type)
