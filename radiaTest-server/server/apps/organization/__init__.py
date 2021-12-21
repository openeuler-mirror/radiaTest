from flask_restful import Api
from .routes import Cla, User, Group


def init_api(api: Api):
    api.add_resource(Cla, '/api/v1/org/cla', '/api/v1/org/<int:org_id>/cla', endpoint='org_cla')
    api.add_resource(User, '/api/v1/org/<int:org_id>/users', endpoint='org_user')
    api.add_resource(Group, '/api/v1/org/<int:org_id>/groups', endpoint='org_group')
