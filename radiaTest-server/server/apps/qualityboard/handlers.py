from importlib_metadata import abc

from flask import jsonify

from server.model.qualityboard import Checklist
from server.utils.db import collect_sql_error
from server.utils.response_util import RET
from server.utils.page_util import PageUtil


class ChecklistHandler:
    @staticmethod
    @collect_sql_error
    def handler_get_one(checklist_id):
        _checklist = Checklist.query.get(checklist_id)
        if not _checklist:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="current checklist does not exist/already deleted"
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_checklist.to_json()
        )

    @staticmethod
    @collect_sql_error
    def handler_get_checklist(query):
        _filter = []
        if query.check_item:
            _filter.append(Checklist.check_item.like(f'%{query.check_item}%'))
        filter_chain = Checklist.query.filter(*_filter)
        page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f'get checklist page error {e}'
            )
        return jsonify(
            error_code=RET.OK,
            error_msg='OK',
            data=page_dict
        )


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
            
            return_data.append(overview)
    
        return return_data