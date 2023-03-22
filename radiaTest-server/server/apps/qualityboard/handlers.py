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
import io

from flask import jsonify, current_app, g, make_response
from sqlalchemy import func, or_
import pytz
import xlwt
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db, redis_client
from sqlalchemy import and_
from server.model.qualityboard import Checklist, QualityBoard, CheckItem, Round, SameRpmCompare, RpmCompare
from server.model.milestone import IssueSolvedRate, Milestone
from server.model.organization import Organization
from server.model.product import Product
from server.utils.db import Edit, Select, collect_sql_error, Insert
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

        md_content = None
        with open(f"/tmp/release-management/{product_version}/release-plan.md", 'r'
        ) as f:
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
                table_row = self.table(**data)
                db.session.add(table_row)
                db.session.flush()
                feature_id = table_row.id

                re_row = self.re_table(
                    **{
                        "feature_id": feature_id,
                        "is_new": True,
                        "product_id": self.product_id,
                        "is_archived": False,                       
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
        _filename = f"{_product_version}-{self.repo_path}-{self.arch}"
        _round = None
        if self._round.type == "round":
            _round = self._round.round_num
            _filename = f"{_product_version}-round-{_round}-{self.repo_path}-{self.arch}"

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
                "gitee_id": g.gitee_id,
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
    def update_round_issue_rate_by_field(round_id, field):
        from celeryservice.lib.issuerate import update_field_issue_rate
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

        update_field_issue_rate.delay(
            "round",
            g.gitee_id,
            {"org_id": _round.product.org_id, "product_id": _round.product_id},
            field,
            round_id
        )
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
    def __init__(self, repo_path, round_id=None, rg=None, arches=None) -> None:
        self.repo_path = repo_path
        self.round_id = round_id
        self.rg = rg
        self.arches = arches

    def get_pkg_compare_result(self):
        wb = None
        pkg_results = RpmCompare.query.filter(
            RpmCompare.round_group_id == self.rg.id,
            RpmCompare.repo_path == self.repo_path,
            RpmCompare.arch.in_(self.arches),
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
        if os.path.exists(file_path) and not new_result:
            # 读取保存的文件
            filedata = open(file_path, 'rb').read()
        else:
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