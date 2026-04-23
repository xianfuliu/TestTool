from django.urls import path

from . import views

urlpatterns = [
    path("databases/test-connection/", views.test_database_connection),
    path("databases/", views.databases),
    path("databases/<int:database_id>/schemas/", views.database_schemas),
    path("databases/<int:database_id>/", views.database_detail),
]
