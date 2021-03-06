from abc import ABCMeta, abstractmethod


class Executor(metaclass=ABCMeta):
    @abstractmethod
    def deploy(self, **kargs):
        """prepare something before run test,except download code"""
        pass

    @abstractmethod
    def run_test(self, **kargs):
        """run test code after deploy"""
        pass

    @abstractmethod
    def deploy_env(self, *args):
        """deploy code except download code"""
        pass

    @abstractmethod
    def init_env(self, *args):
        """resolving dependencies for test project"""
        pass

    @abstractmethod
    def init_conf(self, *args):
        """init config for test project"""
        pass

    @abstractmethod
    def get_case_code(self, *args):
        """get test case code"""
        pass

    @abstractmethod
    def suite2cases_resolver(self, *args):
        """get test suite details info,such as suite config,test cases and so on"""
        pass

    @abstractmethod
    def run_all_cases(self, *args):
        """run all testcases"""
        pass

    @abstractmethod
    def run_suite(self, *args):
        """run test suite"""
        pass

    @abstractmethod
    def run_case(self, *args):
        """run some testcases"""
        pass