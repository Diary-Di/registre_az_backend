"""Collection /api/dossiers/ : GET (liste filtrée) et POST (ouverture, MO 01)."""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.access.models import AffectationDossier, Compartiment, DossierCompartiment
from apps.access.ouverture import verifier_ouverture
from apps.access.services import journaliser
from apps.dossiers.models import Dossier
from apps.dossiers.serializers import DossierSerializer
from apps.dossiers.views import REFUS, DossierListView
from apps.users.models import Utilisateur


class DossierCreateSerializer(serializers.Serializer):
    titre = serializers.CharField()
    finalite = serializers.CharField()
    niveau = serializers.IntegerField(min_value=0, max_value=4)
    echeance = serializers.DateField(required=False, allow_null=True)
    compartiments = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    membres = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class DossierCollectionView(DossierListView):
    """GET hérité de DossierListView ; POST ajouté ici."""

    def post(self, request):
        entree = DossierCreateSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        d = entree.validated_data
        user = request.user

        # Compartiments : un code inconnu ou inactif = même refus qu'un compartiment non détenu
        codes = set(d["compartiments"])
        compartiments = list(Compartiment.objects.filter(code__in=codes, actif=True))
        if len(compartiments) != len(codes):
            journaliser(user, "creer", "dossier", None, False,
                        {"condition": 4, "operation": "ouverture", "motif": "compartiment"})
            raise PermissionDenied(REFUS)

        if not verifier_ouverture(user, d["niveau"], [c.id for c in compartiments]):
            raise PermissionDenied(REFUS)

        # Membres à affecter (après le contrôle d'accès : pas d'énumération de comptes)
        identifiants = set(d["membres"])
        membres = list(Utilisateur.objects.filter(identifiant__in=identifiants))
        if len(membres) != len(identifiants) or not all(m.is_active for m in membres):
            raise ValidationError({"membres": "Un ou plusieurs membres sont introuvables ou inactifs."})

        now = timezone.now()
        with transaction.atomic():
            dossier = Dossier.objects.create(
                titre=d["titre"],
                finalite=d["finalite"],
                unite=user.unite,
                niveau=d["niveau"],
                statut="actif",
                echeance=d.get("echeance"),
            )
            for compartiment in compartiments:
                DossierCompartiment.objects.create(dossier=dossier, compartiment=compartiment)

            # Le rang n'ouvre pas un dossier : le créateur s'y affecte explicitement
            AffectationDossier.objects.create(
                utilisateur=user, dossier=dossier, debut=now, fonction="Ouverture")
            for membre in membres:
                if membre.id != user.id:
                    AffectationDossier.objects.create(
                        utilisateur=membre, dossier=dossier, debut=now)

            journaliser(user, "creer", "dossier", dossier.id, True,
                        {"operation": "ouverture", "niveau": dossier.niveau})

        return Response(DossierSerializer(dossier).data, status=status.HTTP_201_CREATED)