from rest_framework import serializers

from apps.dossiers.models import Dossier, Renseignement


class DossierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dossier
        fields = ["id", "titre", "finalite", "niveau", "statut", "echeance"]
        read_only_fields = fields


class RenseignementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Renseignement
        fields = ["id", "dossier", "titre", "resume", "type", "niveau",
                  "statut", "auteur", "date_fait", "zone"]
        read_only_fields = fields


class RenseignementCreateSerializer(serializers.Serializer):
    titre = serializers.CharField()
    resume = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    type = serializers.CharField()
    niveau = serializers.IntegerField(min_value=0, max_value=4)
    date_fait = serializers.DateField()
    zone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    contenu = serializers.CharField()  # texte de la version 1