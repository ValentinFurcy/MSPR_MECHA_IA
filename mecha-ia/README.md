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

**Prérequis** : Docker + Docker Compose, et Python 3.10+ en local pour exécuter
le notebook. Les jeux de données sont versionnés dans `data/` ; les modèles
`.joblib` (dossier `outputs/`, non versionné) sont produits par le notebook.

```bash
# 1. Cloner le repo (le projet vit dans le sous-dossier mecha-ia/)
git clone https://github.com/ValentinFurcy/MSPR_MECHA_IA.git
cd MSPR_MECHA_IA/mecha-ia

# 2. Copier le fichier d'environnement
cp .env.example .env

# 3. Entraîner les modèles (outputs/models/) et régénérer data/
pip install -r scripts/requirements.txt matplotlib jupyter
jupyter nbconvert --to notebook --execute --inplace mecha_maintenance_predictive.ipynb

# 4. Lancer la stack (Postgres, InfluxDB, API, Grafana, Metabase)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 5. Simuler l'envoi des capteurs vers InfluxDB
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm pipeline python scripts/load_sensors_to_influx.py

# 6. Lancer le pipeline (InfluxDB -> prédiction -> PostgreSQL)
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm pipeline python scripts/run_pipeline.py --site site_fr1

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

> **Astuce** : pour éviter de répéter les deux `-f`, exporte-les une fois pour
> toute la session. Attention au séparateur — `:` sous Linux/macOS, `;` sous
> Windows (y compris en Git Bash, car le binaire `docker` reste natif) :
> ```bash
> export COMPOSE_FILE=docker-compose.yml:docker-compose.dev.yml    # Linux / macOS
> export COMPOSE_FILE="docker-compose.yml;docker-compose.dev.yml"  # Git Bash sous Windows
> ```
> ```powershell
> $env:COMPOSE_FILE = "docker-compose.yml;docker-compose.dev.yml"  # PowerShell
> ```

### Sous Windows (PowerShell)

Trois commandes diffèrent :

```powershell
# Étape 7 — PowerShell ne supporte pas la redirection `<`
Get-Content scripts/seed_demo.sql | docker compose exec -T postgres psql -U admin -d mecha

# Étape 8 — `open` est une commande macOS
start http://localhost:3000

# `curl` est un alias d'Invoke-WebRequest : utiliser curl.exe pour le vrai curl
curl.exe http://localhost:8000/health
```

## Structure du projet

Le workflow CI est à la racine du dépôt (`.github/workflows/ci.yml`), le reste
du projet dans `mecha-ia/` :

```
MSPR_MECHA_IA/mecha-ia/            # racine des commandes ci-dessous
├── docker-compose.yml              # Stack complète (Influx, Postgres, API, Grafana, Metabase, pipeline)
├── docker-compose.dev.yml          # Override local : build depuis les sources au lieu de ghcr.io
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
│   ├── cleaning.py                 # Règles de nettoyage partagées notebook/pipeline
│   ├── decision.py                 # Règle de décision du classifieur (seuil sur P(a_risque))
│   └── api/
│       ├── main.py                 # API REST (FastAPI)
│       └── requirements.txt
├── tests/                          # pytest (nettoyage, règle de décision, API, export des modèles)
├── grafana/
│   └── provisioning/
│       ├── datasources/postgres.yml
│       └── dashboards/           # Dashboards versionnés (chargés au démarrage)
│           ├── dashboards.yml
│           ├── maintenance_predictive.json
│           └── pilotage_industriel.json
├── mecha_maintenance_predictive.ipynb  # Notebook ML (préparation, entraînement, évaluation, export)
├── data/                           # Jeux de données livrés (versionnés, régénérés par le notebook)
│   ├── mecha_dataset_raw.csv       # Brut, rejoué comme flux capteurs
│   ├── mecha_dataset.csv           # Nettoyé et adapté au vocabulaire MECHA
│   └── predictions.csv             # Prédictions sur les machines de test
├── outputs/                        # Générés par le notebook — NON versionné (.gitignore)
│   ├── benchmark_*.csv             # Comparaisons de modèles, modes d'entraînement
│   ├── alertes_capteurs.csv
│   └── models/                     # Modèles entraînés exportés (.joblib + metadata.json)
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
    ├── 12_solution_applicative.md
    ├── architecture_mecha.png
    └── architecture_mecha.py       # Génère le schéma d'architecture
```

## Intégration continue (CI)

Le workflow `.github/workflows/ci.yml` (à la racine du dépôt) s'exécute à chaque
push et pull request sur `main` :

```
1. test  : lint (ruff) + tests (pytest) + validation docker-compose
        ↓
2. build : construction des images api & pipeline
           (publiées sur ghcr.io uniquement lors d'un push sur main)
```

Aucun secret à configurer : `GITHUB_TOKEN` est fourni automatiquement par
GitHub Actions pour la publication sur GHCR.

### Développement local (sans passer par le registry)

`docker-compose.yml` seul référence les images `ghcr.io/<org>/mecha-ia-{api,pipeline}`
publiées par la CI. En local, ces images
n'existent pas — il faut systématiquement ajouter l'override qui build depuis
les sources, y compris pour `docker compose run pipeline` :

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm pipeline python scripts/run_pipeline.py --site site_fr1
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
| `POST` | `/predictions/{site}` | Insérer une prédiction (+ alerte automatique si RUL ≤ 8) |
| `GET` | `/alertes/{site}` | Alertes actives |
| `GET` / `POST` | `/alertes-capteurs/{site}` | Alertes capteur défaillant |

Sites valides : `site_fr1`, `site_fr2`, `site_fr3`, `site_es1`, `site_es2`

## Modèles ML retenus

| Tâche | Modèle | Métrique clé | Résultat |
|---|---|---|---|
| Classification état machine | Logistic Regression (seuil de décision 0,35) | Rappel `a_risque` / faux positifs (test) | 0,867 / 9,0 % |
| Prédiction RUL | Random Forest Regressor | MAE (validation croisée) | 19,9 cycles |

Justification complète : `docs/07_justification_modele.md`