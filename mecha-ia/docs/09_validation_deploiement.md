# Validation globale de la solution IA MECHA

## 1. Stratégie de validation

La validation suit 3 niveaux, du technique au fonctionnel.

| Niveau | Quoi | Comment | Critère de succès |
|---|---|---|---|
| **Technique** | Le code fonctionne | Tests unitaires (pytest) + CI | 100% des tests passent |
| **ML** | Les modèles prédisent correctement | Validation croisée `GroupKFold` groupée par machine | Recall `a_risque` ≥ 70%, MAE ≤ 25 cycles |
| **Fonctionnel** | La chaîne bout en bout produit des alertes | Scénario de test complet | Alerte générée dans Grafana pour une machine `a_risque` |

## 2. Validation technique

### 2.1 Tests unitaires

| Test | Fichier | Vérifie |
|---|---|---|
| Nettoyage | `tests/test_cleaning.py` | Pas de NaN après cleaning, types corrects |
| Features | `tests/test_features.py` | RUL ≥ 0, risk_level sans valeur manquante |
| API | `tests/test_api.py` | Endpoints retournent 200, insertion fonctionne |

### 2.2 CI/CD

GitHub Actions exécute à chaque push/PR : lint (ruff) → tests (pytest) → build image Docker → validation docker-compose.

## 3. Validation ML

### 3.1 Protocole

- **Split par machine** (pas par ligne) pour éviter la fuite de données — 80% train / 20% test
- **Validation croisée `GroupKFold` 5 folds**, groupée par `machine_id` : chaque machine sert une fois en test. C'est elle qui décide des modèles retenus
- 6 modèles comparés en classification, 5 en régression (voir `07_justification_modele.md`)

### 3.2 Résultats obtenus

**Classification (Logistic Regression retenue)**

| Classe | Precision | Recall | F1 |
|---|---|---|---|
| `a_risque` | 0.60 | 0.76 | 0.67 |
| `a_surveiller` | 0.58 | 0.68 | 0.62 |
| `normal` | 0.97 | 0.90 | 0.93 |

**Régression RUL (Random Forest retenu)** : MAE = 18.9 cycles, R² = 0.839 (split unique)

**En validation croisée (5 folds)** — chiffres de référence : recall `a_risque` = 0.766 ± 0.037 (pire fold 0.706), MAE = 19.9 ± 0.2 cycles, R² = 0.823. Les deux critères de succès sont tenus.

### 3.3 Limites identifiées

- Recall `a_risque` = 0.766 en CV → ~23% de pannes non détectées, et jusqu'à 29% sur le pire fold. Sous le seuil métier de 80% (à améliorer par optimisation hyperparamètres)
- Données synthétiques/CMAPSS → résultats à revalider sur données réelles
- Un seul type de machine simulé → généralisation non garantie inter-types

## 4. Validation fonctionnelle (scénario bout en bout)

### Scénario de test

1. Le notebook génère `predictions.csv`
2. Un script injecte les prédictions dans PostgreSQL via l'API (`POST /predictions/site_fr1`)
3. Les prédictions `a_risque` génèrent automatiquement une alerte dans la table `alertes`
4. Grafana affiche l'alerte en temps réel via la datasource PostgreSQL
5. Le responsable maintenance voit la machine en rouge sur le dashboard

### Critères d'acceptation

| Critère | Attendu | Obtenu |
|---|---|---|
| API répond | `GET /health` → `{"status": "ok"}` | ✅ |
| Insertion fonctionne | `POST /predictions/site_fr1` → `201` | ✅ |
| Alerte auto-générée | Ligne dans `site_fr1.alertes` pour `risk_level = a_risque` | ✅ |
| Dashboard affiche | Score de risque visible dans Grafana | ✅ |

## 5. Projection industrielle

### 5.1 Conditions de déploiement

| Prérequis | État | Action |
|---|---|---|
| VPN inter-sites | Existant chez MECHA | Configurer accès au serveur central |
| Serveur dédié | À provisionner | 4 vCPU, 16 Go RAM, 200 Go SSD |
| Capteurs IoT opérationnels | 3 sites FR complets, 2 sites ES partiels | Compléter équipement ES |
| GMAO intégrée | Partiel | Connecteur GMAO → PostgreSQL |

### 5.2 Plan de déploiement

| Phase | Durée | Périmètre | Objectif |
|---|---|---|---|
| Pilote | 3 mois | 1 site FR, 3 machines | Valider la chaîne technique |
| Extension site | 3 mois | Toutes machines du site pilote | Stabiliser |
| Roll-out FR | 6 mois | 3 sites France | Uniformiser |
| Roll-out ES | 6 mois | 2 sites Espagne | Couverture complète |

### 5.3 Points de vigilance

- **Dérive du modèle** : suivi MLflow, réentraînement trimestriel minimum
- **Qualité capteurs** : taux de disponibilité capteur à monitorer (dashboard dédié)
- **Adoption utilisateurs** : indicateurs de suivi (% alertes traitées, satisfaction)
- **Sécurité OT/IT** : le broker MQTT est en zone OT, la plateforme IA en zone IT — passage via firewall dédié
- **Continuité de production** : déploiement en heures creuses, pas d'impact sur SCADA/MES existant
