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
import pytz
from datetime import datetime
from functools import wraps

from flask import g, current_app
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous.exc import SignatureExpired, BadSignature, BadData

from server import redis_client
from server.utils.aes_util import FileAES
from server.utils.redis_util import RedisKey
from pydantic import BaseModel


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
messenger_serializer = None


def init(app):
    global serializer
    serializer = Serializer(
        app.config.get("TOKEN_SECRET_KEY"),
        expires_in=app.config.get("TOKEN_EXPIRES_TIME")
    )

    global messenger_serializer
    messenger_serializer = Serializer(
        app.config.get("TOKEN_SECRET_KEY"),
        expires_in=app.config.get("MESSENGER_TOKEN_EXPIRES_TIME")
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
    aes_payload = FileAES().encrypt(_token.split('.')[1])
    token = _token.replace(_token.split('.')[1], aes_payload)
    
    # 缓存新令牌，绑定到当前用户
    redis_client.set(RedisKey.token(user_id), token, ex)
    redis_client.hmset(
        RedisKey.token(token), 
        mapping={
            "user_id": user_id,
            "user_login": user_login
        }, 
        ex=ex
    )
    
    return token


@auth.verify_token
def verify_token(token):
    data = None
    try:
        token_info = redis_client.hgetall(RedisKey.messenger_token(token))
        if not redis_client.exists(RedisKey.token(token)) and not token_info:
            return False

        # 令牌payload解密
        aes = FileAES()
        decode_payload = aes.decrypt(token.split('.')[1])
        _token = token.replace(token.split('.')[1], decode_payload)
        # 反序列化，还原为原始信息
        if not token_info:
            global serializer
            data = serializer.loads(_token)
        else:
            global messenger_serializer
            data = messenger_serializer.loads(_token)
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
    finally:
        if (data and data.get("user_login") == redis_client.hget(RedisKey.oauth_user(data.get("user_id")), "user_login")) \
                or (data and data.get("time")):
            try:
                g.user_id = int(data.get("user_id"))
            except:
                g.user_id = data.get("user_id")
            g.user_login = data.get("user_login")
            g.token = token
            return True, data.get("user_id")
    return False


class RefreshTokenSchema(BaseModel):
    refresh_token: str


def generate_messenger_token(payload, ex=60 * 60 * 24):
    now_time = datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
    token_data = dict(
        user_id=payload.user_id,
        user_login=payload.user_login,
        time= now_time
    )
    _token = str(
        messenger_serializer.dumps(token_data),
        encoding='utf-8'
    )
    # 令牌payload加密
    aes_payload = FileAES().encrypt(_token.split('.')[1])
    token = _token.replace(_token.split('.')[1], aes_payload)

    redis_client.hmset(
        RedisKey.messenger_token(token),
        mapping={
            "user_id": payload.user_id,
            "user_login": payload.user_login,
            "time": now_time
        },
        ex=ex
    )

    return token
