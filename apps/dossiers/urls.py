from django.urls import path

from .views import DossierDetailView, DossierListView, RenseignementListCreateView

urlpatterns = [
    path("", DossierListView.as_view()),
    path("<int:pk>/", DossierDetailView.as_view()),
    path("<int:dossier_id>/renseignements/", RenseignementListCreateView.as_view()),
]