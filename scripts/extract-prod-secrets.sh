#!/bin/bash

# Script para extraer valores de secrets de PROD
# ⚠️  IMPORTANTE: Solo ejecutar en tu máquina local, nunca en servidor compartido
# Uso: ./scripts/extract-prod-secrets.sh

set -euo pipefail

echo "🔐 Extrayendo valores de secrets de PROD..."
echo "⚠️  ADVERTENCIA: Este script expone valores secretos en la consola"
echo "   Solo ejecutar en tu máquina local, nunca en servidor compartido"
echo ""

# Lista de secrets a extraer
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

echo "📋 Valores de secrets de PROD:"
echo "================================"

# Extraer cada secret
for secret in "${SECRETS[@]}"; do
    echo ""
    echo "🔑 $secret:"
    echo "----------------------------------------"
    
    # Intentar obtener el valor del secret
    # Nota: GitHub CLI no permite leer valores de secrets por seguridad
    # Este comando solo mostrará si el secret existe
    if gh secret list --env prod | grep -q "$secret"; then
        echo "✅ Secret existe en PROD"
        echo "❌ No se puede leer el valor por seguridad"
        echo "   Necesitas copiarlo manualmente desde GitHub"
    else
        echo "❌ Secret no encontrado en PROD"
    fi
done

echo ""
echo "================================"
echo "⚠️  IMPORTANTE:"
echo "   GitHub CLI no permite leer valores de secrets por seguridad"
echo "   Necesitas copiarlos manualmente desde GitHub:"
echo "   1. Ve a Settings > Environments > prod"
echo "   2. Copia cada secret"
echo "   3. Ve a Settings > Environments > dev"
echo "   4. Pega cada secret"
echo ""
echo "💡 Alternativa: Usa el navegador para copiar/pegar los secrets"
