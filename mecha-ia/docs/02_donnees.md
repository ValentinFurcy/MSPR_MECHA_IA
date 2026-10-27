# Données : cartographie, RGPD et jeu de données

Des sources disponibles chez MECHA au jeu de données livré dans `data/`.

## 1. Cartographie des données

Inventaire des sources disponibles, sélection de celles qui alimentent la solution IA, et réduction de l'espace de travail du modèle.

### 1.1 Sources disponibles

| Source | Contenu | Granularité | Propriétaire | Couverture des 5 sites | Données personnelles |
|---|---|---|---|---|---|
| **Capteurs IoT machines** | Températures, vitesses, vibrations, états machine, temps de cycle | Seconde à minute | Direction industrielle | 3 sites FR complets, 2 sites ES partiels | Non |
| **SCADA** | Supervision atelier, états de ligne, alarmes | Seconde | DSI | Hétérogène selon site | Indirect (utilisateur ayant acquitté) |
| **MES** | Ordres de fabrication, temps de cycle, rebuts | Ordre / pièce | DSI | Hétérogène | Indirect (opérateur ayant validé) |
| **GMAO / historique maintenance** | Interventions, causes, durées, pièces changées | Événement | Maintenance | Partiel, parfois hors outil | Indirect (matricule intervenant) |
| **Contrôle qualité** | Non-conformités, mesures dimensionnelles | Pièce / lot | Direction qualité | Complète | Non |
| **ERP** | Coûts, contrats, délais | Commande | Direction financière | Complète | Oui (RH) |

Volume attendu côté capteurs : environ **10 000 points/minute** tous sites confondus, soit ~14,4 M points/jour et ~1,3 milliard de points sur 90 jours de rétention (source : `01_besoin_et_conduite_du_changement.md` §1.2.2).

### 1.2 Réduction de l'espace de l'IA

#### 1.2.1 Au niveau des sources

| Source | Retenue | Justification |
|---|---|---|
| Capteurs IoT machines | **Oui** | Porte le signal de dégradation, seule source à la granularité requise |
| GMAO / historique maintenance | Cible | Indispensable pour obtenir de vrais labels de panne ; qualité insuffisante à ce jour |
| SCADA / MES | Cible | Apporte le contexte de production (mode, charge), utile en variable explicative |
| Contrôle qualité | Non | Relève d'un autre cas d'usage (dérive qualité), hors périmètre du prototype |
| ERP | Non | Hors finalité maintenance ; contient des données RH, exclu par principe de minimisation |

Écarter l'ERP n'est pas qu'un choix technique : c'est l'application directe de la limitation de finalité (`02_donnees.md` §2.3.3) et de l'engagement de non-usage RH pris devant le CSE.

#### 1.2.2 Au niveau des variables

Le jeu source expose **21 capteurs**, dont **10 sont retenus** et renommés au vocabulaire MECHA :

| Capteur source | Nom MECHA | Capteur source | Nom MECHA |
|---|---|---|---|
| `sensor_2` | `temperature_moteur` | `sensor_12` | `vibration_axe_y` |
| `sensor_3` | `temperature_lubrifiant` | `sensor_14` | `debit_refroidissement` |
| `sensor_4` | `temperature_carter` | `sensor_15` | `humidite_ambiante` |
| `sensor_7` | `pression_hydraulique` | `sensor_21` | `indice_usure_outil` |
| `sensor_9` | `vitesse_broche` | `sensor_11` | `vibration_axe_x` |

Onze capteurs sont écartés : `sensor_1, 5, 6, 8, 10, 13, 16, 17, 18, 19, 20`.

**Critère de réduction retenu pour les données réelles** : écarter les capteurs à variance nulle (aucun signal) puis les capteurs redondants (corrélation forte entre eux, information déjà portée par un capteur conservé).

