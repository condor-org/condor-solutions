# OAuth 2.0 Flow - Condor

## 📋 **Resumen del Flow**

Este documento describe el flujo completo de OAuth 2.0 con PKCE (Proof Key for Code Exchange) implementado en Condor, tanto para DEV como PROD.

## 🔄 **Flow Completo de OAuth**

### **1. Usuario inicia login**
```
Usuario → https://padel-dev.cnd-ia.com/login
```

### **2. Frontend solicita información OAuth al Backend**
```
Frontend → POST /api/auth/oauth/state/
Backend → responde con:
  - client_id: Identificador del cliente OAuth en Google
  - redirect_uri: URL donde Google redirigirá después del login
  - state: JWT firmado con información del tenant
  - code_challenge: Hash SHA256 del code_verifier (PKCE)
  - code_challenge_method: "S256"
```

### **3. Frontend construye URL y redirige a Google**
```
Frontend → https://accounts.google.com/oauth/authorize?
  client_id=...
  redirect_uri=https://padel-dev.cnd-ia.com/oauth/google/callback
  state=... (JWT del backend)
  code_challenge=... (PKCE)
  code_challenge_method=S256
  response_type=code
  scope=openid email profile
```

### **4. Google redirige de vuelta**
```
Google → https://padel-dev.cnd-ia.com/oauth/google/callback?code=...&state=...
```

### **5. Proxy Nginx (Configuración)**
```nginx
# En nginx.ec2.dev.conf
location = /oauth/google/callback {
  proxy_pass http://frontend_dev;  # ← VA AL FRONTEND
}
```

### **6. Frontend maneja el callback**
```
Frontend recibe: /oauth/google/callback?code=...&state=...
Frontend extrae: 
  - code: Código de autorización de Google
  - state: JWT del backend
  - code_verifier: Del sessionStorage (PKCE)
Frontend hace: POST /api/auth/oauth/callback/ al backend
```

### **7. Backend procesa el OAuth**
```
Backend recibe: POST /api/auth/oauth/callback/
Backend valida: 
  - code: Código de autorización
  - state: JWT firmado
  - code_verifier: Para PKCE
Backend responde: tokens JWT + redirect
```

### **8. Frontend completa el login**
```
Frontend recibe: tokens JWT
Frontend guarda: tokens en localStorage
Frontend redirige: a la página principal
```

## 🔐 **Conceptos Clave**

### **PKCE (Proof Key for Code Exchange)**

**¿Qué es?**
- Extensión de OAuth 2.0 para aplicaciones públicas (SPA, móviles)
- Previene ataques de interceptación de código de autorización
- Usa un par de valores: `code_verifier` y `code_challenge`

**¿Cómo funciona?**
1. **Frontend genera `code_verifier`**: String aleatorio de 43-128 caracteres
2. **Frontend genera `code_challenge`**: SHA256(code_verifier) en base64url
3. **Frontend envía `code_challenge`** a Google en el paso 3
4. **Frontend envía `code_verifier`** al backend en el paso 6
5. **Backend valida**: SHA256(code_verifier) == code_challenge

**Ejemplo:**
```javascript
// Frontend genera
const code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
const code_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM";

// Backend valida
const isValid = sha256(code_verifier) === code_challenge;
```

### **State Parameter**

**¿Qué es?**
- Parámetro de seguridad para prevenir ataques CSRF
- Contiene información del estado de la aplicación
- Debe ser único e impredecible

**En Condor:**
```json
{
  "cliente_id": 1,
  "host": "padel-dev.cnd-ia.com",
  "return_to": "/",
  "exp": 1758817811,
  "ts": 1758817511,
  "v": 1,
  "nonce": "tR724UzgByNIMby6hRJXPrKF"
}
```

**¿Cómo se usa?**
1. **Backend genera**: JWT firmado con información del tenant
2. **Frontend envía**: A Google en el paso 3
3. **Google devuelve**: El mismo state en el paso 4
4. **Backend valida**: JWT firmado y expiración

