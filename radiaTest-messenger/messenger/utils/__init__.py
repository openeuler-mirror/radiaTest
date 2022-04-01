import json
import datetime


class DateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(0, datetime.date):
            return o.strftime("%Y-%m-%d")
        else:
            return super().default(o)
