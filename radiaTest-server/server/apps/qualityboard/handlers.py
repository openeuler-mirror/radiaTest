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
import re
from collections import defaultdict
from datetime import datetime
from math import floor
import os
import subprocess
import io

from flask import jsonify, current_app, g, make_response, send_file
from sqlalchemy import func
import requests
import pytz
import xlwt
import redis
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db, redis_client
from server.apps.issue.handler import GiteeV8BaseIssueHandler
from server.apps.qualityboard.excel_report import QualityReport, ATReport
from server.model.qualityboard import Checklist, CheckItem, Round, SameRpmCompare, RpmCompare, QualityBoard
from server.model.milestone import IssueSolvedRate, Milestone
from server.model.organization import Organization
from server.model.product import Product
from server.utils.at_utils import OpenqaATStatistic
from server.utils.db import Select, collect_sql_error, Insert
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.md_util import MdUtil
from server.utils.rpm_util import RpmNameComparator, RpmNameLoader
from celeryservice.tasks import resolve_pkglist_after_resolve_rc_name, resolve_pkglist_from_url
from server.utils.shell import add_escape


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
            data=_checklist.to_json2()
        )

    @staticmethod
    @collect_sql_error
    def handler_get_checklist(query):
        _filter = []
        if query.product_id:
            _filter.append(Checklist.product_id == query.product_id)
        filter_chain = Checklist.query.filter(*_filter)
        if not query.paged:
            cls = filter_chain.all()
            data = dict()
            items = []
            for _cl in cls:
                items += _cl.to_json2()
            data.update(
                {
                    "total": len(items),
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
                error_msg=f'get checklist page error {e}'
            )
        return jsonify(
            error_code=RET.OK,
            error_msg='OK',
            data=page_dict
        )


class ChecklistResultHandler:
    @staticmethod
    def get_issue_checklist_result(round_id):
        data = []
        _round = Round.query.filter_by(id=round_id).first()
        issue_rate_dict = dict()
        issue_rate = IssueSolvedRate.query.filter_by(round_id=round_id, type="round").first()
        if issue_rate:
            issue_rate_dict = issue_rate.to_json()
        else:
            return data

        round_num = int(_round.round_num)
        if round_num == 100:
            round_num = 0
        
        _cls = Checklist.query.join(CheckItem).filter(
            Checklist.product_id == _round.product.id,
            Checklist.checkitem_id == CheckItem.id,
            CheckItem.type == "issue",
        ).all()
        
        for _cl in _cls:
            if _cl.rounds[round_num] == "1":
                fns = _cl.checkitem.field_name.split("_")
                passed = "_".join(fns[:-1] + ["passed"])
                data.append(
                    {
                       "title": _cl.checkitem.title,
                       "baseline": _cl.baseline.split(",")[round_num],
                       "operation": _cl.operation.split(",")[round_num],
                       "current_value": issue_rate_dict.get(_cl.checkitem.field_name),
                       "compare_result": issue_rate_dict.get(passed),
                    }
                )
        return data


class QualityResultCompareHandler:
    def __init__(self, obj_type, obj_id) -> None:
        self.obj_type = obj_type
        self.obj_id = obj_id

    def compare_result_baseline(self, field: str, field_val):
        baseline, operation = self.get_baseline(field)
        if baseline is None:
            return None
        field_val = str(field_val).replace("%", "")
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

    def compare_issue_rate(self, field: str, field_val=None):
        if field_val is None:
            if self.obj_type == "product":
                isr = Product.query.filter_by(
                    id=self.obj_id
                ).first()
            elif self.obj_type == "milestone":
                isr = IssueSolvedRate.query.filter_by(
                    milestone_id=self.obj_id, type="milestone"
                ).first()
            elif self.obj_type == "round":
                isr = IssueSolvedRate.query.filter_by(
                    round_id=self.obj_id, type="round"
                ).first()
            if not isr:
                return None
            isr_json = isr.to_json()
            field_val = isr_json.get(field)

        if field_val is None:
            return None
        return self.compare_result_baseline(field, field_val)

    @collect_sql_error
    def get_baseline(self, field):
        p = None
        if self.obj_type == "product": 
            p = Product.query.filter_by(id=self.obj_id).first()
            iter_num = 0
        elif self.obj_type == "round":
            _round = Round.query.filter_by(id=self.obj_id).first()
            if not _round:
                return None, None
            iter_num = int(_round.round_num)
            p = _round.product
        elif self.obj_type == "milestone":
            m = Milestone.query.filter_by(id=self.obj_id).first()
            if not m:
                return None, None
            if m.type == "round":
                iter_num = m.round.round_num
            elif m.type == "release":
                iter_num = 0
            else:
                return None, None
            p = m.product

        if p is None:
            return None, None
        cl = Checklist.query.join(CheckItem).filter(
            Checklist.product_id == p.id,
            CheckItem.field_name == field,
            Checklist.checkitem_id == CheckItem.id,
        ).first()
        if not cl:
            return None, None

        if len(cl.rounds) == 0 or len(cl.rounds) <= iter_num:
            return None, None
        r_flag = cl.rounds[iter_num]
        if r_flag == "1":
            return cl.baseline.split(",")[iter_num], cl.operation.split(",")[iter_num]
        else:
            return None, None 


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


class FeatureResolver:
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


class OpenEulerFeatureResolver(FeatureResolver):
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


class FeatureHandler:
    resolver = FeatureResolver
    table_num = 1
    target_index = 0
    colname_dict = {}

    def __init__(self, table, re_table, **kwargs) -> None:
        self.table = table
        self.re_table = re_table
        if kwargs.get("product_id"):
            self.product_id = kwargs.get("product_id")


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


class OpenEulerReleasePlanHandler(FeatureHandler):
    resolver = OpenEulerFeatureResolver
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
                "pushd /tmp && git clone \
                    https://gitee.com/openeuler/release-management && popd"
            )
        if exitcode != 0:
            return None

        file_path = f"/tmp/release-management/{product_version}/release-plan.md"
        if not os.path.exists(file_path):
            return None
        md_content = None
        with open(file_path, 'r') as f:
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
                try:
                    table_row = self.table(**data)
                    db.session.add(table_row)
                    db.session.flush()
                except (IntegrityError, SQLAlchemyError, TypeError) as e:
                    db.session.rollback()
                    raise e
                feature_id = table_row.id

                re_row = self.re_table(
                    **{
                        "feature_id": feature_id,
                        "is_new": True,
                        "product_id": self.product_id,
                    }
                )
                db.session.add(re_row)
                try:
                    db.session.commit()
                except (IntegrityError, SQLAlchemyError) as e:
                    db.session.rollback()
                    raise e
            else:
                for key, value in data.items():
                    if value is not None:
                        setattr(_row, key, value)
                try:
                    db.session.commit()
                except (IntegrityError, SQLAlchemyError) as e:
                    db.session.rollback()
                    raise e


    def statistic(self, _is_new: bool):
        result = defaultdict(int)
        result["developing_count"] = self._stat_status(_is_new, "Developing")
        result["testing_count"] = self._stat_status(_is_new, "Testing")
        result["accepted_count"] = self._stat_status(_is_new, "Accepted")
        
        accepted_count = result["developing_count"] + \
            result["testing_count"] + result["accepted_count"]
         
        result["accepted_rate"] = 100
        if accepted_count != 0:
            result["accepted_rate"] = floor(
                result["accepted_count"] / accepted_count * 100
            )
        
        return result


    def _stat_status(self, _is_new, _status):
        _query = db.session.query(func.count(self.table.id))
        filter_params = [
            self.re_table.product_id == self.product_id,
            self.re_table.is_new == _is_new,
            self.re_table.feature_id == self.table.id
        ]
        _count = _query.filter(
            *filter_params,
            self.table.status == _status,
        ).scalar()

        return _count


