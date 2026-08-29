# Documentation — Dataset & Pipeline ML MECHA

## 1. Origine des données

Inventaire des sources MECHA, sélection et réduction de l'espace de l'IA : `11_cartographie_donnees.md`.

| Élément | Détail |
|---|---|
| **Dataset source** | NASA CMAPSS FD001 (jet engine degradation simulation) |
| **Lien** | https://www.kaggle.com/datasets/behrad3d/nasa-cmaps |
| **Type** | Public, run-to-failure (séquences de dégradation jusqu'à panne) |
| **Adaptation** | Renommage vocabulaire métier MECHA + calcul de labels dérivés |
| **Repli si absent** | Génération synthétique (structure identique : dégradation progressive par cycle, bruit capteur) — utilisée automatiquement par le notebook si `raw/train_FD001.txt` n'est pas fourni |

**Pourquoi CMAPSS ?** C'est le seul type de dataset public permettant de couvrir **à la fois** la classification (état machine) et la prédiction de RUL, car il contient des séquences complètes jusqu'à la panne — contrairement aux datasets "snapshot" (ex. AI4I 2020) qui ne permettent que la classification.

## 2. Dictionnaire de données

### Fichier `mecha_dataset_raw.csv` (brut, avant nettoyage)

| Colonne | Type | Origine | Description |
|---|---|---|---|
| `machine_id` | int | CMAPSS `unit_id` | Identifiant numérique brut de la machine |
| `cycle_number` | int | CMAPSS `cycle` | Compteur de cycles d'usage |
| `op_setting_1..3` | float | CMAPSS | Réglages opérationnels (conservés tels quels) |
| `sensor_1..21` | float | CMAPSS | Mesures capteurs brutes, non renommées |

### Fichier `mecha_dataset.csv` (nettoyé, adapté)

| Colonne | Type | Unité (approximative) | Description |
|---|---|---|---|
| `machine_id` | string | — | Format `MECHA-USI-XXX` |
| `timestamp` | datetime | — | Simulé : 1 cycle = 1 heure (hypothèse) |
| `cycle_number` | int | cycles | Compteur d'usage depuis mise en service |
| `temperature_moteur` | float | °C | Renommé depuis `sensor_2` |
| `temperature_lubrifiant` | float | °C | Renommé depuis `sensor_3` |
| `temperature_carter` | float | °C | Renommé depuis `sensor_4` |
| `pression_hydraulique` | float | bar | Renommé depuis `sensor_7` |
| `vitesse_broche` | float | tr/min | Renommé depuis `sensor_9` |
| `vibration_axe_x` | float | mm/s | Renommé depuis `sensor_11` |
| `vibration_axe_y` | float | mm/s | Renommé depuis `sensor_12` |
| `debit_refroidissement` | float | L/min | Renommé depuis `sensor_14` |
| `humidite_ambiante` | float | % | Renommé depuis `sensor_15` |
| `indice_usure_outil` | float | indice (0-100) | Renommé depuis `sensor_21` |
| `RUL` | int | cycles restants | Calculé : `cycle_max(machine) - cycle_number` |
| `risk_level` | catégoriel | normal / a_surveiller / a_risque | Calculé par seuillage du RUL |

### Fichier `predictions.csv` (sortie modèle)

| Colonne | Type | Description |
|---|---|---|
| `machine_id` | string | Identifiant machine |
| `timestamp` | datetime | Horodatage |
| `cycle_number` | int | Cycle |
| `rul_predit` | int | RUL estimé par le modèle de régression |
| `risk_level_predit` | catégoriel | Classe prédite par le modèle de classification |
| `risk_level_reel` | catégoriel | Classe réelle (pour évaluation) |

## 3. Hypothèses de simulation

| Hypothèse | Justification |
|---|---|
| 1 cycle CMAPSS = 1 heure de fonctionnement | Convention arbitraire pour obtenir un timestamp exploitable ; à ajuster si données réelles disponibles |
| Unités des capteurs (°C, bar, mm/s...) | Approximations pédagogiques — CMAPSS ne fournit pas d'unité physique réelle |
| Seuils `risk_level` : RUL > 50 → normal, 15-50 → à surveiller, < 15 → à risque | Seuils métier définis pour ce prototype, à valider avec retours terrain réels (cf. compte-rendu entretien client) |
| Génération synthétique de repli | Dégradation non linéaire (`cycle^1.5`) + bruit gaussien par capteur, calibrée pour reproduire un pattern de dégradation crédible |

## 4. Sécurité des données (DIC)

L'**intégrité** du jeu de données est assurée par les bornes physiques, la winsorisation par machine et la détection de capteur défaillant détaillées en §6, et l'intégrité de l'évaluation par le groupement `GroupKFold` sur `machine_id` (aucune fuite entre apprentissage et test). **Disponibilité** et **confidentialité** relèvent de l'infrastructure : voir `02_volet_rgpd.md` §4.

## 5. Limites connues

- **Origine aéronautique du dataset** : CMAPSS simule des moteurs d'avion, pas des centres d'usinage — l'analogie est une approximation méthodologique assumée, pas une garantie de représentativité physique
- **Un seul type de machine simulé** : pas de variabilité inter-sites (5 usines MECHA) dans le dataset actuel
- **Volume** : ~9 200 lignes / 50 machines (repli synthétique) — volume pédagogique, pas un volume industriel réel
- **Pas de données réelles opérateur/RH** : conforme à la contrainte RGPD du cahier des charges (aucune donnée personnelle)
- **Seuils de classification arbitraires** : nécessitent validation métier avant tout usage réel

## 6. Pipeline ML — résumé

| Étape | Méthode | Fichier |
|---|---|---|
| 1. Chargement | CMAPSS réel ou génération de repli | Cellules 1-2 |
| 2. Traitement valeurs aberrantes | Bornes physiques + winsorisation IQR **par machine** (k=3) | Cellule 3 |
| 3. Calcul RUL | `cycle_max - cycle_number` par machine | Cellule 4 |
| 4. Adaptation vocabulaire | Renommage colonnes | Cellule 4 |
| 5. Label classification | Seuillage RUL → `risk_level` | Cellule 4 |
| 6. Split train/test | **Par `machine_id`** (évite fuite de données) | Cellule 5 |
| 7. Modèle classification | 6 modèles comparés (dont XGBoost) | Cellule 6 |
| 8. Modèle régression | 5 modèles comparés (dont XGBoost) | Cellule 7 |
| 9. Export résultats | `predictions.csv` (format prêt PostgreSQL) | Cellule 11 |

### Traitement des valeurs aberrantes — détail

Deux règles appliquées, dans cet ordre :

1. **Bornes physiques absolues** : toute valeur capteur négative est supprimée (impossible physiquement, ex. température ou vibration négative)
2. **Winsorisation IQR par machine** (`k=3`, seuil large) : les valeurs hors `[Q1 - 3×IQR, Q3 + 3×IQR]` sont écrêtées vers la borne, **calculées machine par machine** — pas globalement

**Pourquoi par machine et pas globalement** : une vibration élevée en toute fin de vie d'une machine est un signal normal (dégradation), pas une anomalie. La calculer par machine évite de supprimer le signal qu'on cherche justement à prédire.

**Pourquoi winsorisation (écrêtage) et pas suppression de ligne** : supprimer une ligne casserait la continuité temporelle utilisée pour le calcul du RUL. L'écrêtage neutralise l'erreur de mesure tout en gardant la trajectoire complète.

### Alerte capteur défaillant

**Distinction fondamentale** :

| Type d'alerte | Cause | Équipe concernée |
|---|---|---|
| `risk_level = a_risque` | Dégradation **mécanique** réelle de la machine | Maintenance mécanique |
| Alerte capteur | Dysfonctionnement **instrumental** (câble, calibration, interférence) | Instrumentation / DSI |

**Règle** : si un même capteur, sur une même machine, produit **3 valeurs aberrantes ou plus** (détectées par la winsorisation), une alerte capteur est levée — indépendamment du niveau de risque de la machine.

Table PostgreSQL dédiée : `{site}.alertes_capteur` (colonnes : `machine_id`, `capteur`, `nb_aberrations`, `premier_cycle`, `dernier_cycle`).
Endpoint API : `GET/POST /alertes-capteurs/{site}`.

Export notebook : `outputs/alertes_capteurs.csv`.

## 7. Résultats obtenus (dataset de repli synthétique)

| Modèle | Métrique | Valeur |
|---|---|---|
| Classification (`risk_level`) | Accuracy | 0.85 |
| Classification | F1-score classe `a_risque` | 0.68 |
| Régression (`RUL`) | MAE | 18.9 cycles |
| Régression (`RUL`) | R² | 0.839 |

**Interprétation** : la classe `a_risque` (la plus critique métier) a un rappel de 0.68 — un tiers des situations à risque ne sont pas détectées. C'est une limite à corriger avant tout déploiement réel (ex. rééquilibrage des classes plus poussé, seuils de décision ajustés, features supplémentaires).

## 8. Reproductibilité

```bash
pip install pandas numpy scikit-learn matplotlib jupyter nbconvert --break-system-packages
jupyter nbconvert --to notebook --execute --inplace mecha_maintenance_predictive.ipynb
```

Sorties générées dans `outputs/` : `mecha_dataset_raw.csv`, `mecha_dataset.csv`, `predictions.csv`.
