"""Cycle de vie d'un renseignement : brouillon -> soumis -> valide / rejete."""
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.services import journaliser, verifier_acces
from apps.dossiers.models import Renseignement, Validation, Version
from apps.dossiers.serializers import RenseignementSerializer

REFUS = "Accès refusé."


class Conflit(APIException):
    status_code = 409
    default_detail = "Transition impossible depuis le statut actuel."
    default_code = "conflit"


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepte", "rejet"])
    commentaire = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        if data["decision"] == "rejet" and not (data.get("commentaire") or "").strip():
            raise serializers.ValidationError(
                {"commentaire": "Un commentaire est obligatoire pour un rejet."}
            )
        return data


class _CycleView(APIView):
    action_az = None  # action métier contrôlée par le moteur d'accès

    def charger(self, request, pk):
        """Renseignement + contrôle des 7 conditions (id inconnu = refus)."""
        try:
            renseignement = Renseignement.objects.select_related("dossier").get(pk=pk)
        except Renseignement.DoesNotExist:
            raise PermissionDenied(REFUS)
        if not verifier_acces(
            request.user, renseignement.dossier, self.action_az,
            type_objet="renseignement", objet_id=renseignement.id,
            niveau_objet=renseignement.niveau,
        ):
            raise PermissionDenied(REFUS)
        return renseignement

    def refuser(self, request, renseignement, regle, message):
        journaliser(request.user, self.action_az, "renseignement", renseignement.id,
                    False, {"regle": regle, "dossier_id": renseignement.dossier_id})
        raise PermissionDenied(message)


class SoumettreView(_CycleView):
    """brouillon -> soumis, par l'auteur uniquement."""
    action_az = "modifier"

    def post(self, request, pk):
        renseignement = self.charger(request, pk)
        if renseignement.auteur_id != request.user.id:
            self.refuser(request, renseignement, "auteur_seul",
                         "Seul l'auteur peut soumettre ce renseignement.")

        with transaction.atomic():
            renseignement = Renseignement.objects.select_for_update().get(pk=renseignement.pk)
            if renseignement.statut != "brouillon":
                raise Conflit()
            renseignement.statut = "soumis"
            renseignement.save(update_fields=["statut"])
        return Response(RenseignementSerializer(renseignement).data)


class ValiderView(_CycleView):
    """soumis -> valide ou rejete, par un réviseur autre que l'auteur."""
    action_az = "valider"

    def post(self, request, pk):
        entree = DecisionSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        d = entree.validated_data

        renseignement = self.charger(request, pk)
        if renseignement.auteur_id == request.user.id:  # séparation des tâches
            self.refuser(request, renseignement, "separation_des_taches",
                         "Vous ne pouvez pas valider votre propre renseignement.")

        accepte = d["decision"] == "accepte"
        with transaction.atomic():
            renseignement = Renseignement.objects.select_for_update().get(pk=renseignement.pk)
            if renseignement.statut != "soumis":
                raise Conflit()
            version = (Version.objects.filter(renseignement=renseignement)
                       .order_by("-numero").first())
            Validation.objects.create(
                renseignement=renseignement,
                version=version,
                decision="accepté" if accepte else "rejet",
                reviseur=request.user,
                commentaire=d.get("commentaire"),
            )
            renseignement.statut = "valide" if accepte else "rejete"
            renseignement.save(update_fields=["statut"])
        return Response(RenseignementSerializer(renseignement).data)