feature_handlers = {
    "default": FeatureHandler,
    "openEuler": OpenEulerReleasePlanHandler,
}


class PackageListHandler:
    def __init__(self, round_id, repo_path, arch) -> None:
        self.repo_path = repo_path
        self.arch = arch

        self._round = Round.query.filter_by(id=round_id).first()
        if not self._round:
            raise ValueError(f"round {round_id} does not exist")

        org_id = self._round.product.org_id
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"this api only serves for milestones of organizations")
        
        if self._round.type == "round":
            self.pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_DAILYBUILD_REPO_URL")
            if not self.pkgs_repo_url:
                raise ValueError(
                    f"lack of definition of {org.name.upper()}_DAILYBUILD_REPO_URL, please check the settings"
                )
        elif self._round.type == "release":
            self.pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_OFFICIAL_REPO_URL")
            if not self.pkgs_repo_url:
                raise ValueError(
                    f"lack of definition of {org.name.upper()}_OFFICIAL_REPO_URL, please check the settings"
                )

        self.packages = self.get_packages()

    def get_packages(self):
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        _product_version = f"{self._round.product.name}-{self._round.product.version}"
        _filename = f"{_product_version}-{self.repo_path}"
        _round = None
        if self._round.type == "round":
            _round = self._round.round_num
            _filename = f"{_product_version}-round-{_round}-{self.repo_path}"
        if self.arch != "":
            _filename = f"{_filename}-{self.arch}"

        try:
            return RpmNameLoader.load_rpmlist_from_file(
                f"{_path}/{_filename}.pkgs",
            )
        except FileNotFoundError as e:
            raise ValueError(
                f"resolve packages of {_filename} failed, " \
                f"please refetch data manually or check whether it exists in {self.pkgs_repo_url}"
            ) from e

    @staticmethod
    def get_all_packages_file(round_id):
        _round = Round.query.filter_by(id=round_id).first()
        org = Organization.query.filter_by(id=_round.product.org_id).first()
        _product = _round.product.name + "-" + _round.product.version
        if _round.type == "release":
            _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_OFFICIAL_REPO_URL")
            _filename_p = f"{_product}-release"
            round_num = None
        else:
            _pkgs_repo_url = current_app.config.get(f"{org.name.upper()}_DAILYBUILD_REPO_URL")
            _filename_p = f"{_product}-round-{_round.round_num}"
            round_num = _round.round_num

        if _round.product.built_by_ebs is True and _round.type != "release":
            _pkgs_repo_url = f"{_pkgs_repo_url}/EBS-{_product}"
        else:
            _pkgs_repo_url = f"{_pkgs_repo_url}/{_product}"

        key_val = f"resolving_{_filename_p}_pkglist"
        _keys = redis_client.keys(key_val)
        if len(_keys) > 0:
            raise RuntimeError(
                f"LOCKED: the packages of {_round.name} " \
                f"has been in resolving process, " \
                "please wait in patient or try again after a half hour"
            )
        redis_client.hmset(
            key_val,
            {
                "user_id": g.user_id,
                "resolve_time": datetime.now(
                    tz=pytz.timezone('Asia/Shanghai')
                ).strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        redis_client.expire(key_val, 1800)
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        resolve_pkglist_after_resolve_rc_name.delay(
            repo_url=_pkgs_repo_url,
            store_path=_path,
            product=_product,
            round_num=round_num,
        )

    def compare(self, packages):
        if not self.packages or not packages:
            return None
        
        rpm_name_dict_comparer, repeat_rpm_list_comparer = RpmNameLoader.rpmlist2rpmdict(self.packages)
        rpm_name_dict_comparee, repeat_rpm_list_comparee = RpmNameLoader.rpmlist2rpmdict(packages)

        return RpmNameComparator.compare_rpm_dict(
            rpm_name_dict_comparee,
            rpm_name_dict_comparer,
        ), repeat_rpm_list_comparer, repeat_rpm_list_comparee

    def compare2(self, packages):
        if not self.packages or not packages:
            return None
        
        rpm_name_dict_comparer = RpmNameLoader.rpmlist2rpmdict_by_name(self.packages)
        rpm_name_dict_comparee = RpmNameLoader.rpmlist2rpmdict_by_name(packages)

        return RpmNameComparator.compare_rpm_dict2(
            rpm_name_dict_comparee,
            rpm_name_dict_comparer,
        )


class DailyBuildPackageListHandler(PackageListHandler):
    def __init__(self, repo_name, repo_path, arch, repo_url) -> None:
        self.repo_name = repo_name
        self.repo_path = f"{repo_name}-{repo_path}-{arch}"
        self.repo_url = repo_url
        self.packages = self.get_packages() 

    def get_packages(self):
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")

        try:
            return RpmNameLoader.load_rpmlist_from_file(
                f"{_path}/{self.repo_path}.pkgs",
            )
        except FileNotFoundError as e:
            raise ValueError(
                f"resolve packages of {self.repo_name} failed, " \
                f"please refetch data manually or check whether it exists in {self.repo_url}"
            ) from e

    @staticmethod
    def get_all_packages_file(repo_name, repo_url):
        key_val = f"resolving_{repo_name}_pkglist"
        _keys = redis_client.keys(key_val)
        if len(_keys) > 0:
            raise RuntimeError(
                f"LOCKED: the packages of {repo_name} " \
                f"has been in resolving process, " \
                "please wait in patient or try again after a half hour"
            )
        redis_client.hmset(
            key_val,
            {
                "user_id": g.user_id,
                "resolve_time": datetime.now(
                    tz=pytz.timezone('Asia/Shanghai')
                ).strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        redis_client.expire(key_val, 1800)
        _path = current_app.config.get("PRODUCT_PKGLIST_PATH")
        resolve_pkglist_from_url.delay(
            repo_name=repo_name,
            repo_url=repo_url,
            store_path=_path,
        )


class RoundHandler:
    @staticmethod
    def add_round(product_id, milestone_id):
        p = Product.query.filter_by(id=product_id).first()
        m = Milestone.query.filter_by(id=milestone_id).first()
        if not p or not m:
            raise RuntimeError(
                "product or milestone does not exist."
            )
        round_num = m.name.split("-")[-1]
        round_name = f"{p.name}-{p.version}-round-{round_num}"
        round_type = "round"
        if m.type == "release":
            round_num = "100"
            round_type = "release"
            round_name = f"{p.name}-{p.version}-release"
        r = Round.query.filter_by(name=round_name).first()
        if not r:
            data = {
                "name": round_name,
                "round_num": round_num,
                "type": round_type,
                "default_milestone_id": milestone_id,
                "product_id": product_id
            }
            r = Insert(Round, data).insert_obj()
        m = Milestone.query.filter_by(id=milestone_id).first()
        m.round_id = r.id
        m.add_update()
        return r.id

    @staticmethod
    def bind_round_milestone(round_id, milestone_ids, isbind):
        _round = Round.query.filter_by(id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round or milstone does not exist",
            )
        
        for m_id in milestone_ids.split(","):
            m = Milestone.query.filter_by(id=m_id).first()
            if not m:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"milstone {m_id} does not exist",
                )
            r = Round.query.filter_by(default_milestone_id=m.id).first()
            if r:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"milstone {m.name} can only bind to round {r.name}",
                )
            if isbind:
                m.round_id = round_id
            else:
                m.round_id = None
            m.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
        )

    @staticmethod
    def get_rate_by_round(round_id):
        _round = Round.query.filter_by(id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist",
            )
        isr = IssueSolvedRate.query.filter_by(
            round_id=round_id, type="round").first()
        data = dict()
        if isr:
            data = isr.to_json()
        return jsonify(error_code=RET.OK, error_msg="OK", data=data)

    @staticmethod
    def get_rounds(product_id):
        return Select(Round, {"product_id":product_id}).precise()

    @staticmethod
    def update_round_issue_rate(round_id):
        from celeryservice.lib.issuerate import UpdateIssueRateData
        _round = Round.query.filter_by(
            id=round_id).first()
        if not _round:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="round does not exist",
            )
        issue_rate = IssueSolvedRate.query.filter_by(
            round_id=round_id, type="round").first()
        if not issue_rate:
            Insert(
                IssueSolvedRate,
                {"round_id": round_id, "type": "round"}
            ).single()

        uird = UpdateIssueRateData(
           {"product_id": _round.product_id, "org_id": _round.product.org_id} 
        )
        uird.update_issue_resolved_rate_round(round_id)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class CompareRoundHandler:
    def __init__(self, round_id) -> None:
        self.round_id = round_id

    @collect_sql_error
    def excute(self, compare_round_ids):
        """
        修改当前round的比对round项
        @param: compare_round_ids: list, 比对项id列表
        @return: 异常,返回错误信息;正常,返回{error_code, error_msg, round_data}
        """
        round_ = Round.query.filter_by(id=self.round_id).first()
        if not round_:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the round does not exist"
            )

        for compare_round_id in compare_round_ids:
            if self.round_id == compare_round_id:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"The id of round and compare round can't be equal."
                )
            compare_round = Round.query.filter_by(id=compare_round_id).first()
            if not compare_round:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"the round whose id is {compare_round_id} does not exist"
                )
        comparee_round_ids_list = list(map(str, compare_round_ids))
        round_.comparee_round_ids = ",".join(comparee_round_ids_list)
        round_.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=round_.to_json(),
        )


