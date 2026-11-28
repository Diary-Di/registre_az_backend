from django.urls import path

from .views_cycle import SoumettreView, ValiderView
from .views_detail import RenseignementDetailView, SourceCreateView

urlpatterns = [
    path("<int:pk>/", RenseignementDetailView.as_view()),
    path("<int:pk>/sources/", SourceCreateView.as_view()),
    path("<int:pk>/soumettre/", SoumettreView.as_view()),
    path("<int:pk>/valider/", ValiderView.as_view()),
]