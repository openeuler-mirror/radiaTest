import re
import json
import requests

from flask import current_app, request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.schema.external import OpenEulerUpdateTaskBase, RepoCaseUpdateBase
from server.model.group import Group
from server.model.mirroring import Repo
from server.utils.db import Insert, Edit
from .handler import UpdateRepo, UpdateTaskHandler, UpdateTaskForm
from server.model.testcase import Suite, Case
from server.schema.testcase import SuiteBase, CaseBase
from server.utils.db import Select
from server.utils.response_util import RET


class UpdateTaskEvent(Resource):
    @validate()
    def post(self, body: OpenEulerUpdateTaskBase):
        form = UpdateTaskForm(body)

        # get group_id
        groups = Group.query.all()
        _group = list(filter(lambda x: x.name == current_app.config.get("OE_QA_GROUP_NAME"), groups))

        if not _group:
            return {"error_code": 60001, "error_mesg": "invalid group name by openEuler QA config"}
        
        group = _group[0]

        # get product_id
        UpdateTaskHandler.get_product_id(form)

        # extract update milestone name
        pattern = r'/(update.+?)/'

        result = re.findall(pattern, body.base_update_url)

        if  not result:
            return {"error_code": 60002, "error_mesg": "invalid repo url format"}

        form.title = "{} {} {}".format(
            body.product,
            body.version,
            result[-1]
        )

        # get milestone_id
        UpdateTaskHandler.get_milestone_id(form)

        # get cases
        UpdateTaskHandler.suites_to_cases(form)

        #create repo config content
        update_repo = UpdateRepo(body)
        update_repo.create_repo_config()

        # insert or update repo config and use internal task execute api
        for frame in ["aarch64", "x86_64"]:
            repo = Repo.query.filter_by(
                milestone_id=form.milestone_id, 
                frame=frame
            ).first()

            if not repo:
                Insert(
                    Repo, 
                    {
                        "content": update_repo.content, 
                        "frame": frame, 
                        "milestone_id": form.milestone_id
                    }
                ).single(Repo, "/repo")
            else:
                Edit(
                    Repo,
                    {
                        "id": repo.id,
                        "content": update_repo.content, 
                    }
                ).single(Repo, "/repo")

            requests.post(
                url="http://{}:{}/api/v1/tasks/execute".format(
                    current_app.config.get("SERVER_IP"),
                    current_app.config.get("SERVER_PORT"),
                ),
                data=json.dumps({
                    "title": "{} {}".format(form.title, frame),
                    "milestone_id": form.milestone_id,
                    "group_id": group.id,
                    "frame": frame,
                    "cases": form.cases,
                }),
                headers=current_app.config.get("HEADERS")
            )
            
        # return response
        return {"error_code": "2000", "error_mesg": "OK"}
                

class RepoSuiteEvent(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(Suite, body).precise()

    
    @validate()
    def post(self, body: SuiteBase):
        return Insert(Suite, body.__dict__).single(Suite, "/suite")


class RepoCaseEvent(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(Case, body).precise()

    @validate()
    def post(self, body: CaseBase):
        _body = body.__dict__
        
        _suite = Suite.query.filter_by(name=_body.get("suite")).first()
        if not _suite:
            return jsonify(
                error_code=RET.PARMA_ERR, 
                error_mesg="The suite {} is not exist".format(
                    _body.get("suite")
                )
            )

        _body["suite_id"] = _suite.id
        _body.pop("suite")
        
        return Insert(Case, _body).single(Case, "/case")
    
    @validate()
    def put(self, body: RepoCaseUpdateBase):
        return Edit(Case, body.__dict__).single(Case, "/case")
