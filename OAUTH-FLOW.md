# OAuth Flow Centralizado - Condor Multi-Tenant

## 🎯 **Arquitectura OAuth Centralizada**

Utilizamos un **OAuth centralizado** con `auth-dev.cnd-ia.com` como punto único de callback para todos los clientes.

### **Ventajas:**
- ✅ Un solo Client ID en Google Console
- ✅ Un solo dominio para configurar
- ✅ Fácil gestión de múltiples clientes
- ✅ No necesitas agregar cada cliente a Google Console

### **Desventajas:**
- ❌ Una redirección extra (auth-dev → cliente)
- ❌ Dependencia de un dominio central

---

## 🔄 **Flujo Completo de Autenticación**

### **1. 👤 Usuario accede a URL**
```
Usuario: https://padel-dev.cnd-ia.com/login
```

### **2. 🌐 EC2 recibe el request**
```
EC2: Recibe GET https://padel-dev.cnd-ia.com/login
```

### **3. 🔀 Reverse Proxy (Nginx)**
```
Nginx: Escucha en puerto 443, ve que es padel-dev.cnd-ia.com
Nginx: Pregunta al backend "¿Qué FE sirvo?"
Backend: "tipo_fe: padel"
Nginx: Redirige a frontend_padel_dev
```

### **4. 🎨 Frontend responde**
```
Frontend: Sirve la SPA de Padel con botón "Login con Google"
```

### **5. 🔐 Usuario hace click en "Login con Google"**
```
Frontend: Redirige a Google OAuth con:
- client_id: 123456789-abc123.apps.googleusercontent.com
- redirect_uri: https://auth-dev.cnd-ia.com/oauth/google/callback
- state: {host: "padel-dev.cnd-ia.com", code_verifier: "xyz123"}
```

### **6. 🌍 Google OAuth**
```
Google: Usuario se autentica
Google: Redirige a: https://auth-dev.cnd-ia.com/oauth/google/callback?code=ABC123&state=xyz
```

### **7. 🔀 Reverse Proxy (Nginx) - OAuth Callback**
```
Nginx: Ve que es auth-dev.cnd-ia.com/oauth/google/callback
Nginx: Redirige a backend_dev:8000/api/auth/oauth/callback/
```

### **8. 🧮 Backend procesa OAuth**
```
Backend: Recibe code=ABC123 y state=xyz
Backend: Valida el state (contiene host original)
Backend: Intercambia code por tokens con Google usando:
- client_id: 123456789-abc123.apps.googleusercontent.com
- client_secret: [SECRET]
- code: ABC123
- redirect_uri: https://auth-dev.cnd-ia.com/oauth/google/callback
```

### **9. 🔄 Backend redirige al cliente original**
```
Backend: Redirige a https://padel-dev.cnd-ia.com/oauth/google/callback?code=ABC123&state=xyz
```

### **10. 🎨 Frontend completa el login**
```
Frontend: Recibe code y state
Frontend: Hace POST a backend con code + code_verifier
Backend: Valida y crea JWT
Frontend: Usuario logueado
```

---

## 🔑 **Configuración Google Console**

### **Authorized JavaScript Origins:**
```
https://padel-dev.cnd-ia.com
https://canchas-dev.cnd-ia.com
https://medicina-dev.cnd-ia.com
https://superadmin-dev.cnd-ia.com
https://auth-dev.cnd-ia.com
```

### **Authorized Redirect URIs:**
```
https://auth-dev.cnd-ia.com/oauth/google/callback
```

**⚠️ IMPORTANTE:** Solo necesitas un Redirect URI porque usas OAuth centralizado.

---

## 🏗️ **Configuración Nginx**

### **Dominio Centralizado (auth-dev.cnd-ia.com):**
```nginx
server {
    server_name auth-dev.cnd-ia.com;
    
    # API → backend_dev
    location /api/ {
        proxy_pass http://backend_dev;
    }
    
    # OAuth Callback → backend_dev
    location = /oauth/google/callback {
        proxy_pass http://backend_dev/api/auth/oauth/callback/;
    }
    
    # Todo lo demás → frontend_dev
    location / {
        proxy_pass http://frontend_dev;
    }
}
```

