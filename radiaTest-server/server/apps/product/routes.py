from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Product

from server.utils.db import Insert, Delete, Edit, Select

from server.schema.base import DeleteBaseModel
from server.schema.product import ProductBase, ProductUpdate


class ProductEvent(Resource):
    @validate()
    def post(self, body: ProductBase):
        return Insert(Product, body.__dict__).single(Product, '/product')

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Product, body.__dict__).batch(Product, '/product')

    @validate()
    def put(self, body: ProductUpdate):
        return Edit(Product, body.__dict__).single(Product, '/product')

    def get(self):
        body = request.args.to_dict()
        return Select(Product, body).fuzz()
