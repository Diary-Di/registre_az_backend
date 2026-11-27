from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import AZAccessPermission
from apps.access.services import (
    dossiers_accessibles,
    journaliser,
    niveau_habilitation,
    verifier_acces,
)
from apps.dossiers.models import Dossier, Renseignement, Version
from apps.dossiers.serializers import (
    DossierSerializer,
    RenseignementCreateSerializer,
    RenseignementSerializer,
)

REFUS = "Accès refusé."


def _dossier_ou_refus(pk):
    """Un id inexistant donne la même réponse qu'un refus."""
    try:
        return Dossier.objects.get(pk=pk)
    except Dossier.DoesNotExist:
        raise PermissionDenied(REFUS)


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
        dossier = _dossier_ou_refus(self.kwargs["pk"])
        self.check_object_permissions(self.request, dossier)
        return dossier


class RenseignementListCreateView(APIView):
    """
    GET  : renseignements d'un dossier (brouillons visibles par leur auteur seul).
    POST : crée un renseignement en brouillon + sa version 1.
    """

    def get(self, request, dossier_id):
        dossier = _dossier_ou_refus(dossier_id)
        if not verifier_acces(request.user, dossier, "lire"):
            raise PermissionDenied(REFUS)

        plafond = niveau_habilitation(request.user)
        renseignements = (
            Renseignement.objects.filter(dossier=dossier, niveau__lte=plafond)
            .filter(Q(statut__in=["soumis", "valide", "rejete"]) | Q(auteur=request.user))
            .order_by("id")
        )
        return Response(RenseignementSerializer(renseignements, many=True).data)

    def post(self, request, dossier_id):
        # Pas de @transaction.atomic sur toute la vue : un refus lève une
        # exception, et la transaction annulerait la ligne de journal du refus.
        entree = RenseignementCreateSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        d = entree.validated_data

        dossier = _dossier_ou_refus(dossier_id)
        if not verifier_acces(request.user, dossier, "creer",
                              niveau_objet=d["niveau"], journaliser_succes=False):
            raise PermissionDenied(REFUS)

        if d["niveau"] < dossier.niveau:
            raise ValidationError(
                {"niveau": "Le niveau doit être supérieur ou égal à celui du dossier."}
            )

        with transaction.atomic():
            renseignement = Renseignement.objects.create(
                dossier=dossier,
                titre=d["titre"],
                resume=d.get("resume"),
                type=d["type"],
                niveau=d["niveau"],
                statut="brouillon",
                auteur=request.user,
                date_fait=d["date_fait"],
                zone=d.get("zone"),
            )
            Version.objects.create(
                renseignement=renseignement,
                numero=1,
                contenu=d["contenu"],
                auteur=request.user,
                motif="Création initiale",
            )
            journaliser(request.user, "creer", "renseignement", renseignement.id,
                        True, {"dossier_id": dossier.id})

        return Response(RenseignementSerializer(renseignement).data,
                        status=status.HTTP_201_CREATED)