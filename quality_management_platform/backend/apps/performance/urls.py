from django.urls import path

from . import views

urlpatterns = [
    path("bootstrap/", views.bootstrap),
    path("test-suites/<int:suite_id>/compile-jmx/", views.compile_suite_jmx),
    path("test-suites/<int:suite_id>/run-jmx/", views.run_suite_jmx),
]
