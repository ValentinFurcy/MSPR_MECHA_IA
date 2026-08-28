#!/usr/bin/env bash
# Exécuté sur le VPS via SSH par le job "deploy" du workflow CI/CD.
# Clone le repo au premier déploiement, sinon le met à jour, puis relance
# la stack avec les images fraîchement poussées sur ghcr.io.

set -euo pipefail

REPO_URL="${REPO_URL:?REPO_URL manquant}"
APP_DIR="${APP_DIR:?APP_DIR manquant}"
BRANCH="${BRANCH:-main}"

if [ ! -d "$APP_DIR/.git" ]; then
    echo ">> Premier déploiement : clonage du dépôt dans $APP_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
    echo ">> Dépôt existant : mise à jour"
    cd "$APP_DIR"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
    echo "ATTENTION : .env absent sur le VPS — copie de .env.example (à éditer manuellement !)"
    cp .env.example .env
fi

echo ">> Authentification GHCR"
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin

export API_IMAGE="${API_IMAGE:?API_IMAGE manquant}"
export PIPELINE_IMAGE="${PIPELINE_IMAGE:?PIPELINE_IMAGE manquant}"

echo ">> Récupération des dernières images"
docker compose pull

echo ">> Redémarrage de la stack"
docker compose up -d --remove-orphans

echo ">> Nettoyage des anciennes images"
docker image prune -f

echo ">> Vérification santé API"
sleep 5
curl -sf http://localhost:8000/health || echo "AVERTISSEMENT : l'API ne répond pas encore"

echo ">> Déploiement terminé."
