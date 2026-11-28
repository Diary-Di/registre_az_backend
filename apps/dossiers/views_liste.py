"""Console de validation : renseignements soumis que l'utilisateur peut valider."""
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.services import dossiers_accessibles, niveau_habilitation
from apps.dossiers.models import Renseignement
from apps.dossiers.serializers import RenseignementSerializer


class AValiderListView(APIView):
    """
    Renseignements au statut « soumis » dans les dossiers où l'utilisateur
    peut valider (7 conditions avec l'action « valider »), sans ses propres
    renseignements (réviseur != auteur) et dans la limite de son habilitation.
    Un utilisateur sans droit de validation reçoit simplement une liste vide.
    """

    def get(self, request):
        user = request.user
        dossiers = {d.id: d for d in dossiers_accessibles(user, "valider")}
        plafond = niveau_habilitation(user)
        if not dossiers or plafond is None:
            return Response([])

        renseignements = (
            Renseignement.objects
            .filter(dossier_id__in=list(dossiers), statut="soumis", niveau__lte=plafond)
            .exclude(auteur=user)
            .order_by("id")
        )
        data = RenseignementSerializer(renseignements, many=True).data
        for item in data:
            item["dossier_titre"] = dossiers[item["dossier"]].titre
        return Response(data)