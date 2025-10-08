# 🎯 Fase 1: Multi-FE Básico - Implementación

## 📋 Objetivo
Implementar sistema multi-FE que permita servir diferentes frontends según el tipo de cliente, manteniendo un backend unificado y sistema de autenticación centralizado.

## 🏗️ Arquitectura de la Solución

### **Flujo de Funcionamiento:**
```
Usuario → Nginx → Backend (consulta DB) → Nginx (routing) → FE específico
```

### **Componentes a Implementar:**
1. **Modelo Cliente** - Campo `tipo_fe`
2. **Backend API** - Endpoint de configuración
3. **Nginx Dev** - Routing dinámico con Lua
4. **Docker Compose** - Múltiples containers FE
5. **OAuth** - Mismo Client ID, redirect dinámico
6. **Auth Compartido** - Módulo compartido entre FEs

## 📋 Pasos de Implementación

### **Paso 1: Modificar Modelo Cliente**
**Archivo:** `backend/apps/clientes_core/models.py`

**Cambios:**
```python
class Cliente(models.Model):
    TIPOS_FE = [
        ('padel', 'Frontend Profesores Padel'),
        ('canchas', 'Frontend Administración Canchas'),
        ('medicina', 'Frontend Medicina'),
        ('superadmin', 'Frontend Super Admin'),
    ]
    
    # ... campos existentes ...
    tipo_fe = models.CharField(
        max_length=50, 
        choices=TIPOS_FE, 
        default='padel',
        help_text="Define qué frontend usar para este cliente."
    )
```

**Migración:**
```bash
python manage.py makemigrations clientes_core
python manage.py migrate
```

### **Paso 2: Crear Endpoint de Configuración**
**Archivo:** `backend/apps/common/views.py`

**Nuevo endpoint:**
```python
class TenantConfigView(APIView):
    permission_classes = []
    
    def get(self, request):
        host = request.META.get('HTTP_X_TENANT_HOST') or request.get_host()
        
        try:
            dominio = ClienteDominio.objects.get(hostname=host, activo=True)
            cliente = dominio.cliente
            
            return Response({
                'cliente_id': cliente.id,
                'nombre_cliente': cliente.nombre,
                'tipo_cliente': cliente.tipo_cliente,
                'tipo_fe': cliente.tipo_fe,
                'color_primario': cliente.color_primario,
                'color_secundario': cliente.color_secundario,
                'oauth_redirect_uri': f'https://{host}/oauth/google/callback'
            })
        except ClienteDominio.DoesNotExist:
            return Response({'error': 'tenant_not_found'}, status=404)
```

**URL:**
```python
# backend/apps/common/urls.py
urlpatterns = [
    path('tenant/config/', TenantConfigView.as_view(), name='tenant-config'),
]
```

### **Paso 3: Modificar Nginx Dev**
**Archivo:** `reverse-proxy/nginx.ec2.dev.conf`

**Cambios:**
```nginx
# === Upstreams DEV ===
upstream frontend_padel_dev { server frontend_padel_dev:80; }
upstream frontend_canchas_dev { server frontend_canchas_dev:80; }
upstream frontend_medicina_dev { server frontend_medicina_dev:80; }
upstream frontend_superadmin_dev { server frontend_superadmin_dev:80; }
upstream backend_dev { server backend_condor_dev:8000; }

# === Routing por Tipo de FE ===
server {
    listen 8443 ssl http2;
    server_name ~^(?<tenant>[-a-z0-9]+)-dev\.cnd-ia\.com$;
    
    # API → backend (siempre)
    location /api/ {
        proxy_pass http://backend_dev;
        proxy_set_header X-TENANT-HOST $host;
    }
    
    # FE → según configuración en DB
    location / {
        # Preguntar al backend qué FE servir
        access_by_lua_block {
            local http = require "resty.http"
            local httpc = http.new()
            local res, err = httpc:request_uri("http://backend_dev:8000/api/tenant/config/", {
                method = "GET",
                headers = {
                    ["X-TENANT-HOST"] = ngx.var.host
                }
            })
            
            if res and res.status == 200 then
                local config = cjson.decode(res.body)
                ngx.var.fe_type = config.tipo_fe
            else
                ngx.var.fe_type = "padel"  # default
            end
        }
        
        # Routing por tipo de FE
        if ($fe_type = "canchas") {
            proxy_pass http://frontend_canchas_dev;
        }
        if ($fe_type = "medicina") {
            proxy_pass http://frontend_medicina_dev;
        }
        if ($fe_type = "superadmin") {
            proxy_pass http://frontend_superadmin_dev;
        }
        # default: padel
        proxy_pass http://frontend_padel_dev;
    }
}
```

