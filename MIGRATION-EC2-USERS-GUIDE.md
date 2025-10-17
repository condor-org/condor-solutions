# 🔄 Guía de Migración de Usuarios en EC2 - SIN PERDER DATOS

## ⚠️ IMPORTANTE: BACKUP PRIMERO

### **1. Backup Completo de la Base de Datos**

```bash
# Conectar a EC2 Dev
ssh ec2-dev

# Crear backup completo
cd /opt/condor
docker compose exec db pg_dump -U postgres condor_db > backup_antes_migracion_$(date +%Y%m%d_%H%M%S).sql

# Verificar que el backup se creó
ls -la backup_antes_migracion_*.sql

# Copiar backup a local (opcional pero recomendado)
scp ec2-dev:/opt/condor/backup_antes_migracion_*.sql ./
```

### **2. Verificar Estado Actual**

```bash
# Conectar a EC2 Dev
ssh ec2-dev

# Verificar usuarios existentes
cd /opt/condor
docker compose exec backend python manage.py shell -c "
from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente

print('=== USUARIOS EXISTENTES ===')
for u in Usuario.objects.all():
    print(f'Usuario: {u.email} | Cliente: {u.cliente_id} | Tipo: {u.tipo_usuario}')

print('\\n=== USERCLIENTS EXISTENTES ===')
for uc in UserClient.objects.all():
    print(f'UserClient: {uc.usuario.email} → {uc.cliente.nombre} ({uc.rol})')

print('\\n=== CLIENTES ===')
for c in Cliente.objects.all():
    print(f'Cliente: {c.id} - {c.nombre}')
"
```

---

## 🚀 Proceso de Migración Paso a Paso

### **Paso 1: Preparar Script de Migración**

```bash
# Conectar a EC2 Dev
ssh ec2-dev

# Crear directorio para scripts
cd /opt/condor
mkdir -p scripts

# Crear script de migración
cat > scripts/migrate_users_to_multitenant.py << 'EOF'
#!/usr/bin/env python3
"""
Script para migrar usuarios existentes al sistema multi-tenant.
Convierte usuarios del sistema monolítico al nuevo sistema de roles múltiples.
"""

import os
import sys
import django
from django.db import transaction

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.dev')
django.setup()

from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente
from django.db import IntegrityError

def migrate_users_to_multitenant():
    """
    Migra todos los usuarios existentes al sistema multi-tenant.
    
    Proceso:
    1. Obtener todos los usuarios existentes
    2. Para cada usuario, crear UserClient basado en su cliente actual
    3. Preservar el tipo_usuario como rol inicial
    4. Validar que la migración fue exitosa
    """
    
    print("🚀 Iniciando migración de usuarios al sistema multi-tenant...")
    
    # Estadísticas
    stats = {
        'usuarios_procesados': 0,
        'userclients_creados': 0,
        'errores': 0,
        'usuarios_sin_cliente': 0,
        'usuarios_super_admin': 0
    }
    
    try:
        with transaction.atomic():
            # Obtener todos los usuarios existentes
            usuarios = Usuario.objects.all()
            print(f"📊 Total de usuarios a migrar: {usuarios.count()}")
            
            for usuario in usuarios:
                stats['usuarios_procesados'] += 1
                
                try:
                    # Caso 1: Usuario super admin (no necesita UserClient)
                    if usuario.is_super_admin:
                        stats['usuarios_super_admin'] += 1
                        print(f"✅ Super admin: {usuario.email} (no requiere migración)")
                        continue
                    
                    # Caso 2: Usuario sin cliente asignado
                    if not usuario.cliente_id:
                        stats['usuarios_sin_cliente'] += 1
                        print(f"⚠️  Usuario sin cliente: {usuario.email}")
                        continue
                    
                    # Caso 3: Usuario normal - crear UserClient
                    cliente = Cliente.objects.get(id=usuario.cliente_id)
                    
                    # Determinar rol inicial basado en tipo_usuario
                    rol_inicial = usuario.tipo_usuario or 'usuario_final'
                    
                    # Crear UserClient
                    user_client, created = UserClient.objects.get_or_create(
                        usuario=usuario,
                        cliente=cliente,
                        rol=rol_inicial,
                        defaults={
                            'activo': True,
                            'creado_en': usuario.date_joined,
                        }
                    )
                    
                    if created:
                        stats['userclients_creados'] += 1
                        print(f"✅ Migrado: {usuario.email} → {cliente.nombre} ({rol_inicial})")
                    else:
                        print(f"ℹ️  Ya existe: {usuario.email} → {cliente.nombre} ({rol_inicial})")
                
                except Cliente.DoesNotExist:
                    stats['errores'] += 1
                    print(f"❌ Error: Cliente {usuario.cliente_id} no existe para usuario {usuario.email}")
                
                except IntegrityError as e:
                    stats['errores'] += 1
                    print(f"❌ Error de integridad: {usuario.email} - {str(e)}")
                
                except Exception as e:
                    stats['errores'] += 1
                    print(f"❌ Error inesperado: {usuario.email} - {str(e)}")
    
    except Exception as e:
        print(f"💥 Error crítico en migración: {str(e)}")
        raise
    
    # Mostrar estadísticas finales
    print("\n📈 ESTADÍSTICAS DE MIGRACIÓN:")
    print(f"  • Usuarios procesados: {stats['usuarios_procesados']}")
    print(f"  • UserClients creados: {stats['userclients_creados']}")
    print(f"  • Super admins: {stats['usuarios_super_admin']}")
    print(f"  • Usuarios sin cliente: {stats['usuarios_sin_cliente']}")
    print(f"  • Errores: {stats['errores']}")
    
    return stats

def validate_migration():
    """
    Valida que la migración fue exitosa.
    Verifica que todos los usuarios tengan sus UserClients correspondientes.
    """
    
    print("\n🔍 Validando migración...")
    
    # Verificar usuarios sin UserClients (excepto super admins)
    usuarios_sin_userclient = []
    for usuario in Usuario.objects.filter(is_super_admin=False):
        if not UserClient.objects.filter(usuario=usuario, activo=True).exists():
            usuarios_sin_userclient.append(usuario.email)
    
    if usuarios_sin_userclient:
        print(f"⚠️  Usuarios sin UserClient: {len(usuarios_sin_userclient)}")
        for email in usuarios_sin_userclient[:5]:  # Mostrar solo los primeros 5
            print(f"  - {email}")
        if len(usuarios_sin_userclient) > 5:
            print(f"  ... y {len(usuarios_sin_userclient) - 5} más")
    else:
        print("✅ Todos los usuarios tienen UserClients correspondientes")
    
    # Verificar integridad de datos
    total_userclients = UserClient.objects.filter(activo=True).count()
    total_usuarios = Usuario.objects.filter(is_super_admin=False).count()
    
    print(f"📊 UserClients activos: {total_userclients}")
    print(f"📊 Usuarios no-super-admin: {total_usuarios}")
    
    if total_userclients >= total_usuarios:
        print("✅ Migración validada exitosamente")
        return True
    else:
        print("❌ Migración incompleta")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 MIGRACIÓN DE USUARIOS A SISTEMA MULTI-TENANT")
    print("=" * 60)
    
    # Ejecutar migración
    stats = migrate_users_to_multitenant()
    
    # Validar migración
    if validate_migration():
        print("\n🎉 ¡Migración completada exitosamente!")
    else:
        print("\n💥 Migración falló - revisar errores")
        sys.exit(1)
EOF

# Hacer ejecutable
chmod +x scripts/migrate_users_to_multitenant.py
```

