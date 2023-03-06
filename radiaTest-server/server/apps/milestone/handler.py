import abc
from datetime import datetime
import json
import os
import io
import pytz

from flask.globals import current_app
import requests
from flask import g, jsonify

from server import redis_client
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert, Edit, Delete
from server.utils.page_util import PageUtil
from server.utils.response_util import RET
from server.utils.common_util import calculate_rate
from server.model.organization import Organization
from server.model.milestone import Milestone, IssueSolvedRate, TestReport
from server.model.mirroring import Repo
from server.model.template import Template
from server.model.product import Product
from server.model.task import TaskMilestone
from server.schema.milestone import GiteeMilestoneBase, GiteeMilestoneEdit, MilestoneStateEventSchema
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from server.utils.permission_utils import PermissionManager, GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server.utils.md_util import MdUtil


class CreateMilestone:
    @staticmethod
    def bind_scope(milestone_id, body, api_info_file):
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split("/")[-1], "")
        allow_list, deny_list = PermissionManager().get_api_list(
            "milestone", cur_dir + api_info_file, milestone_id
        )
        PermissionManager().generate(allow_list, deny_list, body)

    @staticmethod
    def run(body):
        if body.get("is_sync"):
            resp = MilestoneOpenApiHandler(body).create()
            if resp.get_json().get("error_code") != RET.OK:
                return resp
            milestone = Milestone.query.filter_by(
                name=body.get("name")).first()
            CreateMilestone.bind_scope(milestone.id, body, "api_infos.yaml")
            return jsonify(
                error_code=RET.OK, error_msg="Request processed successfully."
            )
        else:
            if body.get("start_time"):
                body["start_time"] = datetime.strptime(
                    body["start_time"], "%Y-%m-%d %H:%M:%S"
                )
            if body.get("end_time"):
                body["end_time"] = datetime.strptime(
                    body["end_time"], "%Y-%m-%d %H:%M:%S"
                )
            try:
                milestone_id = Insert(Milestone, body).insert_id(
                    Milestone, "/milestone"
                )
            except (IntegrityError, SQLAlchemyError) as e:
                raise RuntimeError(str(e))
            CreateMilestone.bind_scope(milestone_id, body, "api_infos.yaml")
            return jsonify(
                error_code=RET.OK, error_msg="Request processed successfully."
            )


class DeleteMilestone:
    @staticmethod
    def single(milestone_id):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} does not exist".format(milestone_id),
            )

        if milestone.is_sync is True:
            return MilestoneOpenApiHandler().delete(milestone_id)
        else:
            _tm = TaskMilestone.query.filter_by(
                milestone_id=milestone_id).all()
            if _tm:
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg="Delete failed, Some tasks have been associated with this milestone"
                )
            return ResourceManager("milestone", "v2").del_cascade_single(
                milestone_id, Template, [
                    Template.milestone_id == milestone_id], False
            )


class MilestoneHandler:
    @staticmethod
    @collect_sql_error
    def get_milestone(query, filter_params = None):
        if not filter_params:
            filter_params = list()

        if query.name:
            filter_params.append(Milestone.name.like(f"%{query.name}%"))
        if query.type:
            filter_params.append(Milestone.type == query.type)
        if query.state:
            filter_params.append(Milestone.state == query.state)
        if query.is_sync:
            filter_params.append(Milestone.is_sync == query.is_sync)
        if query.round_id:
            filter_params.append(Milestone.round_id == query.round_id)
        if query.product_id:
            filter_params.append(Milestone.product_id == query.product_id)

        query_filter = Milestone.query.filter(*filter_params).order_by(
            Milestone.product_id, Milestone.name, Milestone.create_time
        )
        if query.create_time_order:
            if query.create_time_order == "ascend":
                query_filter = Milestone.query.filter(*filter_params).order_by(
                    Milestone.create_time.asc()
                )
            if query.create_time_order == "descend":
                query_filter = Milestone.query.filter(*filter_params).order_by(
                    Milestone.create_time.desc()
                )

        if not query.paged:
            milestones = query_filter.all()
            data = dict()
            items = []
            for _m in milestones:
                items.append(_m.to_json())
            data.update(
                {
                    "total": query_filter.count(),
                    "items": items,
                }
            )
            return jsonify(error_code=RET.OK, error_msg="OK", data=data)

        def page_func(item):
            milestone_dict = item.to_json()
            return milestone_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR, error_msg=f"get milestone page error {e}"
            )

        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


