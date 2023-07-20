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
    if not isinstance(app, Flask) or not app.config.get("CONFIG_INI_FILE_PATH"):
        return False

    config_ini = Path(app.config.get("CONFIG_INI_FILE_PATH"))

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    for section, _ in cfg.items():
        for key, value in cfg.items(section):
            try:
                _value = int(value)

            except ValueError as e:
                _value = value
            
            app.config[key.upper()] = _value

    return True