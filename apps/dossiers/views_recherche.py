"""Recherche plein texte (PostgreSQL FTS) limitée au corpus accessible."""
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.services import (
    ROLE_ACTIONS,
    _en_cours,
    dossiers_accessibles,
    journaliser,
    niveau_habilitation,
)
from apps.dossiers.models import Renseignement, RenseignementSource, Version
from apps.dossiers.serializers import RenseignementSerializer
from apps.users.models import UtilisateurRole

REFUS = "Accès refusé."
LIMITE = 50
CONFIG = "french"


class RechercheView(APIView):
    """
    GET ?q=... : cherche dans le titre, le résumé, le contenu des versions,
    les titres de sources et les passages cités.

    Le filtre d'accès est appliqué dans la même requête que la recherche :
    un renseignement hors du corpus accessible n'apparaît ni dans les résultats
    ni dans le total.
    """

    def get(self, request):
        user = request.user
        texte = (request.query_params.get("q") or "").strip()
        if len(texte) < 2 or len(texte) > 200:
            raise ValidationError({"q": "La recherche doit contenir de 2 à 200 caractères."})

        # Le rôle doit autoriser « rechercher » (condition 2)
        now = timezone.now()
        codes = set(
            UtilisateurRole.objects.filter(_en_cours(now), utilisateur=user)
            .values_list("role__code", flat=True)
        )
        if not any("rechercher" in ROLE_ACTIONS.get(c, ()) for c in codes):
            journaliser(user, "rechercher", "recherche", None, False,
                        {"condition": 2, "q": texte})
            raise PermissionDenied(REFUS)

        # Corpus accessible : dossiers (conditions 1 à 7), niveau, brouillons privés
        dossiers = {d.id: d for d in dossiers_accessibles(user, "rechercher")}
        plafond = niveau_habilitation(user)
        if dossiers and plafond is not None:
            requete = SearchQuery(texte, config=CONFIG, search_type="websearch")
            ids_fiche = (Renseignement.objects
                         .annotate(s=SearchVector("titre", "resume", config=CONFIG))
                         .filter(s=requete).values_list("id", flat=True))
            ids_version = (Version.objects
                           .annotate(s=SearchVector("contenu", config=CONFIG))
                           .filter(s=requete).values_list("renseignement_id", flat=True))
            ids_source = (RenseignementSource.objects
                          .annotate(s=SearchVector("passage", "source__titre", config=CONFIG))
                          .filter(s=requete).values_list("renseignement_id", flat=True))

            resultats = (
                Renseignement.objects
                .filter(dossier_id__in=list(dossiers), niveau__lte=plafond)
                .filter(Q(statut__in=["soumis", "valide", "rejete"]) | Q(auteur=user))
                .filter(Q(id__in=ids_fiche) | Q(id__in=ids_version) | Q(id__in=ids_source))
                .order_by("-id")
            )
            total = resultats.count()
            data = RenseignementSerializer(resultats[:LIMITE], many=True).data
            for item in data:
                item["dossier_titre"] = dossiers[item["dossier"]].titre
        else:
            total, data = 0, []

        journaliser(user, "rechercher", "recherche", None, True,
                    {"q": texte, "resultats": total})
        return Response({"q": texte, "total": total, "resultats": list(data)})