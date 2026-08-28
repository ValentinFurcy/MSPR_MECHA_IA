# Justification du choix des modèles

## 1. Méthode

6 modèles de classification et 5 modèles de régression ont été entraînés et évalués sur le **même split train/test par machine** (`test_size=0.2`, `random_state=42`), avec les mêmes features.

Notebook : `mecha_maintenance_predictive.ipynb`
Sorties : `outputs/benchmark_classification.csv`, `outputs/benchmark_regression.csv`

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

## 5. Deux modèles, deux familles — pourquoi c'est cohérent

| Tâche | Nature du signal | Modèle adapté |
|---|---|---|
| Classification `risk_level` | Seuils sur RUL → frontières nettes | Modèle linéaire suffit |
| Régression `RUL` | Dégradation continue non linéaire | Arbres nécessaires |

Choisir **le bon outil pour chaque tâche** > imposer une famille unique par confort.

## 6. Limites de cette comparaison

- Résultats sur le **jeu de repli synthétique**. Sur CMAPSS réel, l'ordre peut légèrement bouger — la méthode reste valable
- Pas d'optimisation d'hyperparamètres : paramètres raisonnables par défaut. Une optimisation dédiée pourrait resserrer les écarts (voir note XGBoost)
- Pas de validation croisée : 1 seul split. En production, prévoir `GroupKFold(groups=machine_id)`
- Modèles non supervisés (Isolation Forest) hors scope — pertinents en démarrage à froid sans labels de panne

## 7. Prochaines étapes recommandées

1. Télécharger le vrai CMAPSS FD001, relancer, vérifier la stabilité du classement
2. **Optimiser XGBoost pour la classification** : GridSearch sur `scale_pos_weight`, `learning_rate`, `max_depth`, seuil de décision
3. Optimiser hyperparamètres de RF / Logistic Regression retenus
4. Ajouter validation croisée `GroupKFold` par `machine_id`
5. Ajouter Isolation Forest (non supervisé, complémentaire, cahier des charges)