### **Dominios de Clientes (padel-dev.cnd-ia.com):**
```nginx
server {
    server_name ~^(?<tenant>[-a-z0-9]+)-dev\.cnd-ia\.com$;
    
    # API → backend_dev
    location /api/ {
        proxy_pass http://backend_dev;
    }
    
    # OAuth Callback → frontend_dev (el frontend maneja el intercambio)
    location = /oauth/google/callback {
        proxy_pass http://frontend_padel_dev;
    }
    
    # FE → según configuración en DB (routing dinámico)
    location / {
        # Pregunta al backend qué FE servir
        access_by_lua_block {
            # Hace request a backend_dev:8000/api/tenant/config/
            # Obtiene el tipo_fe del cliente
        }
        
        # Routing por tipo de FE
        if ($fe_type = "canchas") {
            proxy_pass http://frontend_canchas_dev;
        }
        if ($fe_type = "medicina") {
            proxy_pass http://frontend_medicina_dev;
        }
        # default: padel
        proxy_pass http://frontend_padel_dev;
    }
}
```

---

## ⚠️ **PROBLEMA IDENTIFICADO Y SOLUCIONADO**

### **🔍 El Problema:**
En la configuración actual, el **TENANTS DEV server block** estaba enviando el OAuth callback al **backend** en lugar del **frontend**:

```nginx
# ❌ CONFIGURACIÓN INCORRECTA (causaba loop infinito)
location = /oauth/google/callback {
  proxy_pass http://backend_dev/api/auth/oauth/callback/;  # ← BACKEND
}
```

### **🔄 ¿Por qué causaba loop infinito?**
1. **Usuario** hace login → Google OAuth
2. **Google** redirige a → `https://auth-dev.cnd-ia.com/oauth/google/callback`
3. **AUTH DEV server** → `proxy_pass http://backend_dev/api/auth/oauth/callback/`
4. **Backend** procesa callback → redirige a → `https://padel-dev.cnd-ia.com/oauth/google/callback`
5. **TENANTS DEV server** → `proxy_pass http://backend_dev/api/auth/oauth/callback/` ❌
6. **Backend** recibe el callback de nuevo → redirige a → `https://padel-dev.cnd-ia.com/oauth/google/callback`
7. **Loop infinito** 🔄

### **✅ La Solución:**
El **TENANTS DEV server block** debe enviar el OAuth callback al **frontend** para que maneje el intercambio:

```nginx
# ✅ CONFIGURACIÓN CORRECTA
location = /oauth/google/callback {
  proxy_pass http://frontend_padel_dev;  # ← FRONTEND
}
```

### **🎯 ¿Por qué funciona así?**
- **AUTH DEV server**: OAuth callback → Backend (procesa el callback inicial)
- **TENANTS DEV server**: OAuth callback → Frontend (maneja el intercambio del token)
- **Frontend**: Tiene la lógica para procesar el OAuth callback y completar el login

### **📋 Flujo Correcto:**
1. **Usuario** hace login → Google OAuth
2. **Google** redirige a → `https://auth-dev.cnd-ia.com/oauth/google/callback`
3. **AUTH DEV server** → `proxy_pass http://backend_dev/api/auth/oauth/callback/`
4. **Backend** procesa callback → redirige a → `https://padel-dev.cnd-ia.com/oauth/google/callback`
5. **TENANTS DEV server** → `proxy_pass http://frontend_padel_dev`
6. **Frontend** recibe callback → procesa el token → usuario logueado ✅

---

## 🔧 **Configuración Backend**

### **OAuth Callback View:**
```python
class OAuthCallbackView:
    def get(self, request):
        # 1. Recibe code y state de Google
        # 2. Valida el state (contiene el host original)
        # 3. Extrae el host original del state
        # 4. Redirige de vuelta al cliente original
        
        host = state.get("host")  # ej: "padel-dev.cnd-ia.com"
        redirect_url = f"https://{host}/oauth/google/callback?code={code}&state={state}"
        return Response(status=302, headers={"Location": redirect_url})
```

