# MECHA IA — Maintenance prédictive

**MSPR TPRE822 — EPSI — Bloc 2 : Concevoir une solution I.A.**

Solution de maintenance prédictive pour l'entreprise MECHA (5 usines, pièces mécaniques de haute précision).

## Architecture

```
[théorique — non déployé]     [déployé — docker compose]
Capteurs IoT → MQTT → Kafka → InfluxDB → Pipeline (clean+prédit) → PostgreSQL
                                  ↑              ↓                    ↓
                         scripts/load_        modèles           Grafana / Metabase
                         sensors_to_influx    (.joblib)
                         (simule l'IoT)
```

**Note** : MQTT/Kafka restent théoriques (voir `docs/01_choix_techniques.md`).
`scripts/load_sensors_to_influx.py` en tient lieu : il réinjecte les données
déjà générées comme si elles provenaient des capteurs, avec des timestamps réels.

## Démarrage rapide

```bash
# 1. Cloner le repo
git clone https://github.com/votre-equipe/mecha-ia.git && cd mecha-ia

# 2. Copier le fichier d'environnement
cp .env.example .env

# 3. Lancer la stack (Postgres, InfluxDB, API, Grafana, Metabase)
docker compose up -d

# 4. Générer les données + modèles (si pas déjà fait)
jupyter nbconvert --to notebook --execute --inplace mecha_maintenance_predictive.ipynb

# 5. Simuler l'envoi des capteurs vers InfluxDB
docker compose run --rm pipeline python scripts/load_sensors_to_influx.py

# 6. Lancer le pipeline (InfluxDB -> prédiction -> PostgreSQL)
docker compose run --rm pipeline python scripts/run_pipeline.py --site site_fr1

# 7. (optionnel) Charger un jeu de démonstration pour voir les dashboards
#    sans exécuter tout le pipeline
docker compose exec -T postgres psql -U admin -d mecha < scripts/seed_demo.sql

# 8. Vérifier
curl http://localhost:8000/health        # API
curl http://localhost:8000/predictions/site_fr1
open http://localhost:3000               # Grafana (admin/admin)
open http://localhost:3001               # Metabase (setup au 1er lancement)
open http://localhost:8086               # InfluxDB UI (admin / mecha_influx_2026)
```

## Structure du projet

```
mecha-ia/
├── docker-compose.yml              # Stack complète (Influx, Postgres, API, Grafana, Metabase, pipeline)
├── Dockerfile.api                  # Image API FastAPI
├── Dockerfile.pipeline             # Image scripts d'ingestion/inférence
├── docker/
│   └── init.sql                    # Schéma PostgreSQL (5 sites + base metabase_internal)
├── scripts/
│   ├── load_sensors_to_influx.py   # Simule l'envoi capteurs -> InfluxDB
│   ├── run_pipeline.py             # InfluxDB -> nettoyage -> prédiction -> API
│   ├── seed_demo.sql               # Jeu de démonstration pour les dashboards
│   └── requirements.txt
├── src/
│   └── api/
│       ├── main.py                 # API REST (FastAPI)
│       └── requirements.txt
├── grafana/
│   └── provisioning/
│       ├── datasources/postgres.yml
│       └── dashboards/           # Dashboards versionnés (chargés au démarrage)
│           ├── dashboards.yml
│           ├── maintenance_predictive.json
│           └── pilotage_industriel.json
├── .github/
│   └── workflows/ci.yml           # CI GitHub Actions
├── mecha_maintenance_predictive.ipynb  # Notebook ML (entraînement + export modèles)
├── outputs/                        # Générés par le notebook
│   ├── mecha_dataset_raw.csv
│   ├── mecha_dataset.csv
│   ├── predictions.csv
│   └── models/                     # Modèles entraînés exportés (.joblib)
└── docs/                           # Documentation
    ├── 01_choix_techniques.md
    ├── 02_volet_rgpd.md
    ├── 03_entretien_client.md
    ├── 04_guide_utilisateur.md
    ├── 05_conduite_changement.md
    ├── 06_documentation_dataset_ml.md
    ├── 07_justification_modele.md
    ├── 08_procedure_entrainement.md
    ├── 09_validation_deploiement.md
    ├── 10_cicd_deploiement.md
    ├── 11_cartographie_donnees.md
    └── architecture_mecha.png
```

