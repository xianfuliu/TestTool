from django.urls import path

from . import views

urlpatterns = [
    path("products/", views.products),
    path("products/<str:product_name>/", views.product_detail),
    path("execute/", views.execute),
]
