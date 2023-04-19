import binascii
from datetime import datetime

from flask import g, current_app
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous.exc import SignatureExpired, BadSignature, BadData

from server import redis_client
from server.utils.aes_util import FileAES
from server.utils.redis_util import RedisKey
from pydantic import BaseModel

auth = HTTPTokenAuth(scheme="JWT")
serializer = None


def init(app):
    global serializer
    serializer = Serializer(
        app.config.get("TOKEN_SECRET_KEY"),
        expires_in=app.config.get("TOKEN_EXPIRES_TIME")
    )


def generate_token(gitee_id, gitee_login, ex=60 * 60 * 2):
    # 根据user_id去获取用户token,防止用户多次创建token值
    # 令牌策略为保证后来者登陆有效，旧令牌清除

    # 判断当前用户是否存在令牌
    if redis_client.exists(RedisKey.token(gitee_id)):
        pre_token = redis_client.get(RedisKey.token(gitee_id))
        # 删除旧令牌
        redis_client.delete(RedisKey.token(pre_token))
    # 根据gitee payload序列化生成新令牌
    token_data = dict(
        gitee_id=gitee_id, 
        gitee_login=gitee_login
    )
    _token = str(
        serializer.dumps(token_data), 
        encoding='utf-8'
    )
    # 令牌payload加密
    aes_payload = FileAES().encrypt(_token.split('.')[1])
    token = _token.replace(_token.split('.')[1], aes_payload)
    
    # 缓存新令牌，绑定到当前用户
    redis_client.set(RedisKey.token(gitee_id), token, ex)
    redis_client.hmset(
        RedisKey.token(token), 
        mapping={
            "gitee_id": gitee_id, 
            "gitee_login": gitee_login
        }, 
        ex=ex
    )
    
    return token


@auth.verify_token
def verify_token(token):
    data = None
    try:
        token_info = redis_client.hgetall(RedisKey.messenger_token(token))
        if not redis_client.exists(RedisKey.token(token)) or not token_info:
            return False

        # 令牌payload解密
        aes = FileAES()
        decode_payload = aes.decrypt(token.split('.')[1])
        _token = token.replace(token.split('.')[1], decode_payload)
        # 反序列化，还原为原始信息
        global serializer
        data = serializer.loads(_token)
    
    except SignatureExpired:
        if redis_client.exists(RedisKey.token(token)):
            # 用户签名过期登录不过期
            data = redis_client.hgetall(RedisKey.token(token))
            # 获取原令牌剩余登陆失效时间，并使新令牌继承
            rest_login_expires_time = redis_client.ttl(RedisKey.token(token))

            redis_client.delete(RedisKey.token(data.get('gitee_id')))
            redis_client.expire(RedisKey.token(token), 30)
            new_token = generate_token(
                data.get('gitee_id'), 
                data.get('gitee_login'),
                rest_login_expires_time,
            )
            token = new_token
        else:
            # 登陆已过期
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
        if (data and data.get("gitee_login") == redis_client.hget(RedisKey.user(data.get("gitee_id")), "gitee_login")) \
                or (data and data.get("time")):
            try:
                g.gitee_id = int(data.get("gitee_id"))
            except:
                g.gitee_id = data.get("gitee_id")
            g.gitee_login = data.get("gitee_login")
            g.token = token
            return True, data.get("gitee_id")
    return False


class RefreshTokenSchema(BaseModel):
    refresh_token: str


def generate_messenger_token(payload, ex=60 * 60 * 24):
    now_time = datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
    token_data = dict(
        gitee_id=payload.gitee_id,
        gitee_login=payload.gitee_login,
        time= now_time
    )
    _token = str(
        serializer.dumps(token_data),
        encoding='utf-8'
    )
    # 令牌payload加密
    aes_payload = FileAES().encrypt(_token.split('.')[1])
    token = _token.replace(_token.split('.')[1], aes_payload)

    redis_client.hmset(
        RedisKey.messenger_token(token),
        mapping={
            "gitee_id": payload.gitee_id,
            "gitee_login": payload.gitee_login,
            "time": now_time
        },
        ex=ex
    )

    return token
