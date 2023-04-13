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
    
    def keys(self, pattern):
        return self.connection.keys(pattern)

    def ttl(self, name):
        return self.connection.ttl(name)


class RedisKey(object):
    token = lambda user_id: f"token_{user_id}"
    refresh_token = lambda user_id: f"refresh_token_{user_id}"
    user = lambda user_id: f"user_{user_id}"
    # TODO 请确认gitee_user这个key是否还有用
    gitee_user = lambda user_id: f"gitee_user_{user_id}"
    organization = lambda organization_id: f"organization_{organization_id}"
    login_org = lambda user_id: f"{user_id}_login_org"
    issue_types = lambda enterprise_id: f"issue_types_{enterprise_id}"
    issue_states = lambda enterprise_id: f"issue_states_{enterprise_id}"
    oauth_user = lambda user_id: f"{user_id}"
    projects = lambda enterprise_id: f"projects_{enterprise_id}"
