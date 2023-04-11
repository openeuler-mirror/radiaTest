# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author : 董霖峰
# @email : 1063183942@qq.com
# @Date : 2022/12/11 05:22:35
# @License : Mulan PSL v2
#####################################
# 手工测试任务(ManualJob)相关接口的handler层

import re
from copy import deepcopy

from flask import jsonify, g
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db, redis_client
from server.model import Case, ManualJob, ManualJobStep
from server.utils.redis_util import RedisKey
from server.utils.permission_utils import GetAllByPermission
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.utils.page_util import PageUtil
from server.utils.text_utils import TextItemSplitter, DefaultNumeralRule


class ManualJobHandler:
    @staticmethod
    @collect_sql_error
    def create(_case: Case, body, workspace=None):
        # 向数据库中插入此条ManualJob记录, manual_job_dict中为部分字段.
        manual_job_dict = deepcopy(body.__dict__)

        _permission_body = {
            "permission_type": "org",
            "org_id": int(
                redis_client.hget(
                    RedisKey.user(g.user_id), 
                    "current_org_id"
                )
            )
        }

        if re.match(r'^group_\d+$', workspace):
            _permission_body.update({
                "permission_type": "group",
                "group_id": int(workspace.split("_")[1])
            })
        
        manual_job_dict.update(_permission_body)

        manual_job_dict["executor_id"] = g.user_id
        # 从所属的Case那里计算总步骤数
        if _case.steps is not None and _case.steps != "":
            text_item_splitter = TextItemSplitter(
                numeral_rules=[DefaultNumeralRule],
                separators=[".", "、"],
                terminators=["\n"]
            )
            step_operation_dict = text_item_splitter.split_text_items(_case.steps)
            total_step = len(step_operation_dict)
            step_operation_dict_key_list = sorted(list(step_operation_dict.keys()))
        else:  # 如果该manualjob所属case的steps字段留空, 视为有1个步骤(而不是0个步骤)
            total_step = 1
            step_operation_dict = {1: ""}
            step_operation_dict_key_list = [1]

        manual_job_dict["total_step"] = total_step

        manual_job = ManualJob(**manual_job_dict)

        db.session.add(manual_job)  # 执行插入操作, 并获取本次插入记录的id.
        db.session.flush()  # 此步不会真正的提交, 但会把数据同步到数据库的缓存中, 这之后就可以获取新插入这条数据的id.

        manual_job_id = manual_job.id

        # 根据上面取得的步骤数, 在数据库中创建这个数量的ManualJobStep记录
        for cnt in range(total_step):
            manual_job_step_dict = {}
            manual_job_step_dict["manual_job_id"] = manual_job_id
            manual_job_step_dict["step_num"] = cnt + 1
            manual_job_step_dict["operation"] = step_operation_dict.get(step_operation_dict_key_list[cnt])
            manual_job_step = ManualJobStep(**manual_job_step_dict)
            db.session.add(manual_job_step)

        try:
            db.session.commit()  # 提交事务
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e  # 把异常抛给外层@collect_sql_error

        return jsonify(
            data={"id": manual_job_id},
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )

    @staticmethod
    @collect_sql_error
    def query(query, workspace=None):
        if query.status != 0 and query.status != 1:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="status of a manual_job can only be 0 or 1"
            )

        filter_params = GetAllByPermission(ManualJob, workspace).get_filter()
        filter_params.append(ManualJob.status == query.status)

        # 分页对象
        page_dict, e = PageUtil.get_page_dict(
            query_filter=ManualJob.query.filter(*filter_params),
            page_num=query.page_num,
            page_size=query.page_size,
            func=ManualJob.to_json
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f"get manual_job page error {e}."
            )
        return jsonify(
            data=page_dict,
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )


class ManualJobSubmitHandler:
    @staticmethod
    @collect_sql_error
    def post(manual_job: ManualJob):
        manual_job.status = 1

        result = 1
        # 查询此manual_job所有步骤的日志, 如果此manual_job所有步骤的日志都存在且结果都是True, 则设置manual_job的结果为1.
        for cnt in range(1, manual_job.total_step + 1):
            manual_job_step = ManualJobStep.query.filter_by(manual_job_id=manual_job.id, step_num=cnt).first()
            if manual_job_step is None or manual_job_step.passed is None:
                result = -1  # -1表示存在一些步骤的日志未填写. 提交完成执行失败.
                break
            elif manual_job_step.passed is False:
                result = 0  # 0表示存在一些步骤的日志结果与预期不符

        if result >= 0:
            manual_job.result = result
            try:
                db.session.commit()
            except (IntegrityError, SQLAlchemyError) as e:
                db.session.rollback()
                raise e
            return jsonify(
                error_code=RET.OK,
                error_msg="Request processed successfully."
            )
        else:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Not all the steps' logs are filled."
            )


