# Modèles, entraînement et validation

Choix des modèles, procédure d'entraînement, validation globale et projection dans les usines.

## 1. Justification du choix des modèles

### 1.1 Méthode

6 modèles de classification et 5 modèles de régression, comparés en **deux temps**, à features et hyperparamètres identiques :

1. **Split unique par machine** (40 machines en apprentissage, 10 en test, `random_state=42`) — §1.3 et §1.4. Premier classement, et base des analyses détaillées.
2. **Validation croisée `GroupKFold` 5 folds** — §1.5. Vérifie que ce classement n'est pas un artefact du découpage : c'est **elle qui décide** des modèles retenus.

Le classifieur retenu reçoit ensuite un **seuil de décision** réglé pour atteindre les critères du client (§1.6).

Notebook : `mecha_maintenance_predictive.ipynb`
Sorties : `outputs/benchmark_classification.csv`, `outputs/benchmark_regression.csv`, `outputs/benchmark_cv_classification.csv`, `outputs/benchmark_cv_regression.csv`

### 1.2 Critères de décision

| Tâche | Métrique prioritaire | Pourquoi |
|---|---|---|
| Classification | **Rappel `a_risque`** | Rater une vraie panne coûte plus cher qu'une fausse alerte |
| Régression | **MAE (cycles)** | Directement interprétable par le métier |
| Départage | Rapidité + interprétabilité | Contraintes industrielles : audit, réentraînement, portabilité |

Critères de succès du client (`01_besoin_et_conduite_du_changement.md` §1) : rappel ≥ 80 % sur les pannes, moins de 15 % de faux positifs.

### 1.3 Résultats — Classification (split unique)

Classes : 86 % `normal`, 9 % `a_surveiller`, 5 % `a_risque` (seuils RUL 8 / 24).

| Modèle | Accuracy | F1 macro | **Rappel `a_risque`** |
|---|---|---|---|
| **Logistic Regression** | 0.846 | 0.610 | **0.611** ✅ |
| Random Forest | 0.879 | 0.669 | 0.467 |
| **XGBoost** | **0.921** 🏆 | **0.691** 🏆 | 0.433 |
| Decision Tree | 0.818 | 0.543 | 0.422 |
| Gradient Boosting | 0.916 | 0.686 | 0.422 |
| KNN (k=5) | 0.897 | 0.577 | 0.267 |

**Retenu : Logistic Regression**

- **Meilleur rappel sur la classe critique** (`a_risque`), et de loin : 0.611 contre 0.467 pour Random Forest et 0.433 pour XGBoost
- **XGBoost domine sur l'accuracy et le F1 macro**, mais rate plus d'une panne sur deux : pénalisant en maintenance prédictive
- **Le plus rapide à entraîner** (quelques centièmes de seconde) et **interprétable** : ses coefficients se lisent directement, ce qui sert l'audit qualité (exigence aéronautique)
- `class_weight="balanced"` compense le déséquilibre des classes ; Gradient Boosting, KNN et XGBoost n'en bénéficient pas, ce qui explique en partie leur faible rappel

**Leçon** : un modèle plus complexe n'est pas automatiquement meilleur sur la métrique qui compte. XGBoost gagne sur l'accuracy (métrique « par défaut »), la Logistic Regression gagne sur la métrique **définie par le besoin métier**.

### 1.4 Résultats — Régression du RUL (split unique)

| Modèle | **MAE (cycles)** | RMSE | R² |
|---|---|---|---|
| **Random Forest** | **18.9** ✅ | 24.1 | 0.839 |
| XGBoost | 19.1 | 24.9 | 0.828 |
| Gradient Boosting | 19.3 | 25.0 | 0.826 |
| Linear Regression | 20.9 | 26.0 | 0.812 |
| Decision Tree | 24.0 | 31.0 | 0.734 |

**Retenu : Random Forest**

- **MAE la plus basse** et **R² le plus élevé**
- **Robuste au bruit capteur** : la moyenne de 200 arbres lisse les erreurs
- **Importance des capteurs** exploitable pour le métier
- XGBoost est très proche (+0,2 cycle de MAE) et plus rapide à entraîner : c'est l'alternative naturelle si le temps de réentraînement devient contraignant en multi-sites

### 1.5 Validation croisée par groupe (`GroupKFold`)

Le split unique ne dit pas si le classement est stable : il peut être un artefact des 10 machines tombées en test.

