from flask_restful import Api
from .routes import Login, Register, Org, OrgItem


def init_api(api: Api):
    api.add_resource(Login, '/api/v1/admin/login', endpoint='admin_login')
    api.add_resource(Register, '/api/v1/admin/register', endpoint='admin_register')
    api.add_resource(Org, '/api/v1/admin/org', endpoint='admin_org')
    api.add_resource(OrgItem, '/api/v1/admin/org/<int:org_id>')
