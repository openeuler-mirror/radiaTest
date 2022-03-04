from datetime import datetime


class TaskHandlerBase:
    def __init__(self, logger):
        self.start_time = datetime.now()
        self.running_time = 0
        self.logger = logger

    def next_period(self):
        _current_time = datetime.now()
        self.running_time = (_current_time - self.start_time).seconds*1000 + (_current_time - self.start_time).microseconds/1000


        