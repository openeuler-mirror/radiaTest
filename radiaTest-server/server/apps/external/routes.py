# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : 
# @email   : 
# @Date    : 
# @License : Mulan PSL v2


#####################################
from datetime import datetime, timedelta
import os
import re
import shlex
from subprocess import getstatusoutput
import pytz

import yaml
from flask import current_app, jsonify, request, make_response, send_file, render_template
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer, swagger_adapt
from server.utils.auth_util import auth
from server.schema.external import (
    LoginOrgListSchema,
    OpenEulerUpdateTaskBase,
    DeleteCertifiSchema,
    QueryTestReportFileSchema,
)
from server.model.group import Group
from server.model.organization import Organization
from server.model.product import Product
from server.model.qualityboard import DailyBuild, WeeklyHealth
from server.model.milestone import TestReport
from server.utils.db import Insert, Edit
from server.utils.response_util import RET
from server.utils.file_util import ImportFile
from celeryservice.tasks import resolve_dailybuild_detail, resolve_rpmcheck_detail
from server.model.milestone import Milestone
from server.utils.response_util import response_collect
from server.apps.external.handler import (
    UpdateRepo,
    UpdateTaskHandler,
    UpdateTaskForm,
    AtHandler,
    MajunLoginHandler,
)
from server.utils.external_auth_util import external_auth


def get_external_tag():
    return {
        "name": "对外相关",
        "description": "对外相关接口",
    }


class UpdateTaskEvent(Resource):
    @external_auth
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "UpdateTaskEvent",
        "func_name": "post",
        "tag": get_external_tag(),
        "summary": "对openEuler QA提供的接口，同步创建里程碑、用例",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": OpenEulerUpdateTaskBase,
    })
    def post(self, body: OpenEulerUpdateTaskBase):
        form = UpdateTaskForm(body)

        # get group_id
        groups = Group.query.all()
        _group = list(filter(lambda x: x.name == current_app.config.get("OE_QA_GROUP_NAME"), groups))

        if not _group:
            return {"error_code": RET.TASK_WRONG_GROUP_NAME, "error_msg": "invalid group name by openEuler QA config"}

        group = _group[0]
        form.group = group
        # get product_id
        UpdateTaskHandler.get_product_id(form)

        # extract update milestone name
        pattern = r'/(update.+?)/'

        result = re.findall(pattern, body.base_update_url)

        if not result:
            return {"error_code": RET.WRONG_INSTALL_WAY, "error_msg": "invalid repo url format"}

        form.title = "{} {} {}".format(
            body.product,
            body.version,
            result[-1]
        )

        # get milestone_id
        UpdateTaskHandler.get_milestone_id(form)
        # 同步创建baseline
        UpdateTaskHandler.get_baseline_id(form)
        # get cases
        UpdateTaskHandler.create_case_node(form)

        # create repo config content
        update_repo = UpdateRepo(body)
        update_repo.create_repo_config()

        milstone_info = Milestone.query.filter_by(id=form.milestone_id).first()
        if not milstone_info:
            return {"error_code": RET.NO_DATA_ERR, "error_msg": "invalid milstone id"}
        return {"error_code": RET.OK, "error_msg": "OK", "data": {"milestone_name": milstone_info.name}}


class LoginOrgList(Resource):
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "LoginOrgList",
        "func_name": "get",
        "tag": get_external_tag(),
        "summary": "获取可登录的组织列表",
        "externalDocs": {"description": "", "url": ""},
        "response_data_schema": {
                '200': {'content': {'application/json':
                        {'schema': {
                            'type': "array",
                            'items': LoginOrgListSchema.schema()
                        }}},
                        'description': 'success'}}
    })
    def get(self):
        return_data = []
        orgs = Organization.query.filter_by(is_delete=False).all()
        for org in orgs:
            org_dict = LoginOrgListSchema(**org.__dict__).__dict__
            org_dict.update({
                "cla": True if org.cla_verify_url else False,
                "enterprise": True if org.enterprise_id else False,
            })
            return_data.append(org_dict)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=return_data
        )


