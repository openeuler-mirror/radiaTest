from flask.json import jsonify
from flask_restful import Resource

from messenger.utils.response_util import RET


class HeartbeatEvent(Resource):
    def get(self):
        return jsonify(
            error_code=RET.OK, 
            error_msg="OK"
        )