**État actuel** : ce critère n'est pas discriminant sur le jeu de repli — aucun capteur n'est constant et la corrélation avec la progression d'usure est identique entre retenus et écartés (|r| = 0,795 des deux côtés, 9 200 lignes vérifiées).
La sélection des 10 capteurs est donc une **convention de modélisation** au vocabulaire MECHA, à re-justifier statistiquement sur données réelles.

Aucune des sources industrielles listées en §1 n'alimente le prototype à ce stade : il s'appuie sur un jeu public ou synthétique dont l'origine, le dictionnaire, les hypothèses et les limites sont décrits dans `02_donnees.md` §3.

### 1.3 Outils de collecte et de traitement (ETL)

| Étape | Outil | Justification | État |
|---|---|---|---|
| Collecte capteurs | MQTT | Standard IoT industriel, léger, QoS configurable | Cible |
| Transport / tampon | Apache Kafka | Découplage producteurs/consommateurs, rejeu possible | Cible |
| Stockage brut | InfluxDB | Base temporelle, compression et downsampling natifs | Implémenté |
| Nettoyage / transformation | Python, pandas, scikit-learn | Logique partagée entre entraînement et inférence (`src/cleaning.py`) | Implémenté |
| Stockage exploitable | PostgreSQL | Schéma par site, comptes à moindre privilège | Implémenté |
| Orchestration | `scripts/run_pipeline.py` | Suffisant au volume prototype ; Airflow en cible multi-sites | Implémenté |

Dans le prototype, la chaîne MQTT/Kafka est remplacée par `scripts/load_sensors_to_influx.py`, qui rejoue les données comme si elles provenaient des capteurs. Justification des choix par couche : `03_architecture_technique.md` §1.

### 1.4 Rôle du DPO

Le DPO est consulté sur trois points de cette cartographie : l'exclusion de l'ERP et des données RH du périmètre, la pseudonymisation des matricules dans l'historique GMAO avant tout usage analytique, et la validation du registre des traitements pour les sources SCADA et MES qui tracent indirectement l'activité des opérateurs. Détail : `02_donnees.md` §2.5.

### 1.5 Limites

- Cartographie établie à partir du cahier des charges et de l'entretien client simulé, sans audit des systèmes réels.
- Volumes et taux de couverture par site sont des ordres de grandeur déclaratifs, non mesurés.
- La qualité réelle des données GMAO n'a pas pu être évaluée ; c'est le principal risque pesant sur le passage à des labels de panne réels.

---

## 2. RGPD et sécurité des données

### 2.1 Contexte

Le prototype MECHA utilise **exclusivement des données publiques ou synthétiques** (contrainte cahier des charges, section V). Aucune donnée réelle d'entreprise ni personnelle n'est traitée dans cette phase.

Le présent document décrit néanmoins **le dispositif RGPD qui devrait être appliqué** en cas de bascule sur données réelles (industrialisation).

### 2.2 Typologie des données concernées (cas industrialisation)

| Catégorie | Exemple | Personnelle ? | Sensible ? |
|---|---|---|---|
| Télémétrie machine | Température, vibration, vitesse broche | Non | Non |
| État machine | Codes défaut, marche/arrêt | Non | Non |
| Historique maintenance | Intervention, cause, durée | Indirect (via ID opérateur) | Non |
| Identifiant opérateur | Matricule, badge | **Oui** | Non |
| Log SCADA/MES | Utilisateur ayant validé un ordre | **Oui** | Non |

Les données **techniques** (capteurs, machines) ne relèvent **pas** du RGPD. Les données **d'opérateurs** (matricule, intervention nominative) en relèvent.

### 2.3 Principes appliqués

#### 2.3.1 Minimisation
Seules les variables utiles au modèle sont collectées. Les identifiants opérateurs ne sont **pas** injectés dans les features ML.

#### 2.3.2 Pseudonymisation
Les matricules opérateur sont remplacés par un hash SHA-256 salé avant stockage analytique. La table de correspondance reste dans le SI RH, non accessible à la plateforme IA.

#### 2.3.3 Finalité
Usage limité à : maintenance prédictive, détection d'anomalies, pilotage industriel. **Interdiction** d'usage RH (évaluation individuelle, productivité par opérateur).