class PackagCompareResultExportHandler:
    def __init__(self, repo_path=None, round_id=None, rg=None, arches=None) -> None:
        self.repo_path = repo_path
        self.round_id = round_id
        self.rg = rg
        self.arches = arches

    def get_pkg_compare_result(self):
        wb = None
        filter_param = [
            RpmCompare.round_group_id == self.rg.id,
            RpmCompare.repo_path == self.repo_path
        ]
        if self.arches is not None:
            filter_param.append(RpmCompare.arch.in_(self.arches))
        pkg_results = RpmCompare.query.filter(
            *filter_param
        ).all()
        if not pkg_results:
            return wb
        comparer_round = Round.query.get(self.rg.round_1_id)
        comparee_round = Round.query.get(self.rg.round_2_id)
        cnt = 1
        wb = xlwt.Workbook()
        ws = wb.add_sheet(f"{self.repo_path}")
        ws.write(0, 0, comparer_round.name)
        ws.write(0, 1, comparee_round.name)
        if self.repo_path == "source":
            ws.write(0, 2, "compare result")
            for pkg_result in pkg_results:
                ws.write(cnt, 0, pkg_result.rpm_comparee)
                ws.write(cnt, 1, pkg_result.rpm_comparer)
                ws.write(cnt, 2, pkg_result.compare_result)
                cnt += 1
        else:
            ws.write(0, 2, "arch")
            ws.write(0, 3, "compare result")
            for pkg_result in pkg_results:
                ws.write(cnt, 0, pkg_result.rpm_comparee)
                ws.write(cnt, 1, pkg_result.rpm_comparer)
                ws.write(cnt, 2, pkg_result.arch)
                ws.write(cnt, 3, pkg_result.compare_result)
                cnt += 1
        return wb

    def get_same_pkg_compare_result(self):
        wb = None
        pkg_results = SameRpmCompare.query.filter(
            SameRpmCompare.round_id == self.round_id,
            SameRpmCompare.repo_path == self.repo_path,
        ).all()
        if not pkg_results:
            return wb
        wb = xlwt.Workbook()
        ws = wb.add_sheet(f"{self.repo_path}")
        ws.write(0, 0, "rpm_arm")
        ws.write(0, 1, "rpm_x86")
        ws.write(0, 2, "compare result")
        cnt = 1
        for pkg_result in pkg_results:
            ws.write(cnt, 0, pkg_result.rpm_arm)
            ws.write(cnt, 1, pkg_result.rpm_x86)
            ws.write(cnt, 2, pkg_result.compare_result)
            cnt += 1
        return wb

    def get_compare_result_file(self, file_path, new_result=False, pkg_type="same"):
        # 保证获取excel为最新数据
        if os.path.exists(file_path):
            os.remove(file_path)
        wb = None
        if pkg_type == "same":
            wb = self.get_same_pkg_compare_result()
        else:
            wb = self.get_pkg_compare_result()

        if wb is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no compare data.",
            )

        # 保存比对结果到文件中
        wb.save(file_path)

        # 保存比对结果到文件流中
        stream = io.BytesIO()
        wb.save(stream)
        filedata = stream.getvalue()
        stream.close()

        response = make_response(filedata)
        response.headers["Content-Disposition"] = f'attachment; filename={file_path.split("/")[-1]}'
        response.headers["Content-Type"] = 'application/x-xlsx'
        return response


# 重写GiteeV8BaseIssueHandler query方法返回值, 返回可操作的dict
class GiteeV8IssueHandlerV2(GiteeV8BaseIssueHandler):
    @collect_sql_error
    def query(self, url, params=None):
        _params = {
            "access_token": self.access_token,
        }
        if params is not None and isinstance(params, dict):
            _params.update(params)
        _resp = requests.get(
            url=url, params=_params, headers=self.headers
        )
        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code != 200:
            current_app.logger.error(_resp.text)
            raise Exception(f"gitee v8 接口请求失败，{_resp.text}")
        return _resp.json()


class ReportHandler(object):

    def __init__(self, product_id, params):
        self.product_id = product_id
        self.round_id = params.get("round_id")
        self.branch = params.get("branch")
        self.params = params
        self.gitee_v8_handler = GiteeV8IssueHandlerV2()
        self.max_overdue_days = 0

    @staticmethod
    def verify_date_str(date_str):
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}$", date_str) is None:
            return False
        else:
            return True

    def format_date(self, date_str):
        if not date_str:
            return ""
        if self.verify_date_str(date_str) is True:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y/%m/%d")
        else:
            return "日期解析失败"

    def get_all_issue(self, params):
        # 递归获取所有issue
        res = self.gitee_v8_handler.get_all(params)
        total = res.get("total_count")
        page = params.get("page")
        per_page = params.get("per_page")
        data = res.get("data")
        if int(total) > int(page) * int(per_page):
            params["page"] = page + 1
            data.extend(self.get_all_issue(params))
        return data

    def get_all_issue_by_type_name(self, type_name=None):
        # 获取issue_type为type_name所有issue
        filter_param = [Milestone.product_id == self.product_id, Milestone.is_sync.is_(True)]
        if self.round_id:
            filter_param.append(Milestone.round_id == self.round_id)
        milestones = Milestone.query.filter(*filter_param).all()
        issue_list = []
        if not milestones:
            return issue_list
        m_ids = ",".join([str(i.gitee_milestone_id) for i in milestones])
        query_dict = self.params.__dict__
        update_params = {
                "milestone_id": m_ids,
                "per_page": 100  # 接口最大条数100
            }
        if type_name:
            update_params["issue_type_id"] = self.gitee_v8_handler.get_bug_issue_type_id(type_name)
        query_dict.update(update_params)
        # 从第一页开始递归获取当前条件下的所有issue
        query_dict["page"] = 1
        return self.get_all_issue(query_dict)

    def get_overdue_days(self, deadline, finished_at):
        if not deadline:
            return '无截止日期'
        if self.verify_date_str(deadline) is False:
            return '截止日期格式错误'
        # 获取逾期日期
        deadline_date = datetime.strptime(deadline, "%Y-%m-%dT%H:%M:%S%z").replace(hour=23, minute=59, second=59)
        if finished_at and self.verify_date_str(finished_at):
            finished_date = datetime.strptime(finished_at, "%Y-%m-%dT%H:%M:%S%z").replace(hour=23, minute=59, second=59)
            if finished_date > deadline_date:
                return str((finished_date - deadline_date).days)
            else:
                return '未逾期'
        now_date = datetime.now(tz=pytz.timezone('Asia/Shanghai')).astimezone(
            deadline_date.tzinfo).replace(hour=23, minute=59, second=59)
        if deadline_date >= now_date:
            return '未逾期'
        return str((now_date - deadline_date).days)

    @staticmethod
    def parse_lables(labels):
        label_dict = {}
        all_label_str = ""
        if not labels:
            return {
                "SIG": "未知",
                "block": "否"
            }, all_label_str

        for label in labels:
            label_name = label["name"]
            if not all_label_str:
                all_label_str = label_name
            else:
                all_label_str = f"{all_label_str},{label_name}"
            if label_name.startswith("sig/"):
                label_dict["SIG"] = label_name.split("sig/")[1]
            else:
                label_dict["SIG"] = '未知'
            if label_name.lower() == "block":
                label_dict["block"] = "是"
            else:
                label_dict["block"] = "否"
        return label_dict, all_label_str

    @staticmethod
    def get_di(priority_dict):
        """
        DI = 10×W1＋3×W2＋1×W3＋0.1×W4
        W1：致命问题数。
        W2：严重问题数。
        W3：主要问题数。
        W4：次要、不重要问题数。
        """
        di = 0
        for priority, priority_count in priority_dict.items():
            if priority == "严重":
                di += 10 * priority_count
            elif priority == "主要":
                di += 3 * priority_count
            elif priority == "次要":
                di += 1 * priority_count
            else:
                di += 0.1 * priority_count
        return di

    @staticmethod
    def get_ratio(part, total):
        if isinstance(part, int) and isinstance(total, int) and total != 0:
            return "{:.2%}".format(part / total)
        else:
            return "NAN"

    def issue_sort_compare(self, issue):
        """
        issue列表复杂排序
        排序权重 严重：500 block 200  逾期 0-100  无责任人 50  无优先级 20
        严重 > block > 逾期 > 优先级
        """
        score = 0
        if issue.get("priority_human") == "严重":
            score += 500
        elif issue.get("priority_human") == "无优先级":
            score += 20
        else:
            score += int(issue["priority"])

        if issue["is_block"] == "是":
            score += 200
        if issue["overdue_days"].isdigit() and self.max_overdue_days > 0:
            score += 100 * int(issue["overdue_days"]) / self.max_overdue_days
        if issue.get("assignee_username") == "未知":
            score += 50
        issue["score"] = score
        return score

    def issue_statistic(self, issue_list):
        # 遍历所有issue
        unclosed_list = []  # 所有未闭环issue
        sig_count = {}  # sig统计
        milestone_count = {}  # 里程碑统计
        issue_count = {
            "status": {},  # issue状态分布
            "priority": {},  # 优先级统计
            "total": 0,  # 有效总数
            "all_count": 0,  # 总数
            "unclosed": 0,  # 未闭环数量
            "closed": 0,  # 闭环数量
            "focus": 0,  # 关注issue(严重或阻塞)数量
            "assignee_count": {},
        }

        for issue in issue_list:
            # 分支过滤
            branch = issue["branch"] if issue.get("branch") else ""
            if self.branch and self.branch != branch:
                continue
            label_dict, all_label_str = self.parse_lables(issue["labels"])
            status = issue["issue_state"]["title"]
            sig_name = label_dict.get("SIG")
            is_block = label_dict.get("block", "否")
            priority_human = issue["priority_human"]
            if status not in issue_count["status"]:
                issue_count["status"][status] = 1
            else:
                issue_count["status"][status] += 1

            issue_count["all_count"] += 1
            # 过滤无效问题单
            if status == "已取消":
                continue
            issue_count["total"] += 1

            if priority_human not in issue_count["priority"]:
                issue_count["priority"][priority_human] = 1
            else:
                issue_count["priority"][priority_human] += 1

            if sig_name not in sig_count:
                sig_count[sig_name] = {"total": 1, "unclosed": 0, "priority": {priority_human: 1}}
            else:
                sig_count[sig_name]["total"] += 1
                if priority_human not in sig_count[sig_name]["priority"]:
                    sig_count[sig_name]["priority"][priority_human] = 1
                else:
                    sig_count[sig_name]["priority"][priority_human] += 1

            milestone = issue["milestone"]["title"] if issue.get("milestone") else "未关联里程碑"
            if milestone not in milestone_count:
                milestone_count[milestone] = {"total": 0, "closed": 0}
            milestone_count[milestone]["total"] += 1

            # 总体版本已验收算闭环, 迭代版本已完成也算闭环
            if self.round_id:
                closed_status = ["已完成", "已验收"]
            else:
                closed_status = ["已验收"]
            if status in closed_status:
                milestone_count[milestone]["closed"] += 1
                issue_count["closed"] += 1
            else:
                issue_count["unclosed"] += 1
                sig_count[sig_name]["unclosed"] += 1

            if status in closed_status:
                continue

            if issue["assignee"]:
                assignee_username = issue["assignee"]["username"]
                assignee_name = issue["assignee"]["name"]
            else:
                assignee_username = "未知"
                assignee_name = "未知"
            if assignee_name not in issue_count["assignee_count"]:
                issue_count["assignee_count"][assignee_name] = 1
            else:
                issue_count["assignee_count"][assignee_name] += 1

            overdue_days = self.get_overdue_days(issue["deadline"], issue["finished_at"])
            format_issue = {
                "milestone": milestone,
                "issue_id": issue["ident"],
                "issue_title": issue["title"],
                "assignee_username": assignee_username,
                "assignee_name": assignee_name,
                "assignee_enterprise": "",
                "plan_started_at": self.format_date(issue["plan_started_at"]),
                "deadline": self.format_date(issue["deadline"]),
                "finished_at": self.format_date(issue["finished_at"]),
                "issue_type": issue["issue_type"]["title"],
                "priority": issue["priority"],
                "priority_human": issue["priority_human"],
                "branch":  branch,
                "status": status,
                "SIG": sig_name,
                "is_block": is_block,
                "overdue_days": overdue_days,
                "label": all_label_str,
            }
            if overdue_days.isdigit() and self.max_overdue_days < int(overdue_days):
                self.max_overdue_days = int(overdue_days)

            if is_block == "是" or issue["priority_human"] == "严重":
                issue_count["focus"] += 1
            if status not in closed_status:
                unclosed_list.append(format_issue)

        # 汇总计算
        closed_rate = self.get_ratio(issue_count["closed"], issue_count["total"])
        for sig_name, sig_info in sig_count.items():
            # DI值计算
            sig_info["DI"] = self.get_di(sig_info["priority"])

        for milestone, milestone_info in milestone_count.items():
            milestone_info["closed_rate"] = self.get_ratio(milestone_info["closed"], milestone_info["total"])
        # 完成率、验收率
        completed_rate = self.get_ratio(issue_count["status"].get("已完成", 0) + issue_count["status"].get("已验收", 0),
                                        issue_count["total"])
        approved_rate = self.get_ratio(issue_count["status"].get("已验收", 0), issue_count["total"])
        version_di = self.get_di(issue_count["priority"])

        return {
            "branch": self.branch,
            "version_di": version_di,
            "closed_rate": closed_rate,
            "milestone_count": milestone_count,
            "issue_count": issue_count,
            "sig_count": sig_count,
            "is_round": True if self.round_id else False,
            "completed_rate": completed_rate,
            "approved_rate": approved_rate,
            "unclosed_list": sorted(unclosed_list, key=self.issue_sort_compare, reverse=True),
        }

    def get_quality_report(self):
        all_issue_list = self.get_all_issue_by_type_name("缺陷")
        product = Product.query.filter_by(id=self.product_id).first()
        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product does not exist.",
            )
        product_name = f"{product.name}_{product.version}"
        if self.round_id:
            _round = Round.query.filter_by(id=self.round_id).first()
            if not _round:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="round does not exist.",
                )
            if _round.type == "release":
                round_name = f"{_round.type}"
            else:
                round_name = f"{_round.type}_{_round.round_num}"
        else:
            round_name = None

        quality_report = QualityReport(product_name, round_name=round_name).generate_excel_report(
            self.issue_statistic(all_issue_list))
        if not os.path.exists(quality_report):
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="质量报告生成失败"
            )
        return send_file(quality_report, as_attachment=True)

    def get_branch_list(self):
        branch_list = []
        for issue in self.get_all_issue_by_type_name("缺陷"):
            branch = issue.get("branch")
            if branch and branch not in branch_list:
                branch_list.append(branch)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=branch_list,
        )


