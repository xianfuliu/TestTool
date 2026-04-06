from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta),
    path("runtime-variables/", views.runtime_variables),
    path("workspace/", views.workspace),
    path("user-workspace/", views.user_workspace),
    path("enterprise-workspace/", views.enterprise_workspace),
    path("refresh-field/", views.refresh_field),
    path("refresh-user-field/", views.refresh_user_field),
    path("refresh-enterprise-field/", views.refresh_enterprise_field),
    path("id-card/", views.id_card),
    path("business-license/", views.business_license),
    path("bundle/", views.bundle),
]
