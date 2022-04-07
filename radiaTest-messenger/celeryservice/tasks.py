import os
import sys
import shlex
import subprocess

from celery import current_app as celery
from celery.utils.log import get_task_logger

from celeryservice import celeryconfig
from celeryservice.lib.job.handler import RunSuite, RunTemplate
from messenger.utils.pssh import Connection
from messenger.utils.requests_util import do_request
from messenger.utils.response_util import RET


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)


logger = get_task_logger('manage')


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        10.0, async_check_alive.s(), name="check_heartbeat"
    )


@celery.task
def async_check_alive():
    heartbeat_status = {
        "messenger_ip": celeryconfig.messenger_ip,
        "messenger_alive": True,
        "pxe_alive": True,
        "dhcp_alive": True
    }
    
    # get messenger api
    _resp = dict()
    _r = do_request(
        method="get",
        url="http://{}:{}/api/v1/heartbeat".format(
            celeryconfig.messenger_ip,
            celeryconfig.messenger_listen
        ),
        headers={
            "content-type": "application/json;charset=utf-8"
        },
        obj=_resp,
    )
    if  _r != 0 or _resp.get("error_code") != RET.OK:
        logger.warning("lost heartbeating of messenger service") 
        heartbeat_status["messenger_alive"] = False

    # ssh pxe
    ssh_client = Connection(
        ip=celeryconfig.pxe_ip,
        user=celeryconfig.pxe_ssh_user,
        port=celeryconfig.pxe_ssh_port,
        pkey=celeryconfig.pxe_pkey
    )

    result = ssh_client._conn()
    if not result:
        heartbeat_status["pxe_alive"] = False
    else:
        ssh_client._close()

    # ping dhcp
    exitcode, output = subprocess.getstatusoutput(
        "ping -c 4 {}".format(
            shlex.quote(celeryconfig.dhcp_ip)
        )
    )
    if exitcode != 0:
        heartbeat_status["dhcp_alive"] = False

    # put server api
    _resp = dict()
    _r = do_request(
        method="put",
        url="{}://{}:{}/api/v1/machine_group/heartbeat".format(
            celeryconfig.protocol,
            celeryconfig.server_ip,
            celeryconfig.server_listen,
        ),
        body=heartbeat_status,
        headers={
            "content-type": "application/json;charset=utf-8"
        },
        obj=_resp,
    )
    if _r != 0 or _resp.get("error_code") != RET.OK:
        if _resp.get("error_msg"):
            raise RuntimeError(
                "could not update heartbeat status to server: {}".format(
                    _resp.get("error_msg")
                )
            )


@celery.task(bind=True)
def run_suite(self, body, user):
    RunSuite(body, self, user, logger).run()


@celery.task(bind=True)
def run_template(self, body, user):
    RunTemplate(body, self, user, logger).run()