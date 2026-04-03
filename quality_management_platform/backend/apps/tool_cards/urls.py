from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.overview),
    path("folders/", views.folders),
    path("folders/<int:folder_id>/", views.folder_detail),
    path("cards/", views.cards),
    path("cards/create/", views.create_card),
    path("cards/<int:card_id>/", views.card_detail),
    path("initialize-defaults/", views.initialize_defaults),
]
