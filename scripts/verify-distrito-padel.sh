#!/bin/bash

# Script para verificar que el cliente "Distrito Padel" está configurado correctamente
# Uso: ./scripts/verify-distrito-padel.sh

set -euo pipefail

echo "🔍 Verificación Cliente: Distrito Padel"
echo "========================================"
echo ""

# Verificar que estamos en el entorno correcto
if [ "${DJANGO_ENV:-dev}" != "dev" ]; then
    echo "❌ ERROR: Este script solo debe ejecutarse en el entorno de desarrollo"
    echo "   DJANGO_ENV actual: ${DJANGO_ENV:-dev}"
    exit 1
fi

echo "✅ Entorno: ${DJANGO_ENV:-dev}"
echo ""

# Verificar que el cliente existe en la base de datos
echo "📊 Verificando base de datos..."
echo ""

# Verificar Cliente
echo "1. Verificando Cliente..."
CLIENTE_COUNT=$(python manage.py shell -c "
from apps.clientes_core.models import Cliente
clientes = Cliente.objects.filter(nombre='Distrito Padel')
print(len(clientes))
" 2>/dev/null || echo "0")

if [ "$CLIENTE_COUNT" -eq 0 ]; then
    echo "❌ Cliente 'Distrito Padel' no encontrado en la base de datos"
    echo "   Ejecutar: ./scripts/bootstrap-distrito-padel.sh"
    exit 1
else
    echo "✅ Cliente 'Distrito Padel' encontrado (ID: $CLIENTE_COUNT)"
fi

# Verificar ClienteDominio
echo "2. Verificando Dominio..."
DOMINIO_COUNT=$(python manage.py shell -c "
from apps.clientes_core.models import ClienteDominio
dominios = ClienteDominio.objects.filter(hostname='distrito-padel-dev.cnd-ia.com', activo=True)
print(len(dominios))
" 2>/dev/null || echo "0")

if [ "$DOMINIO_COUNT" -eq 0 ]; then
    echo "❌ Dominio 'distrito-padel-dev.cnd-ia.com' no encontrado"
    echo "   Ejecutar: ./scripts/bootstrap-distrito-padel.sh"
    exit 1
else
    echo "✅ Dominio 'distrito-padel-dev.cnd-ia.com' encontrado"
fi

# Verificar Usuario Admin
echo "3. Verificando Usuario Admin..."
ADMIN_COUNT=$(python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
admins = User.objects.filter(email='admin@distrito-padel.com', tipo_usuario='admin_cliente')
print(len(admins))
" 2>/dev/null || echo "0")

if [ "$ADMIN_COUNT" -eq 0 ]; then
    echo "❌ Usuario admin 'admin@distrito-padel.com' no encontrado"
    echo "   Ejecutar: ./scripts/bootstrap-distrito-padel.sh"
    exit 1
else
    echo "✅ Usuario admin 'admin@distrito-padel.com' encontrado"
fi

echo ""
echo "✅ Verificación completada exitosamente"
echo ""
echo "📋 Resumen:"
echo "   ✅ Cliente: Distrito Padel"
echo "   ✅ Dominio: distrito-padel-dev.cnd-ia.com"
echo "   ✅ Admin: admin@distrito-padel.com"
echo ""
echo "🌐 Próximos pasos:"
echo "   1. Configurar DNS: distrito-padel-dev.cnd-ia.com → IP EC2 Dev"
echo "   2. Configurar OAuth en Google Console"
echo "   3. Actualizar variables de entorno del frontend"
echo "   4. Reiniciar servicios en la EC2 de dev"
echo ""
echo "🎯 Para probar:"
echo "   https://distrito-padel-dev.cnd-ia.com"