class ATOverviewHandler:
    def __init__(self, qualityboard_id):
        self.openqa_url = current_app.config.get("OPENQA_URL")
        self.qualityboard_id = qualityboard_id
        self.qualityboard = QualityBoard.query.filter_by(id=qualityboard_id).first()
        product = self.qualityboard.product
        self.product_name = f"{product.name}-{product.version}"

        self.scrapyspider_pool = redis.ConnectionPool.from_url(
            current_app.config.get("SCRAPYSPIDER_BACKEND"), decode_responses=True)
        self.redis_client = redis.StrictRedis(connection_pool=self.scrapyspider_pool)

    def close(self):
        self.redis_client.close()
        self.scrapyspider_pool.disconnect()

    def get_builds_list(self, start=None, end=None, desc=True):
        product_name = self.product_name
        total_count = self.redis_client.zcard(product_name)
        if not start:
            start = 0
        if not end:
            end = total_count - 1
        builds_list = self.redis_client.zrange(product_name, start, end, desc=desc)
        return_data = {
            "total_num": total_count,
        }
        if not builds_list:
            return_data = {
                "total_num": 0,
                "data": [],
            }
        else:
            return_data["data"] = list(
                map(
                    lambda build: OpenqaATStatistic(
                        arches=current_app.config.get("SUPPORTED_ARCHES"),
                        product=product_name,
                        build=build,
                        redis_client=self.redis_client,
                    ).group_overview,
                    builds_list
                )
            )

        self.scrapyspider_pool.disconnect()
        return return_data

    def get_build_detail(self, build_name):
        at_statistic = OpenqaATStatistic(
            arches=current_app.config.get(
                "SUPPORTED_ARCHES", ["aarch64", "x86_64"]
            ),
            product=self.product_name,
            build=build_name,
            redis_client=self.redis_client
        )
        self.scrapyspider_pool.disconnect()
        return at_statistic.tests_overview

    def get_overview(self, query):
        if not self.qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(self.qualityboard_id)
            )
        build_name = query.get("build_name")
        if not build_name:
            page_num = query.get("page_num")
            page_size = query.get("page_size")
            _start = (page_num - 1) * page_size
            _end = page_num * page_size - 1
            builds_list = self.get_builds_list(start=_start, end=_end, desc=query.get("build_order") == "descend")
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=builds_list.get("data"),
                total_num=builds_list.get("total_num")
            )
        else:
            build_detail = self.get_build_detail(build_name)

            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=build_detail,
            )


class ATReportHandler(object):
    def __init__(self, qualityboard_id):
        self.qualityboard_id = qualityboard_id

    def get_quality_report(self):
        at_handler = ATOverviewHandler(self.qualityboard_id)
        if not at_handler.qualityboard:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="qualityboard {} not exitst".format(self.qualityboard_id)
            )
        builds_list = at_handler.get_builds_list(desc=True).get("data")
        if not builds_list:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="build list is null!".format(self.qualityboard_id)
            )

        for build_info in builds_list:
            build_info["detail_list"] = at_handler.get_build_detail(build_info["build"])

        at_report = ATReport(at_handler.product_name).generate_excel_report(builds_list)

        if not os.path.exists(at_report):
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="AT报告生成失败"
            )
        return send_file(at_report, as_attachment=True)
