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

import binascii
from functools import wraps

from flask import g, current_app, request
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous.exc import SignatureExpired, BadSignature, BadData

from server import redis_client
from server.utils.aes_util import FileAES
from server.utils.redis_util import RedisKey


class RadiaTestTokenAuth(HTTPTokenAuth):
    # 仅检查token，不做拦截
    def login_check(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _auth = self.get_auth()
            self.authenticate(_auth, self.get_auth_password(_auth))
            return func(*args, **kwargs)
        return wrapper


auth = RadiaTestTokenAuth(scheme="JWT")
serializer = None


def init(app):
    global serializer
    serializer = Serializer(
        app.config.get("TOKEN_SECRET_KEY"),
        expires_in=app.config.get("TOKEN_EXPIRES_TIME")
    )


def generate_token(user_id, user_login, ex=60 * 60 * 2):
    # 根据user_id去获取用户token,防止用户多次创建token值
    # 令牌策略为保证后来者登录有效，旧令牌清除

    # 判断当前用户是否存在令牌
    if redis_client.exists(RedisKey.token(user_id)):
        pre_token = redis_client.get(RedisKey.token(user_id))
        # 删除旧令牌
        redis_client.delete(RedisKey.token(pre_token))
    # 根据payload序列化生成新令牌
    token_data = dict(
        user_id=user_id,
        user_login=user_login
    )
    _token = str(
        serializer.dumps(token_data), 
        encoding='utf-8'
    )
    # 令牌payload加密
    aes_payload, tag, nonce = FileAES().encrypt(_token.split('.')[1])
    token = _token.replace(_token.split('.')[1], aes_payload)
    
    # 缓存新令牌，绑定到当前用户
    redis_client.set(RedisKey.token(user_id), token, ex)
    redis_client.hmset(
        RedisKey.token(token), 
        mapping={
            "user_id": user_id,
            "user_login": user_login,
            "tag": tag,
            "nonce": nonce
        }, 
        ex=ex
    )
    
    return token


@auth.verify_token
def verify_token(token):
    try:
        payload = request.headers.get("Authorization")
        if not payload:
            return False
        token = payload.split()[1]
        if not redis_client.exists(RedisKey.token(token)):
            return False

        tag = redis_client.hget(RedisKey.token(token), "tag")
        nonce = redis_client.hget(RedisKey.token(token), "nonce")
        # 令牌payload解密
        aes = FileAES()
        decode_payload = aes.decrypt(token.split('.')[1], tag, nonce)
        _token = token.replace(token.split('.')[1], decode_payload)
        # 反序列化，还原为原始信息
        global serializer
        data = serializer.loads(_token)
    except SignatureExpired:
        if redis_client.exists(RedisKey.token(token)):
            # 用户签名过期登录不过期
            data = redis_client.hgetall(RedisKey.token(token))
            # 获取原令牌剩余登录失效时间，并使新令牌继承
            rest_login_expires_time = redis_client.ttl(RedisKey.token(token))

            redis_client.delete(RedisKey.token(data.get('user_id')))
            redis_client.expire(RedisKey.token(token), 30)
            new_token = generate_token(
                data.get('user_id'),
                data.get('user_login'),
                rest_login_expires_time,
            )
            token = new_token
        else:
            # 登录已过期
            return False
    
    except BadSignature:
        current_app.logger.info(f"Illegal signature in JWT {token} attempt to do request")
        return False
    except BadData:
        current_app.logger.info(f"Illegal token in JWT {token} attempt to do request")
        return False
    except (binascii.Error, IndexError):
        current_app.logger.info(f"Uncrypted/Unknown token {token} attempt to do request")
        return False

    if data and data.get("user_login") == redis_client.hget(RedisKey.oauth_user(data.get("user_id")), "user_login"):
        try:
            g.user_id = int(data.get("user_id"))
        except ValueError as e:
            g.user_id = data.get("user_id")
        g.user_login = data.get("user_login")
        g.token = token
        return True, data.get("user_id")
    return False
