from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Product
from server.utils.auth_util import auth
from server.utils.db import Insert, Delete, Edit, Select

from server.schema.base import DeleteBaseModel
from server.schema.product import ProductBase, ProductUpdate
from .handlers import CreateProduct, DeleteProduct
from server.utils.permission_utils import GetAllByPermission

class ProductEventItem(Resource):
    @auth.login_required
    @validate()
    def delete(self, product_id):
        return DeleteProduct.single(product_id=product_id)

    @auth.login_required
    @validate()
    def get(self, product_id):
        return Select(Product, {"id":product_id}).single()

class ProductEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: ProductBase):
        return CreateProduct.run(body.__dict__)

    @auth.login_required
    @validate()
    def delete(self, body: DeleteBaseModel):
        return DeleteProduct.batch(body.__dict__)

    @auth.login_required
    @validate()
    def put(self, body: ProductUpdate):
        return Edit(Product, body.__dict__).single(Product, '/product')

    @auth.login_required
    def get(self):
        return GetAllByPermission(Product).get()
