# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang, disnight
# @email   : ethanzhang55@outlook.com fjc837005411@outlook.com
# @Date    : 2022/09/04
# @License : Mulan PSL v2
#####################################

import abc
import os
import subprocess

from flask import jsonify, current_app

from server.model.qualityboard import Checklist, QualityBoard
from server.model.milestone import Milestone
from server.model.organization import Organization
from server.utils.db import Edit, collect_sql_error, Insert
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.md_util import MdUtil
from server.utils.rpm_util import RpmName, RpmNameComparator, RpmNameLoader
from celeryservice.tasks import resolve_pkglist_after_resolve_rc_name


class ChecklistHandler:
    @staticmethod
    @collect_sql_error
    def handler_get_one(checklist_id):
        _checklist = Checklist.query.get(checklist_id)
        if not _checklist:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="current checklist does not exist/already deleted"
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_checklist.to_json()
        )

    @staticmethod
    @collect_sql_error
    def handler_get_checklist(query):
        _filter = []
        if query.check_item:
            _filter.append(Checklist.check_item.like(f'%{query.check_item}%'))
        filter_chain = Checklist.query.filter(*_filter)
        page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f'get checklist page error {e}'
            )
        return jsonify(
            error_code=RET.OK,
            error_msg='OK',
            data=page_dict
        )


class FeatureListResolver:
    """parse html format text
    table format as follow
    <table>
        <thead>
            <tr><th>xxx</th><th>xxx</th></tr>
        </thead>
        <tbody>
            <tr><td>xxx</td><td>xxx</td></tr>
            <tr><td>xxx</td><td>xxx</td></tr>
        </tbody>
    </table>
    """

    def __init__(self, table_content):
        self.table_content = table_content
    
    @abc.abstractmethod
    def parse_table(self):
        pass

    @abc.abstractmethod
    def parse_td_text(self):
        pass


class OpenEulerFeatureListResolver(FeatureListResolver):
    def parse_table(self):
        """parse xpath table element 2 python list

        Args:
            table_content (xpath node): result of html.xpath("//table") element
        
        return:
            list: [[th list],[td list 1], [td list 2]]
        """
        table_result = []
        # 解析 thead
        thead_list = self.table_content.xpath("thead/tr/th")
        if not thead_list:
            current_app.logger.debug("html content has no table info")
            return []
        thead_content_list = []
        for thead in thead_list:
            thead_content_list.append(thead.text)
        table_result.append(thead_content_list)
        # 解析 tbody
        tbody_tr_list = self.table_content.xpath("tbody/tr")
        for tbody_tr in tbody_tr_list:
            td_content_list = []
            td_list = tbody_tr.xpath("td")
            # 渲染md过程中,该组件会将连在表格后面的内容一起转换在table标签下,对这些内容进行过滤
            if td_list and (not self.parse_td_text(td_list[0])):
                break
            for td in td_list:
                td_content_list.append(self.parse_td_text(td))
            table_result.append(td_content_list)
        return table_result

    def parse_td_text(self, td_content):
        """parse td’s text and chile nodes' text

        Args:
            self.table_content (xpath node): result of html.xpath("td") element

        td format as follow:
            <td>text</td>
            <td><a>text1</a><a>text1</a></td>
        
        return:
            list: [tds' text]
        """
        if td_content.text:
            return td_content.text
        a_list = td_content.xpath("a")
        if a_list:
            result = []
            for a_content in a_list:
                if a_content.text:
                    result.append(a_content.text) 
            return " ".join(result)
        return ""


class FeatureListHandler:
    resolver = FeatureListResolver
    table_num = 1
    target_index = 0
    colname_dict = {}

    def __init__(self, table) -> None:
        self.table = table 

    def get_md_content(self, product_version) -> str:
        return None

    def resolve(self, md_content):
        resolver = self.resolver
        _data = MdUtil.get_md_tables2list(md_content, resolver)
        if isinstance(_data, list) and len(_data) == self.table_num:
            self.rows = self.extract(_data)

    def transform_colname(self, colnames: list):
        for i, colname in enumerate(colnames):
            if self.colname_dict.get(colname):
                colnames[i] = self.colname_dict.get(colname)
        
    def extract(self, _list):
        rows = _list[self.target_index]
        if not isinstance(rows, list):
            return None
        colnames = rows.pop(0)
        if not isinstance(colnames, list):
            return None
        
        if self.colname_dict:
            self.transform_colname(colnames)

        for i, row in enumerate(rows):
            rows[i] = dict(zip(colnames, row))
        
        return rows
        
    def store(self, qualityboard_id, socket_namespace=None):       
        for data in self.rows:
            Insert(
                self.table,
                {
                    "qualityboard_id": qualityboard_id,
                    **data,
                }
            ).single(
                self.table, socket_namespace
            )


class OpenEulerReleasePlanHandler(FeatureListHandler):
    resolver = OpenEulerFeatureListResolver
    table_num = 2
    target_index = 1
    colname_dict = {
        "发布方式": "release_to",
        "涉及软件包列表": "pkgs",
    }

    def get_md_content(self, product_version) -> str:
        if os.path.isdir("/tmp/release-management"):
            exitcode, _ = subprocess.getstatusoutput(
                "pushd /tmp/release-management && git pull && popd"\
            )
        else:
            exitcode, _ = subprocess.getstatusoutput(
                "pushd /tmp && git clone https://gitee.com/openeuler/release-management && popd"\
            )
        if exitcode != 0:
            return None
        
        md_content = None
        with open(f"/tmp/release-management/{product_version}/release-plan.md", 'r') as f:
            md_content = f.read()

        return md_content

    
feature_list_handlers = {
    "default": FeatureListHandler,
    "openEuler": OpenEulerReleasePlanHandler,
}


class PackageListHandler:
    def __init__(self, qualityboard_id, milestone_id) -> None:
        self.qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not self.qualityboard:
            raise ValueError(f"qualityborad {qualityboard_id} does not exist")
        self.milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not self.milestone:
            raise ValueError(f"milestone {milestone_id} does not exist")

        org_id = self.milestone.org_id
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"this api only serves for milestones of organizations")
        
        self.pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_PACKAGELIST_REPO_URL")
        if not self.pkgs_repo_url:
            raise ValueError(
                f"lack of definition of {org.name.upper()}_PACKAGELIST_REPO_URL, please check the settings"
            )

        self.packages = self.get_packages()

    def get_packages(self):
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        _product_version = f"{self.milestone.product.name}-{self.milestone.product.version}"
        _round = None

        if self.milestone.type == "round":
            _round = self.qualityboard.iteration_version.split("->").index(str(self.milestone.id)) + 1

        if not os.path.isfile(f"{_path}/{_product_version}.pkgs"):
            resolve_pkglist_after_resolve_rc_name.delay(
                repo_url=self.pkgs_repo_url,
                product=_product_version,
                _round=_round,
            )         
            raise RuntimeError(
                f"the packages of {self.milestone.name} " \
                f"have not been resolved yet, please try again after several minutes"
            )

        try:
            if self.milestone.type != "round":
                return RpmNameLoader.load_rpmlist_from_file(
                    f"{_path}/{_product_version}.pkgs",
                )
            else:
                return RpmNameLoader.load_rpmlist_from_file(
                    f"{_path}/{_product_version}-round-{_round}.pkgs",
                )
        except FileNotFoundError as e:
            raise RuntimeError(
                f"resolve packages of {_product_version}-round-{_round} failed, " \
                f"please check whether it exists in {self.pkgs_repo_url}"
            ) from e

    def compare(self, packages):
        if not self.packages or not packages:
            return None
        
        rpm_name_dict_comparee = RpmNameLoader.rpmlist2rpmdict(self.packages)
        rpm_name_dict_comparer = RpmNameLoader.rpmlist2rpmdict(packages)

        return RpmNameComparator.compare_rpm_dict(
            rpm_name_dict_comparee,
            rpm_name_dict_comparer,
        )