#!/bin/bash

# Script para copiar variables de PROD a DEV usando GitHub API
# Uso: ./scripts/copy-prod-to-dev-api.sh

set -euo pipefail

echo "🚀 Copiando configuración de PROD a DEV usando GitHub API..."

# Verificar que tengas un token de GitHub
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ Necesitas configurar GITHUB_TOKEN"
    echo "   export GITHUB_TOKEN=tu_token_aqui"
    exit 1
fi

# Obtener el repositorio actual
REPO=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')
echo "📁 Repositorio: $REPO"

# Crear environment DEV si no existe
echo "🔧 Creando environment DEV si no existe..."
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/environments/dev" \
  -d '{"protection_rules":[]}' || true

# Obtener variables de PROD
echo "📋 Obteniendo variables de PROD..."
VARS=$(curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/environments/prod/variables")

# Copiar cada variable a DEV
echo "$VARS" | jq -r '.variables[] | "\(.name)=\(.value)"' | \
  while IFS='=' read -r name value; do
    echo "  📝 Copiando variable: $name"
    curl -s -X POST \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "https://api.github.com/repos/$REPO/environments/dev/variables" \
      -d "{\"name\":\"$name\",\"value\":\"$value\"}"
  done

# Listar secrets de PROD
echo "🔐 Secrets encontrados en PROD:"
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/environments/prod/secrets" | \
  jq -r '.secrets[].name' | while read -r secret_name; do
    echo "  🔑 $secret_name"
  done

echo ""
echo "⚠️  IMPORTANTE: Los secrets no se pueden copiar automáticamente."
echo "   Necesitas copiarlos manualmente desde GitHub:"
echo "   1. Ve a Settings > Environments > prod"
echo "   2. Copia cada secret"
echo "   3. Ve a Settings > Environments > dev"
echo "   4. Pega cada secret"
echo ""
echo "✅ Variables copiadas exitosamente de PROD a DEV"
echo "🔐 Recuerda copiar los secrets manualmente"
