from django.urls import path

from . import views

urlpatterns = [
    path("context/", views.context),
    path("tasks/", views.tasks),
    path("tasks/<int:task_id>/", views.task_detail),
    path("tasks/<int:task_id>/status/", views.task_status),
    path("tasks/<int:task_id>/runs/", views.task_runs),
    path("tasks/<int:task_id>/runs/<int:run_id>/detail/", views.task_run_detail),
    path("tasks/<int:task_id>/run/", views.run_task),
]
