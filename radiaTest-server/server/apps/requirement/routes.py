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

from flask import jsonify, request
from flask_pydantic import validate
from flask_restful import Resource

from server import casbin_enforcer, swagger_adapt
from .handlers import RequirementHandler, RequirementPackageHandler, RequirementItemHandler
from server.utils.response_util import response_collect, RET
from server.utils.auth_util import auth
from server.schema.requirement import (
    PackageTaskCreateSchema,
    AttachmentBaseSchema,
    ProgressFeedbackSchema,
    PackageCompletionSchema,
    RequirementQuerySchema,
    RequirmentCreateSchema,
    RequirementItemRewardDivideSchema,
    AttachmentFilenameSchema,
    AttachmentLockSchema
)
from server.utils.file_util import identify_file_type, FileTypeMapping


def get_requirement_tag():
    return {
        "name": "需求",
        "description": "需求相关接口",
    }


class RequirementOrgEvent(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementOrgEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "组织需求创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RequirmentCreateSchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, org_id, body: RequirmentCreateSchema):
        _body = body.__dict__
        return RequirementHandler.free_publish(org_id, _body)


class RequirementGroupEvent(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementGroupEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "用户组需求创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RequirmentCreateSchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, group_id, body: RequirmentCreateSchema):
        _body = body.__dict__
        return RequirementHandler.publish(
            body=_body, 
            publisher_type="group", 
            publisher_group_id=group_id,
        )


class RequirementEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "个人需求创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RequirmentCreateSchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: RequirmentCreateSchema):
        _body = body.__dict__
        return RequirementHandler.publish(
            body=_body,
            publisher_type="person",
        )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "分页查看需求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": RequirementQuerySchema,  # 当前接口请求体参数schema校验器
    })
    def get(self, query: RequirementQuerySchema):
        return RequirementHandler.get_all(query)
    

class RequirementItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "需求详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, requirement_id):
        try:
            return RequirementItemHandler(requirement_id).get_info()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
    
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "删除需求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, requirement_id):
        try:
            return RequirementItemHandler(requirement_id).delete()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemAcceptEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAcceptEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "个人接受需求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, requirement_id):
        _body = {
            "acceptor_type": "person"
        }
        try:
            return RequirementItemHandler(requirement_id, _body).accept()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemGroupAcceptEvent(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemGroupAcceptEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "团队接受需求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, requirement_id, group_id):
        _body = {
            "acceptor_type": "group",
            "acceptor_group_id": group_id
        }
        try:
            return RequirementItemHandler(requirement_id, _body).accept()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemRejectEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemRejectEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "拒绝接受需求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, requirement_id):
        try:
            return RequirementItemHandler(requirement_id).reject()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemValidateEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemValidateEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "需求确认",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, requirement_id):
        try:
            return RequirementItemHandler(requirement_id).validate()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemAttachmentEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAttachmentEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "需求附件上传",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "title": "需求附件所属类型",
                                "type": "string",
                                "enum": ["statement", "progress", "validation"]
                            },
                            "file": {
                                "type": "string",
                                "format": "binary"}},
                        "required": ["product", "build", "file"]
                    }}}}
    })
    def post(self, requirement_id):
        _type = request.form.get("type")
        _file = request.files.get("file")

        if _type not in ["statement", "progress", "validation"]:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="attachment type is not valid"
            )

        if not _file:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="attachment file should be provided"
            )

        try:
            _handler = RequirementItemHandler(requirement_id)
            # 文件头检查 支持大多数类型文件压缩包、execl、markdown等
            verify_flag, res = identify_file_type(_file, FileTypeMapping.case_set_type + FileTypeMapping.test_case_type)
            if verify_flag is False:
                return res
            return _handler.upload_attachment(_type, _file)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAttachmentEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "需求附件删除",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AttachmentFilenameSchema
    })
    def delete(self, requirement_id, body: AttachmentFilenameSchema):
        _type = body.type
        _filename = body.filename
        
        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.delete_attachment(_type, _filename)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
    
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAttachmentEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "获取需求附件",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AttachmentBaseSchema
    })
    def get(self, requirement_id, query: AttachmentBaseSchema):
        _type = query.type
        
        try:
            _handler = RequirementItemHandler(requirement_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        return _handler.get_filelist(_type)


class RequirementItemAttachmentDownload(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAttachmentDownload",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "下载需求附件",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AttachmentFilenameSchema
    })
    def get(self, requirement_id, query: AttachmentFilenameSchema):
        _type = query.type
        _filename = query.filename
        
        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.download_attachment(_type, _filename)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemAttachmentLock(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAttachmentLock",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "锁定需求附件",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AttachmentLockSchema
    })
    def put(self, requirement_id, body: AttachmentLockSchema):
        _type = body.type
        _locked = body.locked

        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.lock_attachment(_type, _locked)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemProgressEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemProgressEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "获取需求进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, requirement_id):
        try:
            _handler = RequirementItemHandler(requirement_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        return _handler.get_progress()
    
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemProgressEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "反馈需求进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ProgressFeedbackSchema
    })
    def post(self, requirement_id, body: ProgressFeedbackSchema):
        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.feedback_progress(body.__dict__)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemProgressEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "编辑需求进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ProgressFeedbackSchema
    })
    def put(self, requirement_id, progress_id, body: ProgressFeedbackSchema):
        try:
            _handler = RequirementItemHandler(requirement_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        return _handler.edit_progress(progress_id, body.__dict__)

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemProgressEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "删除需求进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, requirement_id, progress_id):
        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.delete_progress(progress_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemRewardEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemRewardEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "需求奖励分配",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, requirement_id, body: RequirementItemRewardDivideSchema):
        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.divide_reward(body.strategies)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemAttributorEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemAttributorEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "需求相关人员",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, requirement_id):
        try:
            _handler = RequirementItemHandler(requirement_id)
            return _handler.get_attributors()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementItemPackagesEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementItemPackagesEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "获取需求关联的软件包",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, requirement_id):
        try:
            _handler = RequirementItemHandler(requirement_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        return _handler.get_packages()


class RequirementPackageItemValidateEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementPackageItemValidateEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "批量确认需求关联的软件包",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PackageCompletionSchema
    })
    def post(self, requirement_id, package_id, body: PackageCompletionSchema):
        try:
            _handler = RequirementPackageHandler(requirement_id, package_id)
            return _handler.validate(body.completions)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementPackageItemValidateEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "确认需求关联的软件包",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PackageCompletionSchema
    })
    def put(self, requirement_id, package_id, user_id):
        try:
            _handler = RequirementPackageHandler(requirement_id, package_id)
            return _handler.set_validator(user_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class RequirementPackageItemTaskEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_requirement_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RequirementPackageItemTaskEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_requirement_tag(),  # 当前接口所对应的标签
        "summary": "软件包任务创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PackageTaskCreateSchema
    })
    def post(self, requirement_id, package_id, body: PackageTaskCreateSchema):
        try:
            _handler = RequirementPackageHandler(requirement_id, package_id)
            return _handler.create_relative_task(body.__dict__)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )