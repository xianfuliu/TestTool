from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health),
    path("legacy-routes/", views.legacy_routes),
    path("business-groups/", views.business_groups),
    path("business-groups/<int:group_id>/", views.business_group_detail),
    path("business-groups/<int:group_id>/stats/", views.business_group_stats),
    path("projects/", views.projects),
    path("projects/<int:project_id>/", views.project_detail),
    path("projects/<int:project_id>/stats/", views.project_stats),
]
