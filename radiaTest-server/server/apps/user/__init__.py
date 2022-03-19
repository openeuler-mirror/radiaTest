from flask_restful import Api
from .routes import GiteeLogin, Login
from .routes import User
from .routes import UserItem
from .routes import Org
from .routes import Logout
from .routes import Group
from .routes import UserTask
from .routes import UserMachine
# from .routes import Token


def init_api(api: Api):
    api.add_resource(GiteeLogin, '/api/v1/gitee/oauth/login', endpoint='user_login')
    api.add_resource(Login, '/api/v1/login', endpoint='login')
    api.add_resource(User, '/api/v1/users', endpoint="user")
    api.add_resource(UserItem, '/api/v1/users/<int:gitee_id>', endpoint='useritem')
    api.add_resource(Org, '/api/v1/users/org/<int:org_id>', endpoint='user_org')
    api.add_resource(Logout, '/api/v1/logout', endpoint='logout')
    api.add_resource(Group, '/api/v1/users/groups/<int:group_id>', endpoint='user_group')
    api.add_resource(UserTask, '/api/v1/user/task/info', endpoint='user_task')
    api.add_resource(UserMachine, '/api/v1/user/machine/info', endpoint='user_machine')
    # api.add_resource(Token, '/api/v1/auth/token', endpoint='token')
