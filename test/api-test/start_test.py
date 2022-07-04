#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
import time
import sys
import argparse
from public import HTMLTestRunner


sys.path.append(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])


def get_test_suite(suit: str, case_name: str):
    testunit = unittest.TestSuite()
    test_dir = os.path.abspath(os.path.dirname(__file__)) + os.sep + 'testcase'
    if suit == "all":
        discover = unittest.defaultTestLoader.discover(test_dir, pattern='test*.py',top_level_dir=test_dir)
        for test_suite in discover:
            for test_case in test_suite:
                testunit.addTests(test_case)
    else:
        discover = unittest.defaultTestLoader.discover(test_dir, pattern='test_' + suit + '.py',top_level_dir=None)
        for test_suite in discover:
            for test_case in test_suite:
                if case_name == "all":
                    testunit.addTests(test_case)
                else:
                    for t in test_case:
                        if case_name == t._testMethodName:
                            testunit.addTest(t)
    return testunit


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="manual to this script")
    parser.add_argument("--suit", type=str, default="all", required=True)
    parser.add_argument("--case", type=str, default="all", required=True)
    args = parser.parse_args()

    cur_dir = os.path.abspath(os.path.dirname(__file__)) 
    filename = cur_dir + os.sep + 'report' + os.sep + time.strftime("%Y-%m-%d-%H-%M-%S") + '-result.html'
    fp = open(filename, 'wb')
    runner = HTMLTestRunner.HTMLTestRunner(
        stream=fp,
        title=u'radiaTest项目自动化测试报告',
        description=u'用例执行情况：',
        )
    all_test_units = get_test_suite(args.suit, args.case)
    runner.run(all_test_units)
    fp.close()
    print("view test result in " + filename)
