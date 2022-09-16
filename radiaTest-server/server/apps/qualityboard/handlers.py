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
from collections import defaultdict
from datetime import datetime
from math import floor
import os
import subprocess

from flask import jsonify, current_app, g
from sqlalchemy import func, or_
import pytz

from server import db, redis_client
from server.model.qualityboard import Checklist, QualityBoard, CheckItem
from server.model.milestone import IssueSolvedRate, Milestone
from server.model.organization import Organization
from server.model.product import Product
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
        if query.product_name:
            _ps = Product.query.filter_by(name=query.product_name).all()
            if _ps:
                for _p in _ps:
                    _filter.append(
                        Checklist.products.contains(_p)
                    )
        filter_chain = Checklist.query.filter(*_filter)
        page_dict, e = PageUtil.get_page_dict(
            filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
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

    @staticmethod
    @collect_sql_error
    def checklist_sync_product_all(product_name):
        _ps = Product.query.filter_by(name=product_name, is_forced_check=True).all()
        if _ps:
            _filter = []
            for _p in _ps:
                _filter.append(
                    Checklist.products.contains(_p)
                )
            cls = Checklist.query.filter(or_(*_filter)).all()
            for cl in cls:
                for _p in _ps:
                    if cl.products.index(_p) < 0:
                        cl.products.append(_p)
                cl.add_update()
            return jsonify(
                error_code=RET.OK,
                error_msg="OK."
            )
        else:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product doesn't exist,or doesn't need to be checked."
            )

    @staticmethod
    @collect_sql_error
    def checklist_sync_product_single(checklist_id, product_id):
        _cl = Checklist.query.filter_by(id=checklist_id).first()
        if not _cl:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="Checklist  dodes not exist"
            )
        cp = _cl.products[0]
        if product_id == 0:
            ps = Product.query.filter_by(name=cp.name).all()
            for _p in ps:
                if _cl.products.index(_p) < 0:
                    _cl.products.append(_p)
                    _cl.add_update()
        else:
            p = Product.query.filter_by(id=product_id).first()
            if not p:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="product dodes not exist"
                )
            if cp.name != p.name:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="checklist dodes not match product"
                )
            if _cl.products.index(p) >= 0:
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg="checklist has matched product"
                )
            _cl.products.append(p)
            _cl.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )


class QualityResultCompareHandler:
    def __init__(self, product_id, milestone_id=None) -> None:
        self.product_id = product_id
        self.milestone_id = milestone_id

    def compare_issue_rate(self, field: str):
        if self.milestone_id:
            isr = IssueSolvedRate.query.filter_by(
                milestone_id=self.milestone_id
            ).first()
        else:
            isr = Product.query.filter_by(
                id=self.product_id
            ).first()
        if not isr:
            return None
        isr_json = isr.to_json()
        field_val = isr_json.get(field)
        baseline, operation = self.get_baseline(field)
        if not field_val or not baseline:
            return None
        if "rate" in field:
            field_val = field_val.replace("%", "")
            baseline = baseline.replace("%", "")

        lt =  lambda x, y: x < y
        gt =  lambda x, y: x > y
        le =  lambda x, y: x <= y
        ge =  lambda x, y: x >= y
        eq =  lambda x, y: x == y
        operation_dict = {
            "<": lt,
            ">": gt,
            "<=": le,
            ">=": ge,
            "=": eq,
        }
        ret = operation_dict.get(operation)(int(field_val), int(baseline))
        return ret

    @collect_sql_error
    def get_baseline(self, field):
        baseline, operation = None, None
        p = Product.query.filter_by(id=self.product_id).first()
        cl = Checklist.query.join(CheckItem).filter(
            Checklist.products.contains(p),
            CheckItem.field_name == field,
            Checklist.checkitem_id == CheckItem.id,
        ).first()
        if not cl:
            return None, None

        if self.milestone_id:
            m = Milestone.query.filter_by(id=self.milestone_id).first()
            if m.type == "round":
                iter_num = int(m.name.split("-")[-1])
                if len(cl.rounds) < iter_num:
                    return None, None
                r_flag = cl.rounds[iter_num - 1]
                if r_flag == "1":
                    return cl.baseline, cl.operation 
                else:
                    return None, None 
        
        if p.version_type == "LTS-SPx":
            if cl.lts_spx:
                baseline = cl.baseline
                operation = cl.operation
        elif p.version_type == "LTS":
            if cl.lts:
                baseline = cl.baseline
                operation = cl.operation
        else:
            if cl.innovation:
                baseline = cl.baseline
                operation = cl.operation
        return baseline, operation


class CheckItemHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        _filter = []
        if query.field_name:
            _filter.append(CheckItem.field_name.like(f'%{query.field_name}%'))
        if query.title:
            _filter.append(CheckItem.title.like(f'%{query.title}%'))
        filter_chain = CheckItem.query.filter(*_filter)
        if not query.paged:
            cis = filter_chain.all()
            data = dict()
            items = []
            for _ci in cis:
                items.append(_ci.to_json())
            data.update(
                {
                    "total": filter_chain.count(),
                    "items": items,
                }
            )
            return jsonify(
                error_code=RET.OK,
                error_msg='OK',
                data=data
            )
        
        page_dict, e = PageUtil.get_page_dict(
            filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f'get checkitem page error {e}'
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

    def __init__(self, table, qualityboard_id) -> None:
        self.table = table
        self.qualityboard_id = qualityboard_id

    @abc.abstractmethod
    def get_md_content(self, product_version) -> str:
        pass

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
    
    @abc.abstractmethod
    def store(self, socket_namespace=None):
        pass


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
                "pushd /tmp/release-management && git pull && popd"
            )
        else:
            exitcode, _ = subprocess.getstatusoutput(
                "pushd /tmp && git clone https://gitee.com/openeuler/release-management && popd"
            )
        if exitcode != 0:
            return None

        md_content = None
        with open(f"/tmp/release-management/{product_version}/release-plan.md", 'r') as f:
            md_content = f.read()

        return md_content
    
    def store(self, socket_namespace=None):       
        for data in self.rows:
            if data.get("status") == "discussion":
                continue
            
            _is_done, _is_testing, _is_developing = False, False, False
            if isinstance(data.get("status"), str):
                _is_done = data.get("status").lower() == "accepted"
                _is_testing = data.get("status").lower() == "testing"
                _is_developing = data.get("status").lower() == "developing"

            _row = self.table.query.filter_by(
                no=data.get("no")
            ).first()
            if not _row:
                Insert(
                    self.table,
                    {
                        "qualityboard_id": self.qualityboard_id,
                        **data,
                    }
                ).single(
                    self.table, socket_namespace
                )
            else:
                Edit(
                    self.table,
                    {
                        "id": _row.id,
                        **data,
                    }
                ).single(
                    self.table, socket_namespace
                )
        
    def statistic(self, _is_new: bool):
        result = defaultdict(int)

        _query = db.session.query(func.count(self.table.id))
        result["developing_count"] = _query.filter_by(
            qualityboard_id=self.qualityboard_id,
            is_new=_is_new,
            status='Developing',
        ).scalar()
        result["testing_count"] = _query.filter_by(
            qualityboard_id=self.qualityboard_id,
            is_new=_is_new,
            status="Testing",
        ).scalar()
        result["accepted_count"] = _query.filter_by(
            qualityboard_id=self.qualityboard_id,
            is_new=_is_new,
            status="Accepted",
        ).scalar()

        accepted_count = result["developing_count"] + result["testing_count"] + result["accepted_count"]

        result["accepted_rate"] = 100
        if accepted_count != 0:
            result["accepted_rate"] = floor(
                result["accepted_count"] / accepted_count * 100
            )
        
        return result


feature_list_handlers = {
    "default": FeatureListHandler,
    "openEuler": OpenEulerReleasePlanHandler,
}


class PackageListHandler:
    def __init__(self, qualityboard_id, milestone_id, refresh : bool = False) -> None:
        self.refresh = refresh

        self.qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        if not self.qualityboard:
            raise ValueError(f"qualityboard {qualityboard_id} does not exist")

        self.milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not self.milestone:
            raise ValueError(f"milestone {milestone_id} does not exist")

        org_id = self.milestone.org_id
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"this api only serves for milestones of organizations")
        
        if self.milestone.type == "round":
            self.pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_DAILYBUILD_REPO_URL")
            if not self.pkgs_repo_url:
                raise ValueError(
                    f"lack of definition of {org.name.upper()}_DAILYBUILD_REPO_URL, please check the settings"
                )
        elif self.milestone.type == "release":
            self.pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_OFFICIAL_REPO_URL")
            if not self.pkgs_repo_url:
                raise ValueError(
                    f"lack of definition of {org.name.upper()}_OFFICIAL_REPO_URL, please check the settings"
                )

        self.packages = self.get_packages()

    def get_packages(self):
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        _product_version = f"{self.milestone.product.name}-{self.milestone.product.version}"
        _filename = _product_version
        _round = None
        if self.milestone.type == "round":
            _round = self.qualityboard.iteration_version.split("->").index(str(self.milestone.id)) + 1
            _filename = f"{_product_version}-round-{_round}"

        if self.refresh and not redis_client.hgetall(f"resolving_{_filename}_pkglist"):
            redis_client.hset(
                f"resolving_{_filename}_pkglist", "gitee_id", g.gitee_id
            )
            redis_client.hset(
                f"resolving_{_filename}_pkglist", 
                "resolve_time", 
                datetime.now(
                    tz=pytz.timezone('Asia/Shanghai')
                ).strftime("%Y-%m-%d %H:%M:%S")
            )
            redis_client.expire(f"resolving_{_filename}_pkglist", 1800)
            
            resolve_pkglist_after_resolve_rc_name.delay(
                repo_url=self.pkgs_repo_url,
                product=_product_version,
                _round=_round,
            )
            raise RuntimeError(
                f"the packages of {self.milestone.name} " \
                f"start resolving, please wait for several minutes"
            )
        elif self.refresh:
            raise RuntimeError(
                f"LOCKED: the packages of {self.milestone.name} " \
                f"has been in resolving process, " \
                "please wait in patient or try again after a half hour"
            )

        try:
            return RpmNameLoader.load_rpmlist_from_file(
                f"{_path}/{_filename}.pkgs",
            )
        except FileNotFoundError as e:
            raise ValueError(
                f"resolve packages of {_filename} failed, " \
                f"please check whether it exists in {self.pkgs_repo_url}"
            ) from e

    def compare(self, packages):
        if not self.packages or not packages:
            return None
        
        rpm_name_dict_comparer = RpmNameLoader.rpmlist2rpmdict(self.packages)
        rpm_name_dict_comparee = RpmNameLoader.rpmlist2rpmdict(packages)

        return RpmNameComparator.compare_rpm_dict(
            rpm_name_dict_comparee,
            rpm_name_dict_comparer,
        )
