import subprocess

import redis
from flask import jsonify, current_app
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model import Milestone, Product
from server.model.qualityboard import QualityBoard, Checklist
from server.utils.db import Delete, Edit, Select, Insert
from server.schema.qualityboard import (
    QualityBoardSchema,
    AddChecklistSchema,
    UpdateChecklistSchema,
    QueryChecklistSchema,
    ATOverviewSchema
)
from server import casbin_enforcer
from server.apps.qualityboard.handlers import OpenqaATStatistic, ChecklistHandler
from server.utils.shell import add_escape


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
        if not milestones:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard cannot be created， because the iteration of the product does not exist."
            )
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


class ChecklistItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, checklist_id):
        return ChecklistHandler.handler_get_one(checklist_id)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, checklist_id, body: UpdateChecklistSchema):
        _body = {
            **body.__dict__,
            "id": checklist_id,
        }

        return Edit(Checklist, _body).single(Checklist, "/checklist")

    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, checklist_id):
        return Delete(Checklist, {"id": checklist_id}).single()


class ChecklistEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: QueryChecklistSchema):
        return ChecklistHandler.handler_get_checklist(query)

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: AddChecklistSchema):
        return Insert(Checklist, body.__dict__).single(Checklist, "/checklist")


class ATOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, qualityboard_id, query: ATOverviewSchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        product = qualityboard.product
        product_name = f"{product.name}-{product.version}"

        scrapyspider_pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"), 
            decode_responses=True
        )
        scrapyspider_redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)

        openqa_url = current_app.config.get("OPENQA_URL")

        _start = (query.page_num - 1) * query.page_size
        _end = query.page_num * query.page_size - 1

        if not query.build_name:
            builds_list = scrapyspider_redis_client.zrange(
                product_name, 
                _start, 
                _end, 
                desc=query.build_order == "descend",
            )

            if not builds_list:
                return jsonify(
                    error_code=RET.OK,
                    error_msg="OK",
                    data=[],
                    total_num=0
                )

            _tests_overview_url = scrapyspider_redis_client.get(f"{product_name}_{builds_list[0]}_tests_overview_url")
            
            # positively sync crawl latest data from openqa of latest build
            exitcode, output = subprocess.getstatusoutput(
                "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "\
                    f"-a product_build={product_name}_{builds_list[0]} "\
                    f"-a openqa_url={openqa_url} "\
                    f"-a tests_overview_url={add_escape(_tests_overview_url)}"
            )
            if exitcode != 0:
                current_app.logger.error(
                    f"crawl latest tests overview data of {product_name}_{builds_list[0]} fail. Because {output}"
                )
            
            return_data = list(
                map(
                    lambda build: OpenqaATStatistic(
                        arches=current_app.config.get("SUPPORTED_ARCHES"),
                        product=product_name,
                        build=build,
                        redis_client=scrapyspider_redis_client,
                    ).group_overview,
                    builds_list
                )
            )

            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=return_data,
                total_num=scrapyspider_redis_client.zcard(product_name)
            )
        
        else:
            product_build = f"{product_name}_{query.build_name}"
            tests_overview_url = scrapyspider_redis_client.get(f"{product_build}_tests_overview_url")

            # positively crawl latest data from openqa of pointed build
            exitcode, output = subprocess.getstatusoutput(
                "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "\
                    f"-a product_build={product_build} "\
                    f"-a openqa_url={openqa_url} "\
                    f"-a tests_overview_url={add_escape(tests_overview_url)}"
            )
            if exitcode != 0:
                current_app.logger.error(f"crawl latest tests overview data of {product_build} fail. Because {output}")
            
            current_app.logger.info(f"crawl latest tests overview data of product {product_build} succeed")

            at_statistic = OpenqaATStatistic(
                arches=current_app.config.get("SUPPORTED_ARCHES", ["aarch64", "x86_64"]),
                product=product_name,
                build=query.build_name,
                redis_client=scrapyspider_redis_client
            )

            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=at_statistic.tests_overview,
            )


class QualityDefendEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, qualityboard_id):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        product = qualityboard.product
        product_name = f"{product.name}-{product.version}"

        scrapyspider_pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"), 
            decode_responses=True
        )
        scrapyspider_redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)

        openqa_url = current_app.config.get("OPENQA_URL")

        _builds = scrapyspider_redis_client.zrange(
            product_name, 
            0, 
            0, 
            desc=True,
        )
        if not _builds:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={"at_statistic": {}}
            )
        
        latest_build = _builds[0]
        _tests_overview_url = scrapyspider_redis_client.get(f"{product_name}_{latest_build}_tests_overview_url")
            
        # positively sync crawl latest data from openqa of latest build
        exitcode, output = subprocess.getstatusoutput(
            "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "\
                f"-a product_build={product_name}_{latest_build} "\
                f"-a openqa_url={openqa_url} "\
                f"-a tests_overview_url={add_escape(_tests_overview_url)}"
        )
        if exitcode != 0:
            current_app.logger.error(
                f"crawl latest tests overview data of {product_name}_{latest_build} fail. Because {output}"
            )
        
        at_statistic = OpenqaATStatistic(
            arches=current_app.config.get("SUPPORTED_ARCHES", ["aarch64", "x86_64"]),
            product=product_name,
            build=latest_build,
            redis_client=scrapyspider_redis_client
        ).group_overview

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "at_statistic": at_statistic,
            }
        )
