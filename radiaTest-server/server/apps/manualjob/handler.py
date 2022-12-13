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

from copy import deepcopy
from datetime import datetime
from flask import jsonify, g
import pytz
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db
from server.model import Case, ManualJob, ManualJobStep
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.utils.page_util import PageUtil
from server.utils.text_utils import TextItemSplitter, DefaultNumeralRule


class ManualJobHandler:
    @staticmethod
    @collect_sql_error
    def create(_case: Case, body):
        # 向数据库中插入此条ManualJob记录, manual_job_dict中为部分字段.
        manual_job_dict = deepcopy(body.__dict__)
        manual_job_dict["executor_id"] = g.gitee_id
        # 从所属的Case那里计算总步骤数
        text_item_splitter = TextItemSplitter(
            numeral_rules=[DefaultNumeralRule],
            separators=[". ", "、"],
            terminators=["\n"]
        )
        step_item_dict = text_item_splitter.split_text_items(_case.steps)
        total_step = len(step_item_dict)
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
    def query(query):
        if query.status != 0 and query.status != 1:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="status of a manual_job can only be 0 or 1"
            )

        # 分页对象
        page_dict, e = PageUtil.get_page_dict(
            query_filter=ManualJob.query.filter(ManualJob.status == query.status),
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


class ManualJobStatusHandler:
    @staticmethod
    @collect_sql_error
    def update(manual_job: ManualJob, body):
        # 直接在查询到的结果上修改即可
        status = body.status
        if status == 0 or status == 1:
            manual_job.status = status
        else:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="status of a manual_job can only be 0 or 1"
            )

        if status == 1:
            manual_job.end_time = datetime.now(pytz.timezone('Asia/Shanghai'))

        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )


class ManualJobResultHandler:
    @staticmethod
    @collect_sql_error
    def update(manual_job: ManualJob, body):
        manual_job.result = body.result  # 直接在查询到的结果上修改
        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
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
        return_data_dict = {"content": log_content, "passed": passed}
        return jsonify(
            data=return_data_dict,
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )
