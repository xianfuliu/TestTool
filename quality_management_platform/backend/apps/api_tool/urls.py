from django.urls import path

from . import api_views

urlpatterns = [
    path("bootstrap/", api_views.bootstrap),
    path("products/", api_views.products),
    path("products/<int:product_id>/", api_views.product_detail),
    path("preview/", api_views.preview),
    path("execute/", api_views.execute),
    path("execute-sql/", api_views.execute_product_sql),
    path("execute-schedule/", api_views.execute_schedule),
]
