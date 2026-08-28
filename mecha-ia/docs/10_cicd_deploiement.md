# CI/CD — Déploiement VPS

## Pipeline (`.github/workflows/ci.yml`)

```
push/PR sur main
      │
      ▼
   [test] ── lint (ruff) + tests (pytest) + validation docker-compose
      │
      ▼ (uniquement push sur main)
[build-and-push] ── build images api + pipeline → push sur ghcr.io
      │
      ▼
   [deploy] ── SSH sur le VPS → git clone/pull → docker compose pull/up
```

Sur une pull request : seul le job `test` s'exécute (pas de build/déploiement).
Sur un push vers `main` : les 3 jobs s'enchaînent.

## Secrets GitHub à configurer

**Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valeur | Exemple |
|---|---|---|
| `VPS_HOST` | IP ou domaine du VPS | `51.83.XX.XX` |
| `VPS_USER` | Utilisateur SSH | `deploy` |
| `VPS_SSH_KEY` | Clé privée SSH (format PEM, sans passphrase) | contenu de `~/.ssh/id_ed25519` |
| `VPS_PORT` | Port SSH (optionnel, défaut 22) | `22` |
| `VPS_APP_DIR` | Dossier cible sur le VPS | `/opt/mecha-ia` |

`GITHUB_TOKEN` est fourni automatiquement par GitHub Actions — aucune configuration nécessaire pour l'authentification GHCR côté build.

## Prérequis sur le VPS

```bash
# 1. Installer Docker + Docker Compose
curl -fsSL https://get.docker.com | sh

# 2. Créer un utilisateur de déploiement (si pas déjà fait)
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# 3. Générer une paire de clés SSH dédiée (sur ta machine, pas sur le VPS)
ssh-keygen -t ed25519 -f mecha_deploy_key -N ""
# → mecha_deploy_key      : va dans le secret VPS_SSH_KEY
# → mecha_deploy_key.pub  : à ajouter dans ~deploy/.ssh/authorized_keys sur le VPS

# 4. Créer le dossier cible
sudo mkdir -p /opt/mecha-ia && sudo chown deploy:deploy /opt/mecha-ia
```

Le premier déploiement clone automatiquement le repo dans `VPS_APP_DIR` — pas besoin de le cloner manuellement.

## Le fichier `.env` sur le VPS

Le script (`scripts/deploy.sh`) copie `.env.example` vers `.env` **uniquement s'il n'existe pas déjà**. À éditer manuellement après le tout premier déploiement pour mettre de vrais mots de passe :

```bash
ssh deploy@<VPS_HOST>
cd /opt/mecha-ia
nano .env   # remplacer les mots de passe par défaut
docker compose up -d   # relancer avec les nouvelles valeurs
```

## Comment ça fonctionne (résumé)

1. **Build & push** : les images `api` et `pipeline` sont construites et poussées sur `ghcr.io/<owner>/mecha-ia-api` et `mecha-ia-pipeline`, taguées `latest` et `<sha du commit>`
2. **Déploiement** : le script `scripts/deploy.sh` est copié sur le VPS puis exécuté :
   - clone ou met à jour le repo (`git pull`)
   - s'authentifie sur `ghcr.io`
   - `docker compose pull` récupère les nouvelles images (via `API_IMAGE`/`PIPELINE_IMAGE`)
   - `docker compose up -d` redémarre uniquement les conteneurs modifiés
   - nettoie les anciennes images
   - vérifie que l'API répond (`/health`)

## Différence dev / prod

| | Local (dev) | VPS (prod) |
|---|---|---|
| Commande | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` | `docker compose up -d` (géré par le pipeline) |
| Images api/pipeline | Construites depuis les sources | Pré-construites, tirées de GHCR |

## Test manuel du déploiement (sans attendre un push)

Sur GitHub : **Actions → CI/CD — MECHA IA → Run workflow** (si `workflow_dispatch` est ajouté), ou simplement pousser un commit sur `main`.
