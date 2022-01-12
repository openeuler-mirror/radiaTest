import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.networks import HttpUrl

from server.schema.base import UpdateBaseModel


class FrameworkBase(BaseModel):
    name: str
    url: HttpUrl
    logs_path: str


class FrameworkUpdate(UpdateBaseModel):
    name: Optional[str]
    url: Optional[HttpUrl]
    logs_path: Optional[str]