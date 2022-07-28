from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model import Milestone, Product
from server.model.qualityboard import QualityBoard
from server.utils.db import Delete, Edit, Select, Insert
from server.schema.qualityboard import QualityBoardUpdateSchema, QualityBoardSchema
from server import casbin_enforcer


class QualityBoardEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: QualityBoardSchema):
        _db = QualityBoard.query.filter_by(product_id=body.product_id).first()
        if _db:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="qualityboard for product {} exist".format(body.product_id)
            )
        _p = Product.query.filter_by(id=body.product_id).first()
        if not _p:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product {} not exist".format(body.product_id)
            )
        milestones = Milestone.query.filter_by(
            product_id=body.product_id,
            type="round",
            is_sync=True
        ).order_by(Milestone.start_time.asc()).all()
        iteration_version = ""
        for _m in milestones:
            iteration_version = iteration_version + "->" + str(_m.id)
        if len(iteration_version) > 0:
            iteration_version = iteration_version[2:]

        qualityboard = QualityBoard(product_id=body.product_id, iteration_version=iteration_version)
        qualityboard.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
            data=qualityboard.to_json()
        )
    
    @auth.login_required()
    @validate()
    def get(self, query: QualityBoardSchema):
        return Select(QualityBoard, query.__dict__).precise()
    
    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, body: QualityBoardSchema):
        return Delete(QualityBoard, body.__dict__).single()


class QualityBoardItemEvent(Resource):
    @auth.login_required()
    @response_collect
    def put(self, qualityboard_id):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )

        milestones = Milestone.query.filter_by(
            product_id=qualityboard.product_id,
            type="round",
            is_sync=True
            ).order_by(Milestone.start_time.asc()).all()
        milestone = None
        for _m in milestones:
            if str(_m.id) in qualityboard.iteration_version:
                continue
            else:
                milestone = _m
                break
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="there is no milestone for next itration."
            )
        iteration_version = ""
        if qualityboard.iteration_version == "":
            iteration_version = str(milestone.id)
        else:
            iteration_version = qualityboard.iteration_version + "->" + str(milestone.id)
        
        qualityboard.iteration_version = iteration_version
        qualityboard.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
            data=qualityboard.to_json()
        )


class QualityBoardDeleteVersionEvent(Resource):
    @auth.login_required()
    @response_collect
    def put(self, qualityboard_id):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        
        if qualityboard.iteration_version == "":
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no iteration version"
            )
        iteration_version = ""
        _versions = qualityboard.iteration_version.split("->")
        if len(_versions) > 1:
            iteration_version = qualityboard.iteration_version.replace("->"+_versions[-1], "")
        _body = {
            "id": qualityboard_id,
            "iteration_version":iteration_version
            }
    
        return Edit(QualityBoard, _body).single()