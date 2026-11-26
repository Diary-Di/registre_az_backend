-- =============================================================================
-- Schéma SQL PostgreSQL - Registre de Renseignement AZ
-- Généré à partir du dictionnaire des tables (22 tables réparties en 4 domaines)
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- DOMAINE 1 : ORGANISATION
-- -----------------------------------------------------------------------------

-- Table : organisme (Espace logique distinct par client hébergé)
CREATE TABLE organisme (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom TEXT NOT NULL,
    actif BOOLEAN NOT NULL DEFAULT TRUE
);

-- Table : unite_org (Hiérarchie d'organisation)
CREATE TABLE unite_org (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organisme_id BIGINT NOT NULL REFERENCES organisme(id),
    nom TEXT NOT NULL,
    parent_id BIGINT REFERENCES unite_org(id),
    responsable_id BIGINT, -- Ajouté via ALTER TABLE suite à la dépendance circulaire
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Table : utilisateur (Comptes nominatifs)
CREATE TABLE utilisateur (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identifiant TEXT NOT NULL UNIQUE,
    unite_id BIGINT NOT NULL REFERENCES unite_org(id),
    statut TEXT NOT NULL CHECK (statut IN ('actif', 'suspendu', 'clos')),
    mfa_actif BOOLEAN NOT NULL DEFAULT FALSE,
    date_fin DATE
);

-- Contrainte FK responsable sur unite_org
ALTER TABLE unite_org 
    ADD CONSTRAINT fk_unite_org_responsable 
    FOREIGN KEY (responsable_id) REFERENCES utilisateur(id);

-- Table : role (Rôles système)
CREATE TABLE role (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    libelle TEXT NOT NULL
);

-- Table : utilisateur_role (Historique des attributions de rôles)
CREATE TABLE utilisateur_role (
    utilisateur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    role_id BIGINT NOT NULL REFERENCES role(id),
    debut TIMESTAMPTZ NOT NULL,
    fin TIMESTAMPTZ,
    PRIMARY KEY (utilisateur_id, role_id, debut)
);

-- Table : habilitation (Niveaux de habilitation de 0 à 4)
CREATE TABLE habilitation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utilisateur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    niveau_max SMALLINT NOT NULL CHECK (niveau_max BETWEEN 0 AND 4),
    debut TIMESTAMPTZ NOT NULL,
    fin TIMESTAMPTZ,
    autorite TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- DOMAINE 2 : ACCÈS ET CONTRÔLE
-- -----------------------------------------------------------------------------

-- Table : compartiment (Domaine métier ou mission sensible)
CREATE TABLE compartiment (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    responsable_id BIGINT REFERENCES utilisateur(id),
    actif BOOLEAN NOT NULL DEFAULT TRUE
);

-- Table : utilisateur_compartiment (Compartiments détenus par la personne)
CREATE TABLE utilisateur_compartiment (
    utilisateur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    compartiment_id BIGINT NOT NULL REFERENCES compartiment(id),
    debut TIMESTAMPTZ NOT NULL,
    fin TIMESTAMPTZ,
    PRIMARY KEY (utilisateur_id, compartiment_id, debut)
);

-- Table : regle_conservation (Règles de rétention et d'archivage)
CREATE TABLE regle_conservation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    categorie TEXT NOT NULL,
    duree INTERVAL NOT NULL,
    declencheur TEXT NOT NULL,
    sort TEXT NOT NULL CHECK (sort IN ('supprimer', 'archiver')),
    revision DATE
);

-- Table : dossier (Dossiers de renseignement)
CREATE TABLE dossier (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titre TEXT NOT NULL,
    finalite TEXT NOT NULL,
    unite_id BIGINT NOT NULL REFERENCES unite_org(id),
    niveau SMALLINT NOT NULL CHECK (niveau BETWEEN 0 AND 4),
    statut TEXT NOT NULL,
    regle_id BIGINT REFERENCES regle_conservation(id),
    echeance DATE
);

-- Table : dossier_compartiment (Compartiments requis pour un dossier)
CREATE TABLE dossier_compartiment (
    dossier_id BIGINT NOT NULL REFERENCES dossier(id),
    compartiment_id BIGINT NOT NULL REFERENCES compartiment(id),
    PRIMARY KEY (dossier_id, compartiment_id)
);

-- Table : affectation_dossier (Besoin d'en connaître temporaire)
CREATE TABLE affectation_dossier (
    utilisateur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    dossier_id BIGINT NOT NULL REFERENCES dossier(id),
    debut TIMESTAMPTZ NOT NULL,
    fin TIMESTAMPTZ,
    fonction TEXT,
    PRIMARY KEY (utilisateur_id, dossier_id, debut)
);

-- Table : autorisation_dossier (Dérogations nominatives tracées)
CREATE TABLE autorisation_dossier (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utilisateur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    dossier_id BIGINT NOT NULL REFERENCES dossier(id),
    motif TEXT NOT NULL,
    demandeur_id BIGINT REFERENCES utilisateur(id),
    approbateur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    expiration TIMESTAMPTZ NOT NULL,
    CONSTRAINT chk_autorisation_demandeur_approbateur CHECK (demandeur_id IS NULL OR demandeur_id <> approbateur_id)
);

-- Table : blocage (Suspension conformité ou gel pour litige)
CREATE TABLE blocage (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dossier_id BIGINT NOT NULL REFERENCES dossier(id),
    type TEXT NOT NULL CHECK (type IN ('suspension', 'gel litige')),
    motif TEXT NOT NULL,
    decideur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    debut TIMESTAMPTZ NOT NULL,
    fin TIMESTAMPTZ
);

-- Table : journal_acces (Journal d'audit append-only)
CREATE TABLE journal_acces (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    acteur_id BIGINT REFERENCES utilisateur(id),
    action TEXT NOT NULL,
    type_objet TEXT NOT NULL,
    objet_id BIGINT,
    horodatage TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resultat TEXT NOT NULL CHECK (resultat IN ('autorisé', 'refusé')),
    contexte JSONB
);

-- -----------------------------------------------------------------------------
-- DOMAINE 3 : RENSEIGNEMENT ET SOURCES
-- -----------------------------------------------------------------------------

-- Table : renseignement (Éléments de renseignement)
CREATE TABLE renseignement (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dossier_id BIGINT NOT NULL REFERENCES dossier(id),
    titre TEXT NOT NULL,
    resume TEXT,
    type TEXT NOT NULL,
    niveau SMALLINT NOT NULL CHECK (niveau BETWEEN 0 AND 4),
    statut TEXT NOT NULL,
    auteur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    date_fait DATE NOT NULL,
    zone TEXT
);

-- Table : source (Provenance des données)
CREATE TABLE source (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    editeur TEXT,
    titre TEXT NOT NULL,
    url TEXT,
    publication DATE,
    acces TEXT,
    licence TEXT
);

-- Table : renseignement_source (Liaison et citations contrôlables)
CREATE TABLE renseignement_source (
    renseignement_id BIGINT NOT NULL REFERENCES renseignement(id),
    source_id BIGINT NOT NULL REFERENCES source(id),
    passage TEXT,
    role TEXT,
    consultation TIMESTAMPTZ,
    degre_verification TEXT,
    PRIMARY KEY (renseignement_id, source_id)
);

-- Table : piece_jointe (Fichiers joints et empreinte SHA-256)
CREATE TABLE piece_jointe (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id BIGINT NOT NULL REFERENCES source(id),
    objet_stockage TEXT NOT NULL,
    empreinte CHAR(64) NOT NULL,
    type TEXT NOT NULL,
    niveau SMALLINT NOT NULL CHECK (niveau BETWEEN 0 AND 4)
);

-- -----------------------------------------------------------------------------
-- DOMAINE 4 : CYCLE DE VIE ET TRAÇABILITÉ
-- -----------------------------------------------------------------------------

-- Table : version (Versions figées des renseignements)
CREATE TABLE version (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    renseignement_id BIGINT NOT NULL REFERENCES renseignement(id),
    numero INT NOT NULL,
    contenu TEXT NOT NULL,
    auteur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    horodatage TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motif TEXT,
    CONSTRAINT uk_version_renseignement_numero UNIQUE (renseignement_id, numero)
);

-- Table : validation (Approbations / Rejets par le réviseur)
CREATE TABLE validation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    renseignement_id BIGINT NOT NULL REFERENCES renseignement(id),
    version_id BIGINT NOT NULL REFERENCES version(id),
    decision TEXT NOT NULL CHECK (decision IN ('accepté', 'correction', 'rejet')),
    reviseur_id BIGINT NOT NULL REFERENCES utilisateur(id),
    date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commentaire TEXT
);

-- Table : diffusion (Traçabilité des exports et envois)
CREATE TABLE diffusion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    renseignement_id BIGINT NOT NULL REFERENCES renseignement(id),
    version_id BIGINT NOT NULL REFERENCES version(id),
    destinataire TEXT NOT NULL,
    date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    canal TEXT,
    motif TEXT
);

COMMIT;
