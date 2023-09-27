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

import subprocess
import json

import yaml
import redis
from flask import jsonify, current_app, g, request
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db, redis_client, swagger_adapt
from server.utils.auth_util import auth
from server.utils.redis_util import RedisKey
from server.utils.response_util import response_collect, RET
from server.model import Milestone, Product, Organization
from server.model.milestone import IssueSolvedRate
from server.model.strategy import ReProductFeature
from server.model.qualityboard import (
    RpmCompare,
    SameRpmCompare, 
    QualityBoard,
    Checklist,
    DailyBuild,
    WeeklyHealth,
    Feature,
    CheckItem,
    Round,
    RoundGroup,
    RepeatRpm,
)
from server.utils.db import Delete, Select, Insert, collect_sql_error
from server.schema.base import PageBaseSchema
from server.schema.qualityboard import (
    FeatureQuerySchema,
    PackageCompareSchema,
    PackageCompareQuerySchema,
    RoundIssueQueryV8,
    RoundToMilestone,
    RoundUpdateSchema,
    CompareRoundUpdateSchema,
    SamePackageCompareQuerySchema,
    PackageListQuerySchema,
    QualityBoardSchema,
    QualityBoardUpdateSchema,
    AddChecklistSchema,
    UpdateChecklistSchema,
    QueryChecklistSchema,
    ATOverviewSchema,
    CheckItemSchema,
    QueryCheckItemSchema,
    QueryQualityResultSchema,
    DeselectChecklistSchema,
    QueryRound,
    QueryRpmCheckSchema,
    PackageCompareResult,
    SamePackageCompareResult,
    QueryRepeatRpmSchema,
    DailyBuildPackageCompareSchema,
    DailyBuildSchema,
    DailyBuildBaseSchema,
    DailyBuildPackageCompareQuerySchema,
    DailyBuildPackageCompareResultSchema,
)
from server.apps.qualityboard.handlers import (
    ChecklistHandler,
    PackageListHandler,
    DailyBuildPackageListHandler,
    feature_handlers,
    CheckItemHandler,
    QualityResultCompareHandler,
    RoundHandler,
    ChecklistResultHandler,
    CompareRoundHandler,
    PackagCompareResultExportHandler,
    ReportHandler, ATOverviewHandler, ATReportHandler
)
from server.apps.issue.handler import GiteeV8BaseIssueHandler
from server.utils.shell import add_escape
from server.utils.at_utils import OpenqaATStatistic
from server.utils.page_util import PageUtil, Paginate
from server.utils.rpm_util import RpmNameLoader
from celeryservice.sub_tasks import update_compare_result, update_samerpm_compare_result, update_daily_compare_result


def get_quality_board_tag():
    return {
        "name": "质量看板",
        "description": "质量看板相关接口",
    }


class QualityBoardEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityBoardEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "创建质量看板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": QualityBoardSchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: QualityBoardSchema):
        _db = QualityBoard.query.filter_by(product_id=body.product_id).first()
        if _db:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="qualityboard for product {} exist".format(
                    body.product_id)
            )
        _p = Product.query.filter_by(id=body.product_id).first()
        if not _p:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product {} not exist".format(body.product_id)
            )
        milestone = Milestone.query.filter(
            Milestone.product_id == body.product_id,
            Milestone.type == "round",
            Milestone.is_sync.is_(True),
            Milestone.name.like(f'%round-1%')
        ).first()
        iteration_version = ""
        if milestone:
            round_id = RoundHandler.add_round(body.product_id, milestone.id)
            iteration_version = str(round_id)
            PackageListHandler.get_all_packages_file(round_id)

        qualityboard = QualityBoard(
            product_id=body.product_id, iteration_version=iteration_version)
        qualityboard.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
            data=qualityboard.to_json()
        )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityBoardEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取质量看板信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QualityBoardSchema,  # 当前接口请求体参数schema校验器
    })
    def get(self, query: QualityBoardSchema):
        return Select(QualityBoard, query.__dict__).precise()

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityBoardEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "删除质量看板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QualityBoardSchema,  # 当前接口请求体参数schema校验器
    })
    def delete(self, body: QualityBoardSchema):
        return Delete(QualityBoard, body.__dict__).single()


class QualityBoardItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityBoardItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "质量看板发布",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": QualityBoardUpdateSchema,  # 当前接口请求体参数schema校验器
    })
    def put(self, qualityboard_id, body: QualityBoardUpdateSchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        current_round_id = qualityboard.iteration_version.split("->")[-1]
        milestone = None
        iteration_version = ""
        if body.released:
            milestone = Milestone.query.filter_by(
                product_id=qualityboard.product_id,
                type="release",
                is_sync=True,
            ).order_by(Milestone.start_time.asc()).first()
            if not milestone:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="the released milestone does not exist."
                )
            if qualityboard.iteration_version == "":
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="the product cannot be released because the itration has not ended."
                )
            qualityboard.released = body.released
        else:
            if current_round_id == "":
                round_num = 1
            else:
                _round = Round.query.filter_by(id=current_round_id).first()
                round_num = _round.round_num + 1
            milestone = Milestone.query.filter(
                Milestone.product_id == qualityboard.product_id,
                Milestone.type == "round",
                Milestone.is_sync.is_(True),
                Milestone.name.like(f'%round-{round_num}%')
            ).first()

            if not milestone:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="there is no milestone for next itration."
                )
        round_id = RoundHandler.add_round(qualityboard.product_id, milestone.id)
        if qualityboard.iteration_version == "":
            iteration_version = str(round_id)
        else:
            iteration_version = qualityboard.iteration_version + \
                "->" + str(round_id)

        qualityboard.iteration_version = iteration_version
        qualityboard.add_update()
        PackageListHandler.get_all_packages_file(round_id)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
            data=qualityboard.to_json()
        )


class QualityBoardDeleteVersionEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityBoardDeleteVersionEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "返回上一迭代版本",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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
            iteration_version = qualityboard.iteration_version.replace(
                "->"+_versions[-1], "")
        if iteration_version == "":
            return Delete(QualityBoard, {"id": qualityboard_id}).single()
        qualityboard.iteration_version = iteration_version
        qualityboard.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )


class DeselectChecklistItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DeselectChecklistItem",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "取消选中checklist",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DeselectChecklistSchema
    })
    def put(self, checklist_id, body: DeselectChecklistSchema):
        _cl = Checklist.query.filter_by(id=checklist_id).first()
        if not _cl:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checklist {} doesn't exist".format(checklist_id)
            )
        if body.rounds == "1" and _cl.rounds == "1":
            _cl.delete()
            return jsonify(
                error_code=RET.OK,
                error_msg="OK."
            )
        idx = body.rounds.index("1")
        if idx < len(_cl.rounds) - 1:
            _cl.rounds = _cl.rounds[:idx] + "0" + _cl.rounds[idx + 1:]
            bls = _cl.baseline.split(",")
            bls[idx] = ""
            _cl.baseline = ",".join(bls)
            ops = _cl.operation.split(",")
            ops[idx] = ""
            _cl.operation = ",".join(ops)
        elif idx == len(_cl.rounds) - 1:
            rounds = _cl.rounds[:-1] + "0"
            baseline = _cl.baseline
            operation = _cl.operation
            while rounds[-1] == "0" and len(rounds) > 1:
                rounds = rounds[:-1]
                baseline = ",".join(baseline.split(",")[:-1])
                operation = ",".join(operation.split(",")[:-1])
            if rounds == "0":
                _cl.delete()
                return jsonify(
                    error_code=RET.OK,
                    error_msg="OK."
                )
            _cl.rounds = rounds
            _cl.baseline = baseline
            _cl.operation = operation
        else:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="rounds '{}' error".format( body.rounds)
            )
        _cl.add_update(Checklist, "/checklist")
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )


class ChecklistItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistItem",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取checklist",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, checklist_id):
        return ChecklistHandler.handler_get_one(checklist_id)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistItem",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "编辑checklist",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateChecklistSchema
    })
    def put(self, checklist_id, body: UpdateChecklistSchema):
        _cl = Checklist.query.filter_by(id=checklist_id).first()
        if not _cl:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checklist {} doesn't exist".format(checklist_id)
            )
        if body.checkitem_id:
            ci = CheckItem.query.filter_by(id=body.checkitem_id).first()
            if not ci:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="Checkitem {} does not exist".format(ci.id)
                )
            _cl = Checklist.query.filter_by(checkitem_id=body.checkitem_id).first()
            if _cl and _cl.id != checklist_id:
                return jsonify(
                    error_code=RET.DB_DATA_ERR,
                    error_msg="Checklist {} has existed".format(ci.title)
                )
        if body.rounds.count("1") > 1:
            _rounds = body.rounds
            r_len = len(_rounds)
            bls = _cl.baseline.split(",")
            bls_len = len(bls)
            ops = _cl.operation.split(",")
            rs = []
            if r_len <= bls_len:
                for i in range(r_len):
                    if _rounds[i] == "1":
                        bls[i] = body.baseline
                        ops[i] = body.operation
                        rs += ["1"]
                    else:
                        rs += _cl.rounds[i]
                _cl.rounds = "".join(rs) + _cl.rounds[r_len:]
            else:
                for i in range(bls_len):
                    if _rounds[i] == "1":
                        bls[i] = body.baseline
                        ops[i] = body.operation
                        rs += ["1"]
                    else:
                        rs += _cl.rounds[i]
                for i in range(bls_len, r_len):
                    if _rounds[i] == "1":
                        bls += [body.baseline]
                        ops += [body.operation]
                        rs += ["1"]
                    else:
                        bls += [""]
                        ops += [""]
                        rs += ["0"]
                _cl.rounds = "".join(rs)
            _cl.baseline = ",".join(bls)
            _cl.operation = ",".join(ops)
            _cl.add_update(Checklist, "/checklist")

            return jsonify(
                error_code=RET.OK,
                error_msg="OK."
            )
        idx = body.rounds.index("1")
        if idx < len(_cl.rounds):
            rounds = _cl.rounds[:idx] + "1" + _cl.rounds[idx + 1:]
            baseline = _cl.baseline
            operation = _cl.operation
            
            if body.baseline:
                bls = _cl.baseline.split(",")
                bls[idx] = body.baseline
                baseline = ",".join(bls)
            if body.operation:
                ops = _cl.operation.split(",")
                ops[idx] = body.operation
                operation = ",".join(ops)
        elif idx == len(_cl.rounds):
            if body.baseline is None or body.operation is None:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="iteration must have baseline and operation"
                )
            rounds = _cl.rounds + "1"
            baseline = _cl.baseline + "," + body.baseline
            operation = _cl.operation + "," + body.operation
        else:
            if body.baseline is None or body.operation is None:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="iteration must have baseline and operation"
                )
            rounds = _cl.rounds.ljust(idx, "0") + "1"
            baseline = _cl.baseline + "," * (idx + 1 - len(_cl.rounds)) + body.baseline
            operation = _cl.operation + "," * (idx + 1 - len(_cl.rounds)) + body.operation
        
        _body = body.__dict__
        _body.update({
            "rounds": rounds,
            "baseline": baseline,
            "operation": operation
        })
        for key, value in _body.items():
            if value is not None:
                setattr(_cl, key, value)
        _cl.add_update(Checklist, "/checklist")
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistItem",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "删除checklist",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, checklist_id):
        return Delete(Checklist, {"id": checklist_id}).single()


class ChecklistEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页获取checklist",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryChecklistSchema
    })
    def get(self, query: QueryChecklistSchema):
        return ChecklistHandler.handler_get_checklist(query)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "创建checklist",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AddChecklistSchema
    })
    def post(self, body: AddChecklistSchema):
        ci = CheckItem.query.filter_by(id=body.checkitem_id).first()
        if not ci:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="Checkitem {} does not exist".format(ci.id)
            )

        _p = Product.query.filter_by(id=body.product_id, is_forced_check=True).first()
        if not _p:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product {} doesn't exist, or doesn't need to be checked".format(body.product_id)
            )
        
        _cl = Checklist.query.filter(
            Checklist.checkitem_id == body.checkitem_id,
            Checklist.product_id == _p.id,
        ).first()
        if _cl:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checklist {} for {} product has existed".format(ci.title, _p.name)
            )
        cl = Insert(Checklist, body.__dict__).insert_obj(Checklist, "/checklist")
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )


class ChecklistRoundsCountEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistRoundsCountEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取checklist最大rounds数",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryChecklistSchema
    })
    def get(self, query: QueryChecklistSchema):
        _p = Product.query.filter_by(id=query.product_id).first()
        if not _p:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product {} not exist".format(query.product_id)
            )
        count = db.session.query(func.max(func.length(Checklist.rounds))).filter(
            Checklist.product_id == query.product_id
        ).scalar()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            count=count
        )


class CheckItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CheckItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页查询check检查项",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryCheckItemSchema
    })
    def get(self, query: QueryCheckItemSchema):
        return CheckItemHandler.get_all(query)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CheckItemEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "创建check检查项",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": QueryCheckItemSchema
    })
    def post(self, body: CheckItemSchema):
        _ci = CheckItem.query.filter(
            or_(
                CheckItem.title == body.title,
                CheckItem.field_name == body.field_name
            )
        ).first()
        if _ci:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checkitem has existed."
            )
        return Insert(CheckItem, body.__dict__).single(CheckItem, "/checkitem")


class CheckItemSingleEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CheckItemSingleEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "check检查项详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, checkitem_id):
        _ci = CheckItem.query.filter_by(id=checkitem_id).first()
        if not _ci:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checkitem does not existed."
            )

        return Select(CheckItem, {"id": checkitem_id}).single()

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CheckItemSingleEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "编辑check检查项",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CheckItemSchema
    })
    def put(self, checkitem_id, body: CheckItemSchema):
        _ci = CheckItem.query.filter_by(
            id=checkitem_id
        ).first()
        if not _ci:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="Checkitem doesn't exist."
            )
        _ci = CheckItem.query.filter(
            or_(
                CheckItem.title == body.title,
                CheckItem.field_name == body.field_name
            )
        ).first()
        if _ci and _ci.id != checkitem_id:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checkitem has existed."
            )

        _body = body.__dict__
        for key, value in _body.items():
            if value is not None:
                setattr(_ci, key, value)
        _ci.add_update(CheckItem, "/checkitem")
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CheckItemSingleEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "删除check检查项",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, checkitem_id):
        _ci = CheckItem.query.filter_by(id=checkitem_id).first()
        if not _ci:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checkitem does not existed."
            )
        _cl = Checklist.query.filter_by(checkitem_id=checkitem_id).first()
        if _cl:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="Deletion failed because this check item is used."
            )
        return Delete(CheckItem, {"id": checkitem_id}).single()


class ChecklistResultEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ChecklistResultEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取当前round版本的checklist结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, round_id):
        _round = Round.query.filter_by(id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round {} does not exist".format(round_id)
            )
        data = []
        issue_data = ChecklistResultHandler.get_issue_checklist_result(round_id)
        data += issue_data

        # add other checklist result to data

        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
            data=data
        )


class ATOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ATOverview",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "AT总览",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ATOverviewSchema
    })
    def get(self, qualityboard_id, query: ATOverviewSchema):
        return ATOverviewHandler(qualityboard_id=qualityboard_id).get_overview(query.__dict__)


class QualityDefendEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityDefendEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取质量防护数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, qualityboard_id):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        product = qualityboard.product
        
        product_name = f"{product.name}-{product.version}"
        _arches = current_app.config.get(
            "SUPPORTED_ARCHES", ["aarch64", "x86_64"]
        )

        scrapyspider_pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"),
            decode_responses=True
        )
        scrapyspider_redis_client = redis.StrictRedis(
            connection_pool=scrapyspider_pool
            )
        qrsh = QualityResultCompareHandler("product", product.id)
        

        latest_dailybuild = DailyBuild.query.filter(
            DailyBuild.product_id == product.id
        ).order_by(
            DailyBuild.create_time.desc()
        ).first()
        dailybuild_statistic = dict()
        if latest_dailybuild:
            dailybuild_statistic.update(
                {
                    "completion": latest_dailybuild.completion,
                    "passed": qrsh.compare_result_baseline("at_statistic", latest_dailybuild.completion)
                }
            )

        latest_weekly_health = WeeklyHealth.query.order_by(
            WeeklyHealth.end_time.desc()
        ).first()

        weeklybuild_statistic = dict()
        if latest_weekly_health:
            _health_rate = latest_weekly_health.get_statistic(
                scrapyspider_pool,
                _arches
            ).get("health_rate")
            weeklybuild_statistic.update({
                "health_rate": _health_rate,
                "health_passed": qrsh.compare_result_baseline(
                    "weeklybuild_statistic", _health_rate
                ),
            })

        openqa_url = current_app.config.get("OPENQA_URL")

        _builds = scrapyspider_redis_client.zrange(
            product_name,
            0,
            0,
            desc=True,
        )
        at_statistic = dict()

        if _builds:
            latest_build = _builds[0]
            _tests_overview_url = scrapyspider_redis_client.get(
                f"{product_name}_{latest_build}_tests_overview_url"
            )

            # positively sync crawl latest data from openqa of latest build
            exitcode, output = subprocess.getstatusoutput(
                "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "
                f"-a product_build={product_name}_{latest_build} "
                f"-a openqa_url={openqa_url} "
                f"-a tests_overview_url={add_escape(_tests_overview_url)}"
            )
            if exitcode != 0:
                current_app.logger.error(
                    f"crawl latest tests overview data of {product_name}_{latest_build} fail. Because {output}"
                )

            _at_statistic = OpenqaATStatistic(
                arches=_arches,
                product=product_name,
                build=latest_build,
                redis_client=scrapyspider_redis_client
            ).group_overview
            _total = _at_statistic.get("total")
            _success = _at_statistic.get("success")
            if int(_total) == 0:
                at_rate = "100%"
            else:
                at_rate = int(_success) / int(_total)
                at_rate = "%.f%%" % (at_rate * 100)
            at_statistic.update(
                {
                    "total": _at_statistic.get("total"),
                    "success": _at_statistic.get("success"),
                    "passed": qrsh.compare_result_baseline("at_statistic", at_rate)
                }
            )

        scrapyspider_pool.disconnect()
        
        latest_rpmcheck__data = dict()
        rpmcheck_latest_key = f"rpmcheck_{product.name}-{product.version}_latest"
        _rpmcheck_latest = redis_client.keys(
            rpmcheck_latest_key
        )
        if _rpmcheck_latest:
            latest_rpmcheck__data.update(
                {
                    "all_cnt": redis_client.hget(rpmcheck_latest_key, "all_cnt"),
                    "succeeded_rate": redis_client.hget(rpmcheck_latest_key, "succeeded_rate"),
                    "name": redis_client.hget(rpmcheck_latest_key, "name"),
                }
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "at_statistic": at_statistic,
                "dailybuild_statistic": dailybuild_statistic,
                "weeklybuild_statistic": weeklybuild_statistic,
                "rpmcheck_statistic": latest_rpmcheck__data,
            }
        )


class DailyBuildOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildOverview",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页展示每日构建总览",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PageBaseSchema
    })
    def get(self, qualityboard_id, query: PageBaseSchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        query_filter = DailyBuild.query.filter(
            DailyBuild.product_id == qualityboard.product.id
        ).order_by(
            DailyBuild.create_time.desc()
        )

        def page_func(item):
            qualityboard_dict = item.to_json()
            return qualityboard_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func
        )
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get dailybuild page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


