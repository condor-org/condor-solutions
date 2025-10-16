# Sistema Multi-Tenant con Roles Múltiples - Implementación

## 📋 Resumen de Cambios

### **Objetivo**
Transformar el sistema de usuarios de **monolítico** (1 usuario = 1 cliente = 1 rol) a **multi-tenant** (1 usuario = múltiples clientes = múltiples roles por cliente).

### **Cambios Principales**
1. **Nuevo modelo `UserClient`** para relación many-to-many Usuario-Cliente
2. **Super admins globales** con acceso a todos los clientes
3. **Role Switcher** en frontend para cambio dinámico de roles
4. **Nuevos endpoints** para gestión de roles
5. **Compatibilidad hacia atrás** durante la transición

---

## 🏗️ Arquitectura de Datos

### **ANTES (Sistema Monolítico)**
```
Usuario (1) → Cliente (1)
- Un usuario pertenecía a UN solo cliente
- Rol almacenado en `Usuario.tipo_usuario`
- Sin super admins globales
```

### **DESPUÉS (Sistema Multi-Tenant)**
```
Usuario (N) ↔ Cliente (N) via UserClient
- Un usuario puede pertenecer a MÚLTIPLES clientes
- Cada relación Usuario-Cliente tiene su propio rol
- Super admins globales con acceso total
```

---

## 🗄️ Cambios en Modelos de Datos

### **1. Nuevo Modelo `UserClient`**
```python
# apps/auth_core/models.py
"""
Modelos para el sistema multi-tenant con roles múltiples.
Permite que un usuario tenga diferentes roles en diferentes clientes.
"""

class UserClient(models.Model):
    """
    Relación muchos-a-muchos entre Usuario y Cliente con roles específicos.
    Permite que un usuario tenga diferentes roles en diferentes clientes.
    Ejemplo: Juan puede ser admin_cliente en ClienteA y usuario_final en ClienteB.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES_CHOICES)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['usuario', 'cliente', 'rol']
```

### **2. Modificaciones al Modelo `Usuario`**
```python
# apps/auth_core/models.py
class Usuario(models.Model):
    # Campos existentes...
    is_super_admin = models.BooleanField(
        default=False, 
        help_text="Super admin tiene acceso total a todos los clientes"
    )
    
    # Nuevos métodos:
    def es_super_admin(self):
        return self.is_super_admin
    
    def get_rol_en_cliente(self, cliente_id):
        """Retorna el rol principal del usuario en un cliente específico"""
        if self.is_super_admin:
            return "super_admin"
        
        roles = UserClient.objects.filter(
            usuario=self, 
            cliente_id=cliente_id, 
            activo=True
        ).values_list('rol', flat=True)
        
        if roles:
            # Retorna el rol con mayor prioridad
            priority_order = ['admin_cliente', 'empleado_cliente', 'usuario_final']
            for rol in priority_order:
                if rol in roles:
                    return rol
        
        return None
    
    def get_roles_en_cliente(self, cliente_id):
        """Retorna todos los roles del usuario en un cliente"""
        if self.is_super_admin:
            return ["super_admin"]
        
        return list(UserClient.objects.filter(
            usuario=self, 
            cliente_id=cliente_id, 
            activo=True
        ).values_list('rol', flat=True))
    
    def tiene_acceso_a_cliente(self, cliente_id):
        """Verifica si el usuario tiene acceso a un cliente"""
        return self.is_super_admin or UserClient.objects.filter(
            usuario=self, 
            cliente_id=cliente_id, 
            activo=True
        ).exists()
    
    def agregar_rol_a_cliente(self, cliente, rol='usuario_final'):
        """Agrega un rol al usuario en un cliente específico"""
        UserClient.objects.get_or_create(
            usuario=self,
            cliente=cliente,
            rol=rol,
            defaults={'activo': True}
        )
```

---

## 🔐 Cambios en Autenticación y Autorización

### **1. Nuevo Helper Function**
```python
# apps/auth_core/utils.py
"""
Utilidades para el sistema multi-tenant.
Helper functions para extraer información de roles desde JWTs.
"""

def get_rol_actual_del_jwt(request):
    """
    Extrae el rol actual del JWT del request.
    Retorna el rol activo o None si no se puede extraer.
    """
    try:
        # Extraer el token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        # Decodificar el JWT para obtener rol_en_cliente
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        rol_actual = payload.get('rol_en_cliente')
        
        logger.debug(f"[get_rol_actual_del_jwt] Rol extraído: {rol_actual}")
        return rol_actual
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"[get_rol_actual_del_jwt] Token expirado")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[get_rol_actual_del_jwt] Token inválido: {e}")
        return None
    except Exception as e:
        logger.error(f"[get_rol_actual_del_jwt] Error inesperado: {e}")
        return None
```

