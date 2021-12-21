# -*- coding: utf-8 -*-
# @Author : Ethan-Zhang
# @Date   : 2021-09-06 20:39:53
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :

from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model.template import Template
from server.model.testcase import Case
from server.utils.db import Insert, Edit, Select, Delete
from server.schema.base import DeleteBaseModel
from server.schema.template import TemplateBase, TemplateUpdate


class TemplateEvent(Resource):
    @validate()
    def post(self, body: TemplateBase):
        _body = body.__dict__

        cases = []
        for case_name in _body.get("cases"):
            case = Case.query.filter_by(name=case_name).first()
            if not case:
                continue

            cases.append(case)

        _body.pop("cases")
        resp = Insert(Template, _body).single(Template, '/template')

        template = Template.query.filter_by(name=_body.get("name")).first()

        for case in cases:
            template.cases.append(case)

        template.add_update(Template, "/template")

        return resp

    @validate()
    def put(self, body: TemplateUpdate):
        _body = body.__dict__

        cases = []
        for case_name in _body.get("cases"):
            cases.append(Case.query.filter_by(name=case_name).first())

        _body.pop("cases")
        resp = Edit(Template, _body).single(Template, '/template')
        template = Template.query.filter_by(name=_body.get("name")).first()

        for case in template.cases:
            template.cases.remove(case)
            template.add_update(Template, "/template")

        for case in cases:
            template.cases.append(case)
            template.add_update(Template, "/template")

        return resp

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Template, body.__dict__).batch(Template, "/template")

    def get(self):
        body = request.args.to_dict()
        return Select(Template, body).precise()
