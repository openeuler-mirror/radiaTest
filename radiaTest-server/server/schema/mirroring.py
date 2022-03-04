# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-04 15:50:10
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from typing import Optional
from urllib import request, error

from pydantic import BaseModel, HttpUrl, constr, validator, root_validator


from server.schema import Frame
from server.schema.base import UpdateBaseModel

from server.utils.db import Precise

from server.model import Milestone, IMirroring, QMirroring, Repo


class MirroringBase(BaseModel):
    milestone_id: int
    frame: Frame
    url: HttpUrl

    @validator("milestone_id")
    def check_milestone(cls, v):
        milestone = Precise(Milestone, {"id": v}).first()
        if not milestone:
            raise ValueError("The milestone does not exist.")

        if milestone.type not in ["release", "round"]:
            raise ValueError(
                "Only the release version and iterative version can be bound to the iso image."
            )

        return v

    @validator("url")
    def check_url(cls, v):
        try:
            request.urlopen(v)
        except (error.HTTPError, error.URLError):
            raise ValueError("url:%s is not available." % v)

        return v


class IMirroringBase(MirroringBase):
    efi: Optional[constr(max_length=255)]
    ks: Optional[constr(max_length=255)]
    location: Optional[constr(max_length=255)]

    @root_validator
    def guarantee_uniqueness(cls, values):
        if Precise(
            IMirroring,
            {"milestone_id": values.get("milestone_id"), "frame": values.get("frame")},
        ).first():
            raise ValueError(
                "The url of %s iso image already exists under the milestone."
                % values.get("frame")
            )
        return values


class IMirroringUpdate(MirroringBase, UpdateBaseModel):
    frame: Optional[Frame]
    url: Optional[HttpUrl]
    milestone_id: Optional[int]
    efi: Optional[constr(max_length=255)]
    ks: Optional[constr(max_length=255)]
    location: Optional[constr(max_length=255)]

    @root_validator
    def guarantee_uniqueness(cls, values):
        imirroring =  Precise(
            IMirroring,
            {"milestone_id": values.get("milestone_id"), "frame": values.get("frame")},
        ).first()
        if imirroring and imirroring.id != values.get("id"):
            raise ValueError(
                "The url of %s iso image already exists under the milestone."
                % values.get("frame")
            )
        return values

class QMirroringBase(MirroringBase):
    user: constr(max_length=32) = "root"
    port: int = 22
    password: constr(min_length=6, max_length=256)

    @root_validator
    def guarantee_uniqueness(cls, values):
        if Precise(
            QMirroring,
            {"milestone_id": values.get("milestone_id"), "frame": values.get("frame")},
        ).first():
            raise ValueError(
                "The url of %s qcow image already exists under the milestone."
                % values.get("frame")
            )
        return values


class QMirroringUpdate(MirroringBase, UpdateBaseModel):
    milestone_id: Optional[int]
    frame: Optional[Frame]
    url: Optional[HttpUrl]
    user: Optional[constr(max_length=32)]
    port: Optional[int]
    password: Optional[constr(max_length=256)]

    @root_validator
    def guarantee_uniqueness(cls, values):
        qmirroring =  Precise(
            QMirroring,
            {"milestone_id": values.get("milestone_id"), "frame": values.get("frame")},
        ).first()
        if qmirroring and qmirroring.id != values.get("id"):
            raise ValueError(
                "The url of %s qcow image already exists under the milestone."
                % values.get("frame")
            )
        return values

class RepoBase(BaseModel):
    milestone_id: int
    frame: Frame
    content: str

    @validator("milestone_id")
    def check_milestone(cls, v):
        milestone = Precise(Milestone, {"id": v}).first()
        if not milestone:
            raise ValueError("The milestone does not exist.")
        return v

class RepoCreate(RepoBase):
    @root_validator
    def guarantee_uniqueness(cls, values):
        if Precise(
            Repo,
            {"milestone_id": values.get("milestone_id"), "frame": values.get("frame")},
        ).first():
            raise ValueError("The repo address is already registered.")
        return values


class RepoUpdate(RepoBase, UpdateBaseModel):
    content: Optional[str]

    @root_validator
    def guarantee_uniqueness(cls, values):
        repo = Precise(
            Repo,
            {"milestone_id": values.get("milestone_id"), "frame": values.get("frame")},
        ).first()
        if repo and repo.id != values.get("id"):
            raise ValueError("The repo address is already registered.")
        return values