class CaCert(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "CaCert",
        "func_name": "get",
        "tag": get_external_tag(),
        "summary": "获取ca证书",
        "externalDocs": {"description": "", "url": ""},

    })
    def get(self):
        return send_file(
            current_app.config.get("CA_CERT"),
            as_attachment=True
        )

    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "CaCert",
        "func_name": "post",
        "tag": get_external_tag(),
        "summary": "机器组ca证书更新",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                            "type": "object",
                            "properties": {
                                        "san": {
                                            "title": "签名字符串",
                                            "type": "string"
                                        },
                                        "ip": {
                                            "title": "messenger ip",
                                            "type": "string"
                                        },
                                        "csr": {
                                            "type": "string",
                                            "format": "binary"}},
                            "required": ["san", "ip", "csr"]
                    }}}}
    })
    def post(self):
        _san = request.form.get("san")
        _messenger_ip = request.form.get("ip")
        _csr_file = request.files.get("csr")

        if not _messenger_ip or not _csr_file or not _san:
            return make_response(
                jsonify(
                    validation_error="lack of ip address/csr file/subject alternative name"
                ),
                current_app.config.get("FLASK_PYDANTIC_VALIDATION_ERROR_STATUS_CODE", 400)
            )

        csr_file = ImportFile(
            _csr_file,
            filename=request.form.get("ip"),
            filetype="csr"
        )

        try:
            csr_file.file_save(
                "{}/csr".format(
                    current_app.config.get("CA_DIR")
                ),
                timestamp=True,
            )
        except RuntimeError as e:
            return make_response(
                jsonify(
                    message=str(e)
                ),
                500
            )

        certs_dir = "{}/certs".format(
            current_app.config.get("CA_DIR")
        )
        if not os.path.exists(certs_dir):
            csr_file.file_remove()
            return make_response(
                jsonify(
                    message="the directory to storage certfile does not exist"
                ),
                500
            )

        certs_path = f"{certs_dir}/{_messenger_ip}.crt"

        caconf_path = "{}/conf/ca.cnf".format(current_app.config.get("CA_DIR"))

        exitcode, output = getstatusoutput(
            "bash server/apps/external/certs_sign.sh {} {} {} {}".format(
                shlex.quote(csr_file.filepath),
                shlex.quote(certs_path),
                caconf_path,
                shlex.quote(_san)
            )
        )

        if exitcode != 0:
            csr_file.file_remove()
            return make_response(
                jsonify(
                    message=f"fail to create certfile for machine group of messenger ip {_messenger_ip}: {output}"
                ),
                500
            )
        else:
            return send_file(certs_path, as_attachment=True)

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "CaCert",
        "func_name": "delete",
        "tag": get_external_tag(),
        "summary": "删除机器组ca证书",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": DeleteCertifiSchema
    })
    def delete(self, body: DeleteCertifiSchema):
        
        _cert_file = "{0}/certs/{1}.crt".format(
            current_app.config.get("CA_DIR"),
            body.ip,
        )
        _openssl_cfg = "{0}/openssl.cnf".format(
            current_app.config.get("CA_DIR"),
        )

        exitcode, output = getstatusoutput(
            "openssl ca -revoke {0} -config {1}".format(
                shlex.quote(_cert_file),
                shlex.quote(_openssl_cfg),
            )
        )

        if exitcode != 0:
            raise RuntimeError(
                f"fail to delete certfile for machine group of messenger ip {body.ip}: {output}"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )


