# Justification du choix des modèles

## 1. Méthode

6 modèles de classification et 5 modèles de régression, comparés en **deux temps**, à features et hyperparamètres identiques :

1. **Split unique par machine** (`test_size=0.2`, `random_state=42`) — sections 3 et 4. Premier classement, et base des analyses détaillées.
2. **Validation croisée `GroupKFold` 5 folds** — section 5. Vérifie que ce classement n'est pas un artefact du découpage : c'est **elle qui décide** des modèles retenus.

Notebook : `mecha_maintenance_predictive.ipynb`
Sorties : `outputs/benchmark_classification.csv`, `outputs/benchmark_regression.csv`, `outputs/benchmark_cv_classification.csv`, `outputs/benchmark_cv_regression.csv`

## 2. Critères de décision

| Tâche | Métrique prioritaire | Pourquoi |
|---|---|---|
| Classification | **Recall `a_risque`** | Rater une vraie panne coûte plus cher qu'une fausse alerte |
| Régression | **MAE (cycles)** | Directement interprétable par le métier |
| Départage | Rapidité + interprétabilité | Contraintes industrielles : audit, réentraînement, portabilité |

## 3. Résultats — Classification

| Modèle | Accuracy | F1 macro | **Recall `a_risque`** | Temps fit |
|---|---|---|---|---|
| **Logistic Regression** | 0.846 | 0.743 | **0.762** ✅ | 0.02 s |
| Random Forest | 0.852 | 0.760 | 0.681 | 2.13 s |
| **XGBoost** | **0.879** 🏆 | **0.776** 🏆 | 0.637 | 0.58 s |
| Decision Tree | 0.808 | 0.693 | 0.625 | 0.06 s |
| Gradient Boosting | 0.876 | 0.768 | 0.625 | 18.59 s |
| KNN (k=5) | 0.857 | 0.701 | 0.400 | 0.01 s |

**Retenu : Logistic Regression**

### Justification

- **Meilleur recall sur la classe critique** (`a_risque`) : 0.762 vs 0.68 pour RF, 0.64 pour XGBoost
- **XGBoost domine sur accuracy et F1 macro** (0.879 / 0.776), mais rate 36% des vraies pannes — pénalisant en maintenance prédictive
- **Gradient Boosting** : perf équivalente à XGBoost, mais **32× plus lent** (18.6 s vs 0.58 s) → XGBoost dominerait toujours GB en industrialisation
- **Logistic Regression** est **10× plus rapide que XGBoost**, **30× plus rapide que RF**
- **Interprétabilité maximale** : coefficients linéaires directement lisibles pour audit qualité (exigence aéronautique)
- `class_weight="balanced"` compense le déséquilibre (72% `normal`, 19% `a_surveiller`, 9% `a_risque`)

### Note sur XGBoost

XGBoost est un **candidat sérieux à retester** avec :
- Ajustement du seuil de décision (`predict_proba` + seuil custom sur la classe `a_risque`)
- Pondération par classe (`scale_pos_weight`)
- Optimisation d'hyperparamètres (learning_rate, max_depth)

Avec les paramètres par défaut, il perd sur la métrique métier prioritaire.

### Leçon pédagogique

Un modèle plus complexe **n'est pas automatiquement meilleur sur la métrique qui compte**. XGBoost gagne sur accuracy (métrique "par défaut"), mais Logistic Regression gagne sur la métrique **définie par le besoin métier**. Le choix d'algorithme dépend de ce qu'on optimise.

## 4. Résultats — Régression (RUL)

| Modèle | **MAE (cycles)** | RMSE | R² | Temps fit |
|---|---|---|---|---|
| **Random Forest** | **18.9** ✅ | 24.1 | 0.839 | 6.76 s |
| **XGBoost** | 19.1 | 24.9 | 0.829 | **0.39 s** 🏆 |
| Gradient Boosting | 19.3 | 25.0 | 0.826 | 6.35 s |
| Linear Regression | 20.9 | 26.0 | 0.812 | 0.00 s |
| Decision Tree | 24.0 | 31.0 | 0.734 | 0.06 s |

