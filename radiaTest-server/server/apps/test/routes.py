from flask import request, jsonify
from flask_restful import Resource

from server import redis_client
from server.utils.response_util import RET


class TestEvent(Resource):
    def get(self):
        body = request.args.to_dict()

        task_id = body["task_id"]

        status = redis_client.get("celery-task-meta-{}".format(task_id))

        return jsonify(error_code=RET.OK, error_msg="OK", data=status)