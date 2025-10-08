#!/bin/bash
set -e

# Ejecutar migraciones automáticamente
echo "🔄 Ejecutando migraciones..."
python manage.py migrate --noinput

# Ejecutar el comando original
echo "🚀 Iniciando aplicación..."
exec "$@"