### **Paso 4: Modificar Docker Compose Dev**
**Archivo:** `docker-compose-dev.yml`

**Cambios:**
```yaml
services:
  frontend_padel_dev:
    image: ghcr.io/${OWNER}/${IMAGE_PREFIX}-frontend-padel:${FRONTEND_TAG_DEV}
    container_name: frontend_padel_dev
    env_file: [ .env.dev ]
    environment:
      PUBLIC_API_BASE_URL: ${PUBLIC_API_BASE_URL}
      PUBLIC_GOOGLE_CLIENT_ID: ${PUBLIC_GOOGLE_CLIENT_ID}
      PUBLIC_OAUTH_REDIRECT_URI: ${PUBLIC_OAUTH_REDIRECT_URI}
    networks: [condor_net_dev]
    
  frontend_canchas_dev:
    image: ghcr.io/${OWNER}/${IMAGE_PREFIX}-frontend-canchas:${FRONTEND_TAG_DEV}
    container_name: frontend_canchas_dev
    env_file: [ .env.dev ]
    environment:
      PUBLIC_API_BASE_URL: ${PUBLIC_API_BASE_URL}
      PUBLIC_GOOGLE_CLIENT_ID: ${PUBLIC_GOOGLE_CLIENT_ID}
      PUBLIC_OAUTH_REDIRECT_URI: ${PUBLIC_OAUTH_REDIRECT_URI}
    networks: [condor_net_dev]
    
  frontend_medicina_dev:
    image: ghcr.io/${OWNER}/${IMAGE_PREFIX}-frontend-medicina:${FRONTEND_TAG_DEV}
    container_name: frontend_medicina_dev
    env_file: [ .env.dev ]
    environment:
      PUBLIC_API_BASE_URL: ${PUBLIC_API_BASE_URL}
      PUBLIC_GOOGLE_CLIENT_ID: ${PUBLIC_GOOGLE_CLIENT_ID}
      PUBLIC_OAUTH_REDIRECT_URI: ${PUBLIC_OAUTH_REDIRECT_URI}
    networks: [condor_net_dev]
    
  frontend_superadmin_dev:
    image: ghcr.io/${OWNER}/${IMAGE_PREFIX}-frontend-superadmin:${FRONTEND_TAG_DEV}
    container_name: frontend_superadmin_dev
    env_file: [ .env.dev ]
    environment:
      PUBLIC_API_BASE_URL: ${PUBLIC_API_BASE_URL}
      PUBLIC_GOOGLE_CLIENT_ID: ${PUBLIC_GOOGLE_CLIENT_ID}
      PUBLIC_OAUTH_REDIRECT_URI: ${PUBLIC_OAUTH_REDIRECT_URI}
    networks: [condor_net_dev]
```

### **Paso 5: Crear FEs Adicionales**
**Estructura:**
```
frontend-canchas/
├── src/
│   ├── pages/
│   ├── components/
│   └── config/
├── docker/
│   ├── Dockerfile
│   └── nginx.conf
└── package.json

frontend-medicina/
├── src/
│   ├── pages/
│   ├── components/
│   └── config/
├── docker/
│   ├── Dockerfile
│   └── nginx.conf
└── package.json

frontend-superadmin/
├── src/
│   ├── pages/
│   ├── components/
│   └── config/
├── docker/
│   ├── Dockerfile
│   └── nginx.conf
└── package.json
```

