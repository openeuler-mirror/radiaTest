from typing import Optional

from pydantic import BaseModel

from messenger.schema import Power


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
