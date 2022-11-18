import subprocess
from datetime import datetime
import redis
from flask import jsonify, current_app, g
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import func, or_
import pytz

from server import db, redis_client
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model import Milestone, Product, Organization
from server.model.milestone import IssueSolvedRate
from server.model.qualityboard import (
    QualityBoard, 
    Checklist, 
    DailyBuild,
    RpmCompare,
    SameRpmCompare, 
    QualityBoard,
    Checklist,
    DailyBuild,
    WeeklyHealth,
    FeatureList,
    CheckItem,
    Round,
    RoundGroup,
)
from server.utils.db import Delete, Edit, Select, Insert, collect_sql_error
from server.schema.base import PageBaseSchema
from server.schema.qualityboard import (
    FeatureListQuerySchema,
    PackageCompareSchema,
    PackageCompareQuerySchema,
    RoundIssueQueryV8,
    RoundIssueRateSchema,
    RoundToMilestone,
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
)
from server.apps.qualityboard.handlers import (
    ChecklistHandler,
    PackageListHandler,
    RoundHandler,
    feature_list_handlers,
    CheckItemHandler,
    QualityResultCompareHandler,
    RoundHandler,
)
from server.apps.milestone.handler import IssueOpenApiHandlerV8
from server.utils.shell import add_escape
from server.utils.at_utils import OpenqaATStatistic
from server.utils.page_util import PageUtil
from server.utils.rpm_util import RpmNameLoader
from celeryservice.tasks import resolve_pkglist_after_resolve_rc_name
from celeryservice.sub_tasks import update_compare_result, update_samerpm_compare_result


class QualityBoardEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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

        qualityboard = QualityBoard(
            product_id=body.product_id, iteration_version=iteration_version)
        qualityboard.add_update()

        # 若为组织/社区里程碑，按组织配置的repo启动爬取正式发布版本的软件包清单
        org_id = _p.org_id
        org = Organization.query.filter_by(id=org_id).first()
        if org:
            if not milestone:
                _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_OFFICIAL_REPO_URL")
                _round = None
            else:
                _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_DAILYBUILD_REPO_URL")
                _round = len(qualityboard.iteration_version.split('->'))
            
            for arch in ["x86_64", "aarch64", "all"]:
                for sub_path in ["everything", "EPOL/main"]:
                    _filename = f"{_p.name}-{_p.version}-round-{_round}-{sub_path.split('/')[0]}-{arch}"
                    if _round is None:
                        _filename = f"{_p.name}-{_p.version}-{sub_path.split('/')[0]}-{self.arch}"
                    if not redis_client.hgetall(f"resolving_{_filename}_pkglist"):
                        redis_client.hset(
                            f"resolving_{_filename}_pkglist", "gitee_id", g.gitee_id
                        )
                        redis_client.hset(
                            f"resolving_{_filename}_pkglist", 
                            "resolve_time", 
                            datetime.now(
                                tz=pytz.timezone('Asia/Shanghai')
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        redis_client.expire(f"resolving_{_filename}_pkglist", 1800)
                        resolve_pkglist_after_resolve_rc_name.delay(
                            repo_url=_pkgs_repo_url,
                            repo_path=sub_path,
                            arch=arch,
                            product=f"{_p.name}-{_p.version}",
                            _round=_round
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
    @validate()
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

        # 若为组织/社区里程碑，按组织配置的repo启动爬取迭代版本的软件包清单
        org_id = milestone.org_id
        org = Organization.query.filter_by(id=org_id).first()
        if org:  

            if milestone.type == "release":
                _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_OFFICIAL_REPO_URL")
                _round = None
            else:
                _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_DAILYBUILD_REPO_URL")
                _round = len(qualityboard.iteration_version.split('->'))
            _product = milestone.product.name + "-" + milestone.product.version
            for arch in ["x86_64", "aarch64", "all"]:
                for sub_path in ["everything", "EPOL/main"]:
                    _filename = f"{_product}-round-{_round}-{sub_path.split('/')[0]}-{arch}"
                    if _round is None:
                        _filename = f"{_product}-{sub_path.split('/')[0]}-{self.arch}"
                    if not redis_client.hgetall(f"resolving_{_filename}_pkglist"):
                        redis_client.hset(
                            f"resolving_{_filename}_pkglist", "gitee_id", g.gitee_id
                        )
                        redis_client.hset(
                            f"resolving_{_filename}_pkglist", 
                            "resolve_time", 
                            datetime.now(
                                tz=pytz.timezone('Asia/Shanghai')
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        redis_client.expire(f"resolving_{_filename}_pkglist", 1800)
                        resolve_pkglist_after_resolve_rc_name.delay(
                            repo_url=_pkgs_repo_url,
                            repo_path=sub_path,
                            arch=arch,
                            product=f"{milestone.product.name}-{milestone.product.version}",
                            _round=_round,
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
            iteration_version = qualityboard.iteration_version.replace(
                "->"+_versions[-1], "")
        if iteration_version == "":
            return Delete(QualityBoard, {"id": qualityboard_id}).single()
        _body = {
            "id": qualityboard_id,
            "iteration_version": iteration_version
        }

        return Edit(QualityBoard, _body).single()


class DeselectChecklistItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, checklist_id, body: DeselectChecklistSchema):
        _cl = Checklist.query.filter_by(id=checklist_id).first()
        if not _cl:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="Checklist {} doesn't exist".format(checklist_id)
            )
        idx = body.rounds.index("1")
        if idx < len(_cl.rounds) - 1:
            _cl.rounds = _cl.rounds[:idx] + "0" + _cl.rounds[idx + 1:]
        elif idx == len(_cl.rounds) - 1:
            rounds = _cl.rounds[:-1] + "0"
            baseline = _cl.baseline
            operation = _cl.operation
            while rounds[-1] == "0" and len(rounds) > 1:
                rounds = rounds[:-1]
                baseline = ",".join(baseline.split(",")[:-1])
                operation = ",".join(operation.split(",")[:-1])
            _cl.rounds = rounds
            _cl.baseline = baseline
            _cl.operation = operation
        else:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="rounds '{}' error".format( body.rounds)
            )
        _cl.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )


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
        
        _body = {
            **body.__dict__,
            "id": checklist_id,
        }
        _body.update({
            "rounds": rounds,
            "baseline": baseline,
            "operation": operation
        })

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
                error_msg="Checklist {} for product {} has existed".format(ci.title, _p.id)
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
    def get(self, query: QueryCheckItemSchema):
        return CheckItemHandler.get_all(query)

    @auth.login_required()
    @response_collect
    @validate()
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
        _body = {
            "id": checkitem_id
        }
        _body.update(body.__dict__)
        return Edit(CheckItem, _body).single(CheckItem, "/checkitem")

    @auth.login_required()
    @response_collect
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
        scrapyspider_redis_client = redis.StrictRedis(
            connection_pool=scrapyspider_pool
        )

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

            _tests_overview_url = scrapyspider_redis_client.get(
                f"{product_name}_{builds_list[0]}_tests_overview_url"
            )

            # positively sync crawl latest data from openqa of latest build
            exitcode, output = subprocess.getstatusoutput(
                "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "
                f"-a product_build={product_name}_{builds_list[0]} "
                f"-a openqa_url={openqa_url} "
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
            tests_overview_url = scrapyspider_redis_client.get(
                f"{product_build}_tests_overview_url"
            )

            # positively crawl latest data from openqa of pointed build
            exitcode, output = subprocess.getstatusoutput(
                "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "
                f"-a product_build={product_build} "
                f"-a openqa_url={openqa_url} "
                f"-a tests_overview_url={add_escape(tests_overview_url)}"
            )
            if exitcode != 0:
                current_app.logger.error(
                    f"crawl latest tests overview data of {product_build} fail. Because {output}"
                )

            current_app.logger.info(
                f"crawl latest tests overview data of product {product_build} succeed"
            )

            at_statistic = OpenqaATStatistic(
                arches=current_app.config.get(
                    "SUPPORTED_ARCHES", ["aarch64", "x86_64"]
                ),
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

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func
        )
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
        if qualityboard.product:
            org_id = qualityboard.product.org_id
            org = Organization.query.filter_by(id=org_id).first()
            feature_list_handler = feature_list_handlers.get(org.name)
            if not feature_list_handler:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"feature adapter for {org.name} does not exist.please contact the administrator in time."
                )

            handler = feature_list_handler(FeatureList, qualityboard_id)
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
                handler.store()
            else:
                # 社区暂未统一继承特性的定义
                pass

        feature_list = FeatureList.query.filter_by(
            qualityboard_id=qualityboard_id, is_new=query.new
        ).all()
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

        addition_feature_summary = dict()
        inherit_feature_summary = dict()

        if qualityboard.product:
            org_id = qualityboard.product.org_id
            org = Organization.query.filter_by(id=org_id).first()
            feature_list_handler = feature_list_handlers.get(org.name)
            if not feature_list_handler:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"feature adapter for {org.name} does not exist.please contact the administrator in time."
                )

            handler = feature_list_handler(FeatureList, qualityboard_id)
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
    def get(self, qualityboard_id, round_id, query: PackageListQuerySchema):
        qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard doesn't exist.",
            )
        _round = Round.query.filter_by(id=round_id, product_id=qualityboard.product_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round doesn't exist.",
            )
        
        if query.refresh:
            org_id = qualityboard.product.org_id
            org = Organization.query.filter_by(id=org_id).first()
            _product = _round.product.name + "-" + _round.product.version
            if _round.type == "release":
                _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_OFFICIAL_REPO_URL")
                _filename_p = _product
                round_num = None
            else:
                _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_DAILYBUILD_REPO_URL")
                _filename_p = f"{_product}-round-{_round.round_num}"
                round_num = _round.round_num
            for arch in ["x86_64", "aarch64", "all"]:
                for sub_path in ["everything", "EPOL/main"]:
                    _filename = f"{_filename_p}-{sub_path.split('/')[0]}-{arch}"
                    if not redis_client.hgetall(f"resolving_{_filename}_pkglist"):
                        redis_client.hset(
                            f"resolving_{_filename}_pkglist", "gitee_id", g.gitee_id
                        )
                        redis_client.hset(
                            f"resolving_{_filename}_pkglist", 
                            "resolve_time", 
                            datetime.now(
                                tz=pytz.timezone('Asia/Shanghai')
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        redis_client.expire(f"resolving_{_filename}_pkglist", 1800)
                        resolve_pkglist_after_resolve_rc_name.delay(
                            repo_url=_pkgs_repo_url,
                            repo_path=sub_path,
                            arch=arch,
                            product=_product,
                            _round=round_num
                        )
            return jsonify(
                error_code=RET.OK,
                error_msg=f"the packages of {_round.name} " \
                    f"start resolving, please wait for several minutes",
            )
        try:
            handler = PackageListHandler(
                round_id,
                query.repo_path,
                query.arch,
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
            _round = Round.query.filter_by(id=round_id).first()
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={
                    "name": _round.name,
                    "size": len(pkgs_dict)
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
    def post(self, qualityboard_id, round_id, body: PackageCompareSchema):
        try:
            comparer = PackageListHandler(
                round_id,
                body.repo_path,
                "aarch64",
                False
            )
            comparee = PackageListHandler(
                round_id,
                body.repo_path,
                "x86_64",
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

        compare_results = comparer.compare2(comparee.packages)
        update_samerpm_compare_result.delay(round_id, compare_results, body.repo_path)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    @auth.login_required
    @response_collect
    @validate()
    def get(self, qualityboard_id, round_id, query: SamePackageCompareQuerySchema):
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
    def post(self, qualityboard_id, comparee_round_id, comparer_round_id, body: PackageCompareSchema):
        try:
            comparer = PackageListHandler(
                comparer_round_id,
                body.repo_path,
                "all",
                False
            )
            comparee = PackageListHandler(
                comparee_round_id,
                body.repo_path,
                "all",
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

        update_compare_result.delay(round_group_id, compare_results, body.repo_path)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )
    

    @auth.login_required
    @response_collect
    @validate()
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


class QualityResultCompare(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
    @validate()
    def get(self, query: QueryRound):
        return Select(Round, query.__dict__).precise()


class RoundItemEvent(Resource):
    @auth.login_required
    @validate()
    def put(self, round_id, body: RoundToMilestone):
        return RoundHandler.bind_round_milestone(round_id, body.milestone_id, body.isbind)


class RoundIssueRateEvent(Resource):
    @auth.login_required
    @validate()
    def put(self, round_id, body: RoundIssueRateSchema):
        return RoundHandler.update_round_issue_rate_by_field(round_id, body.field)
    
    @auth.login_required
    @validate()
    def get(self, round_id):
        return RoundHandler.get_rate_by_round(round_id)


class RoundIssueEvent(Resource):
    @auth.login_required
    @validate()
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
        return IssueOpenApiHandlerV8().get_all(_body)
