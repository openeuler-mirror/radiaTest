from datetime import datetime

from server.utils.db import Insert
from server.model.celerytask import CeleryTask


class TaskHandlerBase:
    def __init__(self, logger):
        self.logger = logger
        self.start_time = datetime.now()
        self.running_time = 0

    def next_period(self):
        _current_time = datetime.now()
        self.running_time = (_current_time - self.start_time).seconds * \
            1000 + (_current_time - self.start_time).microseconds/1000


class TaskAuthHandler(TaskHandlerBase):
    def __init__(self, user, logger):
        self.user = user
        super().__init__(logger)

    def save_task_to_db(self, tid, description):
        celerytask = {
            "tid": tid,
            "status": "PENDING",
            "object_type": "testcase_resolve",
            "description": description,
            "user_id": self.user.get("user_id"),
        }

        _ = Insert(CeleryTask, celerytask).single(CeleryTask, "/celerytask")