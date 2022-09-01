import datetime
import pytz
from celeryservice import celeryconfig
import sqlalchemy
from server.utils.requests_util import do_request
from server.utils.response_util import RET
from server import db
from server.model.vmachine import Vmachine
from server.model.pmachine import Pmachine
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
