#!/bin/bash

# Script para crear el cliente "Distrito Padel" en el entorno de desarrollo
# Uso: ./scripts/bootstrap-distrito-padel.sh

set -euo pipefail

echo "🏢 Bootstrap Cliente: Distrito Padel"
echo "====================================="
echo ""

# Verificar que estamos en el entorno correcto
if [ "${DJANGO_ENV:-dev}" != "dev" ]; then
    echo "❌ ERROR: Este script solo debe ejecutarse en el entorno de desarrollo"
    echo "   DJANGO_ENV actual: ${DJANGO_ENV:-dev}"
    exit 1
fi

echo "✅ Entorno: ${DJANGO_ENV:-dev}"

# Verificar que el comando bootstrap existe
if ! python manage.py help bootstrap_condor >/dev/null 2>&1; then
    echo "❌ ERROR: Comando bootstrap_condor no encontrado"
    echo "   Asegúrate de estar en el directorio del backend"
    exit 1
fi

echo "✅ Comando bootstrap_condor disponible"
echo ""

# Ejecutar bootstrap con parámetros específicos para Distrito Padel
echo "🚀 Ejecutando bootstrap para Distrito Padel..."
echo ""

python manage.py bootstrap_condor \
    --cliente-nombre="Distrito Padel" \
    --admin-email="admin@distrito-padel.com" \
    --admin-pass="admin123" \
    --domains="distrito-padel-dev.cnd-ia.com" \
    --skip-migrate

echo ""
echo "✅ Bootstrap completado exitosamente"
echo ""
echo "📋 Resumen:"
echo "   Cliente: Distrito Padel"
echo "   Dominio: distrito-padel-dev.cnd-ia.com"
echo "   Admin: admin@distrito-padel.com / admin123"
echo ""
echo "🌐 Próximos pasos:"
echo "   1. Configurar DNS: distrito-padel-dev.cnd-ia.com → IP EC2 Dev"
echo "   2. Configurar OAuth en Google Console"
echo "   3. Actualizar variables de entorno del frontend"
echo "   4. Reiniciar servicios en la EC2 de dev"
echo ""
echo "🎯 Para probar:"
echo "   https://distrito-padel-dev.cnd-ia.com"
