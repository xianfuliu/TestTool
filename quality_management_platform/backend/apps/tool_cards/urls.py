from django.urls import path

from . import views

urlpatterns = [
    path("bootstrap/", views.bootstrap),
    path("overview/", views.overview),
    path("folders/", views.folders),
    path("folders/<int:folder_id>/", views.folder_detail),
    path("cards/", views.cards),
    path("cards/create/", views.create_card_view),
    path("cards/<int:card_id>/", views.card_detail),
    path("cards/<int:card_id>/copy/", views.card_copy),
    path("cards/<int:card_id>/execute/", views.card_execute),
    path("initialize-defaults/", views.initialize_defaults),
]