class BaseOpenApiHandler:
    def __init__(self, table=None, namespace=None, gitee_id=None):
        self.table = table
        self.namespace = namespace
        self.gitee_id = gitee_id if gitee_id else g.gitee_id

    @abc.abstractmethod
    def gitee_2_radia(self):
        pass

    @abc.abstractmethod
    def radia_2_gitee(self):
        pass

    @property
    def access_token(self):
        return redis_client.hget(RedisKey.user(self.gitee_id), "gitee_access_token")

    @property
    def current_org(self):
        org_id = redis_client.hget(
            RedisKey.user(self.gitee_id), "current_org_id")
        org = Organization.query.filter_by(id=org_id).first()
        return org

    @collect_sql_error
    def add_update(self, act, url, data, schema, handler):
        data.update({"access_token": self.access_token})

        _resp = requests.request(
            method=act,
            url=url,
            data=json.dumps(schema(**data).__dict__),
            headers=current_app.config.get("HEADERS"),
        )

        _resp.encoding = _resp.apparent_encoding

        if (_resp.status_code != 200 and act == "PUT") or (
            _resp.status_code != 201 and act == "POST"
        ):
            current_app.logger.error(_resp.text)
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to add_update through gitee v8 openAPI",
            )

        gitee_milestone = json.loads(_resp.text)

        milestone = self.gitee_2_radia(gitee_milestone)

        _ = handler(self.table, milestone).single(self.table, self.namespace)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @collect_sql_error
    def query(self, url, params=None):
        _params = {
            "access_token": self.access_token,
        }
        if params is not None and isinstance(params, dict):
            _params.update(params)

        _resp = requests.get(
            url=url, params=_params, headers=current_app.config.get("HEADERS")
        )

        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code != 200:
            current_app.logger.error(_resp.text)
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get data through gitee openAPI",
            )

        return jsonify(error_code=RET.OK, error_msg="OK", data=_resp.text)


class MilestoneOpenApiHandler(BaseOpenApiHandler):
    def __init__(self, body=None):
        if body is not None:
            self.type = body.get("type")
            self.product_id = body.get("product_id")
            self.body = self.radia_2_gitee(body)
        super().__init__(Milestone, "/milestone")

    def gitee_2_radia(self, body):
        _body = self.body
        if isinstance(body.get("start_date"), str):
            _body["start_time"] = body.get("start_date")

        if isinstance(body.get("due_date"), str):
            _body["end_time"] = body.get("due_date")

        _body.update(
            {
                "gitee_milestone_id": body.get("id"),
                "name": body.get("title"),
                "type": self.type,
                "product_id": self.product_id,
                "is_sync": True,
            }
        )

        return _body

    def radia_2_gitee(self, body):
        if isinstance(body.get("start_time"), str):
            body["start_time"] = body.get("start_time")

        if isinstance(body.get("end_time"), str):
            body["end_time"] = body.get("end_time")

        return body

    @collect_sql_error
    def create(self):
        _url = "https://api.gitee.com/enterprises/{}/milestones".format(
            self.current_org.enterprise_id
        )

        return self.add_update(
            act="POST",
            url=_url,
            data=self.body,
            schema=GiteeMilestoneBase,
            handler=Insert,
        )

    def edit(self, milestone_id):
        _url = "https://api.gitee.com/enterprises/{}/milestones/{}".format(
            self.current_org.enterprise_id,
            milestone_id,
        )
        return self.add_update(
            act="PUT",
            url=_url,
            data=self.body,
            schema=GiteeMilestoneEdit,
            handler=Edit,
        )

    def delete(self, milestone_id):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR, error_msg="the milestone not exist"
            )
        _tm = TaskMilestone.query.filter_by(milestone_id=milestone_id).all()
        if _tm:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="Delete failed, Some tasks have been associated with this milestone"
            )

        _url = "https://api.gitee.com/enterprises/{}/milestones/{}".format(
            self.current_org.enterprise_id,
            milestone.gitee_milestone_id,
        )
        _resp = self.query(_url).get_json()
        if _resp.get("error_code") == RET.OK:
            if json.loads(_resp.get("data")).get("title") == milestone.name:
                return jsonify(
                    error_code=RET.RUNTIME_ERROR,
                    error_msg="you should delete this milestone in e.gitee.com first",
                )

        return ResourceManager("milestone", "v2").del_cascade_single(
            milestone_id, Template, [
                Template.milestone_id == milestone_id], False
        )

    def edit_state_event(self, milestone_id):
        _url = "https://api.gitee.com/enterprises/{}/milestones/{}".format(
            self.current_org.enterprise_id,
            milestone_id,
        )
        return self.add_update(
            act="PUT",
            url=_url,
            data=self.body,
            schema=MilestoneStateEventSchema,
            handler=Edit,
        )

    def get_milestones(self, params):
        _url = "https://api.gitee.com/enterprises/{}/milestones".format(
            self.current_org.enterprise_id,
        )
        _resp = self.query(url=_url, params=params)
        json_resp = _resp.get_json()
        if json_resp.get("error_code") == RET.OK:
            return jsonify(error_code=RET.OK, error_msg="OK", data=json.loads(json_resp.get("data")))
        return _resp


