#!/bin/bash

# Script para copiar variables y secrets de PROD a DEV
# Uso: ./scripts/copy-prod-to-dev.sh

set -euo pipefail

echo "🚀 Copiando configuración de PROD a DEV..."

# Verificar que GitHub CLI esté instalado
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI no está instalado. Instálalo con: brew install gh"
    exit 1
fi

# Verificar que esté autenticado
if ! gh auth status &> /dev/null; then
    echo "❌ No estás autenticado con GitHub CLI. Ejecuta: gh auth login"
    exit 1
fi

# Obtener el repositorio actual
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "📁 Repositorio: $REPO"

# Crear environment DEV si no existe
echo "🔧 Creando environment DEV si no existe..."
gh api repos/$REPO/environments/dev -X PUT --field protection_rules='[]' || true

# Copiar variables de PROD a DEV
echo "📋 Copiando variables de PROD a DEV..."
gh variable list --env prod --json name,value | \
  jq -r '.[] | "\(.name)=\(.value)"' | \
  while IFS='=' read -r name value; do
    echo "  📝 Copiando variable: $name"
    gh variable set "$name" --body "$value" --env dev
  done

# Listar secrets de PROD (no podemos copiar los valores)
echo "🔐 Secrets encontrados en PROD:"
gh secret list --env prod --json name | jq -r '.[].name' | while read -r secret_name; do
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