### **2. Modificaciones en `_issue_tokens_for_user`**
```python
# apps/auth_core/views.py
def _issue_tokens_for_user(user, cliente_actual=None):
    """Emite tokens JWT con información multi-tenant"""
    
    # Determinar rol y roles disponibles
    if user.is_super_admin:
        rol_en_cliente = "super_admin"
        roles_en_cliente = ["super_admin"]
    elif cliente_actual:
        rol_en_cliente = user.get_rol_en_cliente(cliente_actual.id)
        roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
    else:
        rol_en_cliente = "usuario_final"
        roles_en_cliente = ["usuario_final"]
    
    # Crear payload del access token
    access = {
        "user_id": user.id,
        "cliente_id": cliente_actual.id if cliente_actual else None,
        "rol_en_cliente": rol_en_cliente,
        "roles_en_cliente": roles_en_cliente,
        "is_super_admin": user.is_super_admin,
        "exp": datetime.utcnow() + timedelta(minutes=60),
    }
    
    # Crear tokens
    access_token = jwt.encode(access, settings.SECRET_KEY, algorithm="HS256")
    refresh_token = jwt.encode({"user_id": user.id}, settings.SECRET_KEY, algorithm="HS256")
    
    return {
        "access": access_token,
        "refresh": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "telefono": user.telefono,
            "is_super_admin": user.is_super_admin,
            "cliente_actual": {
                "id": cliente_actual.id if cliente_actual else None,
                "nombre": cliente_actual.nombre if cliente_actual else None,
                "rol": rol_en_cliente,
                "roles": roles_en_cliente,
                "tipo_cliente": cliente_actual.tipo_cliente if cliente_actual else None,
                "tipo_fe": cliente_actual.tipo_fe if cliente_actual else None,
            } if cliente_actual else None,
            "clientes": user.get_clientes_activos() if hasattr(user, 'get_clientes_activos') else [],
        }
    }
```

---

## 🌐 Nuevos Endpoints

### **1. Endpoint de Cambio de Rol**
```python
# apps/auth_core/views.py
class CambiarRolView(APIView):
    """
    Endpoint para cambiar el rol activo del usuario en el cliente actual.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        nuevo_rol = request.data.get('rol')
        if not nuevo_rol:
            return Response({"error": "Rol requerido"}, status=400)
        
        user = request.user
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        if not cliente_actual:
            return Response({"error": "Cliente no encontrado"}, status=400)
        
        # Verificar que el usuario tenga el rol solicitado
        if not user.is_super_admin and not user.tiene_rol_en_cliente(cliente_actual.id, nuevo_rol):
            return Response({"error": "No tienes este rol en este cliente"}, status=403)
        
        # Emitir nuevos tokens con el rol seleccionado
        tokens_data = _issue_tokens_for_user(user, cliente_actual)
        
        # Actualizar el rol en el token
        tokens_data["access"] = jwt.encode({
            **jwt.decode(tokens_data["access"], settings.SECRET_KEY, algorithms=['HS256']),
            "rol_en_cliente": nuevo_rol
        }, settings.SECRET_KEY, algorithm="HS256")
        
        return Response({
            "access": tokens_data["access"],
            "refresh": tokens_data["refresh"],
            "user": tokens_data["user"]
        })
```

### **2. Modificaciones en `MiPerfilView`**
```python
# apps/auth_core/views.py
class MiPerfilView(APIView):
    def get(self, request):
        user = request.user
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        # Obtener rol actual del JWT
        rol_actual = get_rol_actual_del_jwt(request)
        
        # Estructura de respuesta multi-tenant
        response_data = {
            "id": user.id,
            "email": user.email,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "telefono": user.telefono,
            "is_super_admin": user.is_super_admin,
            "cliente_actual": {
                "id": cliente_actual.id if cliente_actual else None,
                "nombre": cliente_actual.nombre if cliente_actual else None,
                "rol": rol_actual,
                "roles": user.get_roles_en_cliente(cliente_actual.id) if cliente_actual else [],
                "tipo_cliente": cliente_actual.tipo_cliente if cliente_actual else None,
                "tipo_fe": cliente_actual.tipo_fe if cliente_actual else None,
            } if cliente_actual else None,
            "clientes": user.get_clientes_activos() if hasattr(user, 'get_clientes_activos') else [],
            # Compatibilidad hacia atrás
            "tipo_usuario": rol_actual or user.tipo_usuario,
            "cliente_id": cliente_actual.id if cliente_actual else user.cliente_id,
        }
        
        return Response(response_data)
```

