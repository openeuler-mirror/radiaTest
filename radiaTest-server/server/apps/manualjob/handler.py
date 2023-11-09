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

from datetime import datetime

import pytz
from flask import jsonify, g
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from celeryservice.lib.manualjob import ManualJobAsyncHandler
from server import db
from server.model import ManualJob, ManualJobStep, Analyzed
from server.model.manualjob import ManualJobGroup
from server.utils.permission_utils import GetAllByPermission
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.utils.page_util import PageUtil
from celeryservice.tasks import resolve_create_manualjob


class ManualJobHandler:
    @staticmethod
    @collect_sql_error
    def create(body):
        manual_job_dict = body.__dict__
        # 同步执行创建任务
        flag, result = ManualJobAsyncHandler.create(manual_job_dict)
        if flag is True:
            return jsonify(
                error_code=RET.OK,
                error_msg="Request processed successfully."
            )
        else:
            return jsonify(
                data=result,
                error_code=RET.PARMA_ERR,
                error_msg="任务创建失败,请检查用例是否存在!"
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
        if query.name is not None:
            filter_params.append(ManualJob.name.like(f'%{query.name}%'))
        if query.case_id is not None:
            filter_params.append(ManualJob.case_id == query.case_id)
        if query.job_group_id is not None:
            filter_params.append(ManualJob.job_group_id == query.job_group_id)
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

    @staticmethod
    @collect_sql_error
    def query_manual_job_group(query, workspace=None):
        filter_params = GetAllByPermission(ManualJobGroup, workspace).get_filter()
        if query.name is not None:
            filter_params.append(ManualJobGroup.name.like(f'%{query.name}%'))
        if query.milestone_id is not None:
            filter_params.append(ManualJobGroup.milestone_id == query.milestone_id)
        if query.status is not None:
            filter_params.append(ManualJobGroup.status == query.status)

        # 分页对象
        page_dict, e = PageUtil.get_page_dict(
            query_filter=ManualJobGroup.query.filter(*filter_params),
            page_num=query.page_num,
            page_size=query.page_size,
            func=ManualJobGroup.to_json
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f"get manual_job_group page error {e}."
            )
        return jsonify(
            data=page_dict,
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )


class ManualJobSubmitHandler:

    @classmethod
    @collect_sql_error
    def post(cls, manual_job: ManualJob):
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
            # 同步执行记录
            cls.update_case_analyzed(manual_job, result)
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

    @classmethod
    @collect_sql_error
    def update(cls, manual_job, body):
        # 设置任务结果
        manual_job.status = 1
        manual_job.result = body.result
        if body.remark:
            manual_job.remark = body.remark
        # 同步执行记录
        cls.update_case_analyzed(manual_job, body.result)
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
    def update_case_analyzed(manual_job, result):
        # 同步创建执行手工任务执行记录
        if result == 1:
            res_str = "success"
        elif result == 0:
            res_str = "fail"
        elif result == 2:
            res_str = "block"
        else:
            res_str = "NA"
        db.session.add(Analyzed(result=res_str, case_id=manual_job.case_id, manual_job_id=manual_job.id))


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

    @staticmethod
    @collect_sql_error
    def delete_manual_job_group(manual_job_group_id: int):
        group_job_result = ManualJobGroup.query.filter_by(id=manual_job_group_id).first()
        if group_job_result is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the manual_job_group with id {manual_job_group_id} does not exist"
            )
        db.session.delete(group_job_result)
        query_result = ManualJob.query.filter_by(job_group_id=manual_job_group_id).all()
        if query_result:
            for manual_job in query_result:
                db.session.delete(manual_job)
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


class ManualJobGroupCopyHandler:
    @staticmethod
    @collect_sql_error
    def copy(manual_job_group, body):
        name = manual_job_group.name + datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime("-%Y-%m-%d-%H:%M:%S")
        if not body.get("milestone_id"):
            milestone_id = manual_job_group.milestone_id
        else:
            milestone_id = body.get("milestone_id")
        case_ids = []
        for manual_job in ManualJob.query.filter_by(job_group_id=manual_job_group.id).all():
            case_ids.append(str(manual_job.case_id))
        create_data = {
            "name": name,
            "milestone_id": milestone_id,
            "cases": ",".join(case_ids),
            "creator_id": g.user_id,
            "permission_type":  manual_job_group.permission_type,
            "group_id": manual_job_group.group_id,
            "org_id": manual_job_group.org_id,
        }
        # 同步执行创建任务
        flag, result = ManualJobAsyncHandler.create(create_data)
        if flag is True:
            return jsonify(
                error_code=RET.OK,
                error_msg="Request processed successfully."
            )
        else:
            return jsonify(
                data=result,
                error_code=RET.PARMA_ERR,
                error_msg="任务创建失败,请检查用例是否存在!"
            )