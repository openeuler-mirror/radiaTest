import datetime

from server import db
from server.model.vmachine import Vmachine
from celeryservice.lib import TaskHandlerBase



class LifecycleMonitor(TaskHandlerBase):
    def main(self):
        v_machines = Vmachine.query.all()

        for vmachine in v_machines:
            end_time = vmachine.end_time

            if (datetime.datetime.now() > end_time):
                self.logger.info(
                    "vmachine {} is going to be destroyed, with end_time {}".format(
                        vmachine.name, 
                        vmachine.end_time
                    )
                )
                db.session.delete(vmachine)
        
        db.session.commit()
