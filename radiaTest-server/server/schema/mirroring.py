# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from typing import Optional
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

    @validator("content")
    def check_content(cls, v):
        if not v:
            raise ValueError("Content can't be empty")
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
