# -*- coding:utf-8 -*-
import requests
import json

class RestApi():
    def __init__(self, api_url):
        self.url = "https://radiatest.openeuler.org/" + api_url
        self.session = requests.session()
        self.header = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
            "Authorization": "JWT eyJhbGciOiJIUzUxMiIsImlhdCI6MTY1MzU1MTc0NiwiZXhwIjoxNjUzNTUzNTQ2fQ.eyJnaXRlZV9pZCI6IjczNjE4MTYiLCJnaXRlZV9sb2dpbiI6ImdhX2JlbmdfY3VpIn0.Wuk1dPf7aY6A8-CoHLZidVp4mLsCuaGQfuw_WePKnoAqeRHpvloJBzddQJStiGcbQlUnDlCJU1Xq1rm1m1faAw"
        }
        
        

    def get(self, **kwargs):
        return self.session.get(self.url, headers=self.header, **kwargs)

    def post(self, data=None, **kwargs):
        return self.session.post(self.url, data=json.dumps(data), headers=self.header, **kwargs)
    
    #当提交的是form表单形式的数据时，data数据不需要使用json.dumps()将字典类型转换为字符串类型
    def post2(self, data=None, **kwargs):
        return self.session.post(self.url, data=data, headers=self.header, **kwargs)

    def put(self, data=None, **kwargs):
        return self.session.put(self.url, data=json.dumps(data), headers=self.header, **kwargs)

    def put2(self, data=None, **kwargs):
        return self.session.put(self.url, data=data, headers=self.header, **kwargs)

    def delete(self, data=None, **kwargs):
        return self.session.delete(self.url, data=json.dumps(data), headers=self.header, **kwargs)


def StrtoArrdict(s: str):
    #s = s.strip().replace("[","").replace("]","")
    s = s.strip()
    s = s[1:]
    s = s[:-1]
    sa = s.split("},{")
    l = len(sa)
    if l == 1:
        sa[0] = json.loads(sa[0])
        return sa
    elif l == 2:
        sa[0] = json.loads(sa[0] + "}")
        sa[1] = json.loads("{" + sa[1])
    else:
        sa[0] = json.loads(sa[0] + "}")
        sa[l - 1] = json.loads("{" + sa[l - 1])
        for i in range(1, l - 1):
            sa[i] = json.loads("{" + sa[i] + "}")
    return sa

def indexArrdict(k: str, num: str, arr: list):
    for i in range(len(arr)):
        if num == arr[i][k]:
            return i
    return -1


def getValbyKeyVal(k1: str, v1: str, k2: str, res: str):
    rs = json.loads(res)
    data = rs["data"]
    for dt in data:
        if dt[k1] == v1:
            return dt[k2]
    return None


def getValbyKeyVal2(k1: str, v1: str, k2: str, res: str):
    rs = json.loads(res)
    data = rs["data"]
    items = data["items"]
    for dt in items:
        if dt[k1] == v1:
            return dt[k2]
    return None

