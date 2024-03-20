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

def calculate_rate(num, total, decimal=0):
    """
    :description: Calculate the percentage with two given numbers and specify the number of decimal places
    :param: num: int, Calculated number
    :param: total: int, total number
    :param: decimal: int, specified number of decimal places
    :return: rate, percentage rate of num and total
    """
    rate = None
    if int(total) != 0:
        rate = int(num) / int(total)
    if rate is not None:
        if decimal > 0:
            rate = f"%.{decimal}f%%" % (rate * 100)
        else:
            rate = "%.f%%" % (rate * 100)
    return rate