from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health),
    path("legacy-routes/", views.legacy_routes),
]
