"""
Ouverture d'un dossier (MO 01, version MVP) : conditions 1 à 4 du moteur d'accès.
Les conditions 5 à 7 portent sur un dossier existant : elles ne s'appliquent pas
à sa création.
"""
from django.utils import timezone

from apps.access.models import UtilisateurCompartiment
from apps.access.services import Refus, _en_cours, journaliser, niveau_habilitation
from apps.users.models import UtilisateurRole

# Rôles autorisés à ouvrir un dossier (à ajuster avec l'équipe).
ROLES_OUVERTURE = {"chef_cellule", "directeur_service"}


def evaluer_ouverture(user, niveau, compartiment_ids):
    now = timezone.now()

    # 1. Compte actif
    if not user.is_active:
        raise Refus(1, "compte inactif")

    # 2. Rôle autorisant l'ouverture
    codes = set(
        UtilisateurRole.objects.filter(_en_cours(now), utilisateur=user)
        .values_list("role__code", flat=True)
    )
    if not codes & ROLES_OUVERTURE:
        raise Refus(2, "aucun rôle n'autorise l'ouverture")

    # 3. Habilitation >= niveau du dossier à ouvrir
    plafond = niveau_habilitation(user)
    if plafond is None or plafond < niveau:
        raise Refus(3, "habilitation insuffisante")

    # 4. On n'attache pas un compartiment qu'on ne détient pas soi-même
    if compartiment_ids:
        detenus = set(
            UtilisateurCompartiment.objects.filter(_en_cours(now), utilisateur=user)
            .values_list("compartiment_id", flat=True)
        )
        if not set(compartiment_ids) <= detenus:
            raise Refus(4, "compartiment non détenu")


def verifier_ouverture(user, niveau, compartiment_ids):
    """True/False ; journalise les refus. Le succès est journalisé par l'appelant."""
    try:
        evaluer_ouverture(user, niveau, compartiment_ids)
    except Refus as refus:
        journaliser(user, "creer", "dossier", None, False,
                    {"condition": refus.condition, "operation": "ouverture"})
        return False
    return True