from flask import jsonify, request
from flask_pydantic import validate
from flask_restful import Resource

from server import casbin_enforcer
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


class RequirementOrgEvent(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    def post(self, org_id, body: RequirmentCreateSchema):
        _body = body.__dict__
        return RequirementHandler.free_publish(org_id, _body)


class RequirementGroupEvent(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
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
    def post(self, body: RequirmentCreateSchema):
        _body = body.__dict__
        return RequirementHandler.publish(
            body=_body,
            publisher_type="person",
        )

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: RequirementQuerySchema):
        return RequirementHandler.get_all(query)
    

class RequirementItemEvent(Resource):
    @auth.login_required()
    @response_collect
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
            return _handler.upload_attachment(_type, _file)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )

    @auth.login_required()
    @response_collect
    @validate()
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
    def delete(self, requirement_id, progress_id):
        try:
            _handler = RequirementItemHandler(requirement_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        return _handler.delete_progress(progress_id)


class RequirementItemRewardEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
    def post(self, requirement_id, package_id, body: PackageTaskCreateSchema):
        try:
            _handler = RequirementPackageHandler(requirement_id, package_id)
            return _handler.create_relative_task(body.__dict__)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )