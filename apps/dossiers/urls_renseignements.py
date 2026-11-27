from django.urls import path

from .views_cycle import SoumettreView, ValiderView

urlpatterns = [
    path("<int:pk>/soumettre/", SoumettreView.as_view()),
    path("<int:pk>/valider/", ValiderView.as_view()),
]