### **Tenant Config Endpoint:**
```python
@api_view(['GET'])
@permission_classes([AllowAny])
def tenant_config(request):
    """
    Endpoint para obtener la configuración del tenant basada en el hostname.
    Usado por el frontend para determinar qué tipo de FE servir.
    """
    hostname = request.META.get('HTTP_X_TENANT_HOST', request.META.get('HTTP_HOST', ''))
    
    try:
        cliente_dominio = ClienteDominio.objects.select_related('cliente').get(
            hostname=hostname,
            activo=True
        )
        
        cliente = cliente_dominio.cliente
        
        return JsonResponse({
            'tipo_fe': cliente.tipo_fe,
            'nombre': cliente.nombre,
            'tipo_cliente': cliente.tipo_cliente,
            'theme': cliente.theme,
            'color_primario': cliente.color_primario,
            'color_secundario': cliente.color_secundario,
            'hostname': hostname
        })
        
    except ClienteDominio.DoesNotExist:
        return JsonResponse({
            'tipo_fe': 'padel',  # default
            'nombre': 'Condor',
            'tipo_cliente': 'padel',
            'theme': 'classic',
            'color_primario': '#F44336',
            'color_secundario': '#000000',
            'hostname': hostname,
            'default': True
        })
```

---

## 🎯 **Flujo de Decisión del Reverse Proxy**

```
Request → Nginx → ¿Es /api/? → Backend
                → ¿Es /oauth/? → Backend  
                → ¿Es /? → Pregunta Backend → Frontend
```

### **Variables que maneja:**
- `$host` - El hostname del request
- `$fe_type` - Tipo de frontend (padel, canchas, medicina)
- `$tenant` - Nombre del tenant extraído del hostname

---

## 📋 **Estándares OAuth 2.0 que Seguimos**

### **✅ Estándar OAuth 2.0 Authorization Code Flow:**
1. **Authorization Request** - Usuario redirige a Google
2. **Authorization Response** - Google redirige con código
3. **Token Request** - Cliente intercambia código por token
4. **Token Response** - Google devuelve access_token

### **🎯 Nuestra Implementación:**
```
1. Usuario → Google OAuth (Authorization Request)
2. Google → auth-dev.cnd-ia.com/oauth/google/callback (Authorization Response)
3. Backend → Procesa callback y redirige al cliente
4. Frontend → Intercambia código por token (Token Request)
5. Frontend → Usuario logueado (Token Response)
```

### **🔑 Componentes OAuth:**
- **Authorization Server**: Google OAuth 2.0
- **Client**: Nuestra aplicación (frontend + backend)
- **Resource Owner**: Usuario final
- **Redirect URI**: `https://auth-dev.cnd-ia.com/oauth/google/callback`

### **🛡️ Seguridad:**
- ✅ **PKCE (Proof Key for Code Exchange)** - Protege contra ataques
- ✅ **State parameter** - Previene CSRF
- ✅ **HTTPS** - Comunicación segura
- ✅ **JWT tokens** - Autenticación stateless

---

## 💡 **Ventajas del OAuth Centralizado**

1. **Un solo Client ID** - fácil de gestionar
2. **Un solo dominio** en Google Console
3. **Fácil agregar clientes** - solo necesitas:
   - Agregar el cliente a la DB
   - Configurar el DNS
   - **NO tocar Google Console**
4. **Consistencia** - todos usan el mismo flujo

---

## 🔍 **Verificación del Flujo**

### **1. Usuario accede a cliente:**
```
https://padel-dev.cnd-ia.com → Frontend Padel
https://canchas-dev.cnd-ia.com → Frontend Canchas
```

### **2. Login redirige a Google:**
```
Google OAuth → auth-dev.cnd-ia.com/oauth/google/callback
```

### **3. Backend procesa y redirige:**
```
Backend → https://padel-dev.cnd-ia.com/oauth/google/callback
```

### **4. Frontend completa login:**
```
Frontend → Usuario logueado
```

---

## 📋 **Checklist de Implementación**

- [ ] Configurar Google Console con dominios
- [ ] Configurar Nginx con routing dinámico
- [ ] Implementar tenant_config endpoint
- [ ] Configurar OAuth centralizado
- [ ] Probar flujo completo
- [ ] Verificar redirecciones
- [ ] Validar autenticación

---

## 🚀 **Próximos Pasos**

1. **Fase 1**: Multi-FE Básico (Sin Automatización)
2. **Fase 2**: OAuth Compartido ✅
3. **Fase 3**: Automatización Básica
4. **Fase 4**: Automatización Completa
