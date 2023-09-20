# swagger插件使用示例

## 1、适配现有框架自动生成对应参数字段，以及生成默认响应

**路径参数插件自动识别无需手动添加，暂时只支持简单类型 string、int、float、bool**

**注意：schema必须是BaseModel(from pydantic import BaseModel)的子类，若不是请手动填写对应schema信息**

### 1.1、get

示例1 ：OauthLoginSchema请求参数自动解析

```python
# radiaTest-server/server/apps/user/routes.py
def get_user_tag():
    return {
        "name": "用户",
        "description": "用户相关接口",
    }
    
    
class OauthLogin(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "OauthLogin",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_user_tag(),  # 当前接口所对应的标签
        "summary": "oauth登录重定向",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": OauthLoginSchema,   # 当前接口查询参数schema校验器
    })
    def get(self, query: OauthLoginSchema):
        return handler_oauth_login(query)
```

示例2 ：UserInfoSchema响应体自动解析

```python
    # radiaTest-server/server/apps/user/routes.py
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserItem",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "获取用户信息接口",
        "externalDocs": {"description": "", "url": ""},
        "response_data_schema": UserInfoSchema,
    })
    def get(self, user_id):
        return handler_user_info(user_id)
```



### 1.2、post

示例：ClaSignSchema请求体自动解析

该接口包含路径参数user_id，插件会自动获取转换

```python
# radiaTest-server/server/apps/user/routes.py
class UserItem(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "UserItem",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_user_tag(),  # 当前接口所对应的标签
        "summary": "用户注册接口",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ClaSignSchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, user_id, body: ClaSignSchema):
        return handler_register(user_id, body)
```



## 2、自定义数据格式

格式参考文档 https://swagger.io/docs/specification/basic-structure/ 

中文文档 https://codeleading.com/article/75955850205/

**自定义请求参数，请求体以及响应体**

### 2.1、自定义请参数和响应体

示例：请求参数和响应体自定义

```python
# radiaTest-server/server/apps/user/routes.py
@oauth.route("/api/v1/oauth/callback", methods=["GET"])
@swagger_adapt.api_schema_model_map({
    # 当前接口非Resource类，需要手动添加 url、method
    "url": "/api/v1/oauth/callback",  # 获取当前接口所在模块
    "method": "get",  # 获取当前接口所在模块
    "__module__": get_user_tag.__module__,  # 获取当前接口所在模块
    "resource_name": "OauthLogin",  # 当前接口视图函数名
    "func_name": "get",  # 当前接口所对应的函数名
    "tag": get_user_tag(),  # 当前接口所对应的标签
    "summary": "oauth回调接口",  # 当前接口概述
    "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    # 自定义请求参数
    "query_schema_model": [{
        "name": "code",
        "in": "query",
        "required": True,
        "style": "form",
        "explode": True,
        "description": "用户oauth code",
        "schema": {"type": "string"}},
        {
            "name": "user_id",
            "in": "cookie",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "用户id",
            "schema": {"type": "string"}}],
    # 自定义响应体
    "response_data_schema": {
            "302": {
                "description": "重定向到登录认证地址",
                "headers": {
                    "Location": {
                        "type": "string",
                        "description": "重定向的位置",
                    },
                    "schema": {
                        "type": "string",
                        "format": "uri",
                    }}}
    }
})
def oauth_callback():
    return handler_oauth_callback()
```

### 2.2、自定义请求体

示例：请求体自定义

```python
# radiaTest-server/server/apps/user/routes.py
class Group(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "Group",
        "func_name": "put",
        "tag": get_user_tag(),
        "summary": "加入群组",
        "externalDocs": {"description": "", "url": ""},
        # 自定义请求体示例
        "request_schema_model": {
            "description": "",
            "content": {
                "application/json":
                    {"schema": {
                        "properties": {
                            "msg_id": {
                                "title": "消息id",
                                "type": "integer"
                            },
                            "access": {
                                "title": "是否接受",
                                "type": "boolean"
                            }
                        },
                        "required": ["msg_id", "access"],
                        "title": "JoinGroupSchema",
                        "type": "object"
                    }}
            },
            "required": True
        }

    })
    def put(self, group_id, body: JoinGroupSchema):
        return handler_add_group(group_id, body)
```