class DailyBuildEvent(Resource):
    @external_auth
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "DailyBuildEvent",
        "func_name": "post",
        "tag": get_external_tag(),
        "summary": "创建DailyBuild",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                            "type": "object",
                            "properties": {
                                    "product": {
                                        "title": "产品",
                                        "type": "string"
                                    },
                                    "build": {
                                        "title": "构建名",
                                        "type": "string"
                                    },
                                    "file": {
                                        "type": "string",
                                        "format": "binary"}},
                            "required": ["product", "build", "file"]
                    }},
            }}
    })
    def post(self):
        _product = request.form.get("product")
        _build = request.form.get("build")
        _file = request.files.get("file")
        if not _product or len(_product.split("-")) != 2 or not _build or not _file:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="params invalid"
            )

        _name, _version = _product.split("-")
        product = Product.query.filter_by(name=_name, version=_version).first()
        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="this build record belongs to a product not enrolled yet"
            )

        _id = None
        _dailybuild = DailyBuild.query.filter_by(product_id=product.id, name=_build).first()
        if _dailybuild:
            _id = _dailybuild.id

        _id = Insert(
            DailyBuild,
            {
                "name": _build,
                "product_id": product.id,
            }
        ).insert_id(DailyBuild, "/dailybuild")

        weekly_health = WeeklyHealth.query.filter_by(
            product_id=product.id
        ).order_by(
            WeeklyHealth.end_time.desc()
        ).first()
        _date = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        _date_formated = _date.strftime("%Y-%m-%d")

        if _date.weekday() == 0 or not weekly_health or _date_formated > weekly_health.end_time:
            _weekly_health_id = Insert(
                WeeklyHealth,
                {
                    "start_time": _date_formated,
                    "end_time": (
                        _date + timedelta(days=(6 - _date.weekday()))
                    ).strftime("%Y-%m-%d"),
                    "product_id": product.id,
                }
            ).insert_id(WeeklyHealth, "/weeklybuild-health")
        else:
            _weekly_health_id = weekly_health.id

        _detail = yaml.safe_load(_file)
        if not isinstance(_detail, dict):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="the file with dailybuild detail is not in valid format"
            )

        resolve_dailybuild_detail.delay(
            dailybuild_id=_id,
            dailybuild_detail=_detail,
            weekly_health_id=_weekly_health_id
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class RpmCheckEvent(Resource):
    @external_auth
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "RpmCheckEvent",
        "func_name": "post",
        "tag": get_external_tag(),
        "summary": "rpm检查",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                            "type": "object",
                            "properties": {
                                    "product": {
                                        "title": "产品",
                                        "type": "string"
                                    },
                                    "build": {
                                        "title": "构建名",
                                        "type": "string"
                                    },
                                    "file": {
                                        "type": "string",
                                        "format": "binary"}},
                            "required": ["product", "build", "file"]
                    }}}}
    })
    def post(self):
        _product = request.form.get("product")
        _build = request.form.get("build")
        _file = request.files.get("file")
        if not _product or len(_product.split("-")) != 2 or not _build or not _file:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="params invalid"
            )

        _name, _version = _product.split("-")
        product = Product.query.filter_by(name=_name, version=_version).first()
        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="this build record belongs to a product not enrolled yet"
            )

        _detail = yaml.safe_load(_file)
        if not isinstance(_detail, list):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="the file with rpmcheck detail is not in valid format"
            )

        _file.seek(0)
        rpmcheck_path = current_app.config.get("RPMCHECK_FILE_PATH")
        _file.save(f"{rpmcheck_path}/rpmcheck_{_product}_{_build}.yaml")

        resolve_rpmcheck_detail.delay(f"{_product}_{_build}", _detail)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class AtEvent(Resource):
    @external_auth
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "AtEvent",
        "func_name": "get",
        "tag": get_external_tag(),
        "summary": "At结果获取",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": [{
            "name": "release_url_x86_64",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "x86_64 release url",
            "schema": {"type": "string"}},
            {
                "name": "release_url_aarch64",
                "in": "query",
                "required": False,
                "style": "form",
                "explode": False,
                "description": "aarch64 release url",
                "schema": {"type": "string"}}],
    })
    def get(self):
        buildname_x86 = request.values.get("release_url_x86_64")
        buildname_aarch64 = request.values.get("release_url_aarch64")

        at = AtHandler(buildname_x86, buildname_aarch64)
        result = at.get_result()
        if result[0]:
            return {
                "error_code": RET.OK,
                "error_msg": "OK",
                "data": result[1]
            }
        else:
            return {
                "error_code": RET.PARMA_ERR,
                "error_msg": "unknown arch"
            }