#### 2.3.4 Conservation
- Télémétrie brute : 90 jours (InfluxDB)
- Données agrégées / features : 3 ans (PostgreSQL)
- Historique interventions : durée légale métier

#### 2.3.5 Sécurité
Traitée à part, §2.4 (concept DIC).

### 2.4 Sécurité des données — concept DIC

Trois exigences : **D**isponibilité, **I**ntégrité, **C**onfidentialité. État réel du prototype, sans complaisance. Trois états : **Implémenté**, **Partiel**, **Absent** (cible d'industrialisation).

#### 2.4.1 Disponibilité — la donnée est accessible quand on en a besoin

| Mesure | État | Où |
|---|---|---|
| Healthchecks + démarrage ordonné des services | Implémenté | `docker-compose.yml` (postgres, influxdb) |
| Fonctionnement dégradé : Grafana lit PostgreSQL en direct, une panne de l'API ne masque pas les dernières prédictions | Implémenté | Choix d'architecture |
| Redémarrage automatique des conteneurs | Absent | `restart: unless-stopped` à ajouter |
| Sauvegarde des volumes de données | Absent | `pg_data`, `influx_data` |
| Rétention maîtrisée du brut (90 j) | Cible | InfluxDB |
| Redondance | Absent — hôte Docker unique, point de défaillance unique | Cible : réplication PostgreSQL |

#### 2.4.2 Intégrité — la donnée est exacte et non altérée

| Mesure | État | Où |
|---|---|---|
| Bornes physiques + winsorisation IQR par machine | Implémenté | `src/cleaning.py` |
| Détection de capteur défaillant (≥ 3 aberrations) | Implémenté | Table `alertes_capteur` |
| Contraintes de schéma (clés primaires, NOT NULL, typage) | Implémenté (14) | `docker/init.sql` |
| Intégrité de l'évaluation : aucune fuite entre apprentissage et test | Implémenté | `GroupKFold` groupé par `machine_id` |
| Traçabilité du modèle (méthode de validation, scores) | Implémenté | Bloc `validation` de `metadata.json` |
| Cohérence temporelle (horodatage, synchronisation) | Partiel | Hypothèse 1 cycle = 1 h, documentée |
| Clés étrangères vers `shared.machines` | Absent | Rien n'empêche une prédiction sur une machine inconnue |

#### 2.4.3 Confidentialité — la donnée n'est accessible qu'aux personnes habilitées

| Mesure | État | Où |
|---|---|---|
| Comptes applicatifs séparés, moindre privilège | Implémenté | `grafana_ro`/`metabase_ro` en SELECT seul, `api_rw` en écriture, `search_path` par rôle |
| Aucune donnée personnelle traitée | Implémenté | Données publiques/synthétiques (cf. §2.1) |
| Pseudonymisation des matricules opérateur | Cible | §2.3.2 |
| Secrets hors du code | Absent | Mots de passe en clair dans `init.sql`, `src/api/main.py`, `grafana/provisioning/datasources/postgres.yml` |
| Chiffrement en transit (TLS) | Absent | Tous les flux en clair |
| Exposition réseau | Partiel | PostgreSQL (5432) et InfluxDB (8086) publiés sur l'hôte — à restreindre au réseau interne Docker |
| Segmentation OT/IT | Cible | Broker MQTT en zone OT, plateforme IA en zone IT |
| Journalisation des accès | Absent | Cible : audit des consultations |

#### 2.4.4 Actions prioritaires avant tout passage en production

1. Sortir les secrets du code (variables d'environnement + secrets manager), et changer toutes les valeurs par défaut.
2. Restreindre l'exposition réseau : ne plus publier 5432 et 8086 sur l'hôte.
3. Ajouter `restart: unless-stopped` et une sauvegarde planifiée des volumes.
4. Activer TLS sur les flux externes.

Les points 1 et 2 sont les plus critiques : ils exposent aujourd'hui la base de données complète à quiconque atteint l'hôte.

### 2.5 Rôle du DPO

Le DPO de MECHA doit :
- Valider le registre des traitements avant mise en production
- Auditer la table de correspondance (hash ↔ matricule)
- Valider les mentions d'information aux opérateurs (art. 13 RGPD)
- Être consulté avant tout usage secondaire des données

### 2.6 Analyse d'impact (AIPD)

Une AIPD est **recommandée** avant industrialisation, car :
- Traitement à grande échelle (multi-sites)
- Croisement de sources (SCADA + RH + maintenance)
- Risque de dérive vers un usage de surveillance individuelle

### 2.7 Information des opérateurs

Note d'information à afficher en atelier + insertion dans le règlement intérieur :
- Nature des données collectées
- Finalité (maintenance prédictive, **pas** de suivi individuel)
- Durées de conservation
- Droit d'accès, rectification, opposition
- Contact DPO

### 2.8 Limites du prototype actuel

Comme les données sont synthétiques, aucune obligation RGPD ne s'applique **au prototype**. La pseudonymisation décrite en §2.3.2 n'est pas implémentée : elle devra être ajoutée à la préparation des données, et validée par le DPO, avant tout passage sur des données réelles.

---

## 3. Jeu de données et pipeline ML

### 3.1 Origine des données

Inventaire des sources MECHA, sélection et réduction de l'espace de l'IA : `02_donnees.md` §1.

| Élément | Détail |
|---|---|
| **Source prévue** | NASA CMAPSS FD001 (simulation de dégradation de moteurs) — https://www.kaggle.com/datasets/behrad3d/nasa-cmaps |
| **Source effectivement utilisée** | **Jeu synthétique** de même structure, généré par le notebook (`generate_synthetic_cmapss`, seed 42). Le notebook bascule automatiquement sur CMAPSS si `raw/train_FD001.txt` est fourni |
| **Type** | Run-to-failure : chaque machine est suivie cycle par cycle jusqu'à la panne |
| **Adaptation** | Renommage au vocabulaire MECHA, identifiant `MECHA-USI-XXX`, horodatage, calcul du RUL et du niveau de risque |

**Pourquoi une structure CMAPSS ?** C'est le seul type de jeu public qui couvre **à la fois** la classification (état machine) et la prédiction de RUL, car il contient des séquences complètes jusqu'à la panne — contrairement aux jeux « instantanés » (ex. AI4I 2020) qui ne permettent que la classification.

### 3.2 Fichiers livrés (`data/`)

Les trois fichiers sont régénérés à l'identique par le notebook (seed fixe).

| Fichier | Contenu | Volume |
|---|---|---|
| `mecha_dataset_raw.csv` | Jeu brut, avant nettoyage. Rejoué comme flux capteurs par `scripts/load_sensors_to_influx.py` | 9 200 lignes, 26 colonnes |
| `mecha_dataset.csv` | Jeu nettoyé et adapté, utilisé pour l'apprentissage | 9 200 lignes, 15 colonnes |
| `predictions.csv` | Prédictions sur les 10 machines de test, au format de la table PostgreSQL `predictions` | 1 865 lignes |

### 3.3 Dictionnaire de données

#### `mecha_dataset_raw.csv` (brut)

| Colonne | Type | Description |
|---|---|---|
| `machine_id` | int | Identifiant numérique de la machine (1 à 50) |
| `cycle_number` | int | Compteur de cycles d'usage |
| `op_setting_1..3` | float | Réglages opérationnels (conservés, non utilisés par les modèles) |
| `sensor_1..21` | float | Mesures capteurs brutes |

#### `mecha_dataset.csv` (nettoyé)

| Colonne | Type | Unité nominale | Description |
|---|---|---|---|
| `machine_id` | string | — | Format `MECHA-USI-XXX` |
| `timestamp` | datetime | — | Simulé : 1 cycle = 1 heure, à partir du 01/01/2026 |
| `cycle_number` | int | cycles | Compteur d'usage depuis la mise en service |
| `temperature_moteur` | float | °C | Depuis `sensor_2` |
| `temperature_lubrifiant` | float | °C | Depuis `sensor_3` |
| `temperature_carter` | float | °C | Depuis `sensor_4` |
| `pression_hydraulique` | float | bar | Depuis `sensor_7` |
| `vitesse_broche` | float | tr/min | Depuis `sensor_9` |
| `vibration_axe_x` | float | mm/s | Depuis `sensor_11` |
| `vibration_axe_y` | float | mm/s | Depuis `sensor_12` |
| `debit_refroidissement` | float | L/min | Depuis `sensor_14` |
| `humidite_ambiante` | float | % | Depuis `sensor_15` |
| `indice_usure_outil` | float | indice | Depuis `sensor_21` |
| `RUL` | int | cycles (= heures) | Cycles restants avant panne : `cycle_max(machine) - cycle_number` |
| `risk_level` | catégoriel | — | `a_risque` (RUL ≤ 8), `a_surveiller` (9 à 24), `normal` (> 24) |

**Unités nominales** : elles donnent le sens métier de chaque variable, mais les valeurs simulées restent sur une échelle arbitraire (environ 420 à 620, cf. §3.4). Elles n'ont pas de signification physique : seules leur évolution et leurs écarts relatifs portent le signal de dégradation.

#### `predictions.csv`

| Colonne | Type | Description |
|---|---|---|
| `machine_id`, `timestamp`, `cycle_number` | — | Comme ci-dessus |
| `rul_predit` | int | RUL estimé par le modèle de régression |
| `risk_level_predit` | catégoriel | Classe prédite par le classifieur (seuil de décision 0,35 sur `a_risque`) |
| `risk_level_reel` | catégoriel | Classe réelle (pour l'évaluation) |
| `modele_classification`, `modele_regression` | string | Modèles ayant produit la prédiction (traçabilité) |
| `capteur_principal` | string | Capteur le plus éloigné de son comportement moyen (score-Z) |

### 3.4 Hypothèses de simulation

| Hypothèse | Justification |
|---|---|
| 50 machines, durée de vie tirée entre 120 et 260 cycles | Ordre de grandeur de CMAPSS FD001 |
| Capteur *i* = 400 + 10·*i* + dégradation + bruit gaussien (σ = 1,5) | Niveau de base propre à chaque capteur, bruit de mesure |
| Dégradation non linéaire : `(cycle / durée de vie)^1,5` | Usure lente au début, accélérée en fin de vie |
| 1 cycle = 1 heure de fonctionnement | Convention pour obtenir un horodatage exploitable |
| Seuils de risque : RUL ≤ 8 → `a_risque`, 9 à 24 → `a_surveiller` | Seuils métier de l'exploitation (alertes, dashboards), cf. `03_architecture_technique.md` §2.3.2 ; à valider terrain |

### 3.5 Sécurité des données (DIC)

L'**intégrité** du jeu de données est assurée par les bornes physiques, la winsorisation par machine et la détection de capteur défaillant détaillées en §3.7, et l'intégrité de l'évaluation par le groupement `GroupKFold` sur `machine_id` (aucune fuite entre apprentissage et test). **Disponibilité** et **confidentialité** relèvent de l'infrastructure : voir §2.4.

### 3.6 Limites connues

- **Données synthétiques** : les résultats valident la méthode, pas la performance sur des machines réelles
- **Signal simplifié** : les 21 capteurs suivent la même forme de dégradation, à des niveaux différents ; aucun capteur ne porte une information propre
- **Pas de défauts réalistes** : ni valeurs manquantes, ni pannes de capteur, ni historique de maintenance simulés (6 valeurs écrêtées sur 193 200)
- **Un seul type de machine** : pas de variabilité entre les 5 usines
- **Volume pédagogique** : 9 200 lignes / 50 machines, loin d'un volume industriel
- **Classe rare** : `a_risque` ne représente que 4,9 % des lignes
- **Pas de données personnelles** : conforme à la contrainte RGPD du cahier des charges

### 3.7 Pipeline ML — résumé

| Étape | Méthode | Section du notebook |
|---|---|---|
| 1. Chargement | CMAPSS si présent, sinon génération synthétique ; export `data/mecha_dataset_raw.csv` | 2 |
| 2. Valeurs aberrantes | Bornes physiques + winsorisation IQR **par machine** (k = 3) | 3 |
| 3. Alerte capteur | ≥ 3 valeurs aberrantes sur un même capteur | 4 |
| 4. Préparation | RUL, renommage, niveau de risque ; export `data/mecha_dataset.csv` | 5 |
| 5. Split train/test | **Par machine** (40 / 10), pour éviter la fuite de données | 6 |
| 6. Comparaison | 6 classifieurs, 5 régresseurs | 7, 8 |
| 7. Validation croisée | `GroupKFold` 5 folds par machine ; sélection des modèles | 9, 10 |
| 8. Seuil de décision | Seuil sur P(`a_risque`) choisi en validation croisée | 12 |
| 9. Export | `data/predictions.csv`, modèles `.joblib` + `metadata.json` | 15, 17 |
| 10. Modes d'entraînement | Lot, mini-lot, online | 18 |

#### Traitement des valeurs aberrantes — détail

Deux règles appliquées, dans cet ordre :

1. **Bornes physiques absolues** : toute ligne contenant une valeur capteur négative est supprimée (impossible physiquement)
2. **Winsorisation IQR par machine** (`k = 3`, seuil large) : les valeurs hors `[Q1 - 3×IQR, Q3 + 3×IQR]` sont écrêtées vers la borne, **calculées machine par machine** — pas globalement

**Pourquoi par machine et pas globalement** : une vibration élevée en toute fin de vie d'une machine est un signal normal (dégradation), pas une anomalie. La calculer par machine évite de supprimer le signal qu'on cherche justement à prédire.

**Pourquoi écrêter plutôt que supprimer** : supprimer une ligne casserait la continuité temporelle utilisée pour le calcul du RUL. L'écrêtage neutralise l'erreur de mesure tout en gardant la trajectoire complète.

#### Alerte capteur défaillant

| Type d'alerte | Cause | Équipe concernée |
|---|---|---|
| Machine `a_risque` | Dégradation **mécanique** réelle de la machine | Maintenance mécanique |
| Alerte capteur | Dysfonctionnement **instrumental** (câble, calibration, interférence) | Instrumentation / DSI |

**Règle** : si un même capteur, sur une même machine, produit **3 valeurs aberrantes ou plus**, une alerte capteur est levée — indépendamment du niveau de risque de la machine. Table PostgreSQL `{site}.alertes_capteur`, endpoint `GET/POST /alertes-capteurs/{site}`, export `outputs/alertes_capteurs.csv`.

### 3.8 Résultats obtenus

| Modèle | Métrique | Valeur |
|---|---|---|
| Classification (Logistic Regression, seuil 0,35) | Rappel `a_risque` (test) | 0,867 |
| | Taux de faux positifs `a_risque` (test) | 9,0 % |
| | Précision `a_risque` (test) | 0,33 |
| Régression RUL (Random Forest) | MAE, validation croisée | 19,9 ± 0,2 cycles |
| | R², validation croisée | 0,824 |

**Interprétation** : les deux critères du client sont tenus (rappel ≥ 80 %, faux positifs < 15 %), mais deux alertes `a_risque` sur trois sont de fausses alertes : c'est le prix d'un rappel élevé sur une classe rare. Détail : `04_modeles_et_validation.md` §1 et `04_modeles_et_validation.md` §3.

### 3.9 Reproductibilité

Depuis `mecha-ia/` :

```bash
pip install -r scripts/requirements.txt matplotlib jupyter
jupyter nbconvert --to notebook --execute --inplace mecha_maintenance_predictive.ipynb
```

Sorties : `data/` (jeux de données, versionnés) et `outputs/` (modèles et benchmarks, non versionnés).