---

## 🔧 Modificaciones en Permisos

### **1. Actualización de Permission Classes**
```python
# apps/auth_core/permissions.py
class EsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_super_admin

class EsAdminCliente(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        if user.is_super_admin:
            return True
        
        if cliente_actual:
            return user.tiene_rol_en_cliente(cliente_actual.id, 'admin_cliente')
        
        return False

class TieneRolEnCliente(BasePermission):
    def __init__(self, roles_requeridos):
        self.roles_requeridos = roles_requeridos
    
    def has_permission(self, request, view):
        user = request.user
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        if user.is_super_admin:
            return True
        
        if cliente_actual:
            rol_actual = get_rol_actual_del_jwt(request)
            return rol_actual in self.roles_requeridos
        
        return False
```

---

## 🎨 Cambios en Frontend

### **1. Nuevo Componente RoleSwitcher**
```jsx
// frontend-padel/src/components/layout/RoleSwitcher.jsx
/**
 * Componente para cambiar roles en tiempo real.
 * Solo se muestra si el usuario tiene múltiples roles disponibles.
 * Permite cambio dinámico de rol con re-login automático.
 */
import React from 'react';
import { useRoleSwitcher } from '../../hooks/useRoleSwitcher';

const RoleSwitcher = () => {
  const { 
    selectedRole, 
    availableRoles, 
    hasMultipleRoles, 
    changeRole, 
    isChanging 
  } = useRoleSwitcher();

  if (!hasMultipleRoles) return null;

  return (
    <Menu>
      <MenuButton>
        <HStack spacing={2}>
          <Icon as={getRoleIcon(selectedRole)} />
          <Text>{getRoleLabel(selectedRole)}</Text>
          {isChanging && <Spinner size="sm" />}
        </HStack>
      </MenuButton>
      <MenuList>
        {availableRoles.map(role => (
          <MenuItem 
            key={role} 
            onClick={() => changeRole(role)}
            bg={role === selectedRole ? 'blue.100' : 'transparent'}
          >
            <HStack spacing={2}>
              <Icon as={getRoleIcon(role)} />
              <Text>{getRoleLabel(role)}</Text>
              {role === selectedRole && <Icon as={StarIcon} color="yellow.400" />}
            </HStack>
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
};
```

### **2. Hook useRoleSwitcher**
```javascript
// frontend-padel/src/hooks/useRoleSwitcher.js
/**
 * Hook para manejar el cambio de roles en el frontend.
 * Permite al usuario cambiar entre diferentes vistas según su rol.
 * Realiza llamadas al backend para cambiar rol y actualiza el estado local.
 */
import { useState, useCallback } from 'react';
import { useAuth } from '../auth/AuthContext';

export const useRoleSwitcher = () => {
  const { user, axiosAuth } = useAuth();
  const [selectedRole, setSelectedRole] = useState(user?.cliente_actual?.rol);
  const [isChanging, setIsChanging] = useState(false);

  const availableRoles = user?.cliente_actual?.roles || [];
  const hasMultipleRoles = availableRoles.length > 1;

  const changeRole = useCallback(async (newRole) => {
    if (newRole === selectedRole) return;
    
    setIsChanging(true);
    try {
      const response = await axiosAuth.post('/auth/cambiar-rol/', { rol: newRole });
      
      // Actualizar localStorage
      localStorage.setItem('accessToken', response.data.access);
      localStorage.setItem('refreshToken', response.data.refresh);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      // Actualizar headers de axios
      axiosAuth.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
      
      // Recargar página para aplicar cambios
      window.location.href = getRedirectPath(newRole);
    } catch (error) {
      console.error('Error cambiando rol:', error);
    } finally {
      setIsChanging(false);
    }
  }, [selectedRole, axiosAuth]);

  return {
    selectedRole,
    availableRoles,
    hasMultipleRoles,
    changeRole,
    isChanging
  };
};
```

