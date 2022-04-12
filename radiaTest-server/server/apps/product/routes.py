from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Product
from server.utils.auth_util import auth
from server.utils.db import Insert, Delete, Edit, Select

from server.schema.base import DeleteBaseModel
from server.schema.product import ProductBase, ProductUpdate
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager

class ProductEventItem(Resource):
    @auth.login_required
    @validate()
    def delete(self, product_id):
        return ResourceManager("product").del_cascade_single(product_id, "milestone", "product_id", False)
        #return ResourceManager("product").del_single(product_id)

    @auth.login_required
    @validate()
    def get(self, product_id):
        return Select(Product, {"id":product_id}).single()
    
    @auth.login_required
    @validate()
    def put(self, product_id, body: ProductUpdate):
        _data = body.__dict__
        _data["id"] = product_id
        return Edit(Product, _data).single(Product, '/product')

class ProductEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: ProductBase):
        return ResourceManager("product").add("api_infos.yaml", body.__dict__)

    @auth.login_required
    @validate()
    def delete(self, body: DeleteBaseModel):
        return ResourceManager("product").del_batch(body.__dict__.get("id"))

    @auth.login_required
    @validate()
    def put(self, body: ProductUpdate):
        return Edit(Product, body.__dict__).single(Product, '/product')

    @auth.login_required
    def get(self):
        body = request.args.to_dict()
        return GetAllByPermission(Product).fuzz(body)
