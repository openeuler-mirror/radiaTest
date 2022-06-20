from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Product, Milestone
from server.utils.auth_util import auth
from server.utils.db import Edit, Select

from server.schema.product import ProductBase, ProductQueryBase, ProductUpdate
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server import casbin_enforcer

class ProductEventItem(Resource):
    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, product_id):
        return ResourceManager("product").del_cascade_single(product_id, Milestone, [Milestone.product_id==product_id], False)

    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    def get(self, product_id):
        return Select(Product, {"id":product_id}).single()
    
    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
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
    def get(self):
        body = request.args.to_dict()
        return GetAllByPermission(Product).fuzz(body)


class PreciseProductEvent(Resource):
    @auth.login_required
    @validate()
    def get(self, body: ProductQueryBase):
        return GetAllByPermission(Product).precise(body.__dict__)
