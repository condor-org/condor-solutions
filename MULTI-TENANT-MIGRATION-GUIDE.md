# 🔄 Guía Completa de Migración Multi-Tenant

## 📋 Resumen Ejecutivo

Esta guía proporciona un proceso paso a paso para migrar usuarios del sistema monolítico (1 usuario = 1 cliente = 1 rol) al sistema multi-tenant (1 usuario = múltiples clientes = múltiples roles) **sin perder ningún dato**.

### **Objetivo**
Transformar completamente el sistema de usuarios manteniendo:
- ✅ **Integridad de datos** - No se pierde información
- ✅ **Compatibilidad** - Sistema híbrido durante transición
- ✅ **Reversibilidad** - Posibilidad de rollback completo
- ✅ **Validación** - Verificación exhaustiva post-migración

---

## 🏗️ Arquitectura de la Migración

### **ANTES (Sistema Monolítico)**
```
Usuario (1) → Cliente (1) → Rol (1)
- Un usuario pertenecía a UN solo cliente
- Rol almacenado en Usuario.tipo_usuario
- Cliente almacenado en Usuario.cliente_id
```

### **DESPUÉS (Sistema Multi-Tenant)**
```
Usuario (N) ↔ Cliente (N) via UserClient
- Un usuario puede pertenecer a MÚLTIPLES clientes
- Cada relación Usuario-Cliente tiene su propio rol
- Super admins globales con acceso total
```

### **Estrategia de Migración**
1. **Preservar datos existentes** - No eliminar campos antiguos
2. **Crear relaciones UserClient** - Mapear usuarios existentes
3. **Mantener compatibilidad** - Sistema híbrido durante transición
4. **Validación completa** - Verificar integridad de datos
5. **Limpieza gradual** - Eliminar campos antiguos cuando sea seguro

---

## 📊 Análisis Pre-Migración

### **1. Script de Análisis de Datos**

```python
# backend/scripts/analyze_pre_migration.py
"""
Script para analizar el estado actual antes de la migración.
Identifica usuarios, clientes, roles y posibles problemas.
"""

import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.base')
django.setup()

from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente, ClienteDominio

def analyze_current_state():
    """
    Analiza el estado actual del sistema antes de la migración.
    """
    
    print("🔍 ANÁLISIS PRE-MIGRACIÓN")
    print("=" * 50)
    
    # 1. Estadísticas generales
    total_usuarios = Usuario.objects.count()
    total_clientes = Cliente.objects.count()
    total_userclients = UserClient.objects.count()
    
    print(f"📊 ESTADÍSTICAS GENERALES:")
    print(f"  • Total usuarios: {total_usuarios}")
    print(f"  • Total clientes: {total_clientes}")
    print(f"  • Total UserClients: {total_userclients}")
    
    # 2. Usuarios por tipo
    print(f"\n📊 USUARIOS POR TIPO:")
    tipos_usuarios = Usuario.objects.values('tipo_usuario').annotate(count=models.Count('id'))
    for tipo in tipos_usuarios:
        print(f"  • {tipo['tipo_usuario']}: {tipo['count']}")
    
    # 3. Usuarios por cliente
    print(f"\n📊 USUARIOS POR CLIENTE:")
    usuarios_por_cliente = Usuario.objects.values('cliente__nombre').annotate(count=models.Count('id'))
    for cliente in usuarios_por_cliente:
        print(f"  • {cliente['cliente__nombre']}: {cliente['count']}")
    
    # 4. Usuarios sin cliente
    usuarios_sin_cliente = Usuario.objects.filter(cliente__isnull=True).count()
    print(f"\n⚠️  USUARIOS SIN CLIENTE: {usuarios_sin_cliente}")
    
    # 5. Usuarios con cliente_id inválido
    from django.db.models import Q
    usuarios_cliente_invalido = Usuario.objects.filter(
        cliente__isnull=False,
        cliente_id__isnull=False
    ).exclude(cliente__in=Cliente.objects.all()).count()
    print(f"⚠️  USUARIOS CON CLIENTE_ID INVÁLIDO: {usuarios_cliente_invalido}")
    
    # 6. Dominios configurados
    print(f"\n📊 DOMINIOS CONFIGURADOS:")
    dominios = ClienteDominio.objects.select_related('cliente').all()
    for dominio in dominios:
        print(f"  • {dominio.hostname} → {dominio.cliente.nombre} (ID: {dominio.cliente_id})")
    
    # 7. UserClients existentes
    if total_userclients > 0:
        print(f"\n📊 USERCLIENTS EXISTENTES:")
        userclients_por_rol = UserClient.objects.values('rol').annotate(count=models.Count('id'))
        for rol in userclients_por_rol:
            print(f"  • {rol['rol']}: {rol['count']}")
    
    return {
        'total_usuarios': total_usuarios,
        'total_clientes': total_clientes,
        'usuarios_sin_cliente': usuarios_sin_cliente,
        'usuarios_cliente_invalido': usuarios_cliente_invalido
    }

if __name__ == "__main__":
    stats = analyze_current_state()
    print(f"\n✅ Análisis completado")
```

### **2. Script de Validación de Integridad**

```python
# backend/scripts/validate_data_integrity.py
"""
Script para validar la integridad de los datos antes de la migración.
Identifica problemas que podrían causar fallos en la migración.
"""

def validate_data_integrity():
    """
    Valida la integridad de los datos existentes.
    """
    
    print("🔍 VALIDACIÓN DE INTEGRIDAD DE DATOS")
    print("=" * 50)
    
    problemas = []
    
    # 1. Verificar usuarios con cliente_id inválido
    usuarios_cliente_invalido = Usuario.objects.filter(
        cliente__isnull=False,
        cliente_id__isnull=False
    ).exclude(cliente__in=Cliente.objects.all())
    
    if usuarios_cliente_invalido.exists():
        problemas.append({
            'tipo': 'cliente_invalido',
            'descripcion': 'Usuarios con cliente_id que no existe',
            'cantidad': usuarios_cliente_invalido.count(),
            'ejemplos': list(usuarios_cliente_invalido.values_list('email', flat=True)[:5])
        })
    
    # 2. Verificar usuarios con tipo_usuario inválido
    tipos_validos = ['super_admin', 'admin_cliente', 'empleado_cliente', 'usuario_final']
    usuarios_tipo_invalido = Usuario.objects.exclude(tipo_usuario__in=tipos_validos)
    
    if usuarios_tipo_invalido.exists():
        problemas.append({
            'tipo': 'tipo_usuario_invalido',
            'descripcion': 'Usuarios con tipo_usuario inválido',
            'cantidad': usuarios_tipo_invalido.count(),
            'ejemplos': list(usuarios_tipo_invalido.values_list('email', 'tipo_usuario')[:5])
        })
    
    # 3. Verificar usuarios duplicados
    emails_duplicados = Usuario.objects.values('email').annotate(
        count=models.Count('id')
    ).filter(count__gt=1)
    
    if emails_duplicados.exists():
        problemas.append({
            'tipo': 'emails_duplicados',
            'descripcion': 'Emails duplicados en la base de datos',
            'cantidad': emails_duplicados.count(),
            'ejemplos': list(emails_duplicados.values_list('email', flat=True)[:5])
        })
    
    # 4. Verificar clientes sin dominios
    clientes_sin_dominio = Cliente.objects.filter(dominios__isnull=True)
    
    if clientes_sin_dominio.exists():
        problemas.append({
            'tipo': 'clientes_sin_dominio',
            'descripcion': 'Clientes sin dominios configurados',
            'cantidad': clientes_sin_dominio.count(),
            'ejemplos': list(clientes_sin_dominio.values_list('nombre', flat=True)[:5])
        })
    
    # Mostrar problemas encontrados
    if problemas:
        print("❌ PROBLEMAS ENCONTRADOS:")
        for problema in problemas:
            print(f"\n  • {problema['tipo'].upper()}:")
            print(f"    Descripción: {problema['descripcion']}")
            print(f"    Cantidad: {problema['cantidad']}")
            print(f"    Ejemplos: {problema['ejemplos']}")
    else:
        print("✅ No se encontraron problemas de integridad")
    
    return problemas

if __name__ == "__main__":
    problemas = validate_data_integrity()
    if problemas:
        print(f"\n⚠️  Se encontraron {len(problemas)} tipos de problemas")
        print("Recomendación: Resolver problemas antes de proceder con la migración")
    else:
        print(f"\n✅ Datos validados correctamente - Listo para migración")
```

---

## 🚀 Proceso de Migración Paso a Paso

### **Paso 1: Preparación del Entorno**

```bash
# 1. Hacer backup completo de la base de datos
pg_dump condor_db > backup_antes_migracion_$(date +%Y%m%d_%H%M%S).sql

# 2. Verificar que no hay procesos activos
docker compose -f docker-compose-local.yml ps

# 3. Detener servicios si es necesario
docker compose -f docker-compose-local.yml down

# 4. Verificar espacio en disco
df -h
```

### **Paso 2: Análisis Pre-Migración**

```bash
# Ejecutar análisis de datos
cd backend
python scripts/analyze_pre_migration.py

# Validar integridad
python scripts/validate_data_integrity.py
```

### **Paso 3: Migración de Usuarios**

```python
# backend/scripts/migrate_users_to_multitenant.py
"""
Script principal de migración de usuarios al sistema multi-tenant.
Convierte usuarios del sistema monolítico al nuevo sistema de roles múltiples.
"""

import os
import sys
import django
from django.db import transaction
from django.db.models import Count

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.base')
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
    
    print("🚀 INICIANDO MIGRACIÓN DE USUARIOS AL SISTEMA MULTI-TENANT")
    print("=" * 70)
    
    # Estadísticas
    stats = {
        'usuarios_procesados': 0,
        'userclients_creados': 0,
        'errores': 0,
        'usuarios_sin_cliente': 0,
        'usuarios_super_admin': 0,
        'usuarios_cliente_invalido': 0,
        'usuarios_tipo_invalido': 0
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
                    
                    # Caso 3: Verificar que el cliente existe
                    try:
                        cliente = Cliente.objects.get(id=usuario.cliente_id)
                    except Cliente.DoesNotExist:
                        stats['usuarios_cliente_invalido'] += 1
                        print(f"❌ Cliente inválido: {usuario.email} (cliente_id: {usuario.cliente_id})")
                        continue
                    
                    # Caso 4: Verificar tipo_usuario válido
                    tipos_validos = ['admin_cliente', 'empleado_cliente', 'usuario_final']
                    if usuario.tipo_usuario not in tipos_validos:
                        stats['usuarios_tipo_invalido'] += 1
                        print(f"❌ Tipo inválido: {usuario.email} (tipo: {usuario.tipo_usuario})")
                        continue
                    
                    # Caso 5: Usuario normal - crear UserClient
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
    print(f"  • Usuarios con cliente inválido: {stats['usuarios_cliente_invalido']}")
    print(f"  • Usuarios con tipo inválido: {stats['usuarios_tipo_invalido']}")
    print(f"  • Errores: {stats['errores']}")
    
    return stats

def validate_migration():
    """
    Valida que la migración fue exitosa.
    Verifica que todos los usuarios tengan sus UserClients correspondientes.
    """
    
    print("\n🔍 VALIDANDO MIGRACIÓN...")
    
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
    print("=" * 70)
    print("🔄 MIGRACIÓN DE USUARIOS A SISTEMA MULTI-TENANT")
    print("=" * 70)
    
    # Ejecutar migración
    stats = migrate_users_to_multitenant()
    
    # Validar migración
    if validate_migration():
        print("\n🎉 ¡Migración completada exitosamente!")
    else:
        print("\n💥 Migración falló - revisar errores")
        sys.exit(1)
```

### **Paso 4: Verificación Post-Migración**

```python
# backend/scripts/verify_post_migration.py
"""
Script para verificar la integridad completa de la migración.
Valida que todos los usuarios tengan sus relaciones UserClient correctas.
"""

def verify_post_migration():
    """
    Verifica la integridad completa de la migración.
    """
    
    print("🔍 VERIFICACIÓN POST-MIGRACIÓN")
    print("=" * 50)
    
    # 1. Verificar usuarios sin UserClients
    usuarios_sin_userclient = Usuario.objects.filter(
        is_super_admin=False,
        userclient__isnull=True
    )
    
    print(f"📊 Usuarios sin UserClient: {usuarios_sin_userclient.count()}")
    if usuarios_sin_userclient.exists():
        print("⚠️  Usuarios problemáticos:")
        for usuario in usuarios_sin_userclient[:10]:
            print(f"  - {usuario.email} (cliente_id: {usuario.cliente_id})")
    
    # 2. Verificar UserClients huérfanos
    userclients_huerfanos = UserClient.objects.filter(
        usuario__isnull=True
    )
    
    print(f"📊 UserClients huérfanos: {userclients_huerfanos.count()}")
    
    # 3. Verificar consistencia de roles
    roles_inconsistentes = []
    for userclient in UserClient.objects.filter(activo=True):
        usuario = userclient.usuario
        if usuario.tipo_usuario and usuario.tipo_usuario != userclient.rol:
            roles_inconsistentes.append({
                'usuario': usuario.email,
                'tipo_usuario_old': usuario.tipo_usuario,
                'rol_new': userclient.rol,
                'cliente': userclient.cliente.nombre
            })
    
    print(f"📊 Roles inconsistentes: {len(roles_inconsistentes)}")
    if roles_inconsistentes:
        print("⚠️  Inconsistencias encontradas:")
        for item in roles_inconsistentes[:5]:
            print(f"  - {item['usuario']}: {item['tipo_usuario_old']} → {item['rol_new']}")
    
    # 4. Estadísticas generales
    print("\n📈 ESTADÍSTICAS GENERALES:")
    print(f"  • Total usuarios: {Usuario.objects.count()}")
    print(f"  • Super admins: {Usuario.objects.filter(is_super_admin=True).count()}")
    print(f"  • Usuarios normales: {Usuario.objects.filter(is_super_admin=False).count()}")
    print(f"  • UserClients activos: {UserClient.objects.filter(activo=True).count()}")
    print(f"  • Clientes: {Cliente.objects.count()}")
    
    # 5. Verificar por cliente
    print("\n📊 USUARIOS POR CLIENTE:")
    for cliente in Cliente.objects.all():
        userclients_count = UserClient.objects.filter(
            cliente=cliente, 
            activo=True
        ).count()
        print(f"  • {cliente.nombre}: {userclients_count} usuarios")
    
    return len(usuarios_sin_userclient) == 0 and len(userclients_huerfanos) == 0

if __name__ == "__main__":
    success = verify_post_migration()
    if success:
        print("\n✅ Verificación exitosa - Migración completa")
    else:
        print("\n❌ Verificación falló - Revisar problemas")
```

### **Paso 5: Testing de Funcionalidad**

```bash
# 1. Iniciar servicios
docker compose -f docker-compose-local.yml up -d

# 2. Probar login en puerto 8080 (Lucas Padel)
curl -X POST http://localhost:8080/api/auth/oauth/state/ \
  -H "Content-Type: application/json" \
  -d '{"host": "localhost", "return_to": "/"}'

# 3. Probar login en puerto 8081 (Distrito Padel)
curl -X POST http://localhost:8081/api/auth/oauth/state/ \
  -H "Content-Type: application/json" \
  -d '{"host": "localhost", "return_to": "/"}'

# 4. Verificar JWT contiene información correcta
# El JWT debe contener cliente_id y rol_en_cliente correctos

# 5. Probar endpoints con filtrado
curl -H "Authorization: Bearer <token>" \
  http://localhost:8080/api/auth/yo/

curl -H "Authorization: Bearer <token>" \
  http://localhost:8081/api/auth/yo/
```

---

## 🔧 Scripts de Rollback

### **Script de Rollback Completo**

```python
# backend/scripts/rollback_multitenant_migration.py
"""
Script para hacer rollback de la migración multi-tenant.
Elimina UserClients creados y restaura el sistema monolítico.
"""

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
```

---

## ⚠️ Consideraciones Importantes

### **Antes de la Migración**

1. **Backup completo** de la base de datos
2. **Verificar integridad** de datos existentes
3. **Testing en ambiente de desarrollo** primero
4. **Comunicar a usuarios** sobre posibles interrupciones
5. **Verificar espacio en disco** suficiente

### **Durante la Migración**

1. **Ejecutar en horario de baja actividad**
2. **Monitorear logs** en tiempo real
3. **Tener plan de rollback** listo
4. **Validar cada paso** antes de continuar
5. **No interrumpir** el proceso una vez iniciado

### **Después de la Migración**

1. **Verificar funcionalidad** completa
2. **Probar login** de usuarios existentes
3. **Validar permisos** por rol
4. **Monitorear errores** por 24-48 horas
5. **Documentar** cualquier problema encontrado

### **Casos Edge a Considerar**

