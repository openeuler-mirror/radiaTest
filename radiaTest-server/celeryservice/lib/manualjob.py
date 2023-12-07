# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author :
# @email :
# @Date :
# @License : Mulan PSL v2
#####################################

from datetime import datetime
import pytz


from server import db
from server.model import Case, ManualJob, ManualJobStep
from server.model.manualjob import ManualJobGroup
from server.utils.db import collect_sql_error
from server.utils.text_utils import TextItemSplitter, DefaultNumeralRule
from celeryservice.lib import TaskHandlerBase


class ManualJobAsyncHandler(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    @staticmethod
    @collect_sql_error
    def create(body):
        manual_job_dict = body
        cases = map(int, manual_job_dict.get('cases').split(','))
        manual_job_dict.pop('cases')
        name = manual_job_dict['name']
        # 手工任务组创建
        manual_job_group = ManualJobGroup(**body)
        db.session.add(manual_job_group)
        db.session.flush()
        manual_job_dict["job_group_id"] = manual_job_group.id
        success_list = []
        failed_list = []
        for case_id in cases:
            _case = Case.query.get(case_id)
            if not _case:
                failed_list.append(case_id)
                continue
            manual_job_dict['case_id'] = case_id
            manual_job_dict['name'] = f"{name}_{str(case_id)}_" \
                                      f"{datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime('%Y%m%d%H%M%S')}"
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

            db.session.add(manual_job)
            db.session.flush()

            manual_job_id = manual_job.id

            # 根据上面取得的步骤数, 在数据库中创建这个数量的ManualJobStep记录
            for cnt in range(total_step):
                manual_job_step_dict = {}
                manual_job_step_dict["manual_job_id"] = manual_job_id
                manual_job_step_dict["step_num"] = cnt + 1
                manual_job_step_dict["operation"] = step_operation_dict.get(step_operation_dict_key_list[cnt])
                manual_job_step = ManualJobStep(**manual_job_step_dict)
                db.session.add(manual_job_step)
            success_list.append(case_id)
        if failed_list:
            db.session.rollback()
            return False, {
                "success_list": success_list,
                "failed_list": failed_list,
            }
        else:
            db.session.commit()
            return True, {
                "success_list": success_list,
                "failed_list": failed_list,
            }