### **3. Actualización de PublicRoute**
```jsx
// frontend-padel/src/router/PublicRoute.jsx
/**
 * Componente para rutas públicas con redirección automática.
 * Redirige usuarios autenticados a su dashboard según su rol actual.
 * Soporta tanto estructura antigua (tipo_usuario) como nueva (cliente_actual.rol).
 */
const PublicRoute = ({ children }) => {
  const { user, loadingUser } = useContext(AuthContext);

  if (loadingUser) return null;

  if (user?.tipo_usuario || user?.cliente_actual?.rol) {
    let destino = "/login";
    
    // Usar nueva estructura multi-tenant primero, luego fallback a la antigua
    const currentRole = user.cliente_actual?.rol || user.tipo_usuario;

    switch (currentRole) {
      case "super_admin":
      case "admin_cliente":
        destino = "/admin";
        break;
      case "usuario_final":
        destino = "/jugador";
        break;
      case "empleado_cliente":
        destino = "/profesores/turnos";
        break;
      default:
        console.warn("[PUBLIC ROUTE] ⚠️ rol desconocido:", currentRole);
    }

    return <Navigate to={destino} replace />;
  }

  return children;
};
```

---

## 🔄 Modificaciones en Views Existentes

### **1. UsuarioViewSet - Lista de Usuarios**
```python
# apps/auth_core/views.py
class UsuarioViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        """Lista usuarios mostrando una entrada por cada rol que tengan."""
        from apps.auth_core.models import UserClient
        
        usuarios = self.get_queryset()
        usuarios_con_roles = []
        
        for usuario in usuarios:
            cliente_actual = getattr(request, 'cliente_actual', None)
            
            if usuario.is_super_admin:
                usuarios_con_roles.append({
                    'usuario': usuario,
                    'rol': 'super_admin',
                    'cliente': None
                })
            else:
                user_clients = UserClient.objects.filter(usuario=usuario, activo=True)
                
                if user_clients.exists():
                    for user_client in user_clients:
                        usuarios_con_roles.append({
                            'usuario': usuario,
                            'rol': user_client.rol,
                            'cliente': user_client.cliente
                        })
                else:
                    # Usuario con sistema antiguo
                    usuarios_con_roles.append({
                        'usuario': usuario,
                        'rol': usuario.tipo_usuario,
                        'cliente': usuario.cliente
                    })
        
        # Serializar cada entrada
        serializer = UsuarioSerializer([entry['usuario'] for entry in usuarios_con_roles], many=True)
        data = serializer.data
        
        # Agregar información de rol a cada entrada
        for i, entry in enumerate(usuarios_con_roles):
            data[i]['rol_activo'] = entry['rol']
            data[i]['tipo_usuario'] = entry['rol']  # Para consistencia
            if entry['cliente']:
                data[i]['cliente_info'] = {
                    'id': entry['cliente'].id,
                    'nombre': entry['cliente'].nombre
                }
        
        return Response({
            'count': len(data),
            'next': None,
            'previous': None,
            'results': data
        })
```

### **2. TurnoListView - Filtrado por Rol**
```python
# apps/turnos_core/views.py
class TurnoListView(ListAPIView):
    def get_queryset(self):
        usuario = self.request.user
        rol_actual = get_rol_actual_del_jwt(self.request)
        cliente_actual = getattr(self.request, 'cliente_actual', None)

        # Super admin ve todos los turnos
        if usuario.is_super_admin:
            qs = Turno.objects.all().select_related("usuario", "lugar")

        # Admin del cliente ve todos los turnos de su cliente
        elif rol_actual == "admin_cliente" and cliente_actual:
            qs = (
                Turno.objects
                .filter(lugar__cliente_id=cliente_actual.id)
                .select_related("usuario", "lugar")
            )

        # Empleado ve sus propios turnos
        elif rol_actual == "empleado_cliente":
            from django.contrib.contenttypes.models import ContentType
            ct_prestador = ContentType.objects.get_for_model(Prestador)
            qs = (
                Turno.objects
                .filter(content_type=ct_prestador, object_id__in=Prestador.objects.filter(user=usuario).values_list("id", flat=True))
                .select_related("usuario", "lugar")
            )

        # Usuario final ve solo sus turnos
        else:
            qs = Turno.objects.filter(usuario=usuario).select_related("usuario", "lugar")

        # Aplicar filtros adicionales
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        # Usuarios finales: ocultar turnos de abonos
        if rol_actual == "usuario_final":
            qs = qs.filter(
                reservado_para_abono=False,
                abono_mes_reservado__isnull=True,
                abono_mes_prioridad__isnull=True,
                comprobante_abono__isnull=True,
            )

        return qs
```

---

## 📊 Modificaciones en Serializers

