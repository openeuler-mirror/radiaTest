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

import pandas as pd


class PandasDict:
    load_methods = {
        "csv": pd.read_csv,
        "xlsx": pd.read_excel,
        "xls": pd.read_excel,
    }


class Excel:
    def __init__(self, filetype):
        self.filetype = filetype
    
    def load(self, filepath, sheet_name=None):
        _load_method = PandasDict.load_methods[self.filetype]
        
        if self.filetype == 'csv':
            with open(filepath, 'rb') as file:
                df = _load_method(file)
                return df.to_dict("records")

        with open(filepath, 'rb') as file:
            df = dict()
            df = _load_method(file, sheet_name=sheet_name)
            total_df = []      
            
            for sheet in df.values():
                total_df += sheet.to_dict("records")
            
            return total_df


class SheetExtractor:
    def __init__(self, cols_dict) -> None:
        self._dict = cols_dict
    
    def run(self, data):
        _result = []

        for row in data:
            _row = {}
            for key, value in row.items():
                _name = key.strip()
                _value = str(value).strip()
                if _name in self._dict.keys() and value == value and value:
                    _row[self._dict.get(_name)] = _value
            
            _result.append(_row)

        return _result            
                

