# Documentation — Dataset & Pipeline ML MECHA

## 1. Origine des données

Inventaire des sources MECHA, sélection et réduction de l'espace de l'IA : `11_cartographie_donnees.md`.

| Élément | Détail |
|---|---|
| **Source prévue** | NASA CMAPSS FD001 (simulation de dégradation de moteurs) — https://www.kaggle.com/datasets/behrad3d/nasa-cmaps |
| **Source effectivement utilisée** | **Jeu synthétique** de même structure, généré par le notebook (`generate_synthetic_cmapss`, seed 42). Le notebook bascule automatiquement sur CMAPSS si `raw/train_FD001.txt` est fourni |
| **Type** | Run-to-failure : chaque machine est suivie cycle par cycle jusqu'à la panne |
| **Adaptation** | Renommage au vocabulaire MECHA, identifiant `MECHA-USI-XXX`, horodatage, calcul du RUL et du niveau de risque |

**Pourquoi une structure CMAPSS ?** C'est le seul type de jeu public qui couvre **à la fois** la classification (état machine) et la prédiction de RUL, car il contient des séquences complètes jusqu'à la panne — contrairement aux jeux « instantanés » (ex. AI4I 2020) qui ne permettent que la classification.

## 2. Fichiers livrés (`data/`)

Les trois fichiers sont régénérés à l'identique par le notebook (seed fixe).

| Fichier | Contenu | Volume |
|---|---|---|
| `mecha_dataset_raw.csv` | Jeu brut, avant nettoyage. Rejoué comme flux capteurs par `scripts/load_sensors_to_influx.py` | 9 200 lignes, 26 colonnes |
| `mecha_dataset.csv` | Jeu nettoyé et adapté, utilisé pour l'apprentissage | 9 200 lignes, 15 colonnes |
| `predictions.csv` | Prédictions sur les 10 machines de test, au format de la table PostgreSQL `predictions` | 1 865 lignes |

## 3. Dictionnaire de données

### `mecha_dataset_raw.csv` (brut)

| Colonne | Type | Description |
|---|---|---|
| `machine_id` | int | Identifiant numérique de la machine (1 à 50) |
| `cycle_number` | int | Compteur de cycles d'usage |
| `op_setting_1..3` | float | Réglages opérationnels (conservés, non utilisés par les modèles) |
| `sensor_1..21` | float | Mesures capteurs brutes |

### `mecha_dataset.csv` (nettoyé)

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

**Unités nominales** : elles donnent le sens métier de chaque variable, mais les valeurs simulées restent sur une échelle arbitraire (environ 420 à 620, cf. §4). Elles n'ont pas de signification physique : seules leur évolution et leurs écarts relatifs portent le signal de dégradation.

### `predictions.csv`