### **1. UsuarioSerializer - Múltiples Roles**
```python
# apps/auth_core/serializers.py
class UsuarioSerializer(LoggedModelSerializer):
    # Campo para múltiples roles (solo para escritura)
    roles = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="Lista de roles a asignar al usuario"
    )
    
    # Campo para leer los roles del usuario
    user_roles = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            "id", "email", "username", "nombre", "apellido", "telefono",
            "is_active", "tipo_usuario", "cliente", "is_super_admin",
            "roles", "user_roles",
        )
        read_only_fields = ["id", "username"]

    def create(self, validated_data):
        roles = validated_data.pop('roles', [])
        
        instance = User(**validated_data)
        if hasattr(instance, "set_unusable_password"):
            instance.set_unusable_password()
        instance.save()
        
        # Asignar roles si se proporcionaron
        if roles:
            from apps.auth_core.models import UserClient
            cliente = validated_data.get('cliente')
            
            if cliente:
                for rol in roles:
                    if rol in ['usuario_final', 'admin_cliente', 'empleado_cliente']:
                        UserClient.objects.get_or_create(
                            usuario=instance,
                            cliente=cliente,
                            rol=rol,
                            defaults={'activo': True}
                        )
                    elif rol == 'super_admin':
                        raise serializers.ValidationError({
                            "roles": "No se puede asignar el rol 'super_admin' a través de este endpoint"
                        })
        
        return instance

    def get_user_roles(self, obj):
        """Obtiene todos los roles del usuario en el cliente actual."""
        request = self.context.get('request')
        if not request:
            return []
        
        cliente_actual = getattr(request, 'cliente_actual', None)
        if not cliente_actual:
            return []
        
        if obj.is_super_admin:
            return ['super_admin']
        
        from apps.auth_core.models import UserClient
        roles = UserClient.objects.filter(
            usuario=obj,
            cliente=cliente_actual,
            activo=True
        ).values_list('rol', flat=True)
        
        return list(roles)
```

---

## 🗂️ Archivos Modificados

### **Backend**
- `apps/auth_core/models.py` - Nuevo modelo UserClient y métodos en Usuario
- `apps/auth_core/views.py` - Nuevos endpoints y lógica multi-tenant
- `apps/auth_core/serializers.py` - Soporte para múltiples roles
- `apps/auth_core/permissions.py` - Permisos actualizados
- `apps/auth_core/utils.py` - Helper functions
- `apps/auth_core/urls.py` - Nuevas rutas
- `apps/turnos_core/views.py` - Filtrado por rol actual (PrestadorViewSet)
- `apps/turnos_padel/views.py` - Filtrado por rol actual (SedePadelViewSet, AbonoMesViewSet, ConfiguracionSedePadelViewSet)
- `apps/pagos_core/views.py` - Filtrado por rol actual (ComprobanteView, ComprobanteAbonoView, PagosPendientesCountView)
- `apps/notificaciones_core/views.py` - Filtrado por rol actual (NotificationListView, NotificationUnreadCountView)
- `apps/common/views.py` - Actualizado MonitoreoRecursosView
- `apps/common/permissions.py` - Permisos ya actualizados correctamente

### **Frontend**
- `src/components/layout/RoleSwitcher.jsx` - Nuevo componente
- `src/hooks/useRoleSwitcher.js` - Hook para manejo de roles
- `src/router/PublicRoute.jsx` - Redirección multi-tenant
- `src/router/ProtectedRoute.jsx` - Autorización por rol
- `src/pages/admin/UsuariosPage.jsx` - Gestión de múltiples roles
- `src/auth/AuthContext.js` - Contexto actualizado
- `src/auth/axiosInterceptor.js` - Interceptores actualizados

---

## 🚀 Flujo de Funcionamiento

### **1. Login del Usuario**
1. Usuario accede a la aplicación
2. Sistema detecta cliente por hostname
3. Si usuario existe:
   - Verifica acceso al cliente actual
   - Si no tiene acceso → agrega como `usuario_final`
   - Si tiene acceso → determina rol activo
4. Emite JWT con información multi-tenant

### **2. Cambio de Rol**
1. Usuario selecciona nuevo rol en RoleSwitcher
2. Frontend llama a `/api/auth/cambiar-rol/`
3. Backend valida que el usuario tenga ese rol
4. Emite nuevos JWTs con el rol seleccionado
5. Frontend actualiza localStorage y recarga página

### **3. Autorización en Endpoints**
1. Request llega al endpoint
2. Helper function extrae rol del JWT
3. Se aplica lógica de autorización basada en rol actual
4. Se filtra data según permisos del rol

---

## ⚠️ Consideraciones Importantes

### **Compatibilidad Hacia Atrás**
- Sistema antiguo sigue funcionando
- Fallbacks en frontend y backend
- Migración gradual de datos existentes

### **Seguridad**
- Super admins no pueden ser creados via endpoints normales
- Validación de roles en cada endpoint
- JWTs contienen información mínima necesaria