class IssueOpenApiHandlerV5:
    def __init__(self, enterprise, milestone) -> None:
        self.per_page = 100
        if current_app.config.get("ISSUES_PER_PAGE"):
            self.per_page = current_app.config.get("ISSUES_PER_PAGE")
        self.headers = None
        if current_app.config.get("HEADERS"):
            self.headers = current_app.config.get("HEADERS")

        self.url = "https://gitee.com/api/v5/enterprises/{}/issues".format(
            enterprise,
        )

        self.access_token = redis_client.hget(
            RedisKey.user(g.gitee_id), "gitee_access_token"
        )

        self.total_count, self.total_page = self._get_summary(
            enterprise,
            milestone,
        )

    def _get_summary(self, enterprise, milestone):
        _resp = requests.get(
            url=self.url,
            params={
                "access_token": self.access_token,
                "enterprise": enterprise,
                "milestone": milestone,
                "state": "all",
                "page": 1,
                "per_page": self.per_page,
            },
            headers=self.headers,
        )
        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code == 200:
            return (
                int(_resp.headers.get("total_count")),
                int(_resp.headers.get("total_page")),
            )
        else:
            return (0, 0)

    def get_all_list(self, params):
        _total_data = []

        for page in range(self.total_page):
            _resp = requests.get(
                url=self.url,
                params={
                    "access_token": self.access_token,
                    "enterprise": params["enterprise"],
                    "state": params["state"],
                    "sort": params["sort"],
                    "direction": params["direction"],
                    "page": page + 1,
                    "per_page": self.per_page,
                    "milestone": params["milestone"],
                },
                headers=self.headers,
            )

            if _resp.status_code == 200:
                _total_data += json.loads(_resp.text)

        return _total_data

    def getAll(self, params):
        total_data = self.get_all_list(params=params)
        return jsonify(total_data)


class IssueOpenApiHandlerV8(BaseOpenApiHandler):
    def get_all(self, params):
        _url = "https://api.gitee.com/enterprises/{}/issues".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url, params=params)

    def get(self, issue_id):
        _url = "https://api.gitee.com/enterprises/{}/issues/{}".format(
            self.current_org.enterprise_id, issue_id
        )
        return self.query(url=_url)

    def get_issue_types(self):
        _url = "https://api.gitee.com/enterprises/{}/issue_types".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url)

    def get_issue_states(self):
        _url = "https://api.gitee.com/enterprises/{}/issue_states".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url)


