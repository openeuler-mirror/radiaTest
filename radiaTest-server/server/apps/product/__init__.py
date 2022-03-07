from flask_restful import Api

from .routes import ProductEvent, ProductEventItem


def init_api(api: Api):
    api.add_resource(ProductEvent, "/api/v1/product")
    api.add_resource(ProductEventItem, "/api/v1/product/<int:product_id>")