from typing import List, Optional
from urllib import request, error

from pydantic import BaseModel, validator
from pydantic.networks import HttpUrl


class OpenEulerUpdateTaskBase(BaseModel):
    product: str
    version: str
    pkgs: List[str]
    base_update_url: HttpUrl
    epol_update_url: Optional[HttpUrl]

    @validator("base_update_url")
    def check_base_url(cls, v):
        try:
            request.urlopen(v + 'aarch64/')
            request.urlopen(v + 'x86_64/')

        except (error.HTTPError, error.URLError):
            raise ValueError("base_update_url:%s is not available." % v)

        return v

    @validator("epol_update_url")
    def check_epol_url(cls, v):
        if v:
            try:
                request.urlopen(v + 'aarch64/')
                request.urlopen(v + 'x86_64/')

            except (error.HTTPError, error.URLError):
                raise ValueError("epol_update_url:%s is not available." % v)

            return v

