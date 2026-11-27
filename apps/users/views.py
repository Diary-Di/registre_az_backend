from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import Habilitation, UtilisateurRole


class MeView(APIView):
    def get(self, request):
        now = timezone.now()
        user = request.user
        en_cours = Q(debut__lte=now) & (Q(fin__isnull=True) | Q(fin__gt=now))

        roles = UtilisateurRole.objects.filter(en_cours, utilisateur=user) \
            .values_list("role__code", flat=True)
        hab = Habilitation.objects.filter(en_cours, utilisateur=user) \
            .order_by("-niveau_max").first()

        return Response({
            "id": user.id,
            "identifiant": user.identifiant,
            "roles": list(roles),
            "niveau_max": hab.niveau_max if hab else None,
        })