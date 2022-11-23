# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang
# @email   : ethanzhang55@outlook.com
# @Date    : 2022/09/15
# @License : Mulan PSL v2
#####################################

from server.utils.db import Insert, Edit
from server.model.qualityboard import RpmCheck, RpmCheckDetail
from celeryservice.lib import TaskHandlerBase


class RpmCheckHandler(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def resolve_detail(self, _id, _detail):
        cnt_dict = {
            "success": 0,
            "failed": 0,
            "broken": 0,
            "unresolvable": 0,
        }
        all_cnt = 0

        for _d in _detail:
            status = _d.get("status")
            cnt_dict.update({
                status: cnt_dict.get(status) + 1
            })
            all_cnt += 1
            _d.update({"rpm_check_id": _id})
            _rpmcd = RpmCheckDetail.query.filter_by(
                package=_d.get("package"),
                arch=_d.get("arch")
            ).first()
            if _rpmcd:
                _d.update({"id": _rpmcd.id})
                Edit(RpmCheckDetail, _d).single()
            else:
                _ = Insert(
                    RpmCheckDetail,
                    _d,
                ).insert_id()

        def calculate_rate(part_cnt, all_cnt):
            _rate = None
            if int(all_cnt) != 0:
                _rate = int(part_cnt) / int(all_cnt)
            if _rate:
                _rate = "%.f%%" % (_rate * 100)
            return _rate

        success_rate = calculate_rate(cnt_dict.get("success"), all_cnt)
        failed_rate = calculate_rate(cnt_dict.get("failed"), all_cnt)
        broken_rate = calculate_rate(cnt_dict.get("broken"), all_cnt)
        unresolvable_rate = calculate_rate(
            cnt_dict.get("unresolvable"), all_cnt
        )
        Edit(
            RpmCheck,
            {
                "id": _id,
                "all_cnt": all_cnt,
                "success_cnt": cnt_dict.get("success"),
                "success_rate": success_rate,
                "failed_cnt": cnt_dict.get("failed"),
                "failed_rate": failed_rate,
                "broken_cnt": cnt_dict.get("broken"),
                "broken_rate": broken_rate,
                "unresolvable_cnt": cnt_dict.get("unresolvable"),
                "unresolvable_rate": unresolvable_rate,
            }
        ).single()
