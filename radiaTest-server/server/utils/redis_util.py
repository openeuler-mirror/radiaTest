import redis
from flask import _app_ctx_stack


class RedisClient(object):

    def __init__(self):
        self.redis_params = dict()

    def init_app(self, app=None):
        self.redis_params = dict(
            host=app.config.get("REDIS_HOST", "localhost"),
            port=app.config.get("REDIS_PORT", 6379),
            password=app.config.get("REDIS_SECRET", None),
            db=app.config.get("REDIS_DB", 0),
            decode_responses=True
        )

    def connect(self):
        pool = redis.ConnectionPool(
            **self.redis_params
        )
        return redis.StrictRedis(connection_pool=pool)

    @property
    def connection(self):
        ctx = _app_ctx_stack.top
        if ctx is not None:
            if not hasattr(ctx, 'redis_db'):
                ctx.redis_db = self.connect()
            return ctx.redis_db

    def set(self, name, value, ex=None):
        self.connection.set(name, value, ex=ex)

    def get(self, name):
        return self.connection.get(name)

    def exists(self, name):
        return self.connection.exists(name)

    def hget(self, name, key):
        return self.connection.hget(name, key)

    def hset(self, name, key, value, ex=None):
        self.connection.hset(name=name, key=key, value=value)
        if ex:
            self.connection.expire(name, time=ex)

    def expire(self, name, ex):
        self.connection.expire(name, time=ex)

    def hgetall(self, name):
        return self.connection.hgetall(name)

    def hmset(self, name, mapping, ex=None):
        new_mapping = {}
        for key, value in mapping.items():
            if type(value) not in [int, str, float, bytes]:
                value = str(value)
            new_mapping[key] = value
        self.connection.hmset(name=name, mapping=new_mapping)
        if ex:
            self.connection.expire(name, time=ex)

    def delete(self, name):
        self.connection.delete(name)

    def flush_db(self):
        if self.connection:
            self.connection.flushdb()
        else:
            temp = self.connect()
            temp.flushdb()
            temp.connection_pool.disconnect()

    def incr(self, name, amount=1):
        self.connection.incr(name, amount=amount)


class RedisKey(object):
    token = lambda gitee_id: f"token_{gitee_id}"
    refresh_token = lambda gitee_id: f"refresh_token_{gitee_id}"
    user = lambda gitee_id: f"user_{gitee_id}"
    gitee_user = lambda gitee_id: f"gitee_user_{gitee_id}"
    organization = lambda organization_id: f"organization_{organization_id}"
    login_org = lambda gitee_id: f"{gitee_id}_login_org"