### **Code Parameter**

**¿Qué es?**
- Código de autorización temporal de Google
- Válido por 10 minutos
- Se usa para obtener tokens de acceso

**¿Cómo se usa?**
1. **Google genera**: Después de que el usuario autoriza
2. **Google envía**: En el callback (paso 4)
3. **Backend intercambia**: Por tokens de acceso (paso 7)

## 🏗️ **Arquitectura por Componentes**

### **Frontend (React SPA)**
- **Responsabilidades:**
  - Generar `code_verifier` (PKCE)
  - Construir URL de autorización
  - Manejar callback de Google
  - Intercambiar code por tokens
  - Gestionar sesión de usuario

- **Almacenamiento:**
  - `sessionStorage`: `code_verifier` (temporal)
  - `localStorage`: tokens JWT (persistente)

### **Backend (Django)**
- **Responsabilidades:**
  - Generar `state` JWT
  - Validar `code` y `state`
  - Intercambiar code por tokens
  - Gestionar sesiones de usuario
  - Validar PKCE

- **Endpoints:**
  - `POST /api/auth/oauth/state/`: Genera información OAuth
  - `POST /api/auth/oauth/callback/`: Procesa callback de Google

### **Proxy Nginx**
- **Responsabilidades:**
  - Enrutar requests según el host
  - Manejar SSL/TLS
  - Balancear carga entre servicios

- **Configuración:**
  - `auth-dev.cnd-ia.com`: Callback va al backend
  - `padel-dev.cnd-ia.com`: Callback va al frontend

### **Google OAuth**
- **Responsabilidades:**
  - Autenticar usuario
  - Generar código de autorización
  - Validar PKCE
  - Redirigir a callback

## 🔧 **Configuración por Ambiente**

### **DEV (padel-dev.cnd-ia.com)**
```nginx
# Callback OAuth → frontend_dev
location = /oauth/google/callback {
  proxy_pass http://frontend_dev;
}
```

### **PROD (lob-padel.cnd-ia.com)**
```nginx
# Callback OAuth → frontend_prod
location = /oauth/google/callback {
  proxy_pass http://frontend_prod;
}
```

## 🚨 **Problemas Comunes**

### **Loop Infinito**
**Causa:** Callback va al backend en lugar del frontend
**Solución:** Configurar proxy para enviar callback al frontend

### **Missing PKCE**
**Causa:** `code_verifier` se pierde entre redirecciones
**Solución:** Usar `sessionStorage` y manejar callback en frontend

### **State Expired**
**Causa:** JWT state expira antes de completar OAuth
**Solución:** Aumentar tiempo de expiración o completar flow más rápido

### **Unknown Host**
**Causa:** Dominio no está en la base de datos
**Solución:** Ejecutar `bootstrap_condor` con el dominio correcto

## 📊 **Logs de Debugging**

### **Frontend (Nginx)**
```
frontend_condor_dev | GET /oauth/google/callback?code=... HTTP/1.1" 200
```

### **Backend (Django)**
```
backend_condor_dev | [OAUTH STATE] issued host=padel-dev.cnd-ia.com cliente_id=1
backend_condor_dev | [OAUTH CB] ok host=padel-dev.cnd-ia.com cliente_id=1
```

### **Proxy (Nginx)**
```
proxy_condor | GET /oauth/google/callback?code=... HTTP/2.0" 200
```

## 🔍 **Comandos de Debugging**

### **Verificar configuración del proxy**
```bash
docker compose -p condor_proxy exec proxy cat /etc/nginx/nginx.conf | grep -A 5 -B 5 'oauth/google/callback'
```

### **Ver logs de OAuth**
```bash
docker compose -p condor_dev logs backend_dev | grep -E '(OAUTH|ERROR)'
```

### **Verificar estado del proxy**
```bash
docker compose -p condor_proxy ps
```

## 📚 **Referencias**

- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC](https://tools.ietf.org/html/rfc7636)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [JWT RFC](https://tools.ietf.org/html/rfc7519)