class IssueBaseHandlerV8:
    def __init__(self, gitee_id=None, org_id=None) -> None:
        self.issv8 = IssueOpenApiHandlerV8(gitee_id=gitee_id)
        if org_id is None:
            org_id = redis_client.hget(
                RedisKey.user(g.gitee_id), "current_org_id")
        org = Organization.query.filter_by(id=org_id).first()
        self.issue_types = redis_client.hget(
            RedisKey.issue_types(org.enterprise_id), "data")
        self.issue_types = self.issue_types[1:-1].replace(
            "\'", "\"").replace("}, {", "}#{").split("#")

        self.issue_states = redis_client.hget(
            RedisKey.issue_states(org.enterprise_id), "data")
        self.issue_states = self.issue_states[1:-1].replace(
            "\'", "\"").replace("}, {", "}#{").split("#")

    def get_bug_issue_type_id(self, title):
        type_id = None
        for _type in self.issue_types:
            _type = json.loads(_type)
            if _type.get("title") == title:
                type_id = _type.get("id")
                break
        return type_id

    def get_state_ids(self, solved_state):
        state_ids = ""
        for _stat in solved_state:
            for _type in self.issue_states:
                _type = json.loads(_type)
                if _type.get("title") == _stat:
                    state_ids = state_ids + str(_type.get("id")) + ","
                    break
        if len(state_ids) > 0:
            state_ids = state_ids[:-1]
        return state_ids

    def get_state_ids_inversion(self, inversion_solved_state: set):
        state_ids = ""
        for _type in self.issue_states:
            _type = json.loads(_type)
            if _type.get("title") not in inversion_solved_state:
                state_ids = state_ids + str(_type.get("id")) + ","
        if len(state_ids) > 0:
            state_ids = state_ids[:-1]
        return state_ids

    def get_issue_cnt_rate(self, param1, param2):
        solved_cnt, all_cnt, solved_rate = None, None, None
        all_cnt = self.get_issues_cnt(param1)
        if all_cnt is not None and int(all_cnt) == 0 and param2 is not None:
            return 0, 0, "100%"
        solved_cnt = self.get_issues_cnt(param2)

        if solved_cnt is not None and all_cnt is not None and int(all_cnt) != 0:
            solved_rate = int(solved_cnt) / int(all_cnt)
        if solved_rate is not None:
            solved_rate = "%.f%%" % (solved_rate * 100)
        return solved_cnt, all_cnt, solved_rate

    def get_issues_cnt(self, param):
        cnt = None
        if not param:
            return cnt
        resp = self.issv8.get_all(param)
        resp = resp.get_json()
        if resp.get("error_code") == RET.OK:
            cnt = json.loads(resp.get("data")).get("total_count")
            return int(cnt)
        return cnt


