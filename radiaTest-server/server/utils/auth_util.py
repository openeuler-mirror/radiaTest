import time
from flask import g
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
    serializer = Serializer(app.config.get("TOKEN_SECRET_KEY"),
                            expires_in=app.config.get("TOKEN_EXPIRES_TIME"))


def generate_token(gitee_id, gitee_login, ex=60 * 60 * 2):
    # 根据user_id去获取用户token,防止用户多次创建token值
    if redis_client.exists(RedisKey.token(gitee_id)):
        return redis_client.get(RedisKey.token(gitee_id))
    token_data = dict(gitee_id=gitee_id, gitee_login=gitee_login)
    _token = str(serializer.dumps(token_data), encoding='utf-8')
    aes_payload = FileAES().encrypt(_token.split('.')[1])
    token = _token.replace(_token.split('.')[1], aes_payload)
    # 缓存token信息
    redis_client.set(RedisKey.token(gitee_id), token, ex)
    redis_client.hmset(RedisKey.token(token), mapping={"gitee_id": gitee_id, "gitee_login": gitee_login}, ex=ex)
    return token


@auth.verify_token
def verify_token(token):
    data = None
    try:
        aes = FileAES()
        decode_payload = aes.decrypt(token.split('.')[1])
        _token = token.replace(token.split('.')[1], decode_payload)

        global serializer
        data = serializer.loads(_token)
    except SignatureExpired:
        # 用户签名过期登录不过期
        if redis_client.exists(RedisKey.token(token)):
            data = redis_client.hgetall(RedisKey.token(token))
            redis_client.delete(RedisKey.token(data.get('gitee_id')))
            redis_client.expire(RedisKey.token(token), 30)
            new_token = generate_token(data.get('gitee_id'), data.get('gitee_login'))
            token = new_token
        else:
            return False, None
    except BadSignature:
        return False, None
    except BadData:
        return False, None
    except Exception:
        return False, None
    finally:
        if data and data.get("gitee_login") == redis_client.hget(RedisKey.user(data.get("gitee_id")), "gitee_login"):
            try:
                g.gitee_id = int(data.get("gitee_id"))
            except:
                g.gitee_id = data.get("gitee_id")
            g.gitee_login = data.get("gitee_login")
            g.token = token
            return True, data.get("gitee_id")
    return False, None


class RefreshTokenSchema(BaseModel):
    refresh_token: str
