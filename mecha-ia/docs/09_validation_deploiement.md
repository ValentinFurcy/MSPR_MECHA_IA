# Validation globale de la solution IA MECHA

## 1. Stratégie de validation

La validation suit 3 niveaux, du technique au fonctionnel.

| Niveau | Quoi | Comment | Critère de succès |
|---|---|---|---|
| **Technique** | Le code fonctionne | Tests unitaires (pytest) + lint, exécutés par la CI | 100 % des tests passent |
| **ML** | Les modèles prédisent correctement | Validation croisée `GroupKFold` groupée par machine + jeu de test tenu à l'écart | Critères du client : rappel `a_risque` ≥ 80 %, faux positifs < 15 % ; MAE du RUL ≤ 25 cycles |
| **Fonctionnel** | La chaîne bout en bout produit des alertes | Scénario de test complet | Alerte visible dans Grafana pour une machine à RUL faible |

## 2. Validation technique

### 2.1 Tests unitaires (51 tests)

| Fichier | Vérifie |
|---|---|
| `tests/test_outliers.py` | Winsorisation par machine, alerte capteur, capteur principal (`src/cleaning.py`) |
| `tests/test_decision.py` | Règle de décision du classifieur (`src/decision.py`) |
| `tests/test_api.py` | Endpoints, validation des sites, génération des alertes selon les seuils de RUL |
| `tests/test_pipeline_models.py` | Contrat d'export notebook → pipeline (fichiers, `metadata.json`, prédictions) |
| `tests/test_cleaning.py` | Calcul du RUL, niveaux de risque, format des identifiants |

### 2.2 Intégration continue

GitHub Actions exécute à chaque push et pull request : lint (ruff) → tests (pytest) → validation du docker-compose → build des images Docker (`10_cicd_deploiement.md`).

## 3. Validation ML

### 3.1 Protocole

- **Split par machine** (pas par ligne) pour éviter la fuite de données : 40 machines en apprentissage, 10 en test
- **Validation croisée `GroupKFold` 5 folds**, groupée par `machine_id` : chaque machine sert une fois en test. C'est elle qui sélectionne les modèles
- **Seuil de décision** du classifieur choisi en validation croisée sur les seules machines d'apprentissage, puis évalué sur les 10 machines de test
- 6 modèles comparés en classification, 5 en régression (`07_justification_modele.md`)

### 3.2 Indicateurs suivis

| Indicateur | Ce qu'il mesure | Pourquoi |
|---|---|---|
| Rappel `a_risque` | Part des pannes détectées | Critère client n°1 : une panne ratée coûte un arrêt non planifié |
| Taux de faux positifs | Part des machines saines déclarées à risque | Critère client n°2 : trop d'alertes et les équipes cessent de les croire |
| Précision `a_risque` | Part des alertes justifiées | Charge de travail inutile pour la maintenance |
| MAE du RUL | Erreur moyenne sur le temps restant, en heures | Directement lisible par le métier |

### 3.3 Résultats obtenus

**Classification — Logistic Regression, seuil de décision 0,35 (10 machines de test)**

| Classe | Précision | Rappel | F1 |
|---|---|---|---|
| `a_risque` | 0.33 | **0.87** | 0.48 |
| `a_surveiller` | 0.22 | 0.25 | 0.24 |
| `normal` | 0.99 | 0.89 | 0.94 |

| Critère client | Cible | Obtenu | |
|---|---|---|---|
| Rappel `a_risque` | ≥ 80 % | 86,7 % (78 pannes détectées sur 90) | ✅ |
| Taux de faux positifs | < 15 % | 9,0 % (159 sur 1 775 cycles sains) | ✅ |

**Régression RUL — Random Forest** : MAE = 19,9 ± 0,2 cycles en validation croisée (18,9 sur le split de test), R² = 0,824. Critère ≤ 25 cycles tenu ✅

### 3.4 Limites identifiées

- **Deux alertes `a_risque` sur trois sont fausses** (précision 0,33) : c'est le coût d'un rappel élevé sur une classe rare (5 % des cycles)
- **Rappel variable selon les machines** : 0,833 ± 0,082 sur les folds d'apprentissage, pire fold à 0,694 — le critère de 80 % n'est pas garanti sur chaque sous-ensemble de machines
- **Erreur du RUL (~20 h) supérieure au seuil d'alerte critique (4 h)** : une alerte critique signale une machine *probablement* proche de la panne, l'inspection humaine reste la décision finale (`04_guide_utilisateur.md` §4)
- Données synthétiques : résultats à revalider sur CMAPSS puis sur données réelles
- Un seul type de machine simulé : généralisation non garantie entre types de machines

## 4. Validation fonctionnelle (scénario bout en bout)

### Scénario de test

1. `scripts/load_sensors_to_influx.py` rejoue `data/mecha_dataset_raw.csv` dans InfluxDB, comme un flux capteurs
2. `scripts/run_pipeline.py` lit le dernier relevé de chaque machine, applique les modèles exportés par le notebook et envoie les prédictions à l'API (`POST /predictions/site_fr1`)
3. L'API génère une alerte quand le RUL prédit est ≤ 8 (urgent) ou ≤ 4 (critique)
4. Grafana affiche les machines à intervenir via la datasource PostgreSQL
5. Le responsable maintenance voit la machine en rouge sur le dashboard

### Critères d'acceptation

| Critère | Attendu | Obtenu |
|---|---|---|
| API répond | `GET /health` → `{"status": "ok"}` | ✅ |
| Insertion fonctionne | `POST /predictions/site_fr1` → `200` | ✅ |
| Alerte auto-générée | Ligne dans `site_fr1.alertes` pour `rul_predit ≤ 8` | ✅ |
| Dashboard affiche | Niveau de risque et RUL visibles dans Grafana | ✅ |

## 5. Projection industrielle

### 5.1 Conditions de déploiement

| Prérequis | État | Action |
|---|---|---|
| VPN inter-sites | Existant chez MECHA | Configurer l'accès au serveur central |
| Serveur dédié | À provisionner | 4 vCPU, 16 Go RAM, 200 Go SSD |
| Capteurs IoT opérationnels | 3 sites FR complets, 2 sites ES partiels | Compléter l'équipement ES |
| GMAO intégrée | Partiel | Connecteur GMAO → PostgreSQL |

### 5.2 Plan de déploiement

| Phase | Durée | Périmètre | Objectif |
|---|---|---|---|
| Pilote | 3 mois | 1 site FR, 3 machines | Valider la chaîne technique |
| Extension site | 3 mois | Toutes machines du site pilote | Stabiliser |
| Roll-out FR | 6 mois | 3 sites France | Uniformiser |
| Roll-out ES | 6 mois | 2 sites Espagne | Couverture complète |

### 5.3 Points de vigilance

- **Dérive du modèle** : suivi du rappel en production, réentraînement mensuel (et recalcul du seuil de décision)
- **Qualité capteurs** : taux de disponibilité capteur à suivre (panneau *Alertes capteur*)
- **Adoption utilisateurs** : indicateurs de suivi (% alertes traitées, satisfaction)
- **Sécurité OT/IT** : le broker MQTT est en zone OT, la plateforme IA en zone IT — passage via firewall dédié
- **Continuité de production** : déploiement en heures creuses, pas d'impact sur SCADA/MES existant
