from django.urls import path

from . import views

urlpatterns = [
    path("verification-code/", views.verification_code),
    path("login/", views.login),
    path("register/", views.register),
    path("logout/", views.logout),
    path("session/", views.session),
]