## CI/CD — Déploiement automatique

Le pipeline `.github/workflows/ci.yml` s'exécute à chaque push sur `main` :

```
1. Tests (lint + pytest + validation docker-compose)
        ↓
2. Build images api & pipeline → push sur ghcr.io
        ↓
3. SSH sur le VPS → clone/pull → docker compose pull → up -d
```

### Secrets GitHub à configurer

**Settings → Secrets and variables → Actions** du repo :

| Secret | Exemple | Description |
|---|---|---|
| `VPS_HOST` | `51.68.XX.XX` | IP ou domaine du VPS |
| `VPS_USER` | `deploy` | Utilisateur SSH sur le VPS |
| `VPS_SSH_KEY` | `-----BEGIN OPENSSH...` | Clé privée SSH (voir génération ci-dessous) |
| `VPS_PORT` | `22` | Port SSH (optionnel, 22 par défaut) |
| `VPS_APP_DIR` | `/home/deploy/mecha-ia` | Dossier cible sur le VPS |

`GITHUB_TOKEN` est fourni automatiquement par GitHub Actions (push vers GHCR + login sur le VPS) — rien à configurer.

### Générer la clé SSH de déploiement

```bash
# En local
ssh-keygen -t ed25519 -f deploy_key -N ""

# Copier la clé PUBLIQUE sur le VPS
ssh-copy-id -i deploy_key.pub deploy@VOTRE_VPS

# Coller le contenu de deploy_key (clé PRIVÉE) dans le secret GitHub VPS_SSH_KEY
cat deploy_key
```

### Premier déploiement — prérequis sur le VPS

```bash
# Sur le VPS : installer Docker + Docker Compose
curl -fsSL https://get.docker.com | sh

# Créer le dossier parent (le clone se fait automatiquement par le pipeline)
mkdir -p /home/deploy/mecha-ia
```

Le `.env` n'est **jamais** commité ni déployé automatiquement — au premier déploiement, le script copie `.env.example` en `.env` sur le VPS. **Il faut ensuite éditer ce fichier manuellement sur le VPS** (mots de passe de prod, jamais ceux du repo).

### Rendre les images GHCR accessibles au VPS

Par défaut, les packages GHCR liés à un repo privé sont privés. Le script de déploiement gère l'authentification automatiquement via `GITHUB_TOKEN`. Si le repo est public, tu peux aussi rendre les packages publics (Settings du package sur GitHub) pour simplifier.

### Développement local (sans passer par le registry)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```



| Service | Port | URL | Usage |
|---|---|---|---|
| InfluxDB | 8086 | http://localhost:8086 | Stockage brut capteurs |
| PostgreSQL | 5432 | — | Données nettoyées + résultats |
| API FastAPI | 8000 | http://localhost:8000/docs | Exposition résultats IA |
| Grafana | 3000 | http://localhost:3000 | Dashboards ops (2 dashboards provisionnés, dossier MECHA) |
| Metabase | 3001 | http://localhost:3001 | Dashboards direction |
| Pipeline | — | (à la demande via `docker compose run`) | Ingestion + inférence |

## API — Endpoints

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | État de l'API + connexion DB |
| `GET` | `/predictions/{site}` | Dernières prédictions |
| `POST` | `/predictions/{site}` | Insérer une prédiction (+ auto-alerte si `a_risque`) |
| `GET` | `/alertes/{site}` | Alertes actives |

Sites valides : `site_fr1`, `site_fr2`, `site_fr3`, `site_es1`, `site_es2`

## Modèles ML retenus

| Tâche | Modèle | Métrique clé | Résultat |
|---|---|---|---|
| Classification état machine | Logistic Regression | Recall `a_risque` | 0.762 |
| Prédiction RUL | Random Forest Regressor | MAE | 18.9 cycles |

Justification complète : `docs/07_justification_modele.md`