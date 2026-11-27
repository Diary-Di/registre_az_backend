"""
Moteur de décision d'accès : les 7 conditions éliminatoires.
Source unique de vérité : la permission DRF et les listes de dossiers passent
toutes par evaluer_acces().
"""
from django.db.models import Q
from django.utils import timezone

from apps.access.models import (
    AffectationDossier,
    AutorisationDossier,
    Blocage,
    DossierCompartiment,
    JournalAcces,
    UtilisateurCompartiment,
)
from apps.dossiers.models import Dossier
from apps.users.models import Habilitation, UtilisateurRole

# Actions autorisées par rôle (condition 2). Point de départ à ajuster
# avec l'équipe. Les codes doivent correspondre à seed_roles.
ROLE_ACTIONS = {
    "analyste": {"lire", "creer", "modifier", "rechercher", "telecharger"},
    "chef_cellule": {"lire", "creer", "modifier", "rechercher", "telecharger", "valider"},
    "directeur_service": {"lire", "rechercher", "telecharger", "valider"},
    "conformite": {"lire", "rechercher"},
    "admin_technique": set(),  # aucune lecture métier
    "auditeur": set(),         # journaux uniquement (hors dossiers)
}

# Seules ces actions sont écrites dans le journal d'accès (cahier §2).
ACTIONS_JOURNALISEES = {"creer", "lire", "rechercher", "telecharger"}


class Refus(Exception):
    """Une condition éliminatoire a échoué (usage interne, jamais exposé)."""

    def __init__(self, condition, motif):
        super().__init__(motif)
        self.condition = condition
        self.motif = motif


def _en_cours(now):
    return Q(debut__lte=now) & (Q(fin__isnull=True) | Q(fin__gt=now))


def evaluer_acces(user, dossier, action, niveau_objet=None):
    """Lève Refus si l'une des 7 conditions échoue, sinon retourne None."""
    now = timezone.now()
    niveau = max(dossier.niveau, niveau_objet or 0)

    # 1. Compte actif
    if not user.is_active:
        raise Refus(1, "compte inactif")

    # 2. Rôle autorisant l'action
    codes = set(
        UtilisateurRole.objects.filter(_en_cours(now), utilisateur=user)
        .values_list("role__code", flat=True)
    )
    if not any(action in ROLE_ACTIONS.get(code, ()) for code in codes):
        raise Refus(2, "aucun rôle n'autorise cette action")

    # 3. Habilitation >= niveau de l'objet
    hab = (
        Habilitation.objects.filter(_en_cours(now), utilisateur=user)
        .order_by("-niveau_max")
        .first()
    )
    if hab is None or hab.niveau_max < niveau:
        raise Refus(3, "habilitation insuffisante")

    # 4. Compartiments compatibles (sans objet si le dossier n'en a pas)
    comp_dossier = set(
        DossierCompartiment.objects.filter(dossier=dossier)
        .values_list("compartiment_id", flat=True)
    )
    if comp_dossier and not UtilisateurCompartiment.objects.filter(
        _en_cours(now), utilisateur=user, compartiment_id__in=comp_dossier
    ).exists():
        raise Refus(4, "compartiments incompatibles")

    # 5. Affectation ou autorisation nominative
    affecte = AffectationDossier.objects.filter(
        _en_cours(now), utilisateur=user, dossier=dossier
    ).exists()
    autorise = AutorisationDossier.objects.filter(
        utilisateur=user, dossier=dossier, expiration__gt=now
    ).exists()
    if not (affecte or autorise):
        raise Refus(5, "ni affectation ni autorisation nominative")

    # 6. État du dossier
    if dossier.statut != "actif":
        raise Refus(6, "dossier non actif")

    # 7. Absence de blocage
    if Blocage.objects.filter(_en_cours(now), dossier=dossier).exists():
        raise Refus(7, "dossier bloqué")


def journaliser(user, action, type_objet, objet_id, autorise, contexte=None):
    JournalAcces.objects.create(
        acteur=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        type_objet=type_objet,
        objet_id=objet_id,
        resultat="autorisé" if autorise else "refusé",
        contexte=contexte,
    )


def verifier_acces(user, dossier, action, type_objet="dossier",
                   objet_id=None, niveau_objet=None):
    """Retourne True/False et journalise (refus toujours, succès selon l'action)."""
    objet_id = objet_id if objet_id is not None else dossier.id
    try:
        evaluer_acces(user, dossier, action, niveau_objet)
    except Refus as refus:
        journaliser(user, action, type_objet, objet_id, False,
                    {"condition": refus.condition, "dossier_id": dossier.id})
        return False
    if action in ACTIONS_JOURNALISEES:
        journaliser(user, action, type_objet, objet_id, True,
                    {"dossier_id": dossier.id})
    return True


def dossiers_accessibles(user, action="lire"):
    """Dossiers que l'utilisateur peut voir : les autres n'existent pas pour lui."""
    now = timezone.now()
    candidats = set(
        AffectationDossier.objects.filter(_en_cours(now), utilisateur=user)
        .values_list("dossier_id", flat=True)
    ) | set(
        AutorisationDossier.objects.filter(utilisateur=user, expiration__gt=now)
        .values_list("dossier_id", flat=True)
    )
    ids = []
    for dossier in Dossier.objects.filter(id__in=candidats):
        try:
            evaluer_acces(user, dossier, action)
            ids.append(dossier.id)
        except Refus:
            pass
    return Dossier.objects.filter(id__in=ids)