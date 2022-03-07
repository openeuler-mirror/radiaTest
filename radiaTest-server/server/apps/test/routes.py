from flask import jsonify, request
from flask_restful import Resource

from server.model.vmachine import Vmachine
from server.utils.response_util import RET
from server.utils.auth_util import auth
from server.utils.permission_utils import PermissionItemsPool


class TestEvent(Resource):
    @auth.login_required
    def get(self):
        _auth = request.headers.get("authorization")

        _vmachines = Vmachine.query.all()

        vmachine_pool = PermissionItemsPool(
            _vmachines, 
            "vmachine", 
            "GET", 
            _auth
        )


        return jsonify(
            error_code=RET.OK, 
            error_msg="OK", 
            data=vmachine_pool.allow_list
        )