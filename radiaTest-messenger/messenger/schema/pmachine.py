from typing import Optional
from ipaddress import IPv4Address
from pydantic import BaseModel, conint, constr, Field, validator, root_validator
import datetime
from messenger.schema import Power, Frame, PmachineState


class PmachineInstallSchema(BaseModel):
    id: int
    user_id: Optional[int]
    pmachine: dict
    mirroring: dict


class PmachinePowerSchema(BaseModel):
    id: int
    user: Optional[int]
    status: Power
    pmachine: dict

class PmachineBaseSchema(BaseModel):
    mac: constr(max_length=17)
    frame: Frame
    bmc_ip: IPv4Address
    bmc_user: constr(max_length=32)
    bmc_password: constr(min_length=6, max_length=256)
    ip: Optional[IPv4Address]
    user: Optional[constr(max_length=32)]
    port: Optional[int]
    password: Optional[constr(min_length=6, max_length=256)]
    end_time: Optional[datetime.datetime]
    start_time: Optional[datetime.datetime]
    listen: Optional[int]
    description: Optional[str]
    state: Optional[PmachineState]
    occupier: Optional[str]
    locked: Optional[bool] = False
    machine_group_id: Optional[int]

    @validator("bmc_password")
    def required_bmc_conditions(cls, v, values):
        exitcode, output = getstatusoutput(
            "ipmitool -I lanplus -H %s -U %s  -P %s power status"
            % (values.get("bmc_ip"), values.get("bmc_user"), v)
        )
        if exitcode != 0:
            raise ValueError("The infomation of BMC provided is wrong.")

        values["status"] = output.split()[-1]

        return v


