import time

from flask import jsonify
from flask_restful import Resource

from worker.apps.monitor.handler import ResourceMonitor


class MonitorEvent(Resource):
    def get(self):
        _monitor = ResourceMonitor()
        time.sleep(1)
        return jsonify(_monitor.get_data())