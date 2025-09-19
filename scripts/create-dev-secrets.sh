#!/bin/bash

# Script para crear secrets en DEV con valor CHANGEIT
# Uso: ./scripts/create-dev-secrets.sh

set -euo pipefail

echo "🔐 Creando secrets en DEV con valor CHANGEIT..."

# Lista de secrets que necesitamos crear
SECRETS=(
    "CF_DNS_API_TOKEN"
    "CONDOR_DB_PASSWORD"
    "DJANGO_SECRET_KEY"
    "EC2_SSH_KEY"
    "GCP_SA_CLIENT_EMAIL"
    "GCP_SA_PROJECT_ID"
    "GHCR_USERNAME"
    "GH_AUTOMATION_TOKEN"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "GOOGLE_CREDS"
    "POSTGRES_PASSWORD"
    "PUBLIC_GOOGLE_CLIENT_ID"
    "STATE_HMAC_SECRET"
    "VISION_OCR_BUCKET"
)

# Crear cada secret con valor CHANGEIT
for secret in "${SECRETS[@]}"; do
    echo "  🔑 Creando secret: $secret"
    gh secret set "$secret" --body "CHANGEIT" --env dev
done

echo ""
echo "✅ Todos los secrets creados en DEV con valor CHANGEIT"
echo "⚠️  IMPORTANTE: Recuerda cambiar los valores de CHANGEIT por los valores reales"
echo "   desde GitHub: Settings > Environments > dev"
