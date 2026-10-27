# Justification du choix des modèles

## 1. Méthode

6 modèles de classification et 5 modèles de régression, comparés en **deux temps**, à features et hyperparamètres identiques :

1. **Split unique par machine** (40 machines en apprentissage, 10 en test, `random_state=42`) — sections 3 et 4. Premier classement, et base des analyses détaillées.
2. **Validation croisée `GroupKFold` 5 folds** — section 5. Vérifie que ce classement n'est pas un artefact du découpage : c'est **elle qui décide** des modèles retenus.

Le classifieur retenu reçoit ensuite un **seuil de décision** réglé pour atteindre les critères du client (section 6).

Notebook : `mecha_maintenance_predictive.ipynb`
Sorties : `outputs/benchmark_classification.csv`, `outputs/benchmark_regression.csv`, `outputs/benchmark_cv_classification.csv`, `outputs/benchmark_cv_regression.csv`

## 2. Critères de décision

| Tâche | Métrique prioritaire | Pourquoi |
|---|---|---|
| Classification | **Rappel `a_risque`** | Rater une vraie panne coûte plus cher qu'une fausse alerte |
| Régression | **MAE (cycles)** | Directement interprétable par le métier |
| Départage | Rapidité + interprétabilité | Contraintes industrielles : audit, réentraînement, portabilité |

Critères de succès du client (`03_entretien_client.md`) : rappel ≥ 80 % sur les pannes, moins de 15 % de faux positifs.

## 3. Résultats — Classification (split unique)

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

## 4. Résultats — Régression du RUL (split unique)

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

## 5. Validation croisée par groupe (`GroupKFold`)

Le split unique ne dit pas si le classement est stable : il peut être un artefact des 10 machines tombées en test.

**Protocole** : `GroupKFold`, 5 folds, groupement par `machine_id` (une machine entière est soit en apprentissage, soit en test — un `KFold` ligne à ligne créerait une fuite), sur **toutes** les machines. Déterministe donc reproductible. Un `assert` vérifie à chaque fold qu'aucune machine n'est des deux côtés.

### Classification (rappel `a_risque`)

| Modèle | **Rappel `a_risque`** | Écart-type | Pire fold | Accuracy | F1 macro |
|---|---|---|---|---|---|
| **Logistic Regression** | **0.607** ✅ | 0.103 | 0.433 | 0.842 | 0.611 |
| Random Forest | 0.482 | 0.053 | 0.389 | 0.871 | 0.662 |
| Gradient Boosting | 0.473 | 0.062 | 0.367 | 0.907 | 0.663 |
| XGBoost | 0.438 | 0.068 | 0.333 | 0.907 | 0.652 |
| Decision Tree | 0.418 | 0.092 | 0.256 | 0.825 | 0.569 |
| KNN (k=5) | 0.284 | 0.051 | 0.200 | 0.890 | 0.565 |

### Régression RUL (MAE)

| Modèle | **MAE (cycles)** | Écart-type | Pire fold | RMSE | R² |
|---|---|---|---|---|---|
| **Random Forest** | **19.9** ✅ | 0.2 | 20.2 | 25.3 | 0.824 |
| Gradient Boosting | 20.2 | 0.2 | 20.4 | 26.0 | 0.814 |
| XGBoost | 20.2 | 0.3 | 20.5 | 26.2 | 0.811 |
| Linear Regression | 22.1 | 0.3 | 22.5 | 27.4 | 0.792 |
| Decision Tree | 24.2 | 0.2 | 24.5 | 31.4 | 0.727 |

### Conclusions

- **Les modèles retenus ne changent pas** : Logistic Regression et Random Forest restent premiers, avec un écart supérieur à l'écart-type entre folds.
- **Le split unique était optimiste sur le RUL** : 18,9 cycles contre 19,9 en validation croisée — c'est 19,9 qu'il faut annoncer au client.
- **Avec la règle de décision par défaut, le rappel (0,607) est loin de la cible de 80 %**, et très variable d'un fold à l'autre (pire fold : 0,433). D'où le réglage du seuil de décision (section 6).

Méthode tracée dans `metadata.json` (bloc `validation`).

## 6. Réglage du seuil de décision

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

Les deux critères du client sont tenus. En contrepartie, deux alertes `a_risque` sur trois sont de fausses alertes, et la classe intermédiaire `a_surveiller` est moins bien reconnue (rappel 0,25 contre 0,54). Ce compromis est acceptable ici parce que **les alertes opérationnelles sont décidées par le RUL** (`12_solution_applicative.md` §3.1) : le classifieur sert de second avis tracé en base.

Sur les folds d'apprentissage, le rappel au seuil 0,35 vaut 0,833 ± 0,082 (pire fold : 0,694) : le critère de 80 % n'est pas garanti sur chaque sous-ensemble de machines.

## 7. Deux modèles, deux familles — pourquoi c'est cohérent

| Tâche | Nature du signal | Modèle adapté |
|---|---|---|
| Classification `risk_level` | Seuils sur le RUL → frontières nettes | Modèle linéaire suffit |
| Régression `RUL` | Dégradation continue non linéaire | Arbres nécessaires |

Choisir **le bon outil pour chaque tâche** plutôt qu'imposer une famille unique.

## 8. Limites de cette comparaison

- Résultats sur le **jeu synthétique** : sur CMAPSS ou des données réelles, l'ordre peut bouger — la méthode reste valable
- Pas d'optimisation d'hyperparamètres : paramètres raisonnables par défaut
- Modèles non supervisés (Isolation Forest, clustering) non étudiés : pertinents pour un démarrage sans labels de panne

## 9. Prochaines étapes recommandées

1. Relancer sur CMAPSS FD001 puis sur données réelles, vérifier la stabilité du classement
2. Optimiser les hyperparamètres des modèles retenus (et de XGBoost, avec pondération des classes)
3. Revalider le seuil de décision avec les retours terrain (coût réel d'une fausse alerte)