class IssueHandlerV8(IssueBaseHandlerV8):
    def __init__(self, gitee_id=None, org_id=None) -> None:
        super().__init__(gitee_id, org_id)
        self.bug_issue_type_id = self.get_bug_issue_type_id("缺陷")

    def get_issues(self, gitee_milestone_id, state_ids, uri):
        param = {
            "milestone_id": gitee_milestone_id,
            "issue_state_ids": state_ids,
            "issue_type_id": self.bug_issue_type_id,
        }
        resp = self.issv8.get_all(param)
        resp = resp.get_json()
        _data = None
        if resp.get("error_code") == RET.OK:
            data = json.loads(resp.get("data")).get("data")
            serious_data, main_data, minor_data, not_main_data, no_assign_data = [], [], [], [], []
            for d in data:
                priority = int(d.get("priority"))
                tmp_issue = {
                    "id": d.get("id"),
                    "ident": d.get("ident"),
                    "title": d.get("title"),
                    "url": f"{uri}/{d.get('ident')}?from=project-issue",
                    "priority": d.get("priority_human"),
                    "state": d.get("issue_state").get("title")
                }
                if priority == 4:
                    serious_data.append(tmp_issue)
                elif priority == 3:
                    main_data.append(tmp_issue)
                elif priority == 2:
                    minor_data.append(tmp_issue)
                elif priority == 1:
                    not_main_data.append(tmp_issue)
                else:
                    no_assign_data.append(tmp_issue)
            issue_data = serious_data + main_data + \
                minor_data + not_main_data + no_assign_data
            issue_data_cnt = len(issue_data)
            _data = {
                "serious_issue_rate": calculate_rate(len(serious_data), issue_data_cnt),
                "serious_issue_cnt": len(serious_data),
                "serious_issue": serious_data,
                "main_issue_rate": calculate_rate(len(main_data), issue_data_cnt),
                "main_issue_cnt": len(main_data),
                "main_issue": main_data,
                "minor_issue_rate": calculate_rate(len(minor_data), issue_data_cnt),
                "minor_issue_cnt": len(minor_data),
                "minor_issue": minor_data,
                "not_main_issue_rate": calculate_rate(len(not_main_data), issue_data_cnt),
                "not_main_issue_cnt": len(not_main_data),
                "not_main_issue": not_main_data,
                "no_assign_issue_rate": calculate_rate(len(no_assign_data), issue_data_cnt),
                "no_assign_issue_cnt": len(no_assign_data),
                "no_assign_issue": no_assign_data,
                "issue_data": issue_data,
                "issue_data_cnt": issue_data_cnt,
            }
        return _data

    def generate_update_test_report(self, milestone_id, uri):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        state_ids = self.get_state_ids_inversion(
            set(["已完成", "已验收", "已取消", "已拒绝", "已修复"])
        )
        data = self.get_issues(milestone.gitee_milestone_id, state_ids, uri)
        if data is None:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get data through gitee openAPI",
            )

        state_ids = self.get_state_ids_inversion(
            set(["已取消", "已拒绝"])
        )
        param = {
            "milestone_id": milestone.gitee_milestone_id,
            "issue_state_ids": state_ids,
            "issue_type_id": self.bug_issue_type_id,
        }
        all_issue_cnt = self.get_issues_cnt(param)
        if all_issue_cnt is None:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get data through gitee openAPI",
            )
        state_ids = self.get_state_ids(
            set(["已验收"])
        )
        param = {
            "milestone_id": milestone.gitee_milestone_id,
            "issue_state_ids": state_ids,
            "issue_type_id": self.bug_issue_type_id,
        }
        accepted_issue_cnt = self.get_issues_cnt(param)
        if accepted_issue_cnt is None:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get data through gitee openAPI",
            )

        issue_info = ""
        issue_info2 = ""
        for d in data.get("issue_data"):
            issue_info += "|{}|{}|{}||{}|".format(
                d.get('ident'),
                d.get('title'),
                d.get('priority'),
                d.get('state')
            ) + "\n"
            issue_info2 += "|[{}]({})|{}|{}||{}|".format(
                d.get('ident'),
                d.get('url'),
                d.get('title'),
                d.get('priority'),
                d.get('state')
            ) + "\n"
        issue_info = issue_info[:-1]
        issue_info2 = issue_info2[:-1]

        issue_rate_info = "|数目|{}|{}|{}|{}|{}|{}|".format(
                data.get('issue_data_cnt'),
                data.get('serious_issue_cnt'),
                data.get('main_issue_cnt'),
                data.get('minor_issue_cnt'),
                data.get('not_main_issue_cnt'),
                data.get('no_assign_issue_cnt') 
            ) + "\n"
        issue_rate_info += "|百分比||{}|{}|{}|{}|{}|".format(
                data.get('serious_issue_rate'),
                data.get('main_issue_rate'),
                data.get('minor_issue_rate'),
                data.get('not_main_issue_rate'),
                data.get('no_assign_issue_rate')
            )
        repo_info = ""
        repo_info_tmp = ""
        repo = Repo.query.filter_by(milestone_id=milestone_id).first()
        if repo:
            repo_info = repo.content
            for rp in repo_info.split("\n"):
                if "baseurl" in rp:
                    repo_info_tmp += rp.split("/")[4] + ":" + "/".join(
                        rp.split("=")[1].split("/")[:-2]) + "\n"
        product_info = f"|{milestone.name}|{milestone.start_time}|{milestone.end_time}|"

        all_testcase_cnt = 0
        failed_testcase_cnt = 0
        succeed_testcase_cnt = 0
        test_result = f"|{milestone.name}|{all_testcase_cnt}|\
            {succeed_testcase_cnt}/{failed_testcase_cnt}|{all_issue_cnt}|"
        accepted_result = "{}版本，共计执行 {} 个测试用例，<br>1）发现{}个问题，\
            <br>2）发现{}个问题，且已经验收通过。<br>".format(
                milestone.name,
                all_testcase_cnt,
                all_issue_cnt,
                accepted_issue_cnt
            )

        timestamp = datetime.now(tz=pytz.timezone(
            'Asia/Shanghai')).strftime('%Y%m%d%H%M%S')
        tmp_filename = "server/static/test_report_template.md"
        md_filename = f"{current_app.config.get('TEST_REPORT_PATH')}/test_report_{timestamp}.md"
        html_filename = f"{current_app.config.get('TEST_REPORT_PATH')}/test_report_{timestamp}.html"
        fmd = io.open(md_filename, "w", encoding="utf-8")
        lines = io.open(tmp_filename, "r", encoding="utf-8").readlines()
        for line in lines:
            fmd.write(
                line.replace("<product_name>", milestone.name)
                .replace("<product_info>", product_info)
                .replace("<accepted_result>", accepted_result)
                .replace("<repo_info>", repo_info_tmp)
                .replace("<issue_info>", issue_info)
                .replace("<issue_rate>", issue_rate_info)
                .replace("<issue_info2>", issue_info2)
                .replace("<test_result>", test_result)
            )
        fmd.close()
        md_text = open(md_filename, "r", encoding="utf-8").read()
        MdUtil.md2html(md_text, html_filename)
        _test_report = TestReport.query.filter_by(
            milestone_id=milestone_id
        ).first()
        if _test_report:
            _test_report.md_file = f"test_report_{timestamp}.md"
            _test_report.html_file = f"test_report_{timestamp}.html"
            _test_report.add_update()
        else:
            _test_report = Insert(
                TestReport,
                {
                    "md_file": f"test_report_{timestamp}.md",
                    "html_file": f"test_report_{timestamp}.html",
                    "milestone_id": milestone_id,
                }
            ).insert_obj()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_test_report.to_json()
        )