### **Paso 2: Ejecutar Migración**

```bash
# Ejecutar script de migración
cd /opt/condor
docker compose exec backend python scripts/migrate_users_to_multitenant.py
```

### **Paso 3: Verificar Migración**

```bash
# Verificar que la migración fue exitosa
docker compose exec backend python manage.py shell -c "
from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente

print('=== VERIFICACIÓN POST-MIGRACIÓN ===')
print('\\nUsuarios con UserClients:')
for usuario in Usuario.objects.filter(is_super_admin=False):
    userclients = UserClient.objects.filter(usuario=usuario, activo=True)
    if userclients.exists():
        print(f'✅ {usuario.email}:')
        for uc in userclients:
            print(f'  - {uc.cliente.nombre}: {uc.rol}')
    else:
        print(f'❌ {usuario.email}: SIN USERCLIENTS')

print('\\nSuper Admins:')
for usuario in Usuario.objects.filter(is_super_admin=True):
    print(f'✅ {usuario.email}: Super Admin')

print('\\nEstadísticas:')
print(f'Total usuarios: {Usuario.objects.count()}')
print(f'Total UserClients: {UserClient.objects.count()}')
print(f'UserClients activos: {UserClient.objects.filter(activo=True).count()}')
"
```

---

## 🔄 Rollback (En caso de problemas)

### **Script de Rollback**

```bash
# Crear script de rollback
cat > scripts/rollback_multitenant_migration.py << 'EOF'
#!/usr/bin/env python3
"""
Script para hacer rollback de la migración multi-tenant.
Elimina UserClients creados y restaura el sistema monolítico.
"""

import os
import sys
import django
from django.db import transaction

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.dev')
django.setup()

from apps.auth_core.models import UserClient

def rollback_migration():
    """
    Hace rollback de la migración multi-tenant.
    Elimina todos los UserClients creados.
    """
    
    print("🔄 ROLLBACK DE MIGRACIÓN MULTI-TENANT")
    print("=" * 40)
    
    # Confirmar rollback
    confirm = input("⚠️  ¿Estás seguro de hacer rollback? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Rollback cancelado")
        return False
    
    try:
        with transaction.atomic():
            # Contar UserClients a eliminar
            total_userclients = UserClient.objects.count()
            print(f"📊 UserClients a eliminar: {total_userclients}")
            
            # Eliminar todos los UserClients
            deleted_count, _ = UserClient.objects.all().delete()
            print(f"✅ Eliminados {deleted_count} UserClients")
            
            # Verificar que no quedan UserClients
            remaining = UserClient.objects.count()
            if remaining == 0:
                print("✅ Rollback completado exitosamente")
                return True
            else:
                print(f"❌ Quedan {remaining} UserClients - Rollback incompleto")
                return False
    
    except Exception as e:
        print(f"💥 Error en rollback: {str(e)}")
        return False

if __name__ == "__main__":
    success = rollback_migration()
    if success:
        print("\n🎉 Rollback exitoso - Sistema restaurado")
    else:
        print("\n💥 Rollback falló - Revisar errores")
EOF

# Hacer ejecutable
chmod +x scripts/rollback_multitenant_migration.py
```

### **Ejecutar Rollback (solo si es necesario)**

```bash
# Ejecutar rollback
docker compose exec backend python scripts/rollback_multitenant_migration.py
```

---

## 🧪 Testing Post-Migración

### **1. Probar Login**

```bash
# Probar login en dev
curl -X POST https://lucas.dev.cnd-ia.com/api/auth/oauth/state/ \
  -H "Content-Type: application/json" \
  -d '{"host": "lucas.dev.cnd-ia.com", "return_to": "/"}'

# Verificar JWT
# El JWT debe contener cliente_id y rol_en_cliente correctos
```

### **2. Probar Endpoints**

```bash
# Probar endpoint de perfil
curl -H "Authorization: Bearer <token>" \
  https://lucas.dev.cnd-ia.com/api/auth/yo/

# Debería mostrar:
# - cliente_actual con información correcta
# - roles disponibles
# - compatibilidad hacia atrás
```

### **3. Probar Role Switcher**

```bash
# Si el usuario tiene múltiples roles, probar cambio
curl -X POST https://lucas.dev.cnd-ia.com/api/auth/cambiar-rol/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"rol": "admin_cliente"}'
```

---

## 📊 Monitoreo Post-Migración

### **1. Logs a Monitorear**

```bash
# Monitorear logs del backend
docker compose logs -f backend | grep -E "(TENANT|OAUTH|USERCLIENT)"

# Buscar errores
docker compose logs backend | grep -i error
```

### **2. Métricas a Verificar**

```bash
# Verificar estadísticas
docker compose exec backend python manage.py shell -c "
from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente

print('=== ESTADÍSTICAS POST-MIGRACIÓN ===')
print(f'Total usuarios: {Usuario.objects.count()}')
print(f'Total UserClients: {UserClient.objects.count()}')
print(f'UserClients activos: {UserClient.objects.filter(activo=True).count()}')
print(f'Usuarios super admin: {Usuario.objects.filter(is_super_admin=True).count()}')

print('\\n=== USUARIOS POR CLIENTE ===')
for cliente in Cliente.objects.all():
    userclients_count = UserClient.objects.filter(cliente=cliente, activo=True).count()
    print(f'{cliente.nombre}: {userclients_count} usuarios')
"
```

---

## ⚠️ Consideraciones Importantes

### **1. Antes de la Migración**
- ✅ **Backup completo** de la base de datos
- ✅ **Verificar integridad** de datos existentes
- ✅ **Testing en ambiente de desarrollo** primero
- ✅ **Comunicar a usuarios** sobre posibles interrupciones

### **2. Durante la Migración**
- ✅ **Ejecutar en horario de baja actividad**
- ✅ **Monitorear logs** en tiempo real
- ✅ **Tener plan de rollback** listo
- ✅ **Validar cada paso** antes de continuar

### **3. Después de la Migración**
- ✅ **Verificar funcionalidad** completa
- ✅ **Probar login** de usuarios existentes
- ✅ **Validar permisos** por rol
- ✅ **Monitorear errores** por 24-48 horas

### **4. Casos Edge a Considerar**
- **Usuarios sin cliente**: ¿Qué hacer con ellos?
- **Usuarios con cliente_id inválido**: ¿Eliminar o asignar default?
- **Roles inválidos**: ¿Mapear a usuario_final?
- **Duplicados**: ¿Manejar conflictos de UserClient?

---

## 🎯 Resultado Esperado

Después de la migración exitosa:

1. **Todos los usuarios existentes** tendrán sus UserClients correspondientes
2. **Sistema multi-tenant** funcionando correctamente
3. **Compatibilidad hacia atrás** mantenida
4. **Datos preservados** sin pérdida
5. **Funcionalidad completa** en dev, listo para prod

### **Verificación Final**

```bash
# Comando de verificación final
docker compose exec backend python manage.py shell -c "
from apps.auth_core.models import Usuario, UserClient

# Verificar que todos los usuarios tienen UserClients
usuarios_sin_userclient = []
for usuario in Usuario.objects.filter(is_super_admin=False):
    if not UserClient.objects.filter(usuario=usuario, activo=True).exists():
        usuarios_sin_userclient.append(usuario.email)

if usuarios_sin_userclient:
    print(f'❌ Usuarios sin UserClient: {usuarios_sin_userclient}')
else:
    print('✅ Todos los usuarios tienen UserClients - Migración exitosa')
"
```

¡Listo para migrar sin perder datos! 🚀