class DailyBuildDetail(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildDetail",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "每日构建详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, dailybuild_id):
        dailybuild = DailyBuild.query.filter_by(id=dailybuild_id).first()
        if not dailybuild:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="build {} not exitst".format(dailybuild_id)
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "name": dailybuild.name,
                "detail": dailybuild.detail,
            }
        )


class RpmCheckOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RpmCheckOverview",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "rpm检查总览",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, qualityboard_id, query: PageBaseSchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        _prouduct = Product.query.filter_by(
            id=qualityboard.product.id
        ).first()
        latest_data = dict()
        rpmcheck_latest_key = f"rpmcheck_{_prouduct.name}-{_prouduct.version}_latest"
        _rpmcheck_latest = redis_client.keys(
            rpmcheck_latest_key
        )
        if _rpmcheck_latest:
            latest_data.update(
                {
                    "all_cnt": redis_client.hget(rpmcheck_latest_key, "all_cnt"),
                    "succeeded_rate": redis_client.hget(rpmcheck_latest_key, "succeeded_rate"),
                    "name": redis_client.hget(rpmcheck_latest_key, "name"),
                }
            )
        _rpmchecks = redis_client.keys(
            f"rpmcheck_{_prouduct.name}-{_prouduct.version}_2*"
        )
        data = list()

        for _rpmcheck in _rpmchecks:
            _data = redis_client.hget(
                _rpmcheck, "data"
            )
            _data = _data[1:-1].replace(
                "\'", "\"").replace("}, {", "}#{").split("#")
            data_t = list()
            for _dat in _data:
                data_t.append(json.loads(_dat))
            data.append(
                {
                    "name": _rpmcheck,
                    "all_cnt": redis_client.hget(_rpmcheck, "all_cnt"),
                    "build_time": _rpmcheck.split("_")[-1],
                    "data": data_t,
                }
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data,
            latest_data=latest_data,
        )


class RpmCheckDetailEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RpmCheckDetailEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "rpm检查详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryRpmCheckSchema
    })
    def get(self, query: QueryRpmCheckSchema):
        _rpmcheck = redis_client.keys(
            query.name
        )
        if len(_rpmcheck) <= 0:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"no rpmcheck info of {query.name}."
            )
        rpmcheck_path = current_app.config.get("RPMCHECK_FILE_PATH")
        row_num = int(current_app.config.get("RPMCHECK_RESULT_ROWS_NUM"))
        if row_num <= 0:
            return jsonify(
                error_code=RET.SYS_CONF_ERR,
                error_msg=f"the value of RPMCHECK_RESULT_ROWS_NUM must be greater than 0."
            )
            
        file_name = f"{rpmcheck_path}/{query.name}.yaml"
        exitcode, total = subprocess.getstatusoutput(
            f"wc -l {file_name}" + " | awk '{print $1}'"
        )
        
        if exitcode != 0:
            return jsonify(
                error_code=RET.FILE_ERR,
                error_msg=f"get rpmcheck data failed."
            )

        def get_part_file_data(start, end, file_name):
            exitcode, content = subprocess.getstatusoutput(
                f"sed -n '{start},{end}p' {file_name}"
            )
            return exitcode, content
  
        exitcode, content = get_part_file_data(
            (query.page_num - 1) * query.page_size * row_num + 1,
            query.page_num * query.page_size * row_num,
            file_name
        )
        if exitcode != 0:
            return jsonify(
                error_code=RET.FILE_ERR,
                error_msg=f"get rpmcheck data failed."
            )

        content = yaml.safe_load(content)
        content, e = Paginate.get_page_dict(
            total=int(int(total) / row_num),
            data=content,
            page_num=query.page_num,
            page_size=query.page_size
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f"get rpmcheck page error: {e}"
            )

        return jsonify(error_code=RET.OK, error_msg="OK", data=content)


class WeeklybuildHealthOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "WeeklybuildHealthOverview",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "每周构建健康度总览",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PageBaseSchema
    })
    def get(self, qualityboard_id, query: PageBaseSchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        query_filter = WeeklyHealth.query.filter(
            WeeklyHealth.product_id == qualityboard.product.id
        ).order_by(
            WeeklyHealth.create_time.desc()
        )

        _pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"),
            decode_responses=True
        )
        arches = current_app.config.get(
            "SUPPORTED_ARCHES", ["aarch64", "x86_64"])

        def page_func(item):
            weeklybuild_dict = item.to_json(_pool, arches)
            # 临时返回值
            weeklybuild_dict["health_baseline"] = 100
            return weeklybuild_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func)
        _pool.disconnect()
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get health of weeklybuild page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


class WeeklybuildHealthEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "WeeklybuildHealthEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "每周构建健康度详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, weeklybuild_id):
        weekly_health = WeeklyHealth.query.filter_by(id=weeklybuild_id).first()
        if not weekly_health:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="weeklyhealth {} not exitst".format(weeklybuild_id)
            )

        if not weekly_health.daily_records:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=[],
            )

        scrapyspider_pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"),
            decode_responses=True
        )
        arches = current_app.config.get(
            "SUPPORTED_ARCHES", ["aarch64", "x86_64"]
        )
        return_data = [
            record.to_health_json(
                scrapyspider_pool,
                arches
            ) for record in weekly_health.daily_records
        ]
        scrapyspider_pool.disconnect()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=return_data
        )


class FeatureEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": FeatureQuerySchema
    })
    def get(self, qualityboard_id, query: FeatureQuerySchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        if qualityboard.product:
            org_id = qualityboard.product.org_id
            org = Organization.query.filter_by(id=org_id).first()
            feature_handler = feature_handlers.get(org.name)
            if not feature_handler:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"feature adapter for {org.name} \
                        does not exist.please contact the administrator in time."
                )

            handler = feature_handler(
                Feature, 
                ReProductFeature, 
                product_id = qualityboard.product_id
            )
            if query.new:
                md_content = handler.get_md_content(
                    f"{qualityboard.product.name}-{qualityboard.product.version}"
                )
                if not md_content:
                    return jsonify(
                        error_code=RET.NO_DATA_ERR,
                        error_msg="there is no release plan of {}-{} of {}".format(
                            qualityboard.product.name,
                            qualityboard.product.version,
                            org.name
                        )
                    )
                handler.resolve(md_content)
                try:
                    handler.store()
                except (IntegrityError, SQLAlchemyError, TypeError) as e:
                    return jsonify(
                        error_code=RET.RUNTIME_ERROR,
                        error_msg=str(e)
                    )
            else:
                # 社区暂未统一继承特性的定义
                pass

        features = Feature.query.join(ReProductFeature).filter( 
            ReProductFeature.product_id == qualityboard.product_id,
            ReProductFeature.is_new == query.new,
            ReProductFeature.feature_id == Feature.id
        ).all()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[feature.to_json() for feature in features],
        )


