from flask.json import jsonify
from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Product, Milestone
from server.utils.auth_util import auth
from server.utils.db import Edit, Select

from server.schema.product import ProductBase, ProductIssueRateFieldSchema, ProductUpdate
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server import casbin_enforcer


class ProductEventItem(Resource):
    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, product_id):
        return ResourceManager("product").del_cascade_single(product_id, Milestone, [Milestone.product_id == product_id], False)

    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    def get(self, product_id):
        return Select(Product, {"id": product_id}).single()

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
        return GetAllByPermission(Product).fuzz(body, [Product.name.asc(), Product.create_time.asc()])


class PreciseProductEvent(Resource):
    @auth.login_required
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Product).precise(body)


class UpdateProductIssueRateByField(Resource):
    @auth.login_required
    @validate()
    def put(self, product_id, body: ProductIssueRateFieldSchema):
        from celeryservice.lib.issuerate import update_field_issue_rate
        from server.apps.milestone.handler import IssueStatisticsHandlerV8
        from server.utils.response_util import RET
        product = Product.query.filter_by(id=product_id).first()
        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product does not exist.",
            )
     
        gitee_id = IssueStatisticsHandlerV8.get_gitee_id(product.org_id)
        if gitee_id:
            update_field_issue_rate.delay(
                "product",
                gitee_id,
                {"product_id": product_id, "org_id": product.org_id},
                body.field,
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )
