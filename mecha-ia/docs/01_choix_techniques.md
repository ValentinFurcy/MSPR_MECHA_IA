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
| Modèles ML | **Random Forest + Isolation Forest** | RF : classification robuste, peu de tuning, interprétable. IF : détection d'anomalies non-supervisée | XGBoost (retenu en alternative comparative), Deep Learning (volume insuffisant, boîte noire) |
| Persistance modèle | **joblib** | Standard scikit-learn, sérialise modèle + pipeline de preprocessing | ONNX (portabilité cross-langage, non nécessaire ici) |
| Stockage exploitable | **PostgreSQL** | Source unique, mature, supporte JSON/relationnel, connecteurs universels | MongoDB (pas de contrainte relationnelle utile ici) |
| Restitution ops | **Grafana** | Standard temps réel, alertes natives, connecteur Postgres | Kibana (moins bon sur Postgres) |
| Restitution direction | **Metabase** | Self-service BI, création de dashboards sans code | PowerBI (payant, moins portable) |
| MLOps (pilote) | **MLflow** | Suivi expérimentations + registry, open-source | Dataiku (payant, retenu en option) |
| Conteneurisation | **Docker + docker-compose** | Reproductibilité, portage multi-sites, requis cahier des charges | Kubernetes (prévu phase 2 industrialisation) |
| CI/CD | **GitHub Actions** | Intégré au repo Git, gratuit, YAML simple | GitLab CI (équivalent, dépend de l'hébergement du repo) |

## 3. Structuration du code

```
mecha-ia/
├── src/
│   ├── ingestion/       # Simulation IoT + connecteurs InfluxDB
│   ├── cleaning/        # Nettoyage, feature engineering
│   ├── models/          # Entraînement, inférence, évaluation
│   ├── storage/         # Écritures PostgreSQL
│   └── api/             # Exposition résultats (FastAPI)
├── notebooks/           # Exploration, prototypage
├── tests/               # Tests unitaires (pytest)
├── docker/              # Dockerfiles + compose
├── .github/workflows/   # CI
└── docs/                # Documentation
```

**Principes :**
- Séparation claire ingestion / traitement / modèle / restitution
- Un module = une responsabilité
- Configuration externalisée (`.env`, `config.yaml`)
- Tests unitaires sur cleaning et features (les modèles sont validés par métriques)

## 4. Gestion du code source

- **Repo Git** unique, branche `main` protégée
- Workflow : `feature/*` → PR → revue → merge sur `main`
- **CI GitHub Actions** : lint (ruff) + tests (pytest) + build image Docker à chaque PR
- Versioning des modèles via MLflow (phase pilote)
- Versioning du dataset via un hash + `dataset_version` dans PostgreSQL

## 5. Limites techniques identifiées

| Limite | Impact | Mitigation |
|---|---|---|
| Hétérogénéité des 5 usines | Formats capteurs différents | Couche d'adaptation par site dans `ingestion/` |
| Volume potentiellement massif | Coût stockage Influx | Rétention 90 jours brut + downsampling |
| Dérive des modèles dans le temps | Perte de performance | Suivi MLflow + réentraînement périodique |
| Pas de labels de panne au démarrage | Blocage du supervisé | Démarrage en non-supervisé (Isolation Forest) puis basculement RF |