class FeatureSummary(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureSummary",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "特性总览",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, qualityboard_id):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )

        addition_feature_summary = dict()
        inherit_feature_summary = dict()

        if qualityboard.product:
            org_id = qualityboard.product.org_id
            org = Organization.query.filter_by(id=org_id).first()
            feature_handler = feature_handlers.get(org.name)
            if not feature_handler:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"feature adapter for {org.name}\
                         does not exist.please contact the administrator in time."
                )

            handler = feature_handler(
                Feature, 
                ReProductFeature, 
                product_id = qualityboard.product_id
            )
            addition_feature_summary = handler.statistic(_is_new=True)
            inherit_feature_summary = handler.statistic(_is_new=False)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "addition_feature_summary": addition_feature_summary,
                "inherit_feature_summary": inherit_feature_summary
            }
        )


class PackageListEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PackageListEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取软件包列表",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PackageListQuerySchema
    })
    def get(self, qualityboard_id, round_id, query: PackageListQuerySchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard doesn't exist.",
            )
        _round = Round.query.get(round_id)
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist.",
            )
        if query.repo_path == "update" and _round.type == "round":
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, round must be release version",
            )
        if query.refresh:
            _round = Round.query.filter_by(id=round_id).first()
            if not _round:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="round doesn't exist.",
                )
            try:
                PackageListHandler.get_all_packages_file(round_id)
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.RUNTIME_ERROR,
                    error_msg=str(e),
                )

            return jsonify(
                error_code=RET.OK,
                error_msg=f"the packages of {_round.name} " \
                f"start resolving, please wait for several minutes"
            )
        arch = "" if query.repo_path == "source" else "all"
        try:
            handler = PackageListHandler(
                round_id,
                query.repo_path,
                arch
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        except ValueError as e:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=str(e),
            )

        _pkgs = handler.packages
        pkgs_dict, _ = RpmNameLoader.rpmlist2rpmdict(_pkgs)

        if query.summary:
            cnt = db.session.query(func.count(RepeatRpm.id)).filter_by(
                round_id=round_id,
                repo_path=query.repo_path,
            ).scalar()
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={
                    "name": _round.name,
                    "size": len(pkgs_dict),
                    "repeat_rpm_cnt": cnt,
                },
            )
        
        return jsonify(
           error_code=RET.OK,
           error_msg="OK",
           data=[ pkg[0].to_dict() for pkg in pkgs_dict.values() ],
        )


class SamePackageListCompareEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SamePackageListCompareEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "同名软件包对比",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PackageCompareSchema
    })
    def post(self, qualityboard_id, round_id, body: PackageCompareSchema):
        _round = Round.query.get(round_id)
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist.",
            )
 
        if body.repo_path == "update" and _round.type == "round":
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, round must be release version",
            )
        compare_key = f"SAME_ROUND_{round_id}_{body.repo_path}_PKG_COMPARE"
        if redis_client.keys(compare_key):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"same pkg compare of round {round_id} is in progress,"
                " please be patient and wait."
            )
        try:
            comparer = PackageListHandler(
                round_id,
                body.repo_path,
                "aarch64"
            )
            comparee = PackageListHandler(
                round_id,
                body.repo_path,
                "x86_64"
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        except ValueError as e:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=str(e),
            )

        #设置锁，避免在比对未完成前，重复触发比对， 比对完成后删除锁
        redis_client.set(compare_key, 1, 2400)

        compare_results = comparer.compare2(comparee.packages)
        update_samerpm_compare_result.delay(round_id, compare_results, body.repo_path)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SamePackageListCompareEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页获取同名软件包对比结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": SamePackageCompareQuerySchema
    })
    def get(self, qualityboard_id, round_id, query: SamePackageCompareQuerySchema):
        _round = Round.query.get(round_id)
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist.",
            )
        if query.repo_path == "update" and _round.type == "round":
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, round must be release version",
            )
        _lack_num = db.session.query(
            func.count(SameRpmCompare.id)
        ).filter(
            SameRpmCompare.round_id == round_id,
            SameRpmCompare.compare_result == "LACK",
            SameRpmCompare.repo_path == query.repo_path
        ).scalar()
        _different_num = db.session.query(
            func.count(SameRpmCompare.id)
        ).filter(
            SameRpmCompare.round_id == round_id,
            SameRpmCompare.compare_result == "DIFFERENT",
            SameRpmCompare.repo_path == query.repo_path
        ).scalar()

        if query.summary:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={
                    "lack_pkgs_num": _lack_num,
                    "different_pkgs_num": _different_num, 
                }
            )

        filter_params = [
            SameRpmCompare.round_id == round_id,
            SameRpmCompare.repo_path == query.repo_path
        ]

        if query.search:
            filter_params.append(
                or_(
                    SameRpmCompare.rpm_x86.like(f"%{query.search}%"),
                    SameRpmCompare.rpm_arm.like(f"%{query.search}%")
                )
            )
        if query.compare_result_list:
            status_filter_params = []
            for result in query.compare_result_list:
                status_filter_params.append(
                    SameRpmCompare.compare_result == result
                )
            filter_params.append(or_(*status_filter_params))
        
        _order = None
        if query.desc:
            _order = [SameRpmCompare.rpm_x86.desc(), SameRpmCompare.rpm_arm.desc()]
        else:
            _order = [SameRpmCompare.rpm_x86.asc(), SameRpmCompare.rpm_arm.asc()]
        
        query_filter = SameRpmCompare.query.filter(*filter_params).order_by(*_order)

        def page_func(item):
            rpm_compare_dict = item.to_json()
            return rpm_compare_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR, error_msg=f"get comparation page error {e}"
            )
        return jsonify(error_code=RET.OK, error_msg="OK", data={
            "lack_pkgs_num": _lack_num,
            "different_pkgs_num": _different_num, 
            **page_dict
        })


class PackageListCompareEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PackageListCompareEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "软件包对比",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PackageCompareSchema
    })
    def post(self, qualityboard_id, comparee_round_id, comparer_round_id, body: PackageCompareSchema):
        round_group = RoundGroup.query.filter_by(
            round_1_id=comparee_round_id,
            round_2_id=comparer_round_id,
        ).first()
        round_group_id = None
        if not round_group:
            round_group_id = Insert(
                RoundGroup,
                {
                    "round_1_id": comparee_round_id,
                    "round_2_id": comparer_round_id
                }
            ).insert_id()
        else:
            round_group_id = round_group.id

        comparee_round = Round.query.get(comparee_round_id)
        comparer_round = Round.query.get(comparer_round_id)
        if body.repo_path == "update" and (comparee_round.type == "round" or comparer_round.type == "round"):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, both comparee_round and comparer_round must be release version",
            )

        compare_key = f"ROUND_GROUP_{round_group_id}_{body.repo_path}_PKG_COMPARE"
        if redis_client.keys(compare_key):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"pkg compare between round {comparee_round_id} and "
                f"round {comparer_round_id} is in progress, please be patient and wait."
            )

        arch = "" if body.repo_path == "source" else "all"
        try:
            comparer = PackageListHandler(
                comparer_round_id,
                body.repo_path,
                arch
            )
            comparee = PackageListHandler(
                comparee_round_id,
                body.repo_path,
                arch
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        except ValueError as e:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=str(e),
            )

        #设置锁时长两个小时，避免在比对未完成前，重复触发比对， 比对完成后删除锁
        redis_client.set(compare_key, 1, 7200)

        (
            compare_results,
            repeat_rpm_list_comparer,
            repeat_rpm_list_comparee,
        ) = comparer.compare(comparee.packages)
        
        round_group = RoundGroup.query.filter_by(
            round_1_id=comparee_round_id,
            round_2_id=comparer_round_id,
        ).first()
        round_group_id = None
        if not round_group:
            round_group_id = Insert(
                RoundGroup,
                {
                    "round_1_id": comparee_round_id,
                    "round_2_id": comparer_round_id
                }
            ).insert_id()
        else:
            round_group_id = round_group.id

        def add_repeat_rpm(repo_path, round_id, rpm_dict_list):
            for rpm in rpm_dict_list:
                _repeat_rpm = RepeatRpm.query.filter(
                    RepeatRpm.rpm_name == rpm.get("rpm_file_name"),
                    RepeatRpm.repo_path == repo_path,
                    RepeatRpm.round_id == round_id,
                ).first()
                if not _repeat_rpm:
                    _repeat_rpm = RepeatRpm(
                        rpm_name=rpm.get("rpm_file_name"),
                        arch=rpm.get("arch"),
                        release=rpm.get("release"),
                        version=rpm.get("version"),
                        repo_path=repo_path,
                        round_id=round_id,
                    )
                    db.session.add(_repeat_rpm)
                    db.session.commit()
        if body.repo_path in ["everything", "EPOL"]:
            add_repeat_rpm(body.repo_path, comparer_round_id, repeat_rpm_list_comparer)
            add_repeat_rpm(body.repo_path, comparee_round_id, repeat_rpm_list_comparee)

        update_compare_result.delay(round_group_id, compare_results, body.repo_path)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PackageListCompareEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页获取软件包对比结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PackageCompareQuerySchema
    })
    def get(self, qualityboard_id, comparer_round_id, comparee_round_id, query: PackageCompareQuerySchema):
        round_group = RoundGroup.query.filter_by(
            round_1_id=comparee_round_id,
            round_2_id=comparer_round_id,
        ).first()
        if not round_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no comparation record for round {} and round {}".format(
                    comparee_round_id,
                    comparer_round_id
                )
            )
        comparee_round = Round.query.get(comparee_round_id)
        comparer_round = Round.query.get(comparer_round_id)
        if query.repo_path == "update" and (comparee_round.type == "round" or comparer_round.type == "round"):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, both comparee_round and comparer_round must be release version",
            )

        _add_num = db.session.query(
            func.count(RpmCompare.id)
        ).filter(
            RpmCompare.round_group_id == round_group.id,
            RpmCompare.compare_result == "ADD",
            RpmCompare.repo_path == query.repo_path
        ).scalar()
        _del_num = db.session.query(
            func.count(RpmCompare.id)
        ).filter(
            RpmCompare.round_group_id == round_group.id,
            RpmCompare.compare_result == "DEL",
            RpmCompare.repo_path == query.repo_path
        ).scalar()

        if query.summary:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={
                    "add_pkgs_num": _add_num,
                    "del_pkgs_num": _del_num, 
                }
            )

        filter_params = [
            RpmCompare.round_group_id == round_group.id,
            RpmCompare.repo_path == query.repo_path
        ]

        if query.arches:
            arches_filter_params = []
            for _arch in query.arches:
                arches_filter_params.append(
                    RpmCompare.arch == _arch
                )
            filter_params.append(or_(*arches_filter_params))
        if query.search:
            filter_params.append(
                or_(
                    RpmCompare.rpm_comparee.like(f"%{query.search}%"),
                    RpmCompare.rpm_comparer.like(f"%{query.search}%")
                )
            )
        if query.compare_result_list:
            status_filter_params = []
            for result in query.compare_result_list:
                status_filter_params.append(
                    RpmCompare.compare_result == result
                )
            filter_params.append(or_(*status_filter_params))
        
        _order = None
        if query.desc:
            _order = [RpmCompare.rpm_comparee.desc(), RpmCompare.rpm_comparer.desc()]
        else:
            _order = [RpmCompare.rpm_comparee.asc(), RpmCompare.rpm_comparer.asc()]
        
        query_filter = RpmCompare.query.filter(*filter_params).order_by(*_order)

        def page_func(item):
            rpm_compare_dict = item.to_json()
            return rpm_compare_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR, error_msg=f"get comparation page error {e}"
            )
        return jsonify(error_code=RET.OK, error_msg="OK", data={
            "add_pkgs_num": _add_num,
            "del_pkgs_num": _del_num, 
            **page_dict
        })


class DailyBuildPackageListCompareEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildPackageListCompareEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "每日构建软件包对比",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DailyBuildPackageCompareSchema
    })
    def post(self, comparer_round_id, body: DailyBuildPackageCompareSchema):
        comparer_round = Round.query.get(comparer_round_id)
        if not comparer_round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"round {comparer_round_id} does not exist.",
            )
        compare_key = f"DAILYBUILD_{body.daily_name}_ROUND_{comparer_round.name}_{body.repo_path}_PKG_COMPARE"
        if redis_client.keys(compare_key):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"pkg compare between {body.daily_name} and "
                f"{comparer_round.name} is in progress, please be patient and wait."
            )

        try:
            comparer = PackageListHandler(
                comparer_round_id,
                body.repo_path,
                "all"
            )
            org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
            repo_url = redis_client.hget(
                RedisKey.daily_build(org_id),
                body.daily_name,
            )
            if repo_url is None:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"daily build {body.daily_name} doesn't exist.",
                )
            comparee = DailyBuildPackageListHandler(
                repo_name=body.daily_name,
                repo_path=body.repo_path,
                arch="all",
                repo_url=repo_url
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        except ValueError as e:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=str(e),
            )

        #设置锁，避免在比对未完成前，重复触发比对， 比对完成后删除锁
        redis_client.set(compare_key, 1, 2400)

        (
            compare_results,
            _,
            repeat_rpm_list_comparee,
        ) = comparer.compare(comparee.packages)

        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        file_path = f"{_path}/{comparer_round.name}-{body.daily_name}-{body.repo_path}.xls"
        update_daily_compare_result.delay(
            body.daily_name,
            comparer_round.name,
            compare_results,
            repeat_rpm_list_comparee,
            file_path
        )
        redis_client.hset(
            f"daily_build_compare_{comparer_round.name}",
            f"{body.daily_name}-{body.repo_path}",
            f"{comparer_round.name}-{body.daily_name}-{body.repo_path}.xls"
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildPackageListCompareEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页获取每日构建软件包对比结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DailyBuildPackageCompareQuerySchema
    })
    def get(self, comparer_round_id, query: DailyBuildPackageCompareQuerySchema):
        comparer_round = Round.query.get(comparer_round_id)
        daily_build_compare_infos = redis_client.hgetall(f"daily_build_compare_{comparer_round.name}")
        data = list()
        if daily_build_compare_infos:
            for daily_name, file_name in daily_build_compare_infos.items():
                if daily_name.endswith(query.repo_path):
                    data.append(
                        {
                            "daily_name": daily_name,
                            "file_name": file_name
                        }
                    )

        if query.paged:
            content, e = Paginate.get_page_dict(
                total=len(data),
                data=data,
                page_num=query.page_num,
                page_size=query.page_size
            )
            if e:
                return jsonify(
                    error_code=RET.SERVER_ERR,
                    error_msg=f"get page error: {e}"
                )
        else:
            content = data[:]

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=content,
        )

    @auth.login_required
    @response_collect
    @validate()
    def delete(self, comparer_round_id, body: DailyBuildPackageCompareResultSchema):
        comparer_round = Round.query.get(comparer_round_id)
        file_name = redis_client.hget(
            f"daily_build_compare_{comparer_round.name}",
            body.compare_name,
        )
        if file_name is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"compre result {body.compare_name} has been deleted",
            )
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        _, _ = subprocess.getstatusoutput(
            f"rm -f {_path}/{file_name}"
        )

        redis_client.hdel(
            f"daily_build_compare_{comparer_round.name}",
            body.compare_name,
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class DailyBuildPkgEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildPkgEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "创建每日构建信息，并获取所有软件包",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DailyBuildSchema
    })
    def post(self, body: DailyBuildSchema):
        try:
            DailyBuildPackageListHandler.get_all_packages_file(body.daily_name, body.repo_url)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        redis_client.hset(
            RedisKey.daily_build(org_id),
            body.daily_name,
            body.repo_url,
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildPkgEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页获取每日构建信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PageBaseSchema
    })
    def get(self, query: PageBaseSchema):
        org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        daily_build_infos = redis_client.hgetall(RedisKey.daily_build(org_id))
        data = list()
        if daily_build_infos:
            for daily_name, repo_url in daily_build_infos.items():
                data.append(
                    {
                        "daily_name": daily_name,
                        "repo_url": repo_url
                    }
                )
        
        if query.paged:
            content, e = Paginate.get_page_dict(
                total=len(data),
                data=data,
                page_num=query.page_num,
                page_size=query.page_size
            )
            if e:
                return jsonify(
                    error_code=RET.SERVER_ERR,
                    error_msg=f"get page error: {e}"
                )
        else:
            content = data[:]

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=content,
        )

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyBuildPkgEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "删除每日构建信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DailyBuildBaseSchema
    })
    def delete(self, body: DailyBuildBaseSchema):
        org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        redis_client.hdel(
            RedisKey.daily_build(org_id),
            body.daily_name,
        )
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        _, _ = subprocess.getstatusoutput(
            f"rm -f {_path}/{body.daily_name}*.pkgs"
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class DailyPackagCompareResultExportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "DailyPackagCompareResultExportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "每日构建软件包对比结果导出",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DailyBuildPackageCompareResultSchema
    })
    def get(self, comparer_round_id, query: DailyBuildPackageCompareResultSchema):
        comparer_round = Round.query.get(comparer_round_id)
        if not comparer_round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist.",
            )

        daily_name = "-".join(query.compare_name.split("-")[:-1])
        repo_path = query.compare_name.split("-")[-1]

        compare_key = f"DAILYBUILD_{daily_name}_ROUND_{comparer_round.name}_{repo_path}_PKG_COMPARE"
        if redis_client.keys(compare_key):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"pkg compare between {daily_name} and "
                f"{comparer_round.name} is in progress, please be patient and wait."
            )

        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        file_path = f"{_path}/{comparer_round.name}-{query.compare_name}.xls"
        result = PackagCompareResultExportHandler().get_compare_result_file(
            file_path=file_path
        )
        return result


class PackagCompareResultExportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PackagCompareResultExportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "软件包对比结果导出",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PackageCompareResult
    })
    def get(self, comparer_round_id, comparee_round_id, query: PackageCompareResult):
        rg = RoundGroup.query.filter_by(
            round_1_id=comparee_round_id,
            round_2_id=comparer_round_id,
        ).first()
        if not rg:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round group does not exist.",
            )
        comparee_round = Round.query.get(comparee_round_id)
        comparer_round = Round.query.get(comparer_round_id)
        if query.repo_path == "update" and (comparee_round.type == "round" or comparer_round.type == "round"):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, both comparee_round and comparer_round must be release version",
            )
        compare_key = f"ROUND_GROUP_{rg.id}_{query.repo_path}_PKG_COMPARE"
        if redis_client.keys(compare_key):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"pkg compare between round {comparee_round_id} and "
                f"round {comparer_round_id} is in progress, please be patient and wait."
            )
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        file_path = f"{_path}/{comparer_round.name}-{comparee_round.name}-{query.repo_path}.xls"
        result = PackagCompareResultExportHandler(
            repo_path=query.repo_path,
            rg=rg,
            arches=query.arches
        ).get_compare_result_file(file_path=file_path, new_result=query.new_result, pkg_type="pkg")
        return result


class SamePackagCompareResultExportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SamePackagCompareResultExportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "同名软件包对比结果导出",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": SamePackageCompareResult
    })
    def get(self, round_id, query: SamePackageCompareResult):
        _round = Round.query.filter_by(
            id=round_id,
        ).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist.",
            )
        if query.repo_path == "update" and _round.type == "round":
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="when repo_path is update, round must be release version",
            )
        compare_key = f"SAME_ROUND_{round_id}_{query.repo_path}_PKG_COMPARE"
        if redis_client.keys(compare_key):
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=f"same pkg compare of round {round_id} is in progress, "
                "please be patient and wait."
            )
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        file_path = f"{_path}/{_round.name}-{query.repo_path}.xls"
        result = PackagCompareResultExportHandler(
            repo_path=query.repo_path,
            round_id=round_id
        ).get_compare_result_file(file_path=file_path, new_result=query.new_result)
        return result


class QualityResultCompare(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityResultCompare",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取issue对比比率",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryQualityResultSchema
    })
    def get(self, query: QueryQualityResultSchema):
        if query.type == "issue":
            qrsh = QualityResultCompareHandler(query.obj_type, query.obj_id)
            ret = qrsh.compare_issue_rate(query.field)
        else:
            #预留接口
            ret = None
            pass
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data = ret
        )


class QualityResult(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QualityResult",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取质量结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id):
        m = Milestone.query.filter_by(id=milestone_id, is_sync=True).first()
        if not m:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone doesn't exist."
            )
        isr = IssueSolvedRate.query.filter_by(milestone_id=milestone_id).first()
        if not isr:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no issue solved rate data."
            )
        param = {
            "serious_resolved_rate": {
                "result": "serious_resolved_rate",
                "passed":"serious_resolved_passed"
            },
            "main_resolved_rate": {
                "result": "main_resolved_rate",
                "passed": "main_resolved_passed",
            },
            "serious_main_resolved_rate": {
                "result": "serious_main_resolved_rate",
                "passed": "serious_main_resolved_passed",
            },
            "current_resolved_rate": {
                "result": "current_resolved_rate",
                "passed": "current_resolved_passed"
            },
            "left_issues_cnt": {
                "result": "left_issues_cnt",
                "passed": "left_issues_passed",
            },
        }
        isr_json = isr.to_json()
        p = Product.query.filter_by(id=m.product_id).first()
        _filter = []
        for k in param.keys():
            _filter.append(CheckItem.field_name == k)
        cls = Checklist.query.join(CheckItem).filter(
            Checklist.products.contains(p),
            or_(*_filter),
            Checklist.checkitem_id == CheckItem.id
        ).all()
        data = dict()
        items = []
        for cl in cls:
            items.append(
                {
                    "check_item": cl.checkitem.title,
                    "baseline": cl.baseline,
                    "operation": cl.operation,
                    "result": isr_json.get(cl.checkitem.field_name),
                    "passed": isr_json.get(param.get(cl.checkitem.field_name).get("passed")),
                }
            )
        data.update(
            {
                "total": len(cls),
                "items": items
            }
        ) 

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data = data
        )


class RoundEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "通过product_id获取所有round",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryRound
    })
    def get(self, query: QueryRound):
        return Select(Round, query.__dict__).precise()


class RoundItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "编辑round名称",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RoundUpdateSchema
    })
    def put(self, round_id, body: RoundUpdateSchema):
        _round = Round.query.filter_by(id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the round does not exist"
            )
        
        _edit_body = body.__dict__
        for key, value in _edit_body.items():
            if value is not None:
                setattr(_round, key, value)
        _round.add_update(Round, "/round")
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )

    @auth.login_required
    @response_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取round详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, round_id):
        _round = Round.query.filter_by(id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the round does not exist"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_round.to_json()
        )


class CompareRoundEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CompareRoundEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "修改当前round的比对round项",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CompareRoundUpdateSchema
    })
    def put(self, round_id, body: CompareRoundUpdateSchema):
        """
        修改当前round的比对round项
        """
        return CompareRoundHandler(round_id).excute(
            body.comparee_round_ids
        )


class RoundMilestoneEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundMilestoneEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "里程碑绑定round",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RoundToMilestone
    })
    def put(self, round_id, body: RoundToMilestone):
        return RoundHandler.bind_round_milestone(round_id, body.milestone_id, body.isbind)


class RoundIssueRateEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundIssueRateEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "更新round issue比率",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, round_id):
        return RoundHandler.update_round_issue_rate(round_id)
    
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundIssueRateEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取round issue比率",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, round_id):
        return RoundHandler.get_rate_by_round(round_id)


class RoundIssueEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundIssueEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取当前round版本的所有issue",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": RoundIssueQueryV8
    })
    def get(self, round_id, query: RoundIssueQueryV8):
        milestones = Milestone.query.filter_by(round_id=round_id, is_sync=True).all()
        if not milestones:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={}
            )
        m_ids = ""
        for milestone in milestones:
            m_ids += str(milestone.gitee_milestone_id) + ","
        m_ids = m_ids[:-1]
        _body = query.__dict__
        _body.update(
            {
                "milestone_id": m_ids,
            }
        )
        return GiteeV8BaseIssueHandler().get_all(_body)


class RoundRepeatRpmEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RoundRepeatRpmEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "分页获取当前round版本的所有重复软件包",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryRepeatRpmSchema
    })
    def get(self, round_id, query: QueryRepeatRpmSchema):
        _round = Round.query.filter_by(id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the round does not exist"
            )

        query_filter = RepeatRpm.query.filter(
            RepeatRpm.round_id == round_id,
            RepeatRpm.repo_path == query.repo_path
        )
        return PageUtil.get_data(query_filter, query)


class ReportEvent(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ReportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取质量报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": [{
            "name": "round_id",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "round id",
            "schema": {"type": "integer"}},
            {
            "name": "branch",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "分支名称",
            "schema": {"type": "string"}}],
    })
    def get(self, product_id):
        return ReportHandler(product_id, request.args).get_quality_report()


class ATReportEvent(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ATReportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "获取AT报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, qualityboard_id):
        return ATReportHandler(qualityboard_id).get_quality_report()


class BranchEvent(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_quality_board_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "BranchEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_quality_board_tag(),  # 当前接口所对应的标签
        "summary": "当前产品下issue关联的所有分支",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": [{
            "name": "round_id",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "round id",
            "schema": {"type": "integer"}},
            {
                "name": "branch",
                "in": "query",
                "required": False,
                "style": "form",
                "explode": True,
                "description": "分支名称",
                "schema": {"type": "string"}}],
    })
    def get(self, product_id):
        return ReportHandler(product_id, request.args).get_branch_list()
