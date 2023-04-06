import shlex
from subprocess import getstatusoutput
from datetime import datetime, timedelta
from typing import Optional
from flask import current_app
from messenger.utils.pssh import ConnectionApi
from pydantic import BaseModel, conint, constr, Field, validator, root_validator
from messenger.schema import Power, Frame, PmachineState
from messenger.utils.iptype_util import ip_type


class PmachineInstallSchema(BaseModel):
    id: int
    user_id: Optional[str]
    pmachine: dict
    mirroring: dict


class PmachinePowerSchema(BaseModel):
    id: int
    user: Optional[str]
    status: Power
    pmachine: dict


class PmachineBaseSchema(BaseModel):
    mac: constr(max_length=17)
    frame: Frame
    bmc_ip: str
    bmc_user: constr(max_length=32)
    bmc_password: constr(min_length=6, max_length=256)
    ip: Optional[str]
    user: Optional[constr(max_length=32)]
    port: Optional[int]
    password: Optional[constr(min_length=6, max_length=256)]
    end_time: Optional[datetime]
    start_time: Optional[datetime]
    listen: Optional[int]
    description: Optional[str]
    state: Optional[PmachineState]
    occupier: Optional[str]
    locked: Optional[bool] = False
    machine_group_id: Optional[int]
    status: Optional[Power]

    @validator("ip")
    def check_ip_format(cls, v):
        if v and not ip_type(v):
            raise ValueError("this ip of machine group format error")
        return v

    @validator("bmc_ip")
    def check_bmc_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this bmc_ip of machine group format error")
        return v

    @validator("status")
    def required_bmc_conditions(cls, v, values):
        exitcode, output = getstatusoutput(
            "ipmitool -I lanplus -H %s -U %s  -P %s power status"
            % (values.get("bmc_ip"), values.get("bmc_user"), values["bmc_password"])
        )
        if exitcode != 0:
            raise ValueError("The infomation of BMC provided is wrong.")

        v = output.split()[-1]
        return v


class PmachineSshSchema(BaseModel):
    id: str
    ip: str
    user: constr(max_length=32)
    port: int
    old_password: constr(min_length=6, max_length=256)
    password: Optional[constr(min_length=6, max_length=256)]
    random_flag: Optional[bool] = False


class PmachineBmcSchema(PmachineBaseSchema):
    mac: Optional[constr(max_length=17)]
    frame: Optional[Frame]
    id: str
    port: int
    bmc_ip: str
    old_bmc_password: constr(min_length=6, max_length=256)
    bmc_user: constr(max_length=32)
    bmc_password: constr(min_length=6, max_length=256)


class PmachineEventSchema(PmachineBaseSchema):
    @root_validator
    def check_description(cls, values):
        if values.get("description") == current_app.config.get("CI_HOST"):
            if not values.get("listen"):
                raise ValueError("As a CI host, listen must be provided.")

            if (
                getstatusoutput(
                    "ping -nq -c 3 -w 5 {}".format(shlex.quote(str(values.get("ip"))))
                )[0]
                != 0
            ):
                raise ValueError("ip address is not available.")

            conn = ConnectionApi(
                str(values.get("ip")),
                str(values.get("password")),
                values.get("port"),
                str(values.get("user")),
            ).conn()
            if not conn:
                raise ValueError(
                    "The information provided cannot be used in normal login using SSH."
                )
            conn.close()
        return values
