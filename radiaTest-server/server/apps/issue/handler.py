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

import abc
import json

from flask import g, jsonify

from server import redis_client, db
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert
from server.utils.response_util import RET
from server.utils.open_api_util import BaseOpenApiHandler
from server.utils.page_util import PageUtil
from server.model.milestone import Milestone
from server.model.issue import Issue
from server.model.task import TaskMilestone
from server.model.testcase import Case
from server.schema.issue import GiteeCreateIssueSchema, CreateIssueSchema, QueryIssueSchema
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class IssueOpenApiHandler(BaseOpenApiHandler):
    @abc.abstractmethod
    def get_all(self, params):
        pass

    @abc.abstractmethod
    def get(self, issue_id):
        pass

    @abc.abstractmethod
    def get_issue_types(self):
        pass

    @abc.abstractmethod
    def get_issue_states(self):
        pass


class QuickIssueBaseHandler(IssueOpenApiHandler):
    pass


class IssueV5BaseHandler(IssueOpenApiHandler):
    pass


class GiteeV8BaseIssueHandler(IssueOpenApiHandler):
    def __init__(self, body=None, org_id=None):
        if body is not None:
            self.body = body
        if org_id is None:
            org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        super().__init__(Issue, "/issue", org_id=org_id)

    @property
    def issue_types(self):
        _issue_types = redis_client.hget(
            RedisKey.issue_types(self.current_org.enterprise_id), "data")
        if _issue_types:
            return json.loads(_issue_types)
        else:
            resp = self.get_issue_types()
            resp = resp.get_json()
            if resp.get("error_code") == RET.OK:
                issue_types = json.loads(
                    resp.get("data")
                ).get("data")
                t_issue_types = []
                for _type in issue_types:
                    t_issue_types.append(
                        {
                            "id": _type.get("id"),
                            "title": _type.get("title"),
                        }
                    )
                redis_client.hmset(
                    RedisKey.issue_types(self.current_org.enterprise_id),
                    {"data": json.dumps(t_issue_types)}
                )
                return t_issue_types
            else:
                return []

    @property
    def issue_states(self):
        _issue_states = redis_client.hget(
            RedisKey.issue_states(self.current_org.enterprise_id), "data")
        if _issue_states:
            return json.loads(_issue_states)
        else:
            resp = self.get_issue_states()
            resp = resp.get_json()
            if resp.get("error_code") == RET.OK:
                issue_states = json.loads(
                    resp.get("data")
                ).get("data")

                t_issue_states = []
                for _state in issue_states:
                    t_issue_states.append(
                        {
                            "id": _state.get("id"),
                            "title": _state.get("title"),
                        }
                    )
                redis_client.hmset(
                    RedisKey.issue_states(self.current_org.enterprise_id),
                    {"data": json.dumps(t_issue_states)}
                )
                return t_issue_states
            else:
                return []

    def gitee_2_radia(self, body):
        radia_body = self.body
        radia_body.update(
            {
                "gitee_issue_id": body.get("id"),
                "ident": body.get("ident"),
                "gitee_issue_url": body.get("issue_url"),
                "creator_id": g.user_id,
            }
        )
        return radia_body

    def radia_2_gitee(self, body):
        gitee_body = dict()
        gitee_body.update({
            "title": body.get("title"),
            "description": body.get("description"),
            "project_id": body.get("project_id"),
            "issue_type_id": body.get("issue_type_id"),
        })
        
        if body.get("gitee_milestone_id"):
            gitee_body.update({
                "milestone_id": body.get("gitee_milestone_id"),
            })
        if body.get("priority") is not None:
            gitee_body.update({
                "priority": body.get("priority"),
            })
        return gitee_body

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

    @collect_sql_error
    def create(self):
        _url = "https://api.gitee.com/enterprises/{}/issues".format(
            self.current_org.enterprise_id
        )

        return self.add_update(
            act="POST",
            url=_url,
            data=self.radia_2_gitee(self.body),
            schema=GiteeCreateIssueSchema,
            handler=Insert,
        )

    def get_projects(self, params):
        _url = "https://api.gitee.com/enterprises/{}/projects".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url, params=params)

    def get_project_id(self, search):
        project_id = redis_client.hget(
            RedisKey.projects(self.current_org.enterprise_id), search)
        if project_id:
            return project_id
        else:
            resp = self.get_projects({"search": search})
            resp = resp.get_json()
            if resp.get("error_code") == RET.OK:
                projects = json.loads(
                    resp.get("data")
                ).get("data")
                redis_client.hset(
                    RedisKey.projects(self.current_org.enterprise_id),
                    projects[0].get("name"),
                    projects[0].get("id"),
                )
                return projects[0].get("id")
            else:
                return None

    def get_all_project(self):
        projects = redis_client.hgetall(
            RedisKey.projects(self.current_org.enterprise_id)
        )
        data = list()
        if projects:
            for project_name, project_id in projects.items():
                data.append(
                    {
                        "name": project_name,
                        "id": project_id
                    }
                )
            return data
        else:
            return data

    def get_bug_issue_type_id(self, title):
        type_id = None
        for _type in self.issue_types:
            if _type.get("title") == title:
                type_id = _type.get("id")
                break
        return type_id

    def get_state_ids(self, solved_state):
        state_ids = ""
        for _stat in solved_state:
            for _type in self.issue_states:
                if _type.get("title") == _stat:
                    state_ids = state_ids + str(_type.get("id")) + ","
                    break
        if len(state_ids) > 0:
            state_ids = state_ids[:-1]
        return state_ids

    def get_state_ids_inversion(self, inversion_solved_state: set):
        state_ids = ""
        for _type in self.issue_states:
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
        resp = self.get_all(param)
        resp = resp.get_json()
        if resp.get("error_code") == RET.OK:
            cnt = json.loads(resp.get("data")).get("total_count")
            return int(cnt)
        return cnt

    def get_all_issues(self, param):
        resp = self.get_all(param)
        resp = resp.get_json()
        if resp.get("error_code") == RET.OK:
            total = json.loads(resp.get("data")).get("total_count")
            data = json.loads(resp.get("data")).get("data")
            return total, data
        return 0, []


class GiteeV8IssueHandler:
    @staticmethod
    def create_issue(body: CreateIssueSchema):
        milestone = Milestone.query.filter_by(id=body.milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"milestone does not exist.",
            )
        case = Case.query.get(body.case_id)
        if not case:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"case does not exist.",
            )
        tm = TaskMilestone.query.filter(
            TaskMilestone.milestone_id == body.milestone_id,
            TaskMilestone.task_id == body.task_id,
            TaskMilestone.cases.contains(case),
        ).first()
        if not tm:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"task with case does not exist.",
            )
        project_id = GiteeV8BaseIssueHandler().get_project_id(body.project_name)
        if project_id is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"project {body.project_name} in gitee does not exist.",
            )

        body_dict = body.__dict__
        body_dict.update(
            {
                "project_id": project_id,
                "gitee_milestone_id": milestone.gitee_milestone_id,
            }
        )
        gitee_issue = GiteeV8BaseIssueHandler(body=body_dict)
        
        return gitee_issue.create()

    @staticmethod
    @collect_sql_error
    def sync_issue(gitee_issue_id, body):
        milestone = Milestone.query.filter_by(
            id=body.get("milestone_id")
        ).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"milestone does not exist.",
            )
        case = Case.query.get(body.get("case_id"))
        if not case:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"case does not exist.",
            )
        tm = TaskMilestone.query.filter(
            TaskMilestone.milestone_id == body.get("milestone_id"),
            TaskMilestone.task_id == body.get("task_id"),
            TaskMilestone.cases.contains(case),
        ).first()
        if not tm:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"task with case does not exist.",
            )
        gitee_resp = GiteeV8BaseIssueHandler().get(gitee_issue_id)
        gitee_resp = gitee_resp.get_json()
        if gitee_resp.get("error_code") != RET.OK:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="OK",
            )
        gitee_issue = json.loads(
            gitee_resp.get("data")
        ).get("data")
        _issue = Issue(
            title=gitee_issue.get("title"),
            description=gitee_issue.get("description"),
            priority=gitee_issue.get("priority"),
            creator_id=g.user_id,
            milstone_id=milestone.milestone_id,
            task_id=body.get("task_id"),
            case_id=body.get("case_id"),
            project_name=gitee_issue.get("project").get("path"),
            issue_type_id=gitee_issue.get("issue_type").get("id"),
            ident=gitee_issue.get("ident"),
            gitee_issue_id=gitee_issue.get("id"),
            gitee_issue_url=gitee_issue.get("issue_url"),
        )
        db.session.add(_issue)
        db.session.flush()
        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )

    @staticmethod
    def get_issues(query: QueryIssueSchema):
        filter_params = list()

        if query.title:
            filter_params.append(Issue.title.like(f"%{query.title}%"))
        if query.description:
            filter_params.append(Issue.description.like(f"%{query.description}%"))
        if query.task_id:
            filter_params.append(Issue.task_id == query.task_id)
        if query.case_id:
            filter_params.append(Issue.case_id == query.case_id)
        if query.milestone_id:
            filter_params.append(Issue.milestone_id == query.milestone_id)
        if query.priority:
            filter_params.append(Issue.priority == query.priority)
        if query.project_name:
            filter_params.append(Issue.project_name == query.project_name)

        query_filter = Issue.query.filter(*filter_params).order_by(
            Issue.create_time
        )
        
        return PageUtil.get_data(query_filter=query_filter, query=query)

    @staticmethod
    def get_issue_type():
        data = GiteeV8BaseIssueHandler().issue_types
        if len(data) > 0:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=data
            )
        else:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get through gitee v8 openAPI",
            )

    @staticmethod
    def get_issue_state():
        data = GiteeV8BaseIssueHandler().issue_states
        if len(data) > 0:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=data
            )
        else:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get through gitee v8 openAPI",
            )
