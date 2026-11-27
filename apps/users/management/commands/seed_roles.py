from django.core.management.base import BaseCommand

from apps.users.models import Role

ROLES = [
    ("analyste", "Opérateur / Analyste"),
    ("chef_cellule", "Chef de cellule"),
    ("directeur_service", "Directeur de service"),
    ("conformite", "Conformité"),
    ("admin_technique", "Admin technique"),
    ("auditeur", "Auditeur"),
]


class Command(BaseCommand):
    help = "Crée les rôles métiers de départ (idempotent)."

    def handle(self, *args, **options):
        for code, libelle in ROLES:
            _, created = Role.objects.get_or_create(code=code, defaults={"libelle": libelle})
            self.stdout.write(f"{'créé' if created else 'existe'} : {code}")