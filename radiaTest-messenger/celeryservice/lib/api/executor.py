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