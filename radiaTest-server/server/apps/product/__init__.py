from flask_restful import Api

from .routes import ProductEvent


def init_api(api: Api):
    api.add_resource(ProductEvent, "/api/v1/product")