from math import floor
import subprocess

import redis
from flask import jsonify, current_app
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import func, or_

from server import db
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model import Milestone, Product, Organization
from server.model.milestone import MilestoneGroup
from server.model.qualityboard import (
    QualityBoard, 
    Checklist, 
    DailyBuild,
    RpmCompare, 
    WeeklyHealth,
    FeatureList,
)
from server.utils.db import Delete, Edit, Select, Insert, collect_sql_error
from server.schema.base import PageBaseSchema
from server.schema.qualityboard import (
    FeatureListQuerySchema,
    PackageCompareQuerySchema,
    PackageListQuerySchema,
    QualityBoardSchema,
    AddChecklistSchema,
    UpdateChecklistSchema,
    QueryChecklistSchema,
    ATOverviewSchema,
)
from server.apps.qualityboard.handlers import ChecklistHandler, PackageListHandler, feature_list_handlers
from server.utils.shell import add_escape
from server.utils.at_utils import OpenqaATStatistic
from server.utils.page_util import PageUtil
from server.utils.rpm_util import RpmNameLoader
from celeryservice.tasks import resolve_pkglist_after_resolve_rc_name


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

        # 启动爬取正式发布版本的软件包清单
        resolve_pkglist_after_resolve_rc_name.delay(
            repo_url=current_app.config.get("OPENEULER_DAILYBUILD_REPO_URL"),
            product=f"{_p.name}-{_p.version}",
        )

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

        # 启动爬取对应迭代版本的软件包清单
        resolve_pkglist_after_resolve_rc_name.delay(
            repo_url=current_app.config.get("OPENEULER_DAILYBUILD_REPO_URL"),
            product=f"{milestone.product.name}-{milestone.product.version}",
            _round=len(qualityboard.iteration_version.split('->')),
        )

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
                scrapyspider_pool.disconnect()
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

            scrapyspider_pool.disconnect()

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
            
            scrapyspider_pool.disconnect()

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
        _arches = current_app.config.get("SUPPORTED_ARCHES", ["aarch64", "x86_64"])

        scrapyspider_pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"), 
            decode_responses=True
        )
        scrapyspider_redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)

        latest_dailybuild = DailyBuild.query.filter(
            DailyBuild.product_id==product.id
        ).order_by(
            DailyBuild.create_time.desc()
        ).first()
        dailybuild_statistic = latest_dailybuild.to_json() if latest_dailybuild else None

        latest_weekly_health = WeeklyHealth.query.order_by(
            WeeklyHealth.end_time.desc()
        ).first()

        _health_rate = None
        if latest_weekly_health:
            _health_rate = latest_weekly_health.get_statistic(
                scrapyspider_pool, 
                _arches
            ).get("health_rate")

        weeklybuild_statistic = {
            "health_rate": _health_rate,
            # 临时返回值
            "health_baseline": 100,
        }

        openqa_url = current_app.config.get("OPENQA_URL")

        _builds = scrapyspider_redis_client.zrange(
            product_name, 
            0, 
            0, 
            desc=True,
        )
        if not _builds:
            scrapyspider_pool.disconnect()
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
            arches=_arches,
            product=product_name,
            build=latest_build,
            redis_client=scrapyspider_redis_client
        ).group_overview

        scrapyspider_pool.disconnect()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "at_statistic": at_statistic,
                "dailybuild_statistic": dailybuild_statistic,
                "weeklybuild_statistic": weeklybuild_statistic
            }
        )


class DailyBuildOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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

        page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get dailybuild page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


class DailyBuildDetail(Resource):
    @auth.login_required()
    @response_collect
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


class WeeklybuildHealthOverview(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
        arches = current_app.config.get("SUPPORTED_ARCHES", ["aarch64", "x86_64"])
        
        def page_func(item):
            weeklybuild_dict = item.to_json(_pool, arches)
            # 临时返回值
            weeklybuild_dict["health_baseline"] = 100
            return weeklybuild_dict

        page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
        _pool.disconnect()
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get health of weeklybuild page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)
        

class WeeklybuildHealthEvent(Resource):
    @auth.login_required()
    @response_collect
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
        arches = current_app.config.get("SUPPORTED_ARCHES", ["aarch64", "x86_64"])
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


class FeatureListEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    def get(self, qualityboard_id, query: FeatureListQuerySchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )
        if not qualityboard.feature_list and qualityboard.product:
            org_id = qualityboard.product.org_id
            org = Organization.query.filter_by(id=org_id).first()
            feature_list_handler = feature_list_handlers.get(org.name)
            if not feature_list_handler:
                feature_list_handler = feature_list_handlers.get("default")
            
            handler = feature_list_handler(FeatureList)
            if query.new:
                md_content = handler.get_md_content(f"{qualityboard.product.name}-{qualityboard.product.version}")
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
                handler.store(qualityboard_id)
            else:
                # 社区暂未统一继承特性的定义
                pass

        feature_list = FeatureList.query.filter_by(qualityboard_id=qualityboard_id, is_new=query.new).all()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[feature.to_json() for feature in feature_list],
        )


class FeatureListSummary(Resource):
    @auth.login_required
    @response_collect
    def get(self, qualityboard_id):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(qualityboard_id)
            )

        addition_feature_count = db.session.query(func.count(FeatureList.id)).filter_by(
            qualityboard_id=qualityboard_id, 
            is_new=True
        ).scalar()
        _addition_feature_finish_count = db.session.query(func.count(FeatureList.id)).filter_by(
            qualityboard_id=qualityboard_id, 
            is_new=True, 
            done=True
        ).scalar()
        addition_feature_rate = 0
        if addition_feature_count != 0:
            addition_feature_rate = floor(_addition_feature_finish_count / addition_feature_count * 100)

        inherit_feature_count = db.session.query(func.count(FeatureList.id)).filter_by(
            qualityboard_id=qualityboard_id, 
            is_new=False
        ).scalar()
        _inherit_feature_finish_count = db.session.query(func.count(FeatureList.id)).filter_by(
            qualityboard_id=qualityboard_id, 
            is_new=False, 
            done=True
        ).scalar()
        inherit_feature_rate = 0
        if inherit_feature_count != 0:
         inherit_feature_rate = floor(_inherit_feature_finish_count / inherit_feature_count * 100)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "addition_feature_count": addition_feature_count,
                "addition_feature_rate": addition_feature_rate,
                "inherit_feature_count": inherit_feature_count,
                "inherit_feature_rate": inherit_feature_rate,
            }
        )


class PackageListEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self, qualityboard_id, milestone_id, query: PackageListQuerySchema):
        try:
            handler = PackageListHandler(
                qualityboard_id,
                milestone_id,
                query.refresh
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.OK,
                error_msg=str(e),
            )
        except ValueError as e:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=str(e),
            )

        _pkgs = handler.packages
        pkgs_dict = RpmNameLoader.rpmlist2rpmdict(_pkgs)

        if query.summary:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={
                    "name": handler.milestone.name,
                    "size": len(pkgs_dict)
                },
            )
        
        return jsonify(
           error_code=RET.OK,
           error_msg="OK",
           data=[ pkg.to_dict() for pkg in pkgs_dict.values() ], 
        )


class PackageListCompareEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def post(self, qualityboard_id, comparee_milestone_id, comparer_milestone_id):
        try:
            comparer = PackageListHandler(
                qualityboard_id,
                comparer_milestone_id,
                False
            )
            comparee = PackageListHandler(
                qualityboard_id,
                comparee_milestone_id,
                False
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

        compare_results = comparer.compare(comparee.packages)
        
        milestone_group = MilestoneGroup.query.filter_by(
            milestone_1_id=comparee_milestone_id,
            milestone_2_id=comparer_milestone_id,
        ).first()
        milestone_group_id = None
        if not milestone_group:
            milestone_group_id = Insert(
                MilestoneGroup,
                {
                    "milestone_1_id": comparee_milestone_id,
                    "milestone_2_id": comparer_milestone_id
                }
            ).insert_id()
        else:
            milestone_group_id = milestone_group.id

        for result in compare_results:
            _ = Insert(
                RpmCompare, 
                {
                    "arch": result.get("arch"),
                    "rpm_comparee": result.get("rpm_list_1"),
                    "rpm_comparer": result.get("rpm_list_2"),
                    "compare_result": result.get("compare_result"),
                    "milestone_group_id": milestone_group_id,
                }
            ).single()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    @auth.login_required
    @response_collect
    @validate()
    def get(self, qualityboard_id, comparer_milestone_id, comparee_milestone_id, query: PackageCompareQuerySchema):
        milestone_group = MilestoneGroup.query.filter_by(
            milestone_1_id=comparee_milestone_id,
            milestone_2_id=comparer_milestone_id,
        ).first()
        if not milestone_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no comparation record for milestone {} and milestone {}".format(
                    comparee_milestone_id,
                    comparer_milestone_id
                )
            )
        
        _add_num = db.session.query(
            func.count(RpmCompare.id)
        ).filter(
            RpmCompare.milestone_group_id == milestone_group.id,
            RpmCompare.compare_result == "ADD"
        ).scalar()
        _del_num = db.session.query(
            func.count(RpmCompare.id)
        ).filter(
            RpmCompare.milestone_group_id == milestone_group.id,
            RpmCompare.compare_result == "DEL"
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
            RpmCompare.milestone_group_id == milestone_group.id
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