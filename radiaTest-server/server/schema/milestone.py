import datetime
from typing import Optional

from pydantic import BaseModel, constr, root_validator


from server.model import Product, Milestone

from server.utils.db import Precise

from server.schema import MilestoneType, PermissionType
from server.schema.base import UpdateBaseModel


class MilestoneBase(BaseModel):
    product_id: int
    type: MilestoneType
    start_time: Optional[datetime.datetime] = datetime.datetime.now()
    end_time: datetime.datetime
    description: Optional[constr(max_length=255)]
    name: Optional[constr(max_length=64)]

    @root_validator
    def assign_name(cls, values):
        if not values.get("name"):
            try:
                if not values.get("product_id"):
                    milestone = Precise(Milestone, {"id": values.get("id")}).first()
                    if not milestone:
                        raise ValueError("The milestone no longer exists.")
                    product = milestone.product
                    milestone_type = milestone.type
                else:
                    milestone_type = values.get("type")
                    product = Precise(Product, {"id": values.get("product_id")}).first()
                    if not product:
                        raise ValueError("The bound product version does not exist.")
            except RuntimeError as e:
                raise RuntimeError(e)

            prefix = product.name + " " + product.version

            if milestone_type == "update":
                values["name"] = (
                    prefix + " update_" + datetime.datetime.now().strftime("%Y%m%d")
                )
            elif milestone_type == "round":
                prefix = prefix + " round-"
                _max_round = (
                    Milestone.query.filter(
                        Milestone.name.op("regexp")(prefix + "[1-9]*")
                    )
                    .order_by(Milestone.name.desc())
                    .first()
                )
                if not _max_round:
                    _max_round = "1"
                else:
                    _max_round = str(int(_max_round.name.replace(prefix, "")) + 1)
                values["name"] = prefix + _max_round
            elif milestone_type == "release":
                values["name"] = prefix + " release"

        return values


class MilestoneUpdate(MilestoneBase, UpdateBaseModel):
    end_time: Optional[datetime.datetime]
    name: Optional[constr(max_length=64)]
    product_id: Optional[int]
    type: Optional[MilestoneType]