### **Performance**
- Queries optimizadas con `select_related`
- Caché de roles en JWT
- Filtrado eficiente por cliente

### **Testing**
- Casos de prueba para múltiples roles
- Validación de permisos por rol
- Flujos de cambio de rol

---

## 🔄 Migración de Usuarios Existentes

### **Objetivo de la Migración**
Transformar usuarios del sistema monolítico (1 usuario = 1 cliente = 1 rol) al sistema multi-tenant (1 usuario = múltiples clientes = múltiples roles).

### **Estrategia de Migración**
1. **Preservar datos existentes** - No perder información
2. **Crear relaciones UserClient** - Mapear usuarios existentes
3. **Mantener compatibilidad** - Sistema híbrido durante transición
4. **Validación completa** - Verificar integridad de datos

---

## 📋 Script de Migración

### **1. Script Principal de Migración**

```python
# backend/scripts/migrate_users_to_multitenant.py
"""
Script para migrar usuarios existentes al sistema multi-tenant.
Convierte usuarios del sistema monolítico al nuevo sistema de roles múltiples.
"""

import os
import sys
import django
from django.db import transaction

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
```

### **2. Script de Verificación Post-Migración**

```python
# backend/scripts/verify_multitenant_migration.py
"""
Script para verificar la integridad de la migración multi-tenant.
Valida que todos los usuarios tengan sus relaciones UserClient correctas.
"""

import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.base')
django.setup()

from apps.auth_core.models import Usuario, UserClient
from apps.clientes_core.models import Cliente

def verify_migration_integrity():
    """
    Verifica la integridad completa de la migración.
    """
    
    print("🔍 VERIFICACIÓN DE INTEGRIDAD POST-MIGRACIÓN")
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
    success = verify_migration_integrity()
    if success:
        print("\n✅ Verificación exitosa - Migración completa")
    else:
        print("\n❌ Verificación falló - Revisar problemas")
```

### **3. Script de Rollback (En caso de problemas)**

```python
# backend/scripts/rollback_multitenant_migration.py
"""
Script para hacer rollback de la migración multi-tenant.
Elimina UserClients creados y restaura el sistema monolítico.
"""

import os
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.base')
django.setup()

from apps.auth_core.models import Usuario, UserClient

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

## 🚀 Proceso de Migración Paso a Paso

### **Paso 1: Preparación**

```bash
# 1. Hacer backup de la base de datos
pg_dump condor_db > backup_antes_migracion.sql

# 2. Verificar estado actual
python manage.py shell -c "
from apps.auth_core.models import Usuario, UserClient
print(f'Usuarios: {Usuario.objects.count()}')
print(f'UserClients: {UserClient.objects.count()}')
"
```

### **Paso 2: Ejecutar Migración**

```bash
# Ejecutar script de migración
cd backend
python scripts/migrate_users_to_multitenant.py
```

### **Paso 3: Verificar Migración**

```bash
# Verificar integridad
python scripts/verify_multitenant_migration.py

# Verificar en Django shell
python manage.py shell -c "
from apps.auth_core.models import Usuario, UserClient
for usuario in Usuario.objects.filter(is_super_admin=False)[:5]:
    userclients = UserClient.objects.filter(usuario=usuario, activo=True)
    print(f'{usuario.email}: {userclients.count()} roles')
    for uc in userclients:
        print(f'  - {uc.cliente.nombre}: {uc.rol}')
"
```

### **Paso 4: Testing Post-Migración**

```bash
# 1. Probar login
curl -X POST http://localhost:8080/api/auth/oauth/state/ \
  -H "Content-Type: application/json" \
  -d '{"host": "localhost", "return_to": "/"}'

# 2. Verificar JWT
# El JWT debe contener cliente_id y rol_en_cliente correctos

# 3. Probar endpoints
curl -H "Authorization: Bearer <token>" \
  http://localhost:8080/api/auth/yo/
