from typing import Optional

from pydantic import BaseModel, constr, root_validator

from server.model import Product
from server.utils.db import Precise
from server.schema.base import UpdateBaseModel


class ProductBase(BaseModel):
    name: constr(max_length=32)
    version: constr(max_length=32)
    description: Optional[constr(max_length=255)]

    @root_validator
    def check_duplicate(cls, values):
        product = Precise(
            Product, {"name": values.get("name"), "version": values.get("version")}
        ).first()
        if product:
            raise ValueError("The version of product has existed.")
        return values


class ProductUpdate(UpdateBaseModel):
    name: Optional[constr(max_length=32)]
    version: Optional[constr(max_length=32)]
    description: Optional[constr(max_length=255)]