**Protocole** : `GroupKFold`, 5 folds, groupement par `machine_id` (une machine entière est soit en apprentissage, soit en test — un `KFold` ligne à ligne créerait une fuite), sur **toutes** les machines. Déterministe donc reproductible. Un `assert` vérifie à chaque fold qu'aucune machine n'est des deux côtés.

#### Classification (rappel `a_risque`)

| Modèle | **Rappel `a_risque`** | Écart-type | Pire fold | Accuracy | F1 macro |
|---|---|---|---|---|---|
| **Logistic Regression** | **0.607** ✅ | 0.103 | 0.433 | 0.842 | 0.611 |
| Random Forest | 0.482 | 0.053 | 0.389 | 0.871 | 0.662 |
| Gradient Boosting | 0.473 | 0.062 | 0.367 | 0.907 | 0.663 |
| XGBoost | 0.438 | 0.068 | 0.333 | 0.907 | 0.652 |
| Decision Tree | 0.418 | 0.092 | 0.256 | 0.825 | 0.569 |
| KNN (k=5) | 0.284 | 0.051 | 0.200 | 0.890 | 0.565 |

#### Régression RUL (MAE)

| Modèle | **MAE (cycles)** | Écart-type | Pire fold | RMSE | R² |
|---|---|---|---|---|---|
| **Random Forest** | **19.9** ✅ | 0.2 | 20.2 | 25.3 | 0.824 |
| Gradient Boosting | 20.2 | 0.2 | 20.4 | 26.0 | 0.814 |
| XGBoost | 20.2 | 0.3 | 20.5 | 26.2 | 0.811 |
| Linear Regression | 22.1 | 0.3 | 22.5 | 27.4 | 0.792 |
| Decision Tree | 24.2 | 0.2 | 24.5 | 31.4 | 0.727 |

#### Conclusions

- **Les modèles retenus ne changent pas** : Logistic Regression et Random Forest restent premiers, avec un écart supérieur à l'écart-type entre folds.
- **Le split unique était optimiste sur le RUL** : 18,9 cycles contre 19,9 en validation croisée — c'est 19,9 qu'il faut annoncer au client.
- **Avec la règle de décision par défaut, le rappel (0,607) est loin de la cible de 80 %**, et très variable d'un fold à l'autre (pire fold : 0,433). D'où le réglage du seuil de décision (§1.6).

Méthode tracée dans `metadata.json` (bloc `validation`).

### 1.6 Réglage du seuil de décision

