# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
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
# @Date    : 2026/09/09
# @License : Mulan PSL v2
#####################################
from server.utils.sheet import Excel, SheetExtractor


def test_sheet_extractor_maps_and_strips():
    extractor = SheetExtractor({"名称": "name", "数量": "count"})
    result = extractor.run([{"名称": " x ", "数量": " 3 ", "other": "z"}])
    assert result == [{"name": "x", "count": "3"}]


def test_sheet_extractor_drops_empty_and_nan_values():
    extractor = SheetExtractor({"名称": "name", "数量": "count"})
    result = extractor.run([{"名称": None, "数量": float("nan")}])
    assert result == [{}]


def test_sheet_extractor_drops_unknown_columns():
    extractor = SheetExtractor({"known": "name"})
    result = extractor.run([{"unknown1": "a", "unknown2": "b"}])
    assert result == [{}]


def test_excel_loads_csv_records(tmp_path):
    csv_path = tmp_path / "t.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    assert Excel("csv").load(str(csv_path)) == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