class AtDetailEvent(Resource):
    @external_auth
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "AtDetailEvent",
        "func_name": "get",
        "tag": get_external_tag(),
        "summary": "At结果详情获取",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": [{
            "name": "release_url_x86_64",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "x86_64 release url",
            "schema": {"type": "string"}},
            {
                "name": "release_url_aarch64",
                "in": "query",
                "required": False,
                "style": "form",
                "explode": False,
                "description": "aarch64 release url",
                "schema": {"type": "string"}}],
    })
    def get(self):
        buildname_x86 = request.values.get("release_url_x86_64")
        buildname_aarch64 = request.values.get("release_url_aarch64")
        at = AtHandler(buildname_x86, buildname_aarch64)
        return {
            "error_code": RET.OK,
            "error_msg": "OK",
            "data": at.get_report()
        }


class GetTestReportFileEvent(Resource):
    @external_auth
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "GetTestReportFileEvent",
        "func_name": "get",
        "tag": get_external_tag(),
        "summary": "获取测试报告",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": QueryTestReportFileSchema
    })
    def get(self, query: QueryTestReportFileSchema):
        _milstone = Milestone.query.filter_by(name=query.milestone_name).first()
        if not _milstone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"{query.milestone_name} milestone does not exist.",
            )
        _test_report = TestReport.query.join(Milestone).filter(
            Milestone.name == query.milestone_name,
            TestReport.milestone_id == Milestone.id
        ).first()
        if not _test_report:
            from server.apps.task.handlers import HandlerTaskProgress
            try:
                progress = HandlerTaskProgress(_milstone.id).get_milestone_test_progress
                return jsonify(
                    error_code=RET.OK,
                    error_msg="test is in progress.",
                    data={"progress": progress}
                )
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="test is not in progress.",
                )

        tmp_folder = current_app.template_folder
        current_app.template_folder = current_app.config.get("TEST_REPORT_PATH")
        if query.file_type == "md":
            resp = make_response(render_template(_test_report.md_file))
        else:
            resp = make_response(render_template(_test_report.html_file))
        current_app.template_folder = tmp_folder
        return resp


class MajunCheckTokenEvent(Resource):
    @auth.login_required()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "MajunCheckTokenEvent",
        "func_name": "post",
        "tag": get_external_tag(),
        "summary": "Majun token 检查",
        "externalDocs": {"description": "", "url": ""},
    })
    def post(self):
        return jsonify(
            error_code=RET.OK,
            error_msg="success"
        )


class MajunLoginEvent(Resource):
    @swagger_adapt.api_schema_model_map({
        "__module__": get_external_tag.__module__,
        "resource_name": "MajunLoginEvent",
        "func_name": "get",
        "tag": get_external_tag(),
        "summary": "Majun登录",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": [{
            "name": "type",
            "in": "query",
            "required": True,
            "style": "form",
            "explode": True,
            "description": "登录类型",
            "schema": {"type": "string", "enum": ["openeuler", "gitee"]}},
            {
                "name": "org_id",
                "in": "query",
                "required": True,
                "style": "form",
                "explode": True,
                "description": "组织id",
                "schema": {"type": "string"}},
            {
                "name": "access_token",
                "in": "query",
                "required": True,
                "style": "form",
                "explode": True,
                "description": "令牌",
                "schema": {"type": "string"}}],
    })
    def get(self):
        majun = MajunLoginHandler(
            request.values.get("type"), request.values.get("org_id"), request.values.get("access_token")
        )
        result = majun.login()

        if result[0]:
            return jsonify(
                error_code=RET.OK,
                error_msg="success",
                data={"user_id": result[1], "token": result[2], "url": result[3]}
            )
        else:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=result[1],
            )
