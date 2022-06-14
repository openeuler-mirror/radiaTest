from abc import ABCMeta, abstractmethod


class LogResolver(metaclass=ABCMeta):
    @abstractmethod
    def loads_logs(self, *args):
        """Loading text of logs file, stratifying data to store"""
        pass