**Retenu : Random Forest** (avec **XGBoost en alternative sérieuse pour l'industrialisation**)

### Justification

- **MAE la plus basse** : 18.9 cycles (vs 19.1 pour XGBoost, 19.3 pour GB)
- **R² le plus élevé** (0.839)
- Écart avec XGBoost très faible (0.2 cycle de MAE) mais **XGBoost est 17× plus rapide** (0.39 s vs 6.76 s)
- **Robustesse au bruit capteur** : le bagging (moyenne d'arbres) lisse les erreurs
- **Importance des features** exploitable pour le métier

### Recommandation industrialisation

- En phase pilote → **Random Forest** (meilleure MAE, référence)
- En phase de scaling multi-sites où le temps de réentraînement compte → **basculer sur XGBoost** : perte de 0.2 cycle de MAE compensée par un gain de temps de facteur 17 (permet un réentraînement horaire au lieu de journalier)

## 5. Validation croisée par groupe (`GroupKFold`)

Le split unique ne dit pas si le classement est stable : il peut être un artefact des 10 machines tombées en test.

**Protocole** : `GroupKFold`, 5 folds, groupement par `machine_id` (une machine entière est soit en apprentissage, soit en test — un `KFold` ligne à ligne créerait une fuite), sur **toutes** les machines. Déterministe donc reproductible. Un `assert` vérifie à chaque fold qu'aucune machine n'est des deux côtés.

### Classification (recall `a_risque`)

| Modèle | **Recall `a_risque`** | Écart-type | Pire fold | Accuracy | F1 macro |
|---|---|---|---|---|---|
| **Logistic Regression** | **0.766** ✅ | 0.037 | 0.706 | 0.843 | 0.742 |
| Random Forest | 0.699 | 0.051 | 0.631 | 0.855 | 0.775 |
| Gradient Boosting | 0.659 | 0.035 | 0.612 | 0.883 | 0.784 |
| Decision Tree | 0.605 | 0.049 | 0.519 | 0.813 | 0.708 |
| KNN (k=5) | 0.402 | 0.046 | 0.331 | 0.847 | 0.684 |

### Régression RUL (MAE)

| Modèle | **MAE (cycles)** | Écart-type | Pire fold | RMSE | R² |
|---|---|---|---|---|---|
| **Random Forest** | **19.9** ✅ | 0.2 | 20.2 | 25.3 | 0.823 |
| Gradient Boosting | 20.2 | 0.4 | 20.6 | 25.9 | 0.814 |
| Linear Regression | 22.1 | 0.3 | 22.4 | 27.4 | 0.792 |
| Decision Tree | 24.6 | 0.3 | 25.1 | 32.0 | 0.717 |

### Conclusions

- **Les modèles retenus ne changent pas** : Logistic Regression et Random Forest restent premiers.
- **Le split unique était optimiste sur le RUL** : 18,9 cycles contre 19,9 en CV — c'est 19,9 à annoncer au client.
- **Le seuil métier de 80 % n'est pas atteint** : 0,766 ± 0,037, pire fold à 0,706. Limite principale de la solution, désormais chiffrée avec son incertitude.

La sélection (section 10 du notebook) s'appuie sur la CV ; le split unique reste utilisé pour les analyses détaillées des sections 11-12, qui ont besoin d'un jeu de test tenu à l'écart. Méthode tracée dans `metadata.json` (bloc `validation`).

> Chiffres issus du jeu de repli synthétique (`seed=42`). **La ligne XGBoost manque** (`xgboost` absent de l'environnement de génération) : la cellule d'export du notebook imprime les tables complètes après exécution.

## 6. Deux modèles, deux familles — pourquoi c'est cohérent

| Tâche | Nature du signal | Modèle adapté |
|---|---|---|
| Classification `risk_level` | Seuils sur RUL → frontières nettes | Modèle linéaire suffit |
| Régression `RUL` | Dégradation continue non linéaire | Arbres nécessaires |

Choisir **le bon outil pour chaque tâche** > imposer une famille unique par confort.

## 7. Limites de cette comparaison

- Résultats sur le **jeu de repli synthétique**. Sur CMAPSS réel, l'ordre peut légèrement bouger — la méthode reste valable
- Pas d'optimisation d'hyperparamètres : paramètres raisonnables par défaut. Une optimisation dédiée pourrait resserrer les écarts (voir note XGBoost)
- Modèles non supervisés (Isolation Forest) hors scope — pertinents en démarrage à froid sans labels de panne

## 8. Prochaines étapes recommandées

1. Télécharger le vrai CMAPSS FD001, relancer, vérifier la stabilité du classement
2. **Optimiser XGBoost pour la classification** : GridSearch sur `scale_pos_weight`, `learning_rate`, `max_depth`, seuil de décision
3. Optimiser hyperparamètres de RF / Logistic Regression retenus
4. Ajouter Isolation Forest (non supervisé, complémentaire, cahier des charges)