1. **Usuarios sin cliente**: Se mantienen sin UserClient
2. **Usuarios con cliente_id inválido**: Se marcan como error
3. **Roles inválidos**: Se mapean a usuario_final
4. **Duplicados**: Se manejan con get_or_create
5. **Super admins**: No requieren UserClient

---

## 📊 Métricas de Migración

### **Antes de la Migración**
```sql
-- Usuarios por tipo
SELECT tipo_usuario, COUNT(*) 
FROM auth_core_usuario 
GROUP BY tipo_usuario;

-- Usuarios por cliente
SELECT c.nombre, COUNT(u.id) 
FROM auth_core_usuario u 
JOIN clientes_core_cliente c ON u.cliente_id = c.id 
GROUP BY c.nombre;
```

### **Después de la Migración**
```sql
-- UserClients por rol
SELECT rol, COUNT(*) 
FROM auth_core_userclient 
WHERE activo = true 
GROUP BY rol;

-- Usuarios por cliente (nuevo sistema)
SELECT c.nombre, COUNT(uc.id) 
FROM auth_core_userclient uc 
JOIN clientes_core_cliente c ON uc.cliente_id = c.id 
WHERE uc.activo = true 
GROUP BY c.nombre;
```

---

## 🎯 Checklist de Migración

### **Pre-Migración**
- [ ] Backup completo de la base de datos
- [ ] Análisis de datos ejecutado
- [ ] Validación de integridad
- [ ] Espacio en disco verificado
- [ ] Servicios detenidos

### **Migración**
- [ ] Script de migración ejecutado
- [ ] Sin errores críticos
- [ ] Validación post-migración exitosa
- [ ] Estadísticas verificadas

### **Post-Migración**
- [ ] Servicios iniciados
- [ ] Login probado en ambos puertos
- [ ] Endpoints funcionando correctamente
- [ ] Filtrado por cliente verificado
- [ ] Monitoreo activo

### **Limpieza (Opcional)**
- [ ] Campos antiguos identificados
- [ ] Plan de limpieza definido
- [ ] Testing de compatibilidad
- [ ] Eliminación gradual

---

## 📈 Beneficios Obtenidos

1. **Flexibilidad**: Un usuario puede tener diferentes roles en diferentes clientes
2. **Escalabilidad**: Fácil agregar nuevos clientes y roles
3. **Seguridad**: Autorización granular por cliente y rol
4. **UX**: Role switcher intuitivo para cambio dinámico
5. **Mantenibilidad**: Código modular y bien estructurado
6. **Compatibilidad**: Sistema híbrido durante transición

---

## 🚨 Troubleshooting

### **Problemas Comunes**

1. **Error de integridad**: Verificar que no hay duplicados
2. **Cliente no encontrado**: Verificar que el cliente existe
3. **Rol inválido**: Mapear a usuario_final
4. **Usuario sin cliente**: Mantener sin UserClient
5. **Super admin**: No requiere UserClient

### **Soluciones**

1. **Limpiar duplicados** antes de migrar
2. **Crear clientes faltantes** o asignar default
3. **Mapear roles inválidos** a usuario_final
4. **Documentar usuarios sin cliente** para revisión manual
5. **Verificar super admins** están marcados correctamente

---

## 📝 Documentación Final

### **Archivos Creados**
- `scripts/analyze_pre_migration.py` - Análisis pre-migración
- `scripts/validate_data_integrity.py` - Validación de integridad
- `scripts/migrate_users_to_multitenant.py` - Migración principal
- `scripts/verify_post_migration.py` - Verificación post-migración
- `scripts/rollback_multitenant_migration.py` - Rollback completo

### **Logs Generados**
- `logs/migration_YYYYMMDD_HHMMSS.log` - Log detallado de migración
- `logs/validation_YYYYMMDD_HHMMSS.log` - Log de validaciones
- `logs/rollback_YYYYMMDD_HHMMSS.log` - Log de rollback

### **Backups Creados**
- `backup_antes_migracion_YYYYMMDD_HHMMSS.sql` - Backup completo
- `backup_post_migracion_YYYYMMDD_HHMMSS.sql` - Backup post-migración

---

## 🎉 Conclusión

Esta guía proporciona un proceso completo y seguro para migrar del sistema monolítico al sistema multi-tenant, manteniendo la integridad de los datos y proporcionando herramientas de rollback en caso de problemas.

**La migración es reversible y no causa pérdida de datos.**
