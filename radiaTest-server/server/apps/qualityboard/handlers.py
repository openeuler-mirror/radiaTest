from importlib_metadata import abc
from server import scrapyspider_redis_client


class ATStatistic:
    def __init__(self, archs, product):
        self.archs = archs
        self.product = product
        self._init_stats()

    @property
    def stats(self):
        return self._stats

    def _init_stats(self):
        self._stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "skipping": 0,
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
    def __init__(self, archs, product, build):
        self.build = build
        super().__init__(archs, product)

    @property
    def _keys_prefix(self):
        return f"{self.product}_{self.build}_"

    @property
    def _pass_suffix(self):
        return "_tests_overview_url"
    
    @property
    def _tests(self):
        return scrapyspider_redis_client.keys(f"{self._keys_prefix}*")

    def calc_stats(self):
        self._init_stats()

        for test in self._tests:
            if test.endswith(self._pass_suffix):
                continue

            for arch in self.archs:
                self.stats["total"] += 1
                _res_status = scrapyspider_redis_client.hget(test, f"{arch}_res_status")
                _failedmodule_name = scrapyspider_redis_client.hget(test, f"{arch}_failedmodule_name")
                
                if _res_status == "Done: passed" and _failedmodule_name == "-":
                    self.stats["success"] += 1
                elif _res_status == "Done: passed" and _failedmodule_name != "-":
                    self.stats["failure"] += 1
                elif _res_status == "Done: failed":
                    self.stats["failure"] += 1
                elif _res_status == "Done: skipped":
                    self.stats["skipping"] += 1
                elif _res_status == "running":
                    self.stats["running"] += 1

    @property
    def group_overview(self):
        self.calc_stats()
        return {
            "build": self.build,
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

            for arch in self.archs:
                overview[f"{arch}_res_status"] = scrapyspider_redis_client.hget(test, f"{arch}_res_status")
                overview[f"{arch}_res_log"] = scrapyspider_redis_client.hget(test, f"{arch}_res_log")
                overview[f"{arch}_failedmodule_name"] = scrapyspider_redis_client.hget(test, f"{arch}_failedmodule_name")
                overview[f"{arch}_failedmodule_log"] = scrapyspider_redis_client.hget(test, f"{arch}_failedmodule_log")
            
            return_data.append(overview)
    
        return return_data