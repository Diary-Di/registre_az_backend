from rest_framework import serializers

from apps.dossiers.models import Dossier


class DossierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dossier
        fields = ["id", "titre", "finalite", "niveau", "statut", "echeance"]
        read_only_fields = fields