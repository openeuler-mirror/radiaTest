from flask_restful import Api
from .routes import Group, User

def init_api(api: Api):
    api.add_resource(Group, '/api/v1/groups', '/api/v1/groups/<int:group_id>', endpoint='group')
    # api.add_resource(OrgGroups, '/api/v1/org/<int:org_id>/groups/all')
    api.add_resource(User, '/api/v1/groups/<int:group_id>/users', endpoint='group_user')
