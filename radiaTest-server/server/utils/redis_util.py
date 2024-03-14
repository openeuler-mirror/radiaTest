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
import ssl

import redis
from flask import _app_ctx_stack


class RedisClient(object):

    def __init__(self):
        self.redis_params = dict()
        self.ssl_context = None

    def init_app(self, app=None):
        self.ssl_context = ssl.create_default_context(cafile=app.config.get("REDIS_CA_CERTS", None))

        self.redis_params = dict(
            host=app.config.get("REDIS_HOST", "localhost"),
            port=app.config.get("REDIS_PORT", 6379),
            password=app.config.get("REDIS_SECRET", None),
            db=app.config.get("REDIS_DB", 0),
            decode_responses=True
        )

    def connect(self):
        pool = redis.ConnectionPool(
            ssl_context=self.ssl_context,
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

    def hdel(self, name, key):
        return self.connection.hdel(name, key)

    def flush_db(self):
        if self.connection:
            self.connection.flushdb()
        else:
            temp = self.connect()
            temp.flushdb()
            temp.connection_pool.disconnect()

    def incr(self, name, amount=1):
        self.connection.incr(name, amount=amount)
    
    def keys(self, pattern):
        return self.connection.keys(pattern)

    def ttl(self, name):
        return self.connection.ttl(name)

    def zrangebyscore(self, name, min_value, max_value):
        return self.connection.zrangebyscore(name, min_value, max_value)

    def zadd(self, name, mapping):
        return self.connection.zadd(name, mapping)

    def zrem(self, name, member):
        return self.connection.zrem(name, member)

    def zcard(self, name):
        return self.connection.zcard(name)


def format_str_wrapper(str_prefix=None, str_suffix=None):
    def get_str_func(value):
        if str_prefix:
            data = f"{str_prefix}{value}"
        else:
            data = value
        if str_suffix:
            data = f"{data}{str_suffix}"
        return data
    return get_str_func


class RedisKey(object):
    token = format_str_wrapper(str_prefix="token_")
    refresh_token = format_str_wrapper(str_prefix="refresh_token_")
    user = format_str_wrapper(str_prefix="user_")
    organization = format_str_wrapper(str_prefix="organization_")
    login_org = format_str_wrapper(str_suffix="_login_org")
    issue_types = format_str_wrapper(str_prefix="issue_types_")
    issue_states = format_str_wrapper(str_prefix="issue_states_")
    oauth_user = format_str_wrapper()
    projects = format_str_wrapper(str_prefix="projects_")
    messenger_token = format_str_wrapper(str_prefix="messenger_token_")
    daily_build = format_str_wrapper(str_prefix="daily_build_infos_")
    message_lock = format_str_wrapper(str_prefix="message_lock_")
