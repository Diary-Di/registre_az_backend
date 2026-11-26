from django.db import models
from django.db.models.functions import Now


class Compartiment(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.TextField(unique=True)
    responsable = models.ForeignKey('users.Utilisateur', models.DO_NOTHING, blank=True, null=True)
    actif = models.BooleanField(db_default=True)

    class Meta:
        managed = False
        db_table = 'compartiment'


class UtilisateurCompartiment(models.Model):
    pk = models.CompositePrimaryKey('utilisateur_id', 'compartiment_id', 'debut')
    utilisateur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    compartiment = models.ForeignKey('access.Compartiment', models.DO_NOTHING)
    debut = models.DateTimeField()
    fin = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'utilisateur_compartiment'


class DossierCompartiment(models.Model):
    pk = models.CompositePrimaryKey('dossier_id', 'compartiment_id')
    dossier = models.ForeignKey('dossiers.Dossier', models.DO_NOTHING)
    compartiment = models.ForeignKey('access.Compartiment', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'dossier_compartiment'


class AffectationDossier(models.Model):
    pk = models.CompositePrimaryKey('utilisateur_id', 'dossier_id', 'debut')
    utilisateur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    dossier = models.ForeignKey('dossiers.Dossier', models.DO_NOTHING)
    debut = models.DateTimeField()
    fin = models.DateTimeField(blank=True, null=True)
    fonction = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'affectation_dossier'


class AutorisationDossier(models.Model):
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    dossier = models.ForeignKey('dossiers.Dossier', models.DO_NOTHING)
    motif = models.TextField()
    demandeur = models.ForeignKey(
        'users.Utilisateur',
        models.DO_NOTHING,
        related_name='autorisationdossier_demandeur_set',
        blank=True,
        null=True,
    )
    approbateur = models.ForeignKey(
        'users.Utilisateur',
        models.DO_NOTHING,
        related_name='autorisationdossier_approbateur_set',
    )
    expiration = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'autorisation_dossier'


class Blocage(models.Model):
    id = models.BigAutoField(primary_key=True)
    dossier = models.ForeignKey('dossiers.Dossier', models.DO_NOTHING)
    type = models.TextField()
    motif = models.TextField()
    decideur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    debut = models.DateTimeField()
    fin = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'blocage'


class JournalAcces(models.Model):
    id = models.BigAutoField(primary_key=True)
    acteur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING, blank=True, null=True)
    action = models.TextField()
    type_objet = models.TextField()
    objet_id = models.BigIntegerField(blank=True, null=True)
    horodatage = models.DateTimeField(db_default=Now())
    resultat = models.TextField()
    contexte = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'journal_acces'