### **Paso 6: Implementar Auth Compartido**
**Estructura:**
```
shared-auth/                 # Módulo compartido
├── src/
│   ├── auth/
│   │   ├── AuthContext.js
│   │   ├── oauthClient.js
│   │   ├── axiosInterceptor.js
│   │   └── pkce.js
│   └── components/
│       ├── LoginForm.jsx
│       ├── OAuthCallback.jsx
│       └── AuthLayout.jsx
├── package.json
└── README.md
```

**Configuración por FE:**
```javascript
// frontend-padel/src/config/auth.js
export const authConfig = {
  redirectAfterLogin: '/padel-dashboard',
  branding: 'padel',
  permissions: ['padel_profesor', 'padel_admin']
};

// frontend-canchas/src/config/auth.js
export const authConfig = {
  redirectAfterLogin: '/canchas-dashboard',
  branding: 'canchas',
  permissions: ['canchas_admin']
};
```

**Dependencias:**
```json
// frontend-padel/package.json
{
  "dependencies": {
    "shared-auth": "file:../shared-auth"
  }
}
```

### **Paso 7: Configurar OAuth Compartido**
**Google Console:**
```
Authorized redirect URIs:
- https://*.cnd-ia.com/oauth/google/callback
- https://*-dev.cnd-ia.com/oauth/google/callback
```

**Variables de entorno:**
```bash
# .env.dev
PUBLIC_GOOGLE_CLIENT_ID=your-shared-client-id
PUBLIC_OAUTH_REDIRECT_URI=https://distrito-padel-dev.cnd-ia.com/oauth/google/callback
```

## 🧪 Testing

### **Test 1: Cliente Padel (Existente)**
```
https://lob-padel-dev.cnd-ia.com
→ Debe servir frontend-padel
→ OAuth debe funcionar
→ Configuración debe cargar correctamente
```

### **Test 2: Cliente Canchas (Nuevo)**
```
https://canchas-padel-dev.cnd-ia.com
→ Debe servir frontend-canchas
→ OAuth debe funcionar
→ Configuración debe cargar correctamente
```

### **Test 3: Cliente Medicina (Futuro)**
```
https://medicina-dev.cnd-ia.com
→ Debe servir frontend-medicina
→ OAuth debe funcionar
→ Configuración debe cargar correctamente
```

### **Test 4: SuperAdmin**
```
https://admin-dev.cnd-ia.com
→ Debe servir frontend-superadmin
→ OAuth debe funcionar
→ Configuración debe cargar correctamente
```

## ✅ Criterios de Éxito

### **Funcionalidad:**
- ✅ Routing dinámico funcional
- ✅ Múltiples FEs operativos
- ✅ OAuth compartido funcional
- ✅ Configuración dinámica por hostname
- ✅ Auth compartido entre FEs

### **Performance:**
- ✅ Tiempo de respuesta < 2s
- ✅ Cache de configuración funcional
- ✅ Sin errores 404 en routing

### **Mantenibilidad:**
- ✅ Código limpio y documentado
- ✅ Logs claros para debugging
- ✅ Fácil agregar nuevos FEs

## 🚨 Riesgos y Mitigaciones

### **Riesgo 1: Nginx Lua no disponible**
**Mitigación:** Implementar routing en backend como fallback

### **Riesgo 2: OAuth redirects incorrectos**
**Mitigación:** Validar configuración en cada FE

### **Riesgo 3: Performance degradada**
**Mitigación:** Cache de configuración en nginx

## 📝 Notas de Implementación

### **Orden de Implementación:**
1. Modelo y migración
2. Backend API
3. Auth compartido
4. Nginx routing
5. Docker compose
6. FEs adicionales
7. OAuth compartido
8. Testing

### **Rollback Plan:**
- Mantener configuración actual como fallback
- Revertir nginx a configuración simple
- Deshabilitar routing dinámico si falla

---

**Estado:** En desarrollo
**Última actualización:** 2024-01-XX
**Próximo paso:** Implementar modelo Cliente
