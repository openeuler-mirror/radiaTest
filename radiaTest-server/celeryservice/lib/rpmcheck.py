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
import subprocess
from flask import current_app

from server import redis_client
from server.utils.math_util import calculate_rate
from celeryservice.lib import TaskHandlerBase


class RpmCheckHandler(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def resolve_detail(self, build_name, _detail, _file=None):
        cnt_dict = dict()
        all_cnt = 0

        for _det in _detail:
            status = _det.get("status")
            if cnt_dict.get(status):
                cnt_dict.update({
                    status: cnt_dict.get(status) + 1
                })
            else:
                cnt_dict.update({
                    status: 1
                })
            all_cnt += 1

        data = []
        for _key in cnt_dict.keys():
            data.append(
                {
                    "status": _key,
                    "cnt": cnt_dict.get(_key),
                    "rate": calculate_rate(cnt_dict.get(_key), all_cnt, 2)
                }
            )
        
        rpm_key = f"rpmcheck_{build_name}"
        redis_client.hmset(
            rpm_key, 
            {
                "all_cnt": all_cnt,
                "data": data,
                "file": f"{rpm_key}.yaml",
            }
        )

        expires_time = int(current_app.config.get("RPMCHECK_RESULT_EXPIRES_TIME"))
        redis_client.expire(rpm_key, expires_time)
        _rpmchecks = redis_client.keys(
            f"rpmcheck_{build_name.split('_')[0]}_*"
        )

        rpmcheck_path = current_app.config.get("RPMCHECK_FILE_PATH")
        exitcode, file_list = subprocess.getstatusoutput(
            f"ls -l {rpmcheck_path} | sed '1d' " + " | awk '{print $9}'"
        )
        if exitcode != 0:
            current_app.logger.info(file_list)
            return
        for _file in file_list.split("\n"):
            if _file.replace(".yaml", "") not in _rpmchecks:
                exitcode, output = subprocess.getstatusoutput(
                    f"rm -f {rpmcheck_path}/{_file}"
                )

