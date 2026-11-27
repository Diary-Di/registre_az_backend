from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.access.permissions import AZAccessPermission
from apps.access.services import dossiers_accessibles
from apps.dossiers.models import Dossier
from apps.dossiers.serializers import DossierSerializer


class DossierListView(ListAPIView):
    """Liste uniquement les dossiers accessibles : les autres n'existent pas."""
    serializer_class = DossierSerializer

    def get_queryset(self):
        return dossiers_accessibles(self.request.user, "lire").order_by("id")


class DossierDetailView(RetrieveAPIView):
    """Détail d'un dossier, protégé par les 7 conditions."""
    serializer_class = DossierSerializer
    permission_classes = [AZAccessPermission]

    def get_object(self):
        try:
            dossier = Dossier.objects.get(pk=self.kwargs["pk"])
        except Dossier.DoesNotExist:
            # même réponse qu'un refus : on ne révèle pas l'existence d'un id
            raise PermissionDenied("Accès refusé.")
        self.check_object_permissions(self.request, dossier)
        return dossier