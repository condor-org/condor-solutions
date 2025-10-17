# 🔍 Multi-Tenant Client Detection Flow

## 📋 Resumen Ejecutivo

El sistema detecta automáticamente el cliente basado en el puerto de acceso y filtra todos los datos para mostrar únicamente la información de ese cliente específico.

**Puerto 8080**: Lucas Padel (Cliente ID: 1)  
**Puerto 8081**: Distrito Padel (Cliente ID: 4)

---

## 🏗️ Arquitectura del Sistema

```
Usuario → Nginx Proxy → Backend Django → TenantMiddleware → Views → Datos Filtrados
```

### Componentes Involucrados

1. **Nginx Reverse Proxy** - Envía header identificador
2. **TenantMiddleware** - Detecta cliente por header
3. **ClienteDominio** - Mapeo hostname → cliente
4. **Views** - Filtran datos por cliente

---

## 1️⃣ Configuración Nginx (Punto de Entrada)

### Puerto 8080 - Lucas Padel

```nginx
# reverse-proxy/nginx.local.conf
server {
  listen 8080;
  server_name localhost;
  
  location /api/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    
    # 🔑 HEADER CLAVE PARA MULTI-TENANT
    proxy_set_header X-Tenant-Host "lucas.localhost";
    
    # Headers básicos
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

### Puerto 8081 - Distrito Padel

```nginx
# reverse-proxy/nginx.local.conf
server {
  listen 8081;
  server_name localhost;
  
  location /api/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    
    # 🔑 HEADER CLAVE PARA MULTI-TENANT
    proxy_set_header X-Tenant-Host "distrito.localhost";
    
    # Headers básicos
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

**🎯 Resultado**: Cada puerto envía un header diferente que identifica el cliente.

---

## 2️⃣ Configuración Base de Datos

### Mapeo de Dominios

```sql
-- Tabla: cliente_dominio
hostname              | cliente_id | activo
---------------------|------------|--------
localhost             | 1          | true
127.0.0.1            | 1          | true  
lucas.localhost       | 1          | true
distrito.localhost    | 4          | true
```

### Verificación en Django Shell

```python
# backend/apps/clientes_core/models.py
from apps.clientes_core.models import ClienteDominio, Cliente

# Verificar configuración
for dominio in ClienteDominio.objects.select_related('cliente').all():
    print(f'Hostname: {dominio.hostname} → Cliente: {dominio.cliente.nombre} (ID: {dominio.cliente_id})')
```

**Salida esperada:**
```
Hostname: localhost → Cliente: Lucas Padel (ID: 1)
Hostname: 127.0.0.1 → Cliente: Lucas Padel (ID: 1)
Hostname: lucas.localhost → Cliente: Lucas Padel (ID: 1)
Hostname: distrito.localhost → Cliente: Distrito Padel (ID: 4)
```

---

## 3️⃣ TenantMiddleware - Detección del Cliente

### Función Principal

```python
# backend/condor_core/tenant.py
class TenantMiddleware:
    def __call__(self, request):
        # 1. Extraer host del header
        host = self._get_request_host(request)
        
        # 2. Log para debugging
        log.info("[TENANT] request_host=%s X-Tenant-Host=%s HTTP_HOST=%s", 
                host, 
                request.META.get("HTTP_X_TENANT_HOST", "N/A"),
                request.META.get("HTTP_HOST", "N/A"))
        
        # 3. Buscar cliente en DB
        cliente = self._resolve_cliente(host)
        
        # 4. Asignar a request
        request.cliente_actual = cliente
        
        return self.get_response(request)
```

### Extracción del Host

```python
# backend/condor_core/tenant.py
def _get_request_host(self, request) -> str:
    """
    Toma el host desde el header del proxy si está habilitado (confiable),
    si no, cae a request.get_host().
    """
    if self.trust_proxy:
        # Prioridad: Header X-Tenant-Host del proxy
        host = request.META.get("HTTP_X_TENANT_HOST") or request.META.get("HTTP_HOST")
        if host:
            return self._normalize_host(host)
    # Fallback: Host directo del request
    return self._normalize_host(request.get_host())

def _normalize_host(self, host: str) -> str:
    """
    Normaliza: lower, sin puerto, punycode → unicode seguro, sin espacios.
    """
    if not host:
        return ""
    host = host.split(":")[0].strip().lower()
    try:
        # soporta IDN (por si acaso)
        host = idna.decode(idna.encode(host))
    except Exception:
        pass
    return host
```

**🎯 Lógica:**
1. **Si `trust_proxy=True`**: Usa `HTTP_X_TENANT_HOST` (del Nginx)
2. **Si no hay header**: Usa `HTTP_HOST` (directo)
3. **Normaliza**: lowercase, sin puerto, sin espacios

---

## 4️⃣ Resolución de Cliente (DB Lookup)

### Función de Resolución

```python
# backend/condor_core/tenant.py
def _resolve_cliente(self, host: str):
    """
    Resuelve cliente por host con cache.
    Devuelve instancia de Cliente o None.
    """
    if not host:
        return None

    # 1. Buscar en cache
    cache_key = f"tenant:host:{host}"
    cached = cache.get(cache_key)
    
    if cached is not None:
        # cached puede ser cliente_id (int) o -1 para "no encontrado"
        if cached == -1:
            return None
        try:
            return Cliente.objects.only("id").get(id=cached)
        except Cliente.DoesNotExist:
            # Evitar bucle si alguien borró cliente: invalidar y seguir a DB
            cache.delete(cache_key)

    # 2. Buscar en DB
    try:
        dom = (
            ClienteDominio.objects
            .select_related("cliente")
            .only("id", "hostname", "activo", "cliente__id")
            .get(hostname=host, activo=True)
        )
        cliente_id = dom.cliente_id
        # 3. Cachear resultado (5 minutos)
        cache.set(cache_key, cliente_id, self.cache_ttl)
        return dom.cliente
    except ClienteDominio.DoesNotExist:
        # Cachear "no existe" para evitar consultas repetidas
        cache.set(cache_key, -1, self.cache_ttl)
        return None
```

**🗄️ Lógica de Resolución:**
1. **Cache**: Busca primero en cache (5 min TTL)
2. **DB**: Si no está en cache, busca en `ClienteDominio`
3. **Resultado**: Retorna `Cliente` o `None`
4. **Cache**: Guarda resultado para futuras consultas

---

## 5️⃣ Uso en Views (Filtrado de Datos)

### OAuthStateView - Generación de State

```python
# backend/apps/auth_core/views.py
class OAuthStateView(APIView):
    def post(self, request):
        # Usar el cliente detectado por el TenantMiddleware
        cliente_actual = getattr(request, 'cliente_actual', None)
        if not cliente_actual:
            logger.warning(f"[OAUTH STATE] no_cliente_actual host={host}")
            return Response({"detail": "cliente_not_resolved"}, status=400)
        
        cliente_id = cliente_actual.id
        logger.info(f"[OAUTH STATE] using_tenant_cliente host={host} cliente_id={cliente_id} cliente_nombre={cliente_actual.nombre}")
        
        # Generar state con cliente correcto
        payload = {
            "v": 1,
            "nonce": nonce,
            "host": host,
            "return_to": return_to,
            "cliente_id": cliente_id,  # ✅ Cliente correcto
        }
```

### SedePadelViewSet - Filtrado de Sedes

```python
# backend/apps/turnos_padel/views.py
class SedePadelViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Super admin (usar nuevo campo)
        if user.is_super_admin:
            return Lugar.objects.all()
        # Admin del cliente → sedes de su cliente
        elif cliente_actual:
            return Lugar.objects.filter(cliente=cliente_actual)
        return Lugar.objects.none()
```

### AbonoMesViewSet - Filtrado de Abonos

```python
# backend/apps/turnos_padel/views.py
class AbonoMesViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Super admin → todos los abonos
        if user.is_super_admin:
            qs = AbonoMes.objects.all()
        # Admin del cliente → abonos de su cliente
        elif rol_actual == "admin_cliente" and cliente_actual:
            qs = AbonoMes.objects.filter(sede__cliente_id=cliente_actual.id)
        # Usuario final → sus propios abonos DEL CLIENTE ACTUAL
        else:
            if cliente_actual:
                qs = AbonoMes.objects.filter(usuario=user, sede__cliente_id=cliente_actual.id)
            else:
                qs = AbonoMes.objects.filter(usuario=user)
        return qs
```

### ComprobanteView - Filtrado de Comprobantes

```python
# backend/apps/pagos_core/views.py
class ComprobanteView(ListCreateAPIView):
    def get_queryset(self):
        usuario = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Super admin (usar nuevo campo)
        if usuario.is_super_admin:
            pass
        # Admin del cliente → comprobantes de su cliente
        elif cliente_actual:
            qs = qs.filter(cliente=cliente_actual)
        # Empleado/usuario final → solo sus propios comprobantes
        else:
            qs = qs.filter(turno__usuario=usuario)
        return qs
```

### TurnoListView - Filtrado de Turnos

```python
# backend/apps/turnos_core/views.py
class TurnoListView(ListAPIView):
    def get_queryset(self):
        usuario = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Super admin ve todo
        if usuario.is_super_admin:
            qs = Turno.objects.all().select_related("usuario", "lugar")
        
        # Admin del cliente → TODOS los turnos de su cliente
        elif rol_actual == "admin_cliente" and cliente_actual:
            qs = (
                Turno.objects
                .filter(lugar__cliente_id=cliente_actual.id)  # ✅ Filtrado por cliente
                .select_related("usuario", "lugar")
            )
        
        # Usuario final → sus propios turnos
        else:
            qs = Turno.objects.filter(usuario=usuario).select_related("usuario", "lugar")
        
        return qs
```

### MiPerfilView - Información del Usuario

```python
# backend/apps/auth_core/views.py
class MiPerfilView(APIView):
    def get(self, request):
        user = request.user
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        # Información del cliente actual
        cliente_actual_info = None
        if cliente_actual:
            roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
            rol_en_cliente = roles_en_cliente[0] if roles_en_cliente else "usuario_final"
            
            cliente_actual_info = {
                "id": cliente_actual.id,
                "nombre": cliente_actual.nombre,
                "rol": rol_en_cliente,
                "roles": roles_en_cliente,
                "tipo_cliente": cliente_actual.tipo_cliente,
                "tipo_fe": getattr(cliente_actual, 'tipo_fe', cliente_actual.tipo_cliente),
            }
        
        data = {
            "id": user.id,
            "email": user.email,
            "is_super_admin": user.is_super_admin,
            "cliente_actual": cliente_actual_info,  # ✅ Solo cliente actual
            # Backward compatibility
            "tipo_usuario": getattr(user, "tipo_usuario", None),
            "cliente_id": getattr(user, "cliente_id", None),
        }
        return Response(data)
```

---

## 6️⃣ Flow Completo en Acción

### Request: `localhost:8081/api/auth/yo/`

#### Paso 1: Nginx
```nginx
# Puerto 8081
proxy_set_header X-Tenant-Host "distrito.localhost";
```

#### Paso 2: TenantMiddleware
```python
# request.META["HTTP_X_TENANT_HOST"] = "distrito.localhost"
host = "distrito.localhost"
cliente = ClienteDominio.objects.get(hostname="distrito.localhost").cliente
# cliente = Cliente(id=4, nombre="Distrito Padel")
request.cliente_actual = cliente
```

#### Paso 3: View
```python
cliente_actual = request.cliente_actual  # Cliente(id=4)
# Filtrar datos solo de Distrito Padel
turnos = Turno.objects.filter(lugar__cliente=cliente_actual)
```

### Logs Esperados

```
[TENANT] request_host=distrito.localhost X-Tenant-Host=distrito.localhost HTTP_HOST=localhost
[OAUTH STATE] using_tenant_cliente host=localhost cliente_id=4 cliente_nombre=Distrito Padel
```

---

## 7️⃣ Verificación y Testing

### Comando de Verificación

```bash
# Request a puerto 8081 (Distrito Padel)
curl -s "http://localhost:8081/api/auth/yo/" -H "Authorization: Bearer fake-token"

# Debería mostrar en logs:
# [TENANT] request_host=distrito.localhost X-Tenant-Host=distrito.localhost
```

### Verificación de Configuración

```bash
# Verificar configuración de dominios
docker compose -f docker-compose-local.yml exec backend python manage.py shell -c "
from apps.clientes_core.models import ClienteDominio
for d in ClienteDominio.objects.all():
    print(f'{d.hostname} → Cliente {d.cliente_id}')
"
```

---

## 8️⃣ Puntos Clave del Sistema

### ✅ Lo que funciona correctamente

1. **Nginx**: Envía headers correctos por puerto
2. **TenantMiddleware**: Detecta cliente correctamente
3. **Cache**: Mejora rendimiento (5 min TTL)
4. **Views**: Filtran datos por cliente

### 🔧 Configuración crítica

1. **Headers Nginx**: `X-Tenant-Host` debe coincidir con DB
2. **ClienteDominio**: Mapeo hostname → cliente_id
3. **Cache**: TTL de 5 minutos para rendimiento
4. **Views**: Siempre usar `request.cliente_actual`

### 🚨 Puntos de falla

1. **Header faltante**: Si Nginx no envía `X-Tenant-Host`
2. **Mapeo incorrecto**: Si `ClienteDominio` no existe
3. **Cache corrupto**: Si cliente se elimina de DB
4. **View sin filtro**: Si view no usa `cliente_actual`

---

## 9️⃣ Resumen del Flow

```
1. Usuario → localhost:8081
2. Nginx → X-Tenant-Host: "distrito.localhost"
3. TenantMiddleware → host = "distrito.localhost"
4. DB Lookup → ClienteDominio.get(hostname="distrito.localhost")
5. Resultado → Cliente(id=4, nombre="Distrito Padel")
6. Asignación → request.cliente_actual = cliente
7. View → Filtrar datos por cliente_actual
8. Respuesta → Solo datos de Distrito Padel
```

**🎯 Resultado**: El sistema sirve únicamente la información del cliente detectado por puerto, garantizando aislamiento completo entre clientes.

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
