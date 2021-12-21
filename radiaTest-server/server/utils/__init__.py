# -*- coding: utf-8 -*-
# @Author : lemon-higgins
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Date   : 2021-11-18 12:12:57


import json
import datetime


class DateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.date):
            return o.strftime("%Y-%m-%d")
        else:
            return super().default(o)
