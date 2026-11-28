from django.urls import path

from .views import DossierDetailView, RenseignementListCreateView
from .views_dossier import DossierCollectionView

urlpatterns = [
    path("", DossierCollectionView.as_view()),
    path("<int:pk>/", DossierDetailView.as_view()),
    path("<int:dossier_id>/renseignements/", RenseignementListCreateView.as_view()),
]