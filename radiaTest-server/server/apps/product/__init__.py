from flask_restful import Api

from .routes import (
    PreciseProductEvent,
    ProductEvent,
    ProductEventItem,
    UpdateProductIssueRate,
    ProductTestReportEvent,
)


def init_api(api: Api):
    api.add_resource(
        ProductEvent, 
        "/api/v1/product", 
        "/api/v1/ws/<str:workspace>/product"
    )
    api.add_resource(
        PreciseProductEvent, 
        "/api/v1/product/preciseget", 
        "/api/v1/ws/<str:workspace>/product/preciseget"
    )
    api.add_resource(ProductEventItem, "/api/v1/product/<int:product_id>")
    api.add_resource(
        UpdateProductIssueRate,
        "/api/v1/product/<int:product_id>/issue-rate"
    )
    api.add_resource(ProductTestReportEvent, "/api/v1/product/<int:product_id>/test-report")
