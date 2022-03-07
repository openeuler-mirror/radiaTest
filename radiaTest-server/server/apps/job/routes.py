from sqlalchemy import or_, and_
from flask import request, g
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.model.job import Analyzed, Job, job_family
from server.utils.db import Edit, Select
from server.schema.job import AnalyzedQueryBase, AnalyzedQueryItem, AnalyzedQueryRecords, RunSuiteBase, RunTemplateBase, JobQuerySchema
from server.model.testcase import Case, Suite
from server.utils.auth_util import auth
from server.utils.page_util import PageUtil
from server.utils.response_util import RET, response_collect
from celeryservice.tasks import run_suite, run_template


class RunSuiteEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: RunSuiteBase):
        _body = body.__dict__
        _user = {
            "user_id": int(g.gitee_id),
            "auth": request.headers.get("authorization"),
        }

        suite = Suite.query.filter_by(id=body.suite_id).first()
        if not suite:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="the suite is not exist")

        run_suite.delay(_body, _user)
        return jsonify(error_code=RET.OK, error_msg="succeed in creating the job for running suite")


class RunTemplateEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: RunTemplateBase):
        _body = body.__dict__
        _user = {
            "user_id": int(g.gitee_id),
            "auth": request.headers.get("authorization"),
        }
        run_template.delay(_body, _user)
        return jsonify(error_code=RET.OK, error_msg="succeed in creating the job for running template")


class JobEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self, query: JobQuerySchema):
        filter_params = [
            or_(
                Job.multiple.is_(True),
                and_(
                    Job.is_suite_job == True,
                    Job.multiple.is_(False),
                )
            )
        ]

        if query.name:
            filter_params.append(Job.name.like(f"%{query.name}%"))
        
        if query.status == "PENDING":
            filter_params.append(Job.status == "PENDING")
        elif query.status == "DONE":
            filter_params.append(
                or_(
                    Job.status == "DONE", 
                    Job.status == "BLOCK"
                )
            )
        else:
            filter_params.append(
                and_(
                    Job.status != "DONE",
                    Job.status != "BLOCK",
                    Job.status != "PENDING"
                )
            )

        query_filter = Job.query.outerjoin(
            job_family, 
            Job.id == job_family.c.parent_id
        ).filter(*filter_params)

        if query.sorted_by == "create_time":
            query_filter = query_filter.order_by(Job.create_time.desc())
        elif query.sorted_by == "end_time":
            query_filter = query_filter.order_by(Job.end_time.desc())

        def page_func(item):
            job_dict = item.to_json()
            return job_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, 
            query.page_num,
            query.page_size, 
            func=page_func
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR, 
                error_msg=f'get job page error: {e}'
            )
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


class JobItemEvent(Resource):
    @auth.login_required
    def get(self, job_id):
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="job is not exist")
        
        data = [child.to_json() for child in job.children]

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data,
        )


class AnalyzedEvent(Resource):
    @auth.login_required
    @validate()
    def get(self, query: AnalyzedQueryBase):
        return_data = []

        job = Job.query.filter_by(id=query.job_id).first()
        if not job:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="the job not exist"
            )

        if job.multiple is True:
            for child in job.children:
                _analyzeds = child.analyzeds
                return_data += [_analyzed.to_json() for _analyzed in _analyzeds]
        else:
            _analyzeds = job.analyzeds
            return_data = [_analyzed.to_json() for _analyzed in _analyzeds]

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


class AnalyzedItemEvent(Resource):
    @auth.login_required
    @validate()
    def get(self, analyzed_id, query: AnalyzedQueryItem):
        body = query.__dict__
        body.update({"id": analyzed_id})
        return Select(Analyzed, body).precise()

    @auth.login_required
    @validate()
    def put(self, analyzed_id, body: AnalyzedQueryItem):
        _body = body.__dict__
        _body.update({"id": analyzed_id})
        return Edit(Analyzed, _body).single(Analyzed, '/analyzed')


class AnalyzedRecords(Resource):
    @auth.login_required
    @validate()
    def get(self, query: AnalyzedQueryRecords):
        _case = Case.query.filter_by(id=query.case_id).first()

        if not _case:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="case is not exist"
            )

        return Select(Analyzed, {"case_id": _case.id}).precise()


class AnalyzedLogs(Resource):
    @auth.login_required
    def get(self, analyzed_id):
        _analyzed = Analyzed.query.filter_by(id=analyzed_id).first()
        return jsonify(
            error_code=RET.OK, 
            error_msg="OK", 
            data=_analyzed.get_logs()
        )
