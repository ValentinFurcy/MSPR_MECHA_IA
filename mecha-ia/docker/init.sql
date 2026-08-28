-- init.sql — Initialisation PostgreSQL MECHA
-- Exécuté automatiquement au premier lancement du conteneur

-- Base interne dédiée à Metabase (stocke sa propre config, jamais les données MECHA)
CREATE DATABASE metabase_internal;

-- Schémas par site (dans la base "mecha", connexion par défaut de ce script)
CREATE SCHEMA IF NOT EXISTS site_fr1;
CREATE SCHEMA IF NOT EXISTS site_fr2;
CREATE SCHEMA IF NOT EXISTS site_fr3;
CREATE SCHEMA IF NOT EXISTS site_es1;
CREATE SCHEMA IF NOT EXISTS site_es2;
CREATE SCHEMA IF NOT EXISTS shared;

-- Table référentiel machines (partagé)
CREATE TABLE shared.machines (
    machine_id   VARCHAR(50) PRIMARY KEY,
    site         VARCHAR(10) NOT NULL,
    type_machine VARCHAR(50) DEFAULT 'centre_usinage',
    date_mise_en_service DATE,
    statut       VARCHAR(20) DEFAULT 'actif'
);

-- Fonction pour créer les tables dans chaque schéma site
DO $$
DECLARE
    s TEXT;
BEGIN
    FOREACH s IN ARRAY ARRAY['site_fr1','site_fr2','site_fr3','site_es1','site_es2']
    LOOP
        EXECUTE format('
            CREATE TABLE %I.sensor_data (
                id              SERIAL PRIMARY KEY,
                machine_id      VARCHAR(50) NOT NULL,
                timestamp       TIMESTAMPTZ NOT NULL,
                cycle_number    INT,
                temperature_moteur      FLOAT,
                temperature_lubrifiant  FLOAT,
                temperature_carter      FLOAT,
                pression_hydraulique    FLOAT,
                vitesse_broche          FLOAT,
                vibration_axe_x         FLOAT,
                vibration_axe_y         FLOAT,
                debit_refroidissement   FLOAT,
                humidite_ambiante       FLOAT,
                indice_usure_outil      FLOAT
            )', s);

        EXECUTE format('
            CREATE TABLE %I.predictions (
                id                  SERIAL PRIMARY KEY,
                machine_id          VARCHAR(50) NOT NULL,
                timestamp           TIMESTAMPTZ DEFAULT NOW(),
                cycle_number        INT,
                rul_predit          INT,
                risk_level_predit   VARCHAR(20),
                anomaly_score       FLOAT,
                modele_classification VARCHAR(50),
                modele_regression     VARCHAR(50),
                capteur_principal   VARCHAR(50),
                created_at          TIMESTAMPTZ DEFAULT NOW()
            )', s);

        EXECUTE format('
            CREATE TABLE %I.alertes (
                id              SERIAL PRIMARY KEY,
                machine_id      VARCHAR(50) NOT NULL,
                timestamp       TIMESTAMPTZ DEFAULT NOW(),
                niveau          VARCHAR(20) NOT NULL,
                message         TEXT,
                acquittee       BOOLEAN DEFAULT FALSE,
                acquittee_par   VARCHAR(100),
                acquittee_at    TIMESTAMPTZ
            )', s);

        -- Alertes capteur défaillant (distinct des alertes machine : cause instrumentale, pas mécanique)
        EXECUTE format('
            CREATE TABLE %I.alertes_capteur (
                id              SERIAL PRIMARY KEY,
                machine_id      VARCHAR(50) NOT NULL,
                capteur         VARCHAR(50) NOT NULL,
                nb_aberrations  INT NOT NULL,
                premier_cycle   INT,
                dernier_cycle   INT,
                detecte_at      TIMESTAMPTZ DEFAULT NOW(),
                acquittee       BOOLEAN DEFAULT FALSE,
                acquittee_par   VARCHAR(100),
                acquittee_at    TIMESTAMPTZ
            )', s);

        -- Index performance
        EXECUTE format('CREATE INDEX idx_%s_sensor_machine_time ON %I.sensor_data (machine_id, timestamp DESC)', s, s);
        EXECUTE format('CREATE INDEX idx_%s_pred_machine_time ON %I.predictions (machine_id, timestamp DESC)', s, s);
        EXECUTE format('CREATE INDEX idx_%s_alertes_machine ON %I.alertes (machine_id, timestamp DESC)', s, s);
        EXECUTE format('CREATE INDEX idx_%s_alertes_capteur ON %I.alertes_capteur (machine_id, capteur)', s, s);
    END LOOP;
END $$;

-- Users applicatifs (lecture seule)
CREATE USER grafana_ro WITH PASSWORD 'grafana_mecha_2026';
CREATE USER metabase_ro WITH PASSWORD 'metabase_mecha_2026';
CREATE USER api_rw WITH PASSWORD 'api_mecha_2026';

-- Droits lecture Grafana/Metabase sur tous les schémas
DO $$
DECLARE
    s TEXT;
BEGIN
    FOREACH s IN ARRAY ARRAY['site_fr1','site_fr2','site_fr3','site_es1','site_es2','shared']
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO grafana_ro, metabase_ro, api_rw', s);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO grafana_ro, metabase_ro', s);
        EXECUTE format('GRANT ALL ON ALL TABLES IN SCHEMA %I TO api_rw', s);
        EXECUTE format('GRANT USAGE ON ALL SEQUENCES IN SCHEMA %I TO api_rw', s);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO grafana_ro, metabase_ro', s);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT ALL ON TABLES TO api_rw', s);
    END LOOP;
END $$;

-- Search path par user
ALTER ROLE grafana_ro SET search_path TO site_fr1, site_fr2, site_fr3, site_es1, site_es2, shared;
ALTER ROLE metabase_ro SET search_path TO site_fr1, site_fr2, site_fr3, site_es1, site_es2, shared;
ALTER ROLE api_rw SET search_path TO site_fr1, shared;