class IssueStatisticsHandlerV8(IssueBaseHandlerV8):
    def __init__(self, gitee_id=None, org_id=None) -> None:
        super().__init__(gitee_id, org_id)
        self.bug_issue_type_id = self.get_bug_issue_type_id("缺陷")

        self.all_state_ids = self.get_state_ids_inversion(
            set(["已挂起", "已取消", "已拒绝"])
        )
        self.serious_state_ids = self.get_state_ids(
            set(["已完成", "已验收", "已挂起", "已取消", "已拒绝"])
        )
        self.current_resolved_state_ids = self.get_state_ids(
            set(["已完成", "已验收"])
        )
        self.left_state_ids = self.get_state_ids(
            set(["已挂起"])
        )
        self.invalid_state_ids = self.get_state_ids(
            set(["已取消", "已拒绝"])
        )

    @staticmethod
    def get_gitee_id(org_id):
        access_token_list = redis_client.keys("access_token*")
        gitee_id = None
        for _token in access_token_list:
            _org_id = redis_client.hget(_token, "org_id")
            if int(_org_id) == int(org_id):
                gitee_id = _token.split("_")[-1]
                break
        return gitee_id

    @staticmethod
    def get_issue_type():
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id")
        org = Organization.query.filter(
            Organization.id == org_id, Organization.enterprise_id is not None).first()
        if not org:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="this organization has no right",
            )
        issue_types = redis_client.hget(
            RedisKey.issue_types(org.enterprise_id),
            "data"
        )
        issue_types = issue_types[1:-1].replace(
            "\'", "\"").replace("}, {", "}#{").split("#")
        _data = list()
        for _type in issue_types:
            _data.append(json.loads(_type))
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_data
        )

    @staticmethod
    def get_issue_state():
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id")
        org = Organization.query.filter(
            Organization.id == org_id, Organization.enterprise_id is not None).first()
        if not org:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="this organization has no right",
            )
        issue_states = redis_client.hget(
            RedisKey.issue_states(org.enterprise_id), "data")
        issue_states = issue_states[1:-1].replace(
            "\'", "\"").replace("}, {", "}#{").split("#")
        _data = list()
        for _state in issue_states:
            _data.append(json.loads(_state))
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_data
        )

    def get_milestone_issue_solved_rate(self, milestone):
        _, _, serious_resolved_rate = self.get_issue_cnt_rate(
            {
                "milestone_id": milestone.gitee_milestone_id,
                "priority": 4,
                "issue_state_ids": self.serious_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            },
            {
                "milestone_id": milestone.gitee_milestone_id,
                "priority": 4,
                "issue_type_id": self.bug_issue_type_id,
            },
        )

        _, _, main_resolved_rate = self.get_issue_cnt_rate(
            {
                "milestone_id": milestone.gitee_milestone_id,
                "priority": 3,
                "issue_state_ids": self.serious_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            },
            {
                "milestone_id": milestone.gitee_milestone_id,
                "priority": 3,
                "issue_type_id": self.bug_issue_type_id,
            },
        )

        (
            serious_main_resolved_cnt,
            serious_main_all_cnt,
            serious_main_resolved_rate,
        ) = self.get_issue_cnt_rate(
            {
                "milestone_id": milestone.gitee_milestone_id,
                "priority": "3,4",
                "issue_state_ids": self.serious_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            },
            {
                "milestone_id": milestone.gitee_milestone_id,
                "priority": "3,4",
                "issue_type_id": self.bug_issue_type_id,
            },
        )

        (
            current_resolved_cnt,
            current_all_cnt,
            current_resolved_rate,
        ) = self.get_issue_cnt_rate(
            {
                "milestone_id": milestone.gitee_milestone_id,
                "issue_state_ids": self.current_resolved_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            },
            {
                "milestone_id": milestone.gitee_milestone_id,
                "issue_state_ids": self.all_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            },
        )

        left_issues_cnt = self.get_issues_cnt(
            {
                "milestone_id": milestone.gitee_milestone_id,
                "issue_state_ids": self.left_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            }
        )
        invalid_issues_cnt = self.get_issues_cnt(
            {
                "milestone_id": milestone.gitee_milestone_id,
                "issue_state_ids": self.invalid_state_ids,
                "issue_type_id": self.bug_issue_type_id,
            }
        )

        return {
            "serious_resolved_rate": serious_resolved_rate,
            "main_resolved_rate": main_resolved_rate,
            "serious_main_resolved_cnt": serious_main_resolved_cnt,
            "serious_main_all_cnt": serious_main_all_cnt,
            "serious_main_resolved_rate": serious_main_resolved_rate,
            "current_resolved_cnt": current_resolved_cnt,
            "current_all_cnt": current_all_cnt,
            "current_resolved_rate": current_resolved_rate,
            "left_issues_cnt": left_issues_cnt,
            "invalid_issues_cnt": invalid_issues_cnt,
        }

    @staticmethod
    def get_rate_by_milestone(milestone_id):
        _milestones = Milestone.query.filter_by(
            is_sync=True, id=milestone_id).first()
        if not _milestones:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone does not exist.",
            )
        rate_data = IssueStatisticsHandlerV8().get_milestone_issue_solved_rate(
            _milestones
        )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=rate_data,
        )

    @staticmethod
    def get_rate_by_milestone2(milestone_id):
        _milestones = Milestone.query.filter_by(
            is_sync=True, id=milestone_id).first()
        if not _milestones:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone does not exist/has no right",
            )
        isr = IssueSolvedRate.query.filter_by(
            gitee_milestone_id=_milestones.gitee_milestone_id).first()
        data = dict()
        if isr:
            data = isr.to_json()
        return jsonify(error_code=RET.OK, error_msg="OK", data=data)

    @staticmethod
    def update_issue_rate():
        from celeryservice.lib.issuerate import UpdateIssueRate
        from celeryservice.tasks import logger
        UpdateIssueRate(logger).main()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @staticmethod
    def update_milestone_issue_rate_by_field(milestone_id, field):
        from celeryservice.lib.issuerate import update_field_issue_rate
        milestone = Milestone.query.filter_by(
            id=milestone_id, is_sync=True).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone does not exist/has no right",
            )
        issue_rate = IssueSolvedRate.query.filter_by(
            gitee_milestone_id=milestone.gitee_milestone_id).first()
        if not issue_rate:
            Insert(
                IssueSolvedRate,
                {"milestone_id": milestone.id,
                    "gitee_milestone_id": milestone.gitee_milestone_id}
            ).single(IssueSolvedRate, "/issue_solved_rate")

        update_field_issue_rate.delay(
            "milestone",
            g.gitee_id,
            {"org_id": milestone.org_id, "product_id": milestone.product_id},
            field,
            milestone.gitee_milestone_id
        )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )
