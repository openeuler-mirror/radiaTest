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

import os
import configparser

import yaml


def loads_config_ini():
    server_config_ini = "/etc/radiaTest/server.ini"
    cfg = configparser.ConfigParser()
    cfg.read(server_config_ini)
    config = {}
    for section, _ in cfg.items():
        for key, value in cfg.items(section):
            try:
                _value = int(value)

            except ValueError as e:
                _value = value
            
            config[key.upper()] = _value
    # clean up config file if exists
    if os.path.isfile(server_config_ini):
        try:
            os.remove(server_config_ini)
        except Exception as err:
            raise RuntimeError(f"Could not remove {server_config_ini}: {str(err)}") from err
    return config


def loads_app_yaml(app):
    """
    The content of the yaml configuration file is:
        - appid = xxxx
          name = test
          secret = xxxx
    When an external platform requests an interface with an external-auth decorator,
    it will verify based on the configuration content
    """
    if os.path.exists(app.config.get("YAML_PATH")):
        with open(app.config.get("YAML_PATH"), 'r') as file:
            app_info = yaml.safe_load(file)
            if app_info:
                app.config["APP"] = app_info
                os.remove(app.config.get("YAML_PATH"))
    else:
        pass