class ManualJobLogHandler:
    @staticmethod
    @collect_sql_error
    def update(manual_job_id, body):
        # 按id查找ManualJob
        manual_job = ManualJob.query.filter_by(id=manual_job_id).first()
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the manual_job with id {manual_job_id} does not exist"
            )

        # 按步骤序号和所属的ManualJob的id查找ManualJobStep
        step_num = body.step
        manual_job_step = ManualJobStep.query.filter_by(manual_job_id=manual_job_id, step_num=step_num).first()
        if manual_job_step is None:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg=f"manual_job with id {manual_job_id} does not have a {body.step}-th step"
            )

        # 修改信息
        manual_job_step.log_content = body.content
        manual_job_step.passed = body.passed

        if manual_job.current_step < step_num:
                manual_job.current_step = step_num

        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )

    @staticmethod
    @collect_sql_error
    def delete(manual_job_id, body):
        # 按id查找ManualJob
        manual_job = ManualJob.query.filter_by(id=manual_job_id).first()
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job with id {manual_job_id} does not exist"
            )

        # 按步骤序号和所属的ManualJob的id查找ManualJobStep
        step_num = body.__dict__.get("step")
        if step_num is not None:  # step不为空表示删除该ManualJob的单条日志
            manual_job_step = ManualJobStep.query.filter_by(manual_job_id=manual_job_id, step_num=step_num).first()
            if manual_job_step is None:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"manual_job with id {manual_job_id} does not have a {step_num}-th step"
                )

            # 修改(删除)信息
            manual_job_step.log_content = None
            manual_job_step.passed = None

            # 如果刪除当前(最新)步骤的日志, ManualJob的current_step字段回退到剩余存在日志的步骤的step_num的最大值.
            if manual_job.current_step == step_num:
                remain_manual_job_steps = ManualJobStep.query.filter_by(manual_job_id=manual_job_id).all()
                latest_step_num = 0
                for each_step in remain_manual_job_steps:
                    if each_step.step_num > latest_step_num and (
                            each_step.log_content is not None or each_step.passed is not None):
                        latest_step_num = each_step.step_num
                manual_job.current_step = latest_step_num

            try:
                db.session.commit()
            except (IntegrityError, SQLAlchemyError) as e:
                db.session.rollback()
                raise e
        else:  # step为空表示删除该ManualJob的所有日志
            manual_job_steps = ManualJobStep.query.filter_by(manual_job_id=manual_job_id).all()
            for each_step in manual_job_steps:
                each_step.log_content = None
                each_step.passed = None

            manual_job.current_step = 0

            try:
                db.session.commit()
            except (IntegrityError, SQLAlchemyError) as e:
                db.session.rollback()
                raise e

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )


class ManualJobDeleteHandler:
    @staticmethod
    @collect_sql_error
    def delete(manual_job_id: int):
        # 按请求参数中的id查询ManualJob
        query_result = ManualJob.query.filter_by(id=manual_job_id).first()
        if query_result is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the manual_job with id {manual_job_id} does not exist"
            )

        db.session.delete(query_result)
        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )


class ManualJobLogQueryHandler:
    @staticmethod
    @collect_sql_error
    def query(manual_job: ManualJob, step_num: int):
        # 按步骤序号和所属的ManualJob的id查找ManualJobStep
        manual_job_step = ManualJobStep.query.filter_by(manual_job_id=manual_job.id, step_num=step_num).first()
        if manual_job_step is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job with id {manual_job.id} does not have a {step_num}-th step"
            )

        log_content = manual_job_step.log_content
        passed = manual_job_step.passed
        operation = manual_job_step.operation
        return_data_dict = {"content": log_content, "passed": passed, "operation": operation}
        return jsonify(
            data=return_data_dict,
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )
