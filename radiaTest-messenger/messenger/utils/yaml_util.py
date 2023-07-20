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
import yaml


class YamlUtil:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path

    def get_yml_data(self, *key_names):
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        yaml_content = yaml.safe_load(content)

        try:
            for key_name in key_names:
                yaml_content = yaml_content.get(key_name, None)
            return yaml_content
        except Exception as e:
            return None
