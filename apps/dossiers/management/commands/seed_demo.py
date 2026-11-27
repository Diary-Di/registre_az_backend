from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.access.models import AffectationDossier, Blocage
from apps.dossiers.models import Dossier
from apps.users.models import Utilisateur

IDENTIFIANT = "analyste1"  # utilisateur de test (habilitation 2, rôle analyste)

# (titre, niveau, affecté ?, bloqué ?, comportement attendu pour analyste1)
CAS = [
    ("TEST A - niveau 1, affecté", 1, True, False, "VISIBLE"),
    ("TEST B - niveau 1, non affecté", 1, False, False, "refusé (condition 5)"),
    ("TEST C - niveau 4, affecté", 4, True, False, "refusé (condition 3)"),
    ("TEST D - niveau 1, affecté mais bloqué", 1, True, True, "refusé (condition 7)"),
]


class Command(BaseCommand):
    help = "Crée 4 dossiers de test pour vérifier les 7 conditions (idempotent)."

    def handle(self, *args, **options):
        try:
            user = Utilisateur.objects.get(identifiant=IDENTIFIANT)
        except Utilisateur.DoesNotExist:
            raise CommandError(f"Utilisateur '{IDENTIFIANT}' introuvable.")

        now = timezone.now()
        for titre, niveau, affecte, bloque, attendu in CAS:
            dossier, _ = Dossier.objects.get_or_create(
                titre=titre,
                defaults={
                    "finalite": "Dossier de test",
                    "unite": user.unite,
                    "niveau": niveau,
                    "statut": "actif",
                },
            )
            if affecte and not AffectationDossier.objects.filter(
                utilisateur=user, dossier=dossier
            ).exists():
                AffectationDossier.objects.create(
                    utilisateur=user, dossier=dossier, debut=now
                )
            if bloque and not Blocage.objects.filter(dossier=dossier).exists():
                Blocage.objects.create(
                    dossier=dossier, type="suspension", motif="Test",
                    decideur=user, debut=now,
                )
            self.stdout.write(f"id={dossier.id}  {titre}  ->  {attendu}")