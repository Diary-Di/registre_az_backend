"""Détail d'un renseignement (version courante, sources, validation) et ajout de sources."""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.services import journaliser, verifier_acces
from apps.dossiers.models import (
    Renseignement,
    RenseignementSource,
    Source,
    Validation,
    Version,
)
from apps.dossiers.serializers import RenseignementSerializer
from apps.dossiers.views_cycle import REFUS, Conflit, _CycleView


class SourceCreateSerializer(serializers.Serializer):
    titre = serializers.CharField()
    passage = serializers.CharField()  # citation contrôlable : passage obligatoire
    editeur = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    publication = serializers.DateField(required=False, allow_null=True)
    acces = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    licence = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    role = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    consultation = serializers.DateTimeField(required=False)  # défaut : maintenant
    degre_verification = serializers.CharField(required=False, allow_blank=True, allow_null=True)


def _payload_source(source, liaison):
    return {
        "id": source.id,
        "titre": source.titre,
        "editeur": source.editeur,
        "url": source.url,
        "publication": source.publication,
        "acces": source.acces,
        "licence": source.licence,
        "passage": liaison.passage,
        "role": liaison.role,
        "consultation": liaison.consultation,
        "degre_verification": liaison.degre_verification,
    }


class SourceCreateView(_CycleView):
    """Ajoute une source (et le passage cité) à un brouillon, par son auteur."""
    action_az = "modifier"

    def post(self, request, pk):
        entree = SourceCreateSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        d = entree.validated_data

        renseignement = self.charger(request, pk)
        if renseignement.auteur_id != request.user.id:
            self.refuser(request, renseignement, "auteur_seul",
                         "Seul l'auteur peut ajouter une source.")

        with transaction.atomic():
            renseignement = Renseignement.objects.select_for_update().get(pk=renseignement.pk)
            if renseignement.statut != "brouillon":
                raise Conflit()
            source = Source.objects.create(
                titre=d["titre"],
                editeur=d.get("editeur"),
                url=d.get("url"),
                publication=d.get("publication"),
                acces=d.get("acces"),
                licence=d.get("licence"),
            )
            liaison = RenseignementSource.objects.create(
                renseignement=renseignement,
                source=source,
                passage=d["passage"],
                role=d.get("role"),
                consultation=d.get("consultation") or timezone.now(),
                degre_verification=d.get("degre_verification"),
            )
        return Response(_payload_source(source, liaison), status=status.HTTP_201_CREATED)


class RenseignementDetailView(APIView):
    """Consultation d'un renseignement : journalisée, 7 conditions + brouillon privé."""

    def get(self, request, pk):
        try:
            r = Renseignement.objects.select_related("dossier").get(pk=pk)
        except Renseignement.DoesNotExist:
            raise PermissionDenied(REFUS)

        # Un brouillon n'est visible que par son auteur
        if r.statut == "brouillon" and r.auteur_id != request.user.id:
            journaliser(request.user, "lire", "renseignement", r.id, False,
                        {"regle": "brouillon_prive", "dossier_id": r.dossier_id})
            raise PermissionDenied(REFUS)

        if not verifier_acces(request.user, r.dossier, "lire",
                              type_objet="renseignement", objet_id=r.id,
                              niveau_objet=r.niveau):
            raise PermissionDenied(REFUS)

        version = Version.objects.filter(renseignement=r).order_by("-numero").first()
        liaisons = (RenseignementSource.objects.filter(renseignement=r)
                    .select_related("source"))
        validation = Validation.objects.filter(renseignement=r).order_by("-id").first()

        data = dict(RenseignementSerializer(r).data)
        data["version_courante"] = None if version is None else {
            "numero": version.numero,
            "contenu": version.contenu,
            "motif": version.motif,
            "auteur": version.auteur_id,
            "horodatage": version.horodatage,
        }
        data["sources"] = [_payload_source(l.source, l) for l in liaisons]
        data["validation"] = None if validation is None else {
            "decision": validation.decision,
            "reviseur": validation.reviseur_id,
            "date": validation.date,
            "commentaire": validation.commentaire,
        }
        return Response(data)