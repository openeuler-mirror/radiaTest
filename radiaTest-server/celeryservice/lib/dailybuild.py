import json
from math import floor

from server.model.qualityboard import DailyBuild
from celeryservice.lib import TaskHandlerBase


class DailyBuildHandler(TaskHandlerBase):
    success_color = "green"
    error_color = "red"

    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def travesal_node(self, detail):
        if not isinstance(detail, dict):
            return

        detail["itemStyle"] = {
            "color": self.success_color if detail.get("value") else self.error_color,
            "shadowColor": self.success_color if detail.get("value") else self.error_color,
            "shadowBlur": 2
        }
        detail["lineStyle"] = {
            "color": self.success_color if detail.get("value") else self.error_color
        }

        if detail.get("value"):
            self.completion_num += 1
        self.total_num += 1

        if isinstance(detail.get("children"), list):
            for child in detail.get("children"):
                self.travesal_node(child)

    def resolve_detail(self, _id, detail, weekly_health_id):
        self.completion_num = 0
        self.total_num = 0 
        self.travesal_node(detail)
        
        dailybuild = DailyBuild.query.filter_by(id=_id).first()
        if not dailybuild:
            self.logger.error(
                "could not resolve dailybuild {} detail due to the build not exist"
            )
            return
        
        dailybuild.detail = json.dumps(detail)
        dailybuild.completion = floor(self.completion_num / self.total_num * 100)
        dailybuild.weekly_health_id = weekly_health_id
        dailybuild.add_update(DailyBuild, "/dailybuild")

        
