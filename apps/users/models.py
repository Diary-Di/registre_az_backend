from django.db import models


class Organisme(models.Model):
    id = models.BigAutoField(primary_key=True)
    nom = models.TextField()
    actif = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'organisme'


class UniteOrg(models.Model):
    id = models.BigAutoField(primary_key=True)
    organisme = models.ForeignKey('users.Organisme', models.DO_NOTHING)
    nom = models.TextField()
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    responsable = models.ForeignKey('users.Utilisateur', models.DO_NOTHING, blank=True, null=True)
    active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'unite_org'


class Utilisateur(models.Model):
    id = models.BigAutoField(primary_key=True)
    identifiant = models.TextField(unique=True)
    unite = models.ForeignKey('users.UniteOrg', models.DO_NOTHING)
    statut = models.TextField()
    mfa_actif = models.BooleanField()
    date_fin = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'utilisateur'


class Role(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.TextField(unique=True)
    libelle = models.TextField()

    class Meta:
        managed = False
        db_table = 'role'


class UtilisateurRole(models.Model):
    pk = models.CompositePrimaryKey('utilisateur_id', 'role_id', 'debut')
    utilisateur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    role = models.ForeignKey('users.Role', models.DO_NOTHING)
    debut = models.DateTimeField()
    fin = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'utilisateur_role'


class Habilitation(models.Model):
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey('users.Utilisateur', models.DO_NOTHING)
    niveau_max = models.SmallIntegerField()
    debut = models.DateTimeField()
    fin = models.DateTimeField(blank=True, null=True)
    autorite = models.TextField()

    class Meta:
        managed = False
        db_table = 'habilitation'
