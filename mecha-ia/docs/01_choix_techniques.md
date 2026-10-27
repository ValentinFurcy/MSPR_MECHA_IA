# Choix techniques — Projet IA MECHA

## 1. Vue d'ensemble

Architecture en 6 couches : acquisition IoT → streaming → stockage brut → traitement/IA → stockage exploitable → restitution. Chaque brique est open-source, conteneurisable, et adaptée à un contexte industriel multi-sites.

## 2. Choix par couche

| Couche | Techno retenue | Justification | Alternatives écartées |
|---|---|---|---|
| Acquisition | **MQTT** | Protocole standard IoT industriel, léger, QoS configurable | HTTP (trop lourd), OPC-UA (plus adapté SCADA lourd) |
| Streaming | **Apache Kafka** | Bus scalable multi-sites, découplage producteurs/consommateurs, rétention configurable | RabbitMQ (moins scalable pour du time-series à haut débit) |
| Stockage brut | **InfluxDB** | Time-series DB optimisée pour capteurs (compression, downsampling natif) | TimescaleDB (viable, mais Influx = standard IoT) |
| Traitement | **Python + Pandas + Scikit-learn** | Écosystème ML mature, courbe d'apprentissage faible pour les équipes data | Spark (surdimensionné pour le volume MECHA) |
| Modèles ML | **Logistic Regression** (état machine) + **Random Forest** (RUL) | Retenus après comparaison de 6 classifieurs et 5 régresseurs en validation croisée (`07_justification_modele.md`) : meilleur rappel sur la classe critique, meilleure MAE | XGBoost, Gradient Boosting, KNN, arbre seul (moins bons sur la métrique métier) ; Deep Learning (volume insuffisant, boîte noire) |
| Persistance modèle | **joblib** | Standard scikit-learn, sérialise modèle + pipeline de preprocessing | ONNX (portabilité cross-langage, non nécessaire ici) |
| Stockage exploitable | **PostgreSQL** | Source unique, mature, supporte JSON/relationnel, connecteurs universels | MongoDB (pas de contrainte relationnelle utile ici) |
| Restitution ops | **Grafana** | Standard temps réel, alertes natives, connecteur Postgres | Kibana (moins bon sur Postgres) |
| Restitution direction | **Metabase** | Self-service BI, création de dashboards sans code | PowerBI (payant, moins portable) |
| MLOps (cible) | **MLflow** | Suivi expérimentations + registry, open-source | Dataiku (payant, retenu en option) |
| Conteneurisation | **Docker + docker-compose** | Reproductibilité, portage multi-sites, requis cahier des charges | Kubernetes (prévu phase 2 industrialisation) |
| CI/CD | **GitHub Actions** | Intégré au repo Git, gratuit, YAML simple | GitLab CI (équivalent, dépend de l'hébergement du repo) |

## 3. Structuration du code

```
.github/workflows/ci.yml          # CI (à la racine du dépôt)
mecha-ia/
├── mecha_maintenance_predictive.ipynb   # Préparation, entraînement, évaluation, export
├── data/                # Jeux de données livrés (brut, nettoyé, prédictions)
├── src/
│   ├── cleaning.py      # Nettoyage, alerte capteur, capteur principal
│   ├── decision.py      # Règle de décision du classifieur (seuil sur P(a_risque))
│   └── api/             # Exposition des résultats (FastAPI)
├── scripts/             # Ingestion InfluxDB + pipeline d'inférence
├── tests/               # Tests unitaires (pytest)
├── docker/              # Schéma PostgreSQL
├── grafana/             # Dashboards provisionnés
└── docs/                # Documentation
```

Le code partagé entre l'entraînement (notebook) et l'inférence (pipeline) vit dans `src/` : une seule implémentation du nettoyage et de la règle de décision.

**Principes :**
- Séparation claire ingestion / traitement / modèle / restitution
- Un module = une responsabilité
- Configuration externalisée (`.env` pour les connexions, `metadata.json` pour le contrat modèle → pipeline)
- Tests unitaires sur le nettoyage, la règle de décision, l'API et le contrat d'export des modèles (les modèles eux-mêmes sont validés par métriques)

## 4. Gestion du code source

- **Repo Git** unique, branche `main` protégée
- Workflow : `feature/*` → PR → revue → merge sur `main`
- **CI GitHub Actions** : lint (ruff) + tests (pytest) + build des images Docker à chaque push et PR (`10_cicd_deploiement.md`)
- Jeux de données versionnés dans `data/` ; modèles régénérés par le notebook (seed fixe, résultats reproductibles)
- Cible : versioning des modèles via MLflow

## 5. Sécurité de l'architecture

Les exigences de **disponibilité, intégrité et confidentialité** (concept DIC) appliquées à cette architecture — healthchecks, fonctionnement dégradé, comptes applicatifs à moindre privilège, exposition réseau, secrets — sont détaillées dans `02_volet_rgpd.md` §4, avec l'état réel de chaque mesure et les actions prioritaires avant production.

## 6. Limites techniques identifiées

| Limite | Impact | Mitigation |
|---|---|---|
| Hétérogénéité des 5 usines | Formats capteurs différents | Couche d'adaptation par site à prévoir (non implémentée) |
| Volume potentiellement massif | Coût stockage Influx | Rétention 90 jours brut + downsampling |
| Dérive des modèles dans le temps | Perte de performance | Suivi MLflow + réentraînement périodique |
| Pas de labels de panne au démarrage | Blocage du supervisé | Démarrage possible en non-supervisé (Isolation Forest), non réalisé dans le prototype |