Par défaut, un classifieur retient la classe la plus probable. Pour une classe rare (5 % des lignes), cela sous-détecte les pannes. On déclare donc `a_risque` dès que **P(a_risque) ≥ seuil** (`src/decision.py`, la même règle dans le notebook et le pipeline d'inférence).

**Protocole** (notebook, section 12) : probabilités *out-of-fold* par `GroupKFold` sur les 40 machines d'apprentissage uniquement, balayage du seuil de 0,05 à 0,95, puis choix du **seuil le plus élevé** qui tient les deux critères du client. L'évaluation finale se fait sur les 10 machines de test, jamais utilisées pour le choix.

| Seuil (out-of-fold, apprentissage) | Rappel | Taux de faux positifs | Précision |
|---|---|---|---|
| 0,25 | 0.925 | 13,2 % | 0.266 |
| 0,30 | 0.875 | 11,0 % | 0.290 |
| **0,35 (retenu)** | **0.833** | **9,2 %** | 0.319 |
| 0,40 | 0.767 | 7,3 % | 0.351 |
| 0,50 | 0.583 | 3,8 % | 0.443 |

**Résultat sur les 10 machines de test** :

| Règle | Rappel `a_risque` | Taux de faux positifs | Précision | Pannes ratées |
|---|---|---|---|---|
| Classe la plus probable | 0.611 | 4,1 % | 0.433 | 35 sur 90 |
| **Seuil 0,35** | **0.867** ✅ | **9,0 %** ✅ | 0.329 | 12 sur 90 |

Les deux critères du client sont tenus. En contrepartie, deux alertes `a_risque` sur trois sont de fausses alertes, et la classe intermédiaire `a_surveiller` est moins bien reconnue (rappel 0,25 contre 0,54). Ce compromis est acceptable ici parce que **les alertes opérationnelles sont décidées par le RUL** (`03_architecture_technique.md` §2.3.1) : le classifieur sert de second avis tracé en base.

Sur les folds d'apprentissage, le rappel au seuil 0,35 vaut 0,833 ± 0,082 (pire fold : 0,694) : le critère de 80 % n'est pas garanti sur chaque sous-ensemble de machines.

### 1.7 Deux modèles, deux familles — pourquoi c'est cohérent

| Tâche | Nature du signal | Modèle adapté |
|---|---|---|
| Classification `risk_level` | Seuils sur le RUL → frontières nettes | Modèle linéaire suffit |
| Régression `RUL` | Dégradation continue non linéaire | Arbres nécessaires |

Choisir **le bon outil pour chaque tâche** plutôt qu'imposer une famille unique.

### 1.8 Limites de cette comparaison

- Résultats sur le **jeu synthétique** : sur CMAPSS ou des données réelles, l'ordre peut bouger — la méthode reste valable
- Pas d'optimisation d'hyperparamètres : paramètres raisonnables par défaut
- Modèles non supervisés (Isolation Forest, clustering) non étudiés : pertinents pour un démarrage sans labels de panne

### 1.9 Prochaines étapes recommandées

1. Relancer sur CMAPSS FD001 puis sur données réelles, vérifier la stabilité du classement
2. Optimiser les hyperparamètres des modèles retenus (et de XGBoost, avec pondération des classes)
3. Revalider le seuil de décision avec les retours terrain (coût réel d'une fausse alerte)

---

## 2. Procédure d'entraînement — lot, mini-lot, online

Notebook : section 18. Sorties : `outputs/benchmark_modes_entrainement.csv`, `outputs/benchmark_taux_apprentissage.csv`

### 2.1 Données d'apprentissage

| Choix | Justification |
|---|---|
| 40 machines en apprentissage, 10 en test, **découpage par machine** | Une machine n'est jamais vue à la fois à l'entraînement et à l'évaluation |
| Les 10 capteurs retenus (`02_donnees.md` §1.2.2) | Variables disponibles en temps réel, sans donnée personnelle |
| Cible : niveau de risque dérivé du RUL (seuils 8 / 24) | Mêmes seuils que l'exploitation |
| Pondération des classes | `a_risque` ne représente que 5 % des lignes |

### 2.2 Les trois modes

| Mode | Principe | Quand c'est le bon choix |
|---|---|---|
| **Lot** (*batch*) | Tout l'historique, un seul ajustement | Le jeu tient en mémoire, réentraînement planifié |
| **Mini-lot** | Paquets de N lignes, ajustements successifs | Le jeu ne tient plus en mémoire, réentraînement fréquent |
| **Online** | Une ligne à la fois, à son arrivée | Flux continu, adaptation immédiate, pas de stockage |

### 2.3 Protocole

Les trois modes portent sur **le même modèle** : la Logistic Regression retenue a un équivalent incrémental exact, `SGDClassifier(loss="log_loss")` — même fonction de coût, optimisée par descente de gradient stochastique, donc compatible `partial_fit`.

Deux contraintes apparaissent hors du mode lot :

| Contrainte | Pourquoi | Réponse |
|---|---|---|
| `class_weight="balanced"` refusé par `partial_fit` | En incrémental, la distribution des classes n'est pas connue d'avance | Poids calculés sur l'historique puis **figés** (`a_risque` 6.79, `a_surveiller` 3.82, `normal` 0.39) |
| Le `StandardScaler` doit être figé | On ne peut pas re-normaliser rétroactivement des données déjà apprises | Scaler ajusté une fois, puis versionné avec le modèle |

Mini-lot et online mélangent les données (SGD suppose des échantillons indépendants). Sans mélange, le modèle voit une machine entière d'affilée — que des cycles `normal`, puis que des `a_risque` — et oscille.

Les trois modes sont comparés avec la règle de décision par défaut (classe la plus probable), avant le réglage du seuil décrit dans `04_modeles_et_validation.md` §1.6.

### 2.4 Résultats

| Mode | Rappel `a_risque` | Précision `a_risque` | F1 macro | Temps |
|---|---|---|---|---|
| **Lot (batch)** | **0.611** ✅ | **0.433** ✅ | **0.610** ✅ | 0.02 s |
| Mini-lot (256, 5 époques) | 0.567 | 0.331 | 0.606 | 0.19 s |
| Online (1 passe, mélangé) | 0.356 | 0.234 | 0.543 | 6.3 s |
| Online (ordre d'arrivée réel) | 0.511 | 0.245 | 0.553 | 6.2 s |

**Le rappel seul ne suffit pas** : un modèle qui prédit `a_risque` trop souvent gonfle son rappel et devient inutilisable en atelier. D'où le suivi conjoint rappel + précision, et la comparaison de la répartition des classes prédites avec la réalité (notebook).

Le mini-lot est **instable d'une époque à l'autre** (rappel 0,28 → 0,78 → 0,13 → 0,56 → 0,57 sur les 5 époques) : avec une classe à 5 %, chaque paquet de 256 lignes n'en contient qu'une douzaine.

### 2.5 Ajuster l'apprentissage par le taux d'apprentissage

En lot, scikit-learn gère la convergence. En incrémental, c'est au concepteur de régler le taux d'apprentissage (mini-lot, 5 époques) :

| `learning_rate` | Rappel | Précision | F1 macro |
|---|---|---|---|
| `optimal` (défaut sklearn) | **0.622** | **0.403** | 0.590 |
| `constant`, `eta0=0.01` | 0.533 | 0.393 | **0.619** |
| `constant`, `eta0=0.001` | 0.567 | 0.331 | 0.606 |
| `constant`, `eta0=0.0001` | 0.133 | 0.197 | 0.488 |
| `adaptive`, `eta0=0.01` | 0.533 | 0.393 | 0.619 |

Trop faible (`eta0=0.0001`), le modèle n'apprend presque rien : rappel 0,13. Bien réglé, le mini-lot rejoint le lot (rappel 0,62 avec `optimal`, F1 0,62 avec `eta0=0.01`), sans le dépasser sur les deux métriques à la fois.

### 2.6 Décision pour MECHA

**Mode retenu : lot (batch), réentraînement planifié.**

- Meilleur compromis rappel / précision / F1, et le plus rapide (0,02 s) au volume actuel.
- Le mini-lot ne se justifie pas tant que l'historique tient en mémoire. Il devient la voie d'industrialisation au-delà : à ~10 000 points/min tous sites (cf. `01_besoin_et_conduite_du_changement.md` §1), soit ~14 M de points/jour, l'historique complet cessera de tenir en RAM.
- **L'online est écarté** : une passe unique ne suffit pas à converger, et le résultat dépend fortement de l'ordre d'arrivée (rappel 0,36 à 0,51). Inadapté à une décision de maintenance auditable.

**Fréquence de réentraînement** : mensuelle en phase pilote, alignée sur la boucle de retour terrain (cf. `01_besoin_et_conduite_du_changement.md` §2), avec réentraînement anticipé si le rappel en production passe sous 0,80. Le seuil de décision est recalculé à chaque réentraînement.

### 2.7 Limites

- Comparaison sur le jeu synthétique (`seed=42`), résultats déterministes et reproductibles.
- Pas d'optimisation d'hyperparamètres au-delà du taux d'apprentissage.
- Le mini-lot n'a pas été testé sur un flux réellement continu (données rejouées depuis un fichier).

---

## 3. Validation globale et projection industrielle

### 3.1 Stratégie de validation

La validation suit 3 niveaux, du technique au fonctionnel.

| Niveau | Quoi | Comment | Critère de succès |
|---|---|---|---|
| **Technique** | Le code fonctionne | Tests unitaires (pytest) + lint, exécutés par la CI | 100 % des tests passent |
| **ML** | Les modèles prédisent correctement | Validation croisée `GroupKFold` groupée par machine + jeu de test tenu à l'écart | Critères du client : rappel `a_risque` ≥ 80 %, faux positifs < 15 % ; MAE du RUL ≤ 25 cycles |
| **Fonctionnel** | La chaîne bout en bout produit des alertes | Scénario de test complet | Alerte visible dans Grafana pour une machine à RUL faible |

### 3.2 Validation technique

#### 3.2.1 Tests unitaires (51 tests)

| Fichier | Vérifie |
|---|---|
| `tests/test_outliers.py` | Winsorisation par machine, alerte capteur, capteur principal (`src/cleaning.py`) |
| `tests/test_decision.py` | Règle de décision du classifieur (`src/decision.py`) |
| `tests/test_api.py` | Endpoints, validation des sites, génération des alertes selon les seuils de RUL |
| `tests/test_pipeline_models.py` | Contrat d'export notebook → pipeline (fichiers, `metadata.json`, prédictions) |
| `tests/test_cleaning.py` | Calcul du RUL, niveaux de risque, format des identifiants |

#### 3.2.2 Intégration continue

GitHub Actions exécute à chaque push et pull request : lint (ruff) → tests (pytest) → validation du docker-compose → build des images Docker (`03_architecture_technique.md` §3).

### 3.3 Validation ML

#### 3.3.1 Protocole

- **Split par machine** (pas par ligne) pour éviter la fuite de données : 40 machines en apprentissage, 10 en test
- **Validation croisée `GroupKFold` 5 folds**, groupée par `machine_id` : chaque machine sert une fois en test. C'est elle qui sélectionne les modèles
- **Seuil de décision** du classifieur choisi en validation croisée sur les seules machines d'apprentissage, puis évalué sur les 10 machines de test
- 6 modèles comparés en classification, 5 en régression (`04_modeles_et_validation.md` §1)

#### 3.3.2 Indicateurs suivis

| Indicateur | Ce qu'il mesure | Pourquoi |
|---|---|---|
| Rappel `a_risque` | Part des pannes détectées | Critère client n°1 : une panne ratée coûte un arrêt non planifié |
| Taux de faux positifs | Part des machines saines déclarées à risque | Critère client n°2 : trop d'alertes et les équipes cessent de les croire |
| Précision `a_risque` | Part des alertes justifiées | Charge de travail inutile pour la maintenance |
| MAE du RUL | Erreur moyenne sur le temps restant, en heures | Directement lisible par le métier |

#### 3.3.3 Résultats obtenus

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

#### 3.3.4 Limites identifiées

- **Deux alertes `a_risque` sur trois sont fausses** (précision 0,33) : c'est le coût d'un rappel élevé sur une classe rare (5 % des cycles)
- **Rappel variable selon les machines** : 0,833 ± 0,082 sur les folds d'apprentissage, pire fold à 0,694 — le critère de 80 % n'est pas garanti sur chaque sous-ensemble de machines
- **Erreur du RUL (~20 h) supérieure au seuil d'alerte critique (4 h)** : une alerte critique signale une machine *probablement* proche de la panne, l'inspection humaine reste la décision finale (`05_guide_utilisateur.md` §4)
- Données synthétiques : résultats à revalider sur CMAPSS puis sur données réelles
- Un seul type de machine simulé : généralisation non garantie entre types de machines

### 3.4 Validation fonctionnelle (scénario bout en bout)

#### Scénario de test

1. `scripts/load_sensors_to_influx.py` rejoue `data/mecha_dataset_raw.csv` dans InfluxDB, comme un flux capteurs
2. `scripts/run_pipeline.py` lit le dernier relevé de chaque machine, applique les modèles exportés par le notebook et envoie les prédictions à l'API (`POST /predictions/site_fr1`)
3. L'API génère une alerte quand le RUL prédit est ≤ 8 (urgent) ou ≤ 4 (critique)
4. Grafana affiche les machines à intervenir via la datasource PostgreSQL
5. Le responsable maintenance voit la machine en rouge sur le dashboard

#### Critères d'acceptation

| Critère | Attendu | Obtenu |
|---|---|---|
| API répond | `GET /health` → `{"status": "ok"}` | ✅ |
| Insertion fonctionne | `POST /predictions/site_fr1` → `200` | ✅ |
| Alerte auto-générée | Ligne dans `site_fr1.alertes` pour `rul_predit ≤ 8` | ✅ |
| Dashboard affiche | Niveau de risque et RUL visibles dans Grafana | ✅ |

### 3.5 Projection industrielle

#### 3.5.1 Conditions de déploiement

| Prérequis | État | Action |
|---|---|---|
| VPN inter-sites | Existant chez MECHA | Configurer l'accès au serveur central |
| Serveur dédié | À provisionner | 4 vCPU, 16 Go RAM, 200 Go SSD |
| Capteurs IoT opérationnels | 3 sites FR complets, 2 sites ES partiels | Compléter l'équipement ES |
| GMAO intégrée | Partiel | Connecteur GMAO → PostgreSQL |

#### 3.5.2 Plan de déploiement

| Phase | Durée | Périmètre | Objectif |
|---|---|---|---|
| Pilote | 3 mois | 1 site FR, 3 machines | Valider la chaîne technique |
| Extension site | 3 mois | Toutes machines du site pilote | Stabiliser |
| Roll-out FR | 6 mois | 3 sites France | Uniformiser |
| Roll-out ES | 6 mois | 2 sites Espagne | Couverture complète |

#### 3.5.3 Points de vigilance

- **Dérive du modèle** : suivi du rappel en production, réentraînement mensuel (et recalcul du seuil de décision)
- **Qualité capteurs** : taux de disponibilité capteur à suivre (panneau *Alertes capteur*)
- **Adoption utilisateurs** : indicateurs de suivi (% alertes traitées, satisfaction)
- **Sécurité OT/IT** : le broker MQTT est en zone OT, la plateforme IA en zone IT — passage via firewall dédié
- **Continuité de production** : déploiement en heures creuses, pas d'impact sur SCADA/MES existant
