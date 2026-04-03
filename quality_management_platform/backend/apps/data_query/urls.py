from django.urls import path

from . import views

urlpatterns = [
    path("config/", views.config),
    path("execute/", views.execute),
]
