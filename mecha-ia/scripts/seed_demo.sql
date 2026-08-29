-- Jeu de démonstration pour les dashboards Grafana.
--
-- Sert uniquement à montrer les écrans sans avoir à exécuter tout le pipeline
-- (notebook -> InfluxDB -> run_pipeline). Ce n'est PAS un jeu d'entraînement :
-- les valeurs sont écrites à la main pour couvrir les cas d'affichage
-- (critique, urgent, à surveiller, normal, alerte capteur).
--
-- Usage :
--   docker compose exec -T postgres psql -U admin -d mecha < scripts/seed_demo.sql
--
-- Pour repartir de zéro : relancer le script, il vide les tables d'abord.

BEGIN;

TRUNCATE site_fr1.predictions, site_fr1.alertes, site_fr1.alertes_capteur RESTART IDENTITY;
TRUNCATE site_fr2.predictions, site_fr2.alertes RESTART IDENTITY;
TRUNCATE site_es1.predictions, site_es1.alertes RESTART IDENTITY;

-- --- Référentiel machines ---
INSERT INTO shared.machines (machine_id, site, type_machine, date_mise_en_service, statut)
VALUES
  ('MECHA-USI-001', 'site_fr1', 'centre_usinage', '2019-03-12', 'actif'),
  ('MECHA-USI-002', 'site_fr1', 'centre_usinage', '2020-07-01', 'actif'),
  ('MECHA-USI-003', 'site_fr1', 'machine_decoupe', '2018-11-23', 'actif'),
  ('MECHA-USI-004', 'site_fr1', 'centre_usinage', '2021-02-15', 'actif'),
  ('MECHA-USI-005', 'site_fr1', 'machine_decoupe', '2017-09-08', 'actif'),
  ('MECHA-USI-101', 'site_fr2', 'centre_usinage', '2020-01-20', 'actif'),
  ('MECHA-USI-102', 'site_fr2', 'centre_usinage', '2019-06-30', 'actif'),
  ('MECHA-USI-201', 'site_es1', 'centre_usinage', '2022-04-04', 'actif')
ON CONFLICT (machine_id) DO NOTHING;

-- --- Historique de prédictions (site_fr1) ---
-- Deux passages par machine : la ligne la plus récente est celle que les
-- dashboards affichent (DISTINCT ON ... ORDER BY timestamp DESC).
INSERT INTO site_fr1.predictions
  (machine_id, "timestamp", cycle_number, rul_predit, risk_level_predit,
   modele_classification, modele_regression, capteur_principal)
VALUES
  -- passage il y a 6 h
  ('MECHA-USI-001', NOW() - INTERVAL '6 hours', 210,  9, 'a_risque',     'Logistic Regression', 'Random Forest', 'vibration_axe_x'),
  ('MECHA-USI-002', NOW() - INTERVAL '6 hours', 150, 42, 'a_surveiller', 'Logistic Regression', 'Random Forest', 'temperature_moteur'),
  ('MECHA-USI-003', NOW() - INTERVAL '6 hours',  80, 96, 'normal',       'Logistic Regression', 'Random Forest', 'pression_hydraulique'),
  ('MECHA-USI-004', NOW() - INTERVAL '6 hours', 120, 61, 'normal',       'Logistic Regression', 'Random Forest', 'vitesse_broche'),
  ('MECHA-USI-005', NOW() - INTERVAL '6 hours', 240, 18, 'a_surveiller', 'Logistic Regression', 'Random Forest', 'indice_usure_outil'),
  -- passage le plus récent
  ('MECHA-USI-001', NOW() - INTERVAL '20 minutes', 216,  3, 'a_risque',     'Logistic Regression', 'Random Forest', 'vibration_axe_x'),
  ('MECHA-USI-002', NOW() - INTERVAL '20 minutes', 156, 37, 'a_surveiller', 'Logistic Regression', 'Random Forest', 'temperature_moteur'),
  ('MECHA-USI-003', NOW() - INTERVAL '20 minutes',  86, 90, 'normal',       'Logistic Regression', 'Random Forest', 'pression_hydraulique'),
  ('MECHA-USI-004', NOW() - INTERVAL '20 minutes', 126, 55, 'normal',       'Logistic Regression', 'Random Forest', 'vitesse_broche'),
  ('MECHA-USI-005', NOW() - INTERVAL '20 minutes', 246, 12, 'a_risque',     'Logistic Regression', 'Random Forest', 'indice_usure_outil');

-- --- Alertes machine (site_fr1) ---
-- Reproduit ce que génère l'API à l'insertion (cf. src/api/main.py) :
-- RUL <= 4 -> critique, sinon a_risque -> urgent.
INSERT INTO site_fr1.alertes (machine_id, "timestamp", niveau, message, acquittee)
VALUES
  ('MECHA-USI-001', NOW() - INTERVAL '20 minutes', 'critique',
   'Intervention nécessaire dans les 4 prochaines heures (RUL estimé : 3h) — capteur principal : vibration_axe_x', FALSE),
  ('MECHA-USI-005', NOW() - INTERVAL '20 minutes', 'urgent',
   'RUL prédit : 12 cycles — intervention à planifier — capteur principal : indice_usure_outil', FALSE),
  ('MECHA-USI-001', NOW() - INTERVAL '6 hours', 'urgent',
   'RUL prédit : 9 cycles — intervention à planifier — capteur principal : vibration_axe_x', TRUE);

-- --- Alerte capteur (cause instrumentale, site_fr1) ---
INSERT INTO site_fr1.alertes_capteur
  (machine_id, capteur, nb_aberrations, premier_cycle, dernier_cycle, detecte_at, acquittee)
VALUES
  ('MECHA-USI-003', 'temperature_carter', 7, 74, 86, NOW() - INTERVAL '2 hours', FALSE),
  ('MECHA-USI-004', 'humidite_ambiante',  3, 119, 126, NOW() - INTERVAL '5 hours', FALSE);

-- --- Autres sites (pour le dashboard multi-sites) ---
INSERT INTO site_fr2.predictions
  (machine_id, "timestamp", cycle_number, rul_predit, risk_level_predit,
   modele_classification, modele_regression, capteur_principal)
VALUES
  ('MECHA-USI-101', NOW() - INTERVAL '15 minutes', 190, 25, 'a_surveiller', 'Logistic Regression', 'Random Forest', 'temperature_lubrifiant'),
  ('MECHA-USI-102', NOW() - INTERVAL '15 minutes', 130, 71, 'normal',       'Logistic Regression', 'Random Forest', 'debit_refroidissement');

INSERT INTO site_es1.predictions
  (machine_id, "timestamp", cycle_number, rul_predit, risk_level_predit,
   modele_classification, modele_regression, capteur_principal)
VALUES
  ('MECHA-USI-201', NOW() - INTERVAL '10 minutes', 205, 6, 'a_risque', 'Logistic Regression', 'Random Forest', 'vibration_axe_y');

INSERT INTO site_es1.alertes (machine_id, "timestamp", niveau, message, acquittee)
VALUES
  ('MECHA-USI-201', NOW() - INTERVAL '10 minutes', 'urgent',
   'RUL prédit : 6 cycles — intervention à planifier — capteur principal : vibration_axe_y', FALSE);

COMMIT;

SELECT 'site_fr1' AS site, count(*) AS predictions FROM site_fr1.predictions
UNION ALL SELECT 'site_fr2', count(*) FROM site_fr2.predictions
UNION ALL SELECT 'site_es1', count(*) FROM site_es1.predictions;
