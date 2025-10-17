#!/usr/bin/env python
"""
Script de migración para convertir datos existentes al nuevo sistema multi-tenant.

Este script:
1. Migra usuarios existentes al nuevo sistema UserClient
2. Marca super_admins existentes con is_super_admin=True
3. Crea UserClient para cada usuario-cliente existente
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.development')
django.setup()

from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente
from django.db import transaction


def migrar_usuarios_existentes():
    """
    Migra usuarios existentes al nuevo sistema multi-tenant.
    """
    print("🚀 Iniciando migración de usuarios existentes...")
    
    with transaction.atomic():
        # 1. Marcar super_admins existentes
        super_admins = Usuario.objects.filter(tipo_usuario='super_admin')
        print(f"📋 Encontrados {super_admins.count()} super_admins existentes")
        
        for usuario in super_admins:
            usuario.is_super_admin = True
            usuario.save(update_fields=['is_super_admin'])
            print(f"✅ Marcado como super_admin: {usuario.email}")
        
        # 2. Migrar usuarios con cliente asignado
        usuarios_con_cliente = Usuario.objects.filter(
            cliente__isnull=False
        ).exclude(tipo_usuario='super_admin')
        
        print(f"📋 Encontrados {usuarios_con_cliente.count()} usuarios con cliente asignado")
        
        for usuario in usuarios_con_cliente:
            # Crear UserClient para el cliente existente
            user_client, created = UserClient.objects.get_or_create(
                usuario=usuario,
                cliente=usuario.cliente,
                rol=usuario.tipo_usuario,
                defaults={'activo': True}
            )
            
            if created:
                print(f"✅ Creado UserClient: {usuario.email} -> {usuario.cliente.nombre} ({usuario.tipo_usuario})")
            else:
                print(f"⚠️  UserClient ya existe: {usuario.email} -> {usuario.cliente.nombre}")
        
        # 3. Verificar usuarios sin cliente (solo super_admins deberían quedar)
        usuarios_sin_cliente = Usuario.objects.filter(
            cliente__isnull=True
        ).exclude(tipo_usuario='super_admin')
        
        if usuarios_sin_cliente.exists():
            print(f"⚠️  ADVERTENCIA: {usuarios_sin_cliente.count()} usuarios sin cliente y no son super_admin")
            for usuario in usuarios_sin_cliente:
                print(f"   - {usuario.email} ({usuario.tipo_usuario})")
        
        print("✅ Migración completada exitosamente!")


def verificar_migracion():
    """
    Verifica que la migración se haya realizado correctamente.
    """
    print("\n🔍 Verificando migración...")
    
    # Verificar super_admins
    super_admins = Usuario.objects.filter(is_super_admin=True)
    print(f"📊 Super admins marcados: {super_admins.count()}")
    
    # Verificar UserClient creados
    user_clients = UserClient.objects.all()
    print(f"📊 UserClient creados: {user_clients.count()}")
    
    # Verificar usuarios con múltiples clientes (debería ser 0 inicialmente)
    usuarios_multi_cliente = Usuario.objects.filter(
        clientes_roles__isnull=False
    ).distinct()
    print(f"📊 Usuarios con múltiples clientes: {usuarios_multi_cliente.count()}")
    
    # Mostrar resumen por cliente
    from django.db.models import Count
    clientes_con_usuarios = Cliente.objects.annotate(
        num_usuarios=Count('usuarios_roles')
    ).filter(num_usuarios__gt=0)
    
    print(f"\n📊 Resumen por cliente:")
    for cliente in clientes_con_usuarios:
        print(f"   - {cliente.nombre}: {cliente.num_usuarios} usuarios")


if __name__ == "__main__":
    try:
        migrar_usuarios_existentes()
        verificar_migracion()
        print("\n🎉 ¡Migración completada exitosamente!")
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        sys.exit(1)