-- =============================================================================
-- Registre AZ - Sécurité et intégrité en base (à exécuter APRÈS schema.sql)
-- =============================================================================
BEGIN;

-- 1. Authentification : colonnes nécessaires à AbstractBaseUser ---------------
ALTER TABLE utilisateur
    ADD COLUMN password   VARCHAR(128) NOT NULL DEFAULT '!',
    ADD COLUMN last_login TIMESTAMPTZ;

-- 2. Pièces : taille du fichier (cahier des charges §4) -----------------------
ALTER TABLE piece_jointe ADD COLUMN taille BIGINT;

-- 3. Valeurs de statut contrôlées ---------------------------------------------
ALTER TABLE dossier
    ADD CONSTRAINT chk_dossier_statut
    CHECK (statut IN ('actif', 'archive', 'cloture'));
ALTER TABLE renseignement
    ADD CONSTRAINT chk_renseignement_statut
    CHECK (statut IN ('brouillon', 'soumis', 'valide', 'rejete'));

-- 4. Une seule habilitation effective par période -----------------------------
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE habilitation
    ADD CONSTRAINT excl_habilitation_periode
    EXCLUDE USING gist (
        utilisateur_id WITH =,
        tstzrange(debut, fin) WITH &&
    );

-- 5. Recherche plein texte (index utilisé par les requêtes FTS) ---------------
CREATE INDEX idx_renseignement_fts ON renseignement
    USING gin (to_tsvector('french',
        coalesce(titre, '') || ' ' || coalesce(resume, '')));

-- 6. Fonctions de blocage -----------------------------------------------------
CREATE OR REPLACE FUNCTION az_refuse_modification() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

-- journal_acces : INSERT seul (même pour le propriétaire de la table)
CREATE TRIGGER trg_journal_append_only
    BEFORE UPDATE OR DELETE ON journal_acces
    FOR EACH ROW EXECUTE FUNCTION az_refuse_modification();
CREATE TRIGGER trg_journal_no_truncate
    BEFORE TRUNCATE ON journal_acces
    FOR EACH STATEMENT EXECUTE FUNCTION az_refuse_modification();

-- validation et piece_jointe : on ne les modifie jamais
CREATE TRIGGER trg_validation_append_only
    BEFORE UPDATE OR DELETE ON validation
    FOR EACH ROW EXECUTE FUNCTION az_refuse_modification();
CREATE TRIGGER trg_piece_jointe_immuable
    BEFORE UPDATE OR DELETE ON piece_jointe
    FOR EACH ROW EXECUTE FUNCTION az_refuse_modification();

-- 7. Version validée non modifiable -------------------------------------------
CREATE OR REPLACE FUNCTION az_version_validee_figee() RETURNS trigger AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM validation
               WHERE version_id = OLD.id AND decision = 'accepté') THEN
        RAISE EXCEPTION 'Version % validée : modification interdite', OLD.id
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_version_figee
    BEFORE UPDATE OR DELETE ON version
    FOR EACH ROW EXECUTE FUNCTION az_version_validee_figee();

-- 8. Séparation des tâches : réviseur != auteur -------------------------------
CREATE OR REPLACE FUNCTION az_controle_reviseur() RETURNS trigger AS $$
DECLARE v_auteur BIGINT;
BEGIN
    SELECT auteur_id INTO v_auteur FROM renseignement WHERE id = NEW.renseignement_id;
    IF v_auteur = NEW.reviseur_id THEN
        RAISE EXCEPTION 'Le réviseur ne peut pas valider son propre renseignement'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM version
                   WHERE id = NEW.version_id AND renseignement_id = NEW.renseignement_id) THEN
        RAISE EXCEPTION 'La version % n''appartient pas au renseignement %',
            NEW.version_id, NEW.renseignement_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validation_reviseur
    BEFORE INSERT ON validation
    FOR EACH ROW EXECUTE FUNCTION az_controle_reviseur();

-- 9. Niveau d'un renseignement >= niveau de son dossier -----------------------
CREATE OR REPLACE FUNCTION az_controle_niveau() RETURNS trigger AS $$
BEGIN
    IF NEW.niveau < (SELECT niveau FROM dossier WHERE id = NEW.dossier_id) THEN
        RAISE EXCEPTION 'Le niveau du renseignement doit être >= à celui du dossier'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_renseignement_niveau
    BEFORE INSERT OR UPDATE OF niveau, dossier_id ON renseignement
    FOR EACH ROW EXECUTE FUNCTION az_controle_niveau();

COMMIT;

-- 10. Rôle applicatif à droits limités (à adapter, hors transaction) ----------
-- Django doit se connecter avec ce rôle, pas avec un superuser/propriétaire.
-- CREATE ROLE az_app LOGIN PASSWORD '...';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO az_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO az_app;
-- REVOKE UPDATE, DELETE, TRUNCATE ON journal_acces, validation, piece_jointe FROM az_app;