| Colonne | Type | Description |
|---|---|---|
| `machine_id`, `timestamp`, `cycle_number` | — | Comme ci-dessus |
| `rul_predit` | int | RUL estimé par le modèle de régression |
| `risk_level_predit` | catégoriel | Classe prédite par le classifieur (seuil de décision 0,35 sur `a_risque`) |
| `risk_level_reel` | catégoriel | Classe réelle (pour l'évaluation) |
| `modele_classification`, `modele_regression` | string | Modèles ayant produit la prédiction (traçabilité) |
| `capteur_principal` | string | Capteur le plus éloigné de son comportement moyen (score-Z) |

## 4. Hypothèses de simulation

| Hypothèse | Justification |
|---|---|
| 50 machines, durée de vie tirée entre 120 et 260 cycles | Ordre de grandeur de CMAPSS FD001 |
| Capteur *i* = 400 + 10·*i* + dégradation + bruit gaussien (σ = 1,5) | Niveau de base propre à chaque capteur, bruit de mesure |
| Dégradation non linéaire : `(cycle / durée de vie)^1,5` | Usure lente au début, accélérée en fin de vie |
| 1 cycle = 1 heure de fonctionnement | Convention pour obtenir un horodatage exploitable |
| Seuils de risque : RUL ≤ 8 → `a_risque`, 9 à 24 → `a_surveiller` | Seuils métier de l'exploitation (alertes, dashboards), cf. `12_solution_applicative.md` §3.2 ; à valider terrain |

## 5. Sécurité des données (DIC)

L'**intégrité** du jeu de données est assurée par les bornes physiques, la winsorisation par machine et la détection de capteur défaillant détaillées en §7, et l'intégrité de l'évaluation par le groupement `GroupKFold` sur `machine_id` (aucune fuite entre apprentissage et test). **Disponibilité** et **confidentialité** relèvent de l'infrastructure : voir `02_volet_rgpd.md` §4.

## 6. Limites connues

- **Données synthétiques** : les résultats valident la méthode, pas la performance sur des machines réelles
- **Signal simplifié** : les 21 capteurs suivent la même forme de dégradation, à des niveaux différents ; aucun capteur ne porte une information propre
- **Pas de défauts réalistes** : ni valeurs manquantes, ni pannes de capteur, ni historique de maintenance simulés (6 valeurs écrêtées sur 193 200)
- **Un seul type de machine** : pas de variabilité entre les 5 usines
- **Volume pédagogique** : 9 200 lignes / 50 machines, loin d'un volume industriel
- **Classe rare** : `a_risque` ne représente que 4,9 % des lignes
- **Pas de données personnelles** : conforme à la contrainte RGPD du cahier des charges

## 7. Pipeline ML — résumé

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

### Traitement des valeurs aberrantes — détail

Deux règles appliquées, dans cet ordre :

1. **Bornes physiques absolues** : toute ligne contenant une valeur capteur négative est supprimée (impossible physiquement)
2. **Winsorisation IQR par machine** (`k = 3`, seuil large) : les valeurs hors `[Q1 - 3×IQR, Q3 + 3×IQR]` sont écrêtées vers la borne, **calculées machine par machine** — pas globalement

**Pourquoi par machine et pas globalement** : une vibration élevée en toute fin de vie d'une machine est un signal normal (dégradation), pas une anomalie. La calculer par machine évite de supprimer le signal qu'on cherche justement à prédire.

**Pourquoi écrêter plutôt que supprimer** : supprimer une ligne casserait la continuité temporelle utilisée pour le calcul du RUL. L'écrêtage neutralise l'erreur de mesure tout en gardant la trajectoire complète.

### Alerte capteur défaillant

| Type d'alerte | Cause | Équipe concernée |
|---|---|---|
| Machine `a_risque` | Dégradation **mécanique** réelle de la machine | Maintenance mécanique |
| Alerte capteur | Dysfonctionnement **instrumental** (câble, calibration, interférence) | Instrumentation / DSI |

**Règle** : si un même capteur, sur une même machine, produit **3 valeurs aberrantes ou plus**, une alerte capteur est levée — indépendamment du niveau de risque de la machine. Table PostgreSQL `{site}.alertes_capteur`, endpoint `GET/POST /alertes-capteurs/{site}`, export `outputs/alertes_capteurs.csv`.

## 8. Résultats obtenus

| Modèle | Métrique | Valeur |
|---|---|---|
| Classification (Logistic Regression, seuil 0,35) | Rappel `a_risque` (test) | 0,867 |
| | Taux de faux positifs `a_risque` (test) | 9,0 % |
| | Précision `a_risque` (test) | 0,33 |
| Régression RUL (Random Forest) | MAE, validation croisée | 19,9 ± 0,2 cycles |
| | R², validation croisée | 0,824 |

**Interprétation** : les deux critères du client sont tenus (rappel ≥ 80 %, faux positifs < 15 %), mais deux alertes `a_risque` sur trois sont de fausses alertes : c'est le prix d'un rappel élevé sur une classe rare. Détail : `07_justification_modele.md` et `09_validation_deploiement.md`.

## 9. Reproductibilité

Depuis `mecha-ia/` :

```bash
pip install -r scripts/requirements.txt matplotlib jupyter
jupyter nbconvert --to notebook --execute --inplace mecha_maintenance_predictive.ipynb
```

Sorties : `data/` (jeux de données, versionnés) et `outputs/` (modèles et benchmarks, non versionnés).
