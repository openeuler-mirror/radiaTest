# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-20 10:02:56
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Desc   :


import datetime
from re import template
from typing import Optional

from pydantic import BaseModel, constr, root_validator

from server.schema import Frame
from server.schema.template import TemplateUpdate
from server.schema.base import UpdateBaseModel
from server.utils.db import Precise
from server.model import Milestone, Template


class RunSuiteBase(BaseModel):
    name: Optional[constr(max_length=64)]
    milestone_id: int
    frame: Frame
    testsuite: str

    @root_validator
    def assignment(cls, values):
        values["start_time"] = datetime.datetime.now()

        if not values.get("name"):
            milestone = Precise(Milestone, {"id": values.get("milestone_id")}).first()

            values["name"] = "Job-%s-%s-%s" % (
                milestone.name.replace(" ", "-"),
                values.get("frame"),
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            )
        return values


class RunTemplateBase(TemplateUpdate):
    frame: Frame
    taskmilestone_id: Optional[int]

    @root_validator
    def assignment(cls, values):
        values["start_time"] = datetime.datetime.now()

        template = Precise(Template, values).first()
        values["template"] = template

        if not values.get("name"):
            values["name"] = "Job-%s-%s-%s" % (
                template.name.replace(" ", "-"),
                values.get("frame"),
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            )
        else:
            values["name"] = values["name"].replace(" ", "-")

        return values


class AnalyzedUpdate(UpdateBaseModel):
    fail_type: Optional[str]
    details: Optional[str]

