from rest_framework.permissions import BasePermission

from apps.access.services import verifier_acces

ACTION_PAR_METHODE = {
    "GET": "lire",
    "HEAD": "lire",
    "OPTIONS": "lire",
    "POST": "creer",
    "PUT": "modifier",
    "PATCH": "modifier",
    # DELETE absent : suppression refusée partout
}


def resoudre_objet(obj):
    """Retourne (dossier, niveau_objet, type_objet) pour un objet protégé."""
    nom = obj.__class__.__name__
    if nom == "Dossier":
        return obj, None, "dossier"
    if nom == "Renseignement":
        return obj.dossier, obj.niveau, "renseignement"
    if nom == "Version":
        return obj.renseignement.dossier, obj.renseignement.niveau, "version"
    raise TypeError(f"Objet non protégé par AZAccessPermission : {nom}")


class AZAccessPermission(BasePermission):
    """
    Permission centrale. Une vue peut forcer l'action métier avec un attribut
    `action_az` (ex. "valider", "telecharger", "rechercher").
    Pour une création (POST sans objet existant), appeler directement
    apps.access.services.verifier_acces() sur le dossier cible.
    """
    message = "Accès refusé."  # message neutre : ni titre ni contenu

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action_az", None) or ACTION_PAR_METHODE.get(request.method)
        if action is None:
            return False
        dossier, niveau_objet, type_objet = resoudre_objet(obj)
        return verifier_acces(
            request.user, dossier, action,
            type_objet=type_objet, objet_id=obj.pk, niveau_objet=niveau_objet,
        )