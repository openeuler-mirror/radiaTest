import json
import datetime
import pytz
from celeryservice import celeryconfig
import sqlalchemy
from server.utils.requests_util import do_request
from server.utils.response_util import RET
from server import db
from server.model.vmachine import Vmachine
from server.model.pmachine import Pmachine
from server.model.milestone import Milestone
from server.model.organization import Organization
from server.model.product import Product
from server.apps.milestone.handler import IssueStatisticsHandlerV8, IssueOpenApiHandlerV8
from celeryservice.lib import TaskHandlerBase


class LifecycleMonitor(TaskHandlerBase):
    def check_vmachine_lifecycle(self):
        v_machines = Vmachine.query.all()

        for vmachine in v_machines:
            end_time = vmachine.end_time

            if datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai")) > \
                    end_time.replace(tzinfo=pytz.timezone('Asia/Shanghai')):
                self.logger.info(
                    "vmachine {} is going to be destroyed, with end_time {}".format(
                        vmachine.name, vmachine.end_time
                    )
                )
                db.session.delete(vmachine)

        db.session.commit()

    def check_pmachine_lifecycle(self):
        filter_params = [
            Pmachine.state == "occupied",
            Pmachine.end_time.isnot(None),
        ]
        pmachines = Pmachine.query.filter(*filter_params).all()

        for pmachine in pmachines:
            end_time = pmachine.end_time

            if datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai")) > \
                    end_time.replace(tzinfo=pytz.timezone('Asia/Shanghai')):
                self.logger.info(
                    "pmachine {} is going to be released, with end_time {}".format(
                        pmachine.id, pmachine.end_time
                    )
                )

                pmachine.state = "idle"
                pmachine.end_time = sqlalchemy.null()
                pmachine.description = ""
                pmachine.occupier = ""
                pmachine.add_update(Pmachine, "/pmachine")

    def main(self):
        self.check_pmachine_lifecycle()
        self.check_vmachine_lifecycle()


class UpdateIssueRate(TaskHandlerBase):
    def main(self):
        products = Product.query.order_by(Product.org_id).all()
        t_org_id = -1
        _ishv8 = None
        for _p in products:
            if _p.org_id != t_org_id:
                gitee_id = IssueStatisticsHandlerV8.get_gitee_id(_p.org_id)
                if gitee_id:
                    _ishv8 = IssueStatisticsHandlerV8(gitee_id=gitee_id, org_id=_p.org_id)
                else:
                    _ishv8 = None
            if _ishv8:
                _ishv8.update_product_issue_solved_rate(product_id=_p.id)
                milestones = Milestone.query.filter_by(
                    is_sync=True, product_id=_p.id
                ).all()
                for _m in milestones:
                    _ishv8.update_milestone_issue_solved_rate(
                        gitee_milestone_id=_m.gitee_milestone_id)
            t_org_id = _p.org_id


class UpdateIssueTypeState(TaskHandlerBase):
    def main(self):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        orgs = Organization.query.filter(
            Organization.enterprise_id is not None).all()
        for _org in orgs:
            gitee_id = IssueStatisticsHandlerV8.get_gitee_id(_org.id)
            if gitee_id:
                isa = IssueOpenApiHandlerV8(gitee_id=gitee_id)
                resp = isa.get_issue_types()
                issue_types = json.loads(
                    resp.get_json().get("data")).get("data")
                t_issue_types = []
                for _type in issue_types:
                    t_issue_types.append({"id": _type.get("id"),
                                         "title": _type.get("title"), })
                redis_client.hmset(RedisKey.issue_types(_org.enterprise_id), {"data": t_issue_types})
                resp = isa.get_issue_states()
                issue_states = json.loads(
                    resp.get_json().get("data")).get("data")
                
                t_issue_states = []
                for _state in issue_states:
                    t_issue_states.append({"id": _state.get("id"),
                                         "title": _state.get("title"), })
                redis_client.hmset(RedisKey.issue_states(_org.enterprise_id), {"data": t_issue_states})
