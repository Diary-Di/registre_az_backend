from django.urls import path

from .views import DossierDetailView, DossierListView

urlpatterns = [
    path("", DossierListView.as_view()),
    path("<int:pk>/", DossierDetailView.as_view()),
]