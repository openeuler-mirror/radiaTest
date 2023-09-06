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

import datetime

from importlib_metadata import abc


class ATStatistic:
    def __init__(self, arches, product, redis_client):
        self.arches = arches
        self.product = product
        self._init_stats()
        self.redis_client = redis_client

    @property
    def stats(self):
        return self._stats

    def _init_stats(self):
        self._stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "block": 0,
            "running": 0
        }
    
    @property
    @abc.abstractmethod
    def group_overview(self):
        pass

    @property
    @abc.abstractmethod
    def tests_overview(self):
        pass


class OpenqaATStatistic(ATStatistic):
    def __init__(self, arches, product, build, redis_client):
        self.build = build
        super().__init__(arches, product, redis_client)

    @property
    def _keys_prefix(self):
        return f"{self.product}_{self.build}_"

    @property
    def _pass_suffix(self):
        return "_tests_overview_url"
    
    @property
    def _tests(self):
        return self.redis_client.keys(f"{self._keys_prefix}*")

    def calc_stats(self):
        self._init_stats()

        for test in self._tests:
            if test.endswith(self._pass_suffix):
                continue

            for arch in self.arches:
                _res_status = self.redis_client.hget(test, f"{arch}_res_status")
                if _res_status == "-":
                    continue
                self.stats["total"] += 1

                _failedmodule_name = self.redis_client.hget(test, f"{arch}_failedmodule_name")
                
                if _res_status == "Done: passed" and _failedmodule_name == "-":
                    self.stats["success"] += 1
                elif _res_status.endswith("skipped"):
                    self.stats["block"] += 1
                elif _res_status == "running" or _res_status.startswith("schedule"):
                    self.stats["running"] += 1
                else:
                    self.stats["failure"] += 1

    @staticmethod
    def format_test_duration(test_duration):
        try:
            test_duration = int(test_duration)
            return str(datetime.timedelta(seconds=test_duration))
        except ValueError:
            return "-"

    @property
    def test_duration(self):
        test_duration = 0
        key_name = f'product_build_test_set_{self.product}_{self.build}'
        for member in self.redis_client.zrange(key_name, 0, -1):
            score = int(self.redis_client.zscore(key_name, member))
            test_duration += score
        return self.format_test_duration(test_duration)

    @property
    def group_overview(self):
        self.calc_stats()
        return {
            "build": self.build,
            "finish_timestamp": self.redis_client.zscore(
                self.product,
                self.build
            ),
            **self.stats,
            "test_duration": self.test_duration
        }

    @property
    def tests_overview(self):
        return_data = list()
        for test in self._tests:
            if test.endswith(self._pass_suffix):
                continue
        
            overview = dict()
            overview["test"] = test.split(self._keys_prefix)[1]

            for arch in self.arches:
                overview[f"{arch}_res_status"] = self.redis_client.hget(test, f"{arch}_res_status")
                overview[f"{arch}_res_log"] = self.redis_client.hget(test, f"{arch}_res_log")
                overview[f"{arch}_failedmodule_name"] = self.redis_client.hget(test, f"{arch}_failedmodule_name")
                overview[f"{arch}_failedmodule_log"] = self.redis_client.hget(test, f"{arch}_failedmodule_log")
                overview[f"{arch}_start_time"] = self.redis_client.hget(test, f"{arch}_start_time")
                overview[f"{arch}_end_name"] = self.redis_client.hget(test, f"{arch}_end_name")
                overview[f"{arch}_test_duration"] = self.format_test_duration(
                    self.redis_client.hget(test, f"{arch}_test_duration"))
            
            return_data.append(overview)
    
        return return_data
