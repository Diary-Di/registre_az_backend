from django.db import models
from django.db.models.functions import Now


class Dossier(models.Model):
    id = models.BigAutoField(primary_key=True)
    titre = models.TextField()
    finalite = models.TextField()
    unite = models.ForeignKey('users.UniteOrg', models.DO_NOTHING)
    niveau = models.SmallIntegerField()
    statut = models.TextField()
    regle = models.ForeignKey('dossiers.RegleConservation', models.DO_NOTHING, blank=True, null=True)
    echeance = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dossier'


class Renseignement(models.Model):
    id = models.BigAutoField(primary_key=True)
    dossier = models.ForeignKey('dossiers.Dossier', models.DO_NOTHING)
    titre = models.TextField()
    resume = models.TextField(blank=True, null=True)
    type = models.TextField()
    niveau = models.SmallIntegerField()
    statut = models.TextField()
    auteur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    date_fait = models.DateField()
    zone = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'renseignement'


class Source(models.Model):
    id = models.BigAutoField(primary_key=True)
    editeur = models.TextField(blank=True, null=True)
    titre = models.TextField()
    url = models.TextField(blank=True, null=True)
    publication = models.DateField(blank=True, null=True)
    acces = models.TextField(blank=True, null=True)
    licence = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'source'


class RenseignementSource(models.Model):
    pk = models.CompositePrimaryKey('renseignement_id', 'source_id')
    renseignement = models.ForeignKey('dossiers.Renseignement', models.DO_NOTHING)
    source = models.ForeignKey('dossiers.Source', models.DO_NOTHING)
    passage = models.TextField(blank=True, null=True)
    role = models.TextField(blank=True, null=True)
    consultation = models.DateTimeField(blank=True, null=True)
    degre_verification = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'renseignement_source'


class PieceJointe(models.Model):
    id = models.BigAutoField(primary_key=True)
    source = models.ForeignKey('dossiers.Source', models.DO_NOTHING)
    objet_stockage = models.TextField()
    empreinte = models.CharField(max_length=64)
    type = models.TextField()
    niveau = models.SmallIntegerField()
    taille = models.BigIntegerField(null=True)

    class Meta:
        managed = False
        db_table = 'piece_jointe'


class Version(models.Model):
    id = models.BigAutoField(primary_key=True)
    renseignement = models.ForeignKey('dossiers.Renseignement', models.DO_NOTHING)
    numero = models.IntegerField()
    contenu = models.TextField()
    auteur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    horodatage = models.DateTimeField(db_default=Now())
    motif = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'version'
        unique_together = (('renseignement', 'numero'),)


class Validation(models.Model):
    id = models.BigAutoField(primary_key=True)
    renseignement = models.ForeignKey('dossiers.Renseignement', models.DO_NOTHING)
    version = models.ForeignKey('dossiers.Version', models.DO_NOTHING)
    decision = models.TextField()
    reviseur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    date = models.DateTimeField(db_default=Now())
    commentaire = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'validation'


class Diffusion(models.Model):
    id = models.BigAutoField(primary_key=True)
    renseignement = models.ForeignKey('dossiers.Renseignement', models.DO_NOTHING)
    version = models.ForeignKey('dossiers.Version', models.DO_NOTHING)
    destinataire = models.TextField()
    date = models.DateTimeField(db_default=Now())
    canal = models.TextField(blank=True, null=True)
    motif = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'diffusion'


class RegleConservation(models.Model):
    id = models.BigAutoField(primary_key=True)
    categorie = models.TextField()
    duree = models.DurationField()
    declencheur = models.TextField()
    sort = models.TextField()
    revision = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'regle_conservation'