```

---

## ⚠️ Consideraciones Importantes

### **Antes de la Migración**

1. **Backup completo** de la base de datos
2. **Verificar integridad** de datos existentes
3. **Testing en ambiente de desarrollo** primero
4. **Comunicar a usuarios** sobre posibles interrupciones

### **Durante la Migración**

1. **Ejecutar en horario de baja actividad**
2. **Monitorear logs** en tiempo real
3. **Tener plan de rollback** listo
4. **Validar cada paso** antes de continuar

### **Después de la Migración**

1. **Verificar funcionalidad** completa
2. **Probar login** de usuarios existentes
3. **Validar permisos** por rol
4. **Monitorear errores** por 24-48 horas

### **Casos Edge a Considerar**

1. **Usuarios sin cliente**: ¿Qué hacer con ellos?
2. **Usuarios con cliente_id inválido**: ¿Eliminar o asignar default?
3. **Roles inválidos**: ¿Mapear a usuario_final?
4. **Duplicados**: ¿Manejar conflictos de UserClient?

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

## 📈 Beneficios Obtenidos

1. **Flexibilidad**: Un usuario puede tener diferentes roles en diferentes clientes
2. **Escalabilidad**: Fácil agregar nuevos clientes y roles
3. **Seguridad**: Autorización granular por cliente y rol
4. **UX**: Role switcher intuitivo para cambio dinámico
5. **Mantenibilidad**: Código modular y bien estructurado

---

## 📝 Comentarios Agregados a Archivos

### **Backend - Comentarios Agregados:**

#### **`apps/auth_core/models.py`**
- **Header del archivo**: Descripción del sistema multi-tenant
- **Clase `Usuario`**: Documentación de funcionalidad multi-tenant
- **Clase `UserClient`**: Ejemplo práctico de uso (Juan en ClienteA y ClienteB)
- **Métodos**: Documentación detallada de cada función helper

#### **`apps/auth_core/utils.py`**
- **Header del archivo**: Propósito de utilidades multi-tenant
- **Función `get_rol_actual_del_jwt`**: Logs detallados para debugging

### **Frontend - Comentarios Agregados:**

#### **`src/components/layout/RoleSwitcher.jsx`**
- **Header del archivo**: Funcionalidad del componente y condiciones de uso
- **Lógica**: Comentarios sobre cambio dinámico de rol

#### **`src/hooks/useRoleSwitcher.js`**
- **Header del archivo**: Propósito del hook y flujo de trabajo
- **Funciones**: Documentación de llamadas al backend y actualización de estado

#### **`src/router/PublicRoute.jsx`**
- **Header del archivo**: Funcionalidad de redirección automática
- **Lógica**: Soporte para estructuras antigua y nueva

#### **`src/router/ProtectedRoute.jsx`**
- **Header del archivo**: Autorización por roles
- **Lógica**: Compatibilidad con sistemas antiguo y nuevo

### **Beneficios de los Comentarios:**

1. **Claridad**: Cada archivo tiene su propósito claramente definido
2. **Mantenibilidad**: Futuros desarrolladores entienden la lógica rápidamente
3. **Debugging**: Logs y comentarios facilitan la resolución de problemas
4. **Documentación**: El código se auto-documenta
5. **Onboarding**: Nuevos desarrolladores pueden entender el sistema rápidamente

---

## 🚀 PIPELINES MODULARES IMPLEMENTADOS

### **📋 Nuevos Pipelines de Deploy:**

**✅ 1. Backend Deploy** (`.github/workflows/backend-deploy.yml`)
- **Trigger:** Release `v*-backend` + manual dispatch
- **Build:** `condor-backend` + `condor-cron` → GHCR
- **Deploy:** Backend + Cron + DB + Redis (EC2)

**✅ 2. Frontend Padel Deploy** (`.github/workflows/frontend-padel-deploy.yml`)
- **Trigger:** Release `v*-frontend-padel` + manual dispatch
- **Build:** `condor-frontend` → GHCR
- **Deploy:** Frontend Padel (EC2)

**✅ 3. Frontend Canchas Deploy** (`.github/workflows/frontend-canchas-deploy.yml`)
- **Trigger:** Release `v*-frontend-canchas` + manual dispatch
- **Build:** `condor-frontend-canchas` → GHCR
- **Deploy:** Frontend Canchas (EC2)

**✅ 4. Frontend Medicina Deploy** (`.github/workflows/frontend-medicina-deploy.yml`)
- **Trigger:** Release `v*-frontend-medicina` + manual dispatch
- **Build:** `condor-frontend-medicina` → GHCR
- **Deploy:** Frontend Medicina (EC2)

**✅ 5. Frontend SuperAdmin Deploy** (`.github/workflows/frontend-superadmin-deploy.yml`)
- **Trigger:** Release `v*-frontend-superadmin` + manual dispatch
- **Build:** `condor-frontend-superadmin` → GHCR
- **Deploy:** Frontend SuperAdmin (EC2)

**✅ 6. Proxy Deploy** (`.github/workflows/proxy-deploy.yml`)
- **Trigger:** Release `v*-proxy` + manual dispatch
- **Build:** `condor-proxy` → GHCR
- **Deploy:** Proxy (EC2)

### **📋 Docker Compose Modulares Creados:**

**✅ Backend:**
- `docker-compose-backend-dev.yml` → Backend + Cron + DB + Redis (dev)
- `docker-compose-backend-prod.yml` → Backend + Cron + Redis (prod)

**✅ Frontend Padel:**
- `docker-compose-frontend-padel-dev.yml` → Frontend Padel (dev)
- `docker-compose-frontend-padel-prod.yml` → Frontend Padel (prod)

**✅ Frontend Canchas:**
- `docker-compose-frontend-canchas-dev.yml` → Frontend Canchas (dev)
- `docker-compose-frontend-canchas-prod.yml` → Frontend Canchas (prod)

**✅ Frontend Medicina:**
- `docker-compose-frontend-medicina-dev.yml` → Frontend Medicina (dev)
- `docker-compose-frontend-medicina-prod.yml` → Frontend Medicina (prod)

**✅ Frontend SuperAdmin:**
- `docker-compose-frontend-superadmin-dev.yml` → Frontend SuperAdmin (dev)
- `docker-compose-frontend-superadmin-prod.yml` → Frontend SuperAdmin (prod)

**✅ Proxy:**
- `docker-compose-proxy-dev.yml` → Proxy (dev)
- `docker-compose-proxy-prod.yml` → Proxy (prod)

### **🎯 Ventajas del Sistema Modular:**

**✅ Deploy Independiente:**
- Cada servicio se deploya por separado
- Solo se actualiza lo que cambió
- Rollback granular por servicio

**✅ Versionado Granular:**
- Tags específicos por servicio (`v1.0.0-backend`, `v1.0.0-frontend-padel`)
- Fácil identificación de versiones
- Trazabilidad completa

**✅ Mantiene Sistema Actual:**
- Workflows existentes se mantienen
- Docker Compose existentes se mantienen
- Migración gradual posible

**✅ Triggers Automáticos:**
- Release con tag específico → Deploy automático
- Workflow dispatch → Deploy manual
- Selectivo por servicio

### **🔧 Flujo de Deploy Modular:**

**1. Build (GitHub Actions):**
```bash
Release v1.0.0-backend → Build automático → Push GHCR
```

**2. Deploy (EC2 via SSH):**
```bash
appleboy/ssh-action → EC2 → docker compose up -d
```

**3. Health Checks:**
```bash
Esperar servicios healthy → Migraciones → Limpieza
```

### **📊 Archivos Creados/Modificados:**

**✅ Nuevos Pipelines (6):**
- `.github/workflows/backend-deploy.yml`
- `.github/workflows/frontend-padel-deploy.yml`
- `.github/workflows/frontend-canchas-deploy.yml`
- `.github/workflows/frontend-medicina-deploy.yml`
- `.github/workflows/frontend-superadmin-deploy.yml`
- `.github/workflows/proxy-deploy.yml`

**✅ Nuevos Docker Compose (12):**
- 6 archivos dev + 6 archivos prod

**✅ Sistema Actual Mantenido:**
- Workflows existentes → **SE MANTIENEN**
- Docker Compose existentes → **SE MANTIENEN**

---

## 🔧 Optimización Realizada: Eliminación de `get_rol_en_cliente`

### **Problema Identificado:**
El método `get_rol_en_cliente` retornaba un "rol principal" basado en prioridad arbitraria:
```python
priority_order = ['admin_cliente', 'empleado_cliente', 'usuario_final']
```

### **Problemas que Causaba:**
1. **Arbitrario**: No hay lógica de negocio clara para determinar el "rol principal"
2. **Confuso**: Un usuario con `usuario_final` y `admin_cliente` siempre retornaba `admin_cliente`
3. **Redundante**: `get_roles_en_cliente` ya proporciona toda la información necesaria

### **Solución Implementada:**
- ✅ **Eliminado** `get_rol_en_cliente` del modelo `Usuario`
- ✅ **Reemplazado** por lógica simple: `roles_en_cliente[0]` como rol inicial
- ✅ **Mantenido** `get_roles_en_cliente` que es más completo y flexible

### **Código Antes:**
```python
rol_en_cliente = user.get_rol_en_cliente(cliente_actual.id)  # ❌ Arbitrario
```

### **Código Después:**
```python
roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
rol_en_cliente = roles_en_cliente[0] if roles_en_cliente else "usuario_final"  # ✅ Simple
```

### **Beneficios:**
1. **Simplicidad**: Lógica más clara y directa
2. **Flexibilidad**: El usuario puede cambiar de rol fácilmente
3. **Consistencia**: Un solo método para obtener roles
4. **Mantenibilidad**: Menos código que mantener
