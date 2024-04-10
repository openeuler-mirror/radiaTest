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
import re


def check_illegal_lables(content):
    malicious_tags_pattern = re.compile(
        r'<(script|iframe|object|embed|form|input|a|img|style|link)(\s|/?>).*?>',
        re.IGNORECASE
    )

    malicious_tags = malicious_tags_pattern.findall(content)

    # 如果找到匹配的标签，返回 True，否则返回 False
    if malicious_tags:
        raise RuntimeError("content contain illegal labels")
