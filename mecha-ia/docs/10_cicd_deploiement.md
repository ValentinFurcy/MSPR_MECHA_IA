# Intégration continue (CI)

## Pipeline (`.github/workflows/ci.yml`, à la racine du dépôt)

```
push / pull request sur main
      │
      ▼
   [test] ── lint (ruff) + tests (pytest) + validation docker-compose
      │
      ▼
   [build] ── build des images api + pipeline
              (push sur ghcr.io uniquement lors d'un push sur main)
```

Le projet vit dans le sous-dossier `mecha-ia/` : le workflow y exécute toutes
ses commandes (`defaults.run.working-directory: mecha-ia`), et le build Docker
utilise `mecha-ia/` comme contexte.

| Événement | `test` | `build` | Publication GHCR |
|---|---|---|---|
| Pull request vers `main` | Oui | Oui | Non |
| Push sur `main` | Oui | Oui | Oui |

Le build s'exécute aussi sur les pull requests : une image qui ne se construit
plus est détectée avant la fusion, pas après.

## Images produites

| Image | Dockerfile | Tags |
|---|---|---|
| `ghcr.io/<owner>/mecha-ia-api` | `Dockerfile.api` | `latest`, `<sha du commit>` |
| `ghcr.io/<owner>/mecha-ia-pipeline` | `Dockerfile.pipeline` | `latest`, `<sha du commit>` |

Le nom du propriétaire est converti en minuscules : Docker refuse les
majuscules dans un nom d'image.

Aucun secret à configurer : `GITHUB_TOKEN` est fourni automatiquement par
GitHub Actions pour la publication sur GHCR.

## Exécuter la solution

| | Local (dev) | Images publiées |
|---|---|---|
| Commande | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` | `docker compose up -d` avec `API_IMAGE` / `PIPELINE_IMAGE` pointant vers GHCR |
| Images api/pipeline | Construites depuis les sources | Tirées de GHCR |
