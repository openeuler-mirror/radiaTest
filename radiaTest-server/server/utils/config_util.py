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
import configparser
from pathlib import Path

from flask import Flask


def loads_config_ini(app):
    if not isinstance(app, Flask) or not app.config.get("INI_PATH"):
        return False

    server_config_ini = Path(app.config.get("INI_PATH"))

    cfg = configparser.ConfigParser()
    cfg.read(server_config_ini)

    for section, _ in cfg.items():
        for key, value in cfg.items(section):
            try:
                value = int(value)
            except ValueError as e:
                pass

            up_key = key.upper()

            if up_key == 'PROTECTED_PMS':
                app.config[up_key] = value.strip('\'"').split(';')
                continue

            app.config[up_key] = value

    return True
