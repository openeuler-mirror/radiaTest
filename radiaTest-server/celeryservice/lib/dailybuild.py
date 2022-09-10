# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang
# @email   : ethanzhang55@outlook.com
# @Date    : 2022/09/15
# @License : Mulan PSL v2
#####################################

import json
from math import floor

from server.model.qualityboard import DailyBuild
from celeryservice.lib import TaskHandlerBase


class DailyBuildHandler(TaskHandlerBase):
    # colors support to be set in rgbd/hexcode/name format
    success_color = "green"
    error_color = "red"

    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def travesal_node(self, node_key: str, node_value):
        """
        Parse each node of dailybuild result to the format which echarts needs of web
        e.g.
            in: 
                "node1": {
                    "value": True, 
                    "node2": {
                        "value": True
                    }, 
                    "node3": {}
                }
            out: 
                {
                    "name": "node1", 
                    "value": True,
                    "itemStyle": {...},
                    "lineStyle": {...},
                    "children": [
                        {
                            "name": "node2",
                            "value": True,
                        }
                    ]
                }
        Args:
            node_key(str): the name of directory node of dailybuild
            node_value(dict): the build result of the directory node of dailybuild
                value(bool): whether the build is done of this node
        Return: 
            dict: parsed build result which in a specific format
        """
        if not isinstance(node_value, dict) and not isinstance(node_value.get("value"), bool):
            return None

        item = dict()
        item["name"] = node_key
        item["value"] = node_value.pop("value")

        item["itemStyle"] = {
            "color": self.success_color if item.get("value") else self.error_color,
            "shadowColor": self.success_color if item.get("value") else self.error_color,
            "shadowBlur": 2
        }
        item["lineStyle"] = {
            "color": self.success_color if item.get("value") else self.error_color
        }

        if item.get("value"):
            self.completion_num += 1
        self.total_num += 1

        _children = list()
        for key,value in node_value.items():
            _child = self.travesal_node(key, value)
            if _child is not None:
                _children.append(_child)
        if len(_children) > 0:
            item["children"] = _children
        
        return item

    def resolve_detail(self, _id, detail, weekly_health_id):
        if not isinstance(detail, dict):
            raise ValueError(f"the type of param detail should be dictionary, not {type(detail)}")
        
        self.completion_num = 0
        self.total_num = 0
        
        detail["value"] = True
        parsed_detail = self.travesal_node("MAIN_DIR", detail)
        
        dailybuild = DailyBuild.query.filter_by(id=_id).first()
        if not dailybuild:
            self.logger.error(
                "could not resolve dailybuild {} detail due to the build not exist"
            )
            return
        
        dailybuild.detail = json.dumps(parsed_detail)
        dailybuild.completion = floor(self.completion_num / self.total_num * 100)
        dailybuild.weekly_health_id = weekly_health_id
        dailybuild.add_update(DailyBuild, "/dailybuild")

        
