# `auth_core` — OAuth (Google) + Invites + Tenancy

Este documento resume **todos los cambios** aplicados en `apps/auth_core` y explica **cómo emitir y consumir links de invitación** para admins de cliente, con enforcement multi-tenant por subdominio.

---

## 1) Resumen funcional

- **Login con Google (OIDC + PKCE)** con emisión de JWT (`rest_framework_simplejwt`).
- **State firmado** (HMAC) que incluye `nonce`, `host` y `cliente_id` resuelto por subdominio (modelo `ClienteDominio`).
- **Invites firmados** para alta/ascenso de usuarios. Soportados roles:
  - `admin_cliente`
  - `usuario_final` (por defecto si no hay invite)
- **Promoción automática**: si un usuario existente entra con un invite de admin, se promueve a `admin_cliente` (salvo que ya sea `super_admin` o `admin_cliente`).
- **Onboarding**: si el usuario no existe, se deriva a `/signup` con `pending_token` para crear cuenta (setea password como **unusable**).
- **JWT enriquecido**: `email`, `tipo_usuario`, `cliente_id` en el access token para que el FE pueda rutear según rol.

---

## 2) Endpoints relevantes

### 2.1 `POST /api/auth/oauth/state/`

- **Pide**: `{ host, return_to?, invite? }`
- **Hace**: valida config OIDC, resuelve `cliente_id` por `host` usando `ClienteDominio`, genera `state` firmado (TTL 5m) con:
  ```jsonc
  {
    "v": 1,
    "nonce": "...",
    "host": "sub.dominio.com",
    "return_to": "/",
    "cliente_id": 123,
    // opcional
    "invite": "<token_invite_firmado>"
  }
  ```
- **Responde**: `{ state, nonce }` para ir a Google.

### 2.2 `POST /api/auth/oauth/callback/`

- **Pide**: `{ provider:"google", code, code_verifier, state }`
- **Hace**:
  1. Verifica y decodifica `state` (HMAC).
  2. Intercambia `code` por tokens de Google y valida `id_token` (aud, iss, exp, iat, sub, nonce).
  3. **Enforcement de tenant** (`cliente_id` del state vs usuario existente / invite).
  4. **Invite opcional** dentro del `state`:
     - Valida **intent** = `"invite"`
     - Verifica `cliente_id` del invite vs `state`
     - Verifica `email` del invite (si vino) vs `email` del ID token
     - Si `role=admin_cliente` y el usuario **ya existe**, se promueve (si no lo era).
  5. Si el usuario **no existe**: devuelve
     ```json
     {
       "needs_onboarding": true,
       "pending_token": "...",  // firmado
       "prefill": { "email": "...", "given_name": "...", "family_name": "...", "picture": "..." },
       "return_to": "/signup"
     }
     ```
  6. Si el usuario **existe**: devuelve tokens via `_issue_tokens_for_user()`.

### 2.3 `POST /api/auth/oauth/onboard/`

- **Pide**: `{ pending_token, nombre, apellido, telefono?, acepta_tos:true }`
- **Hace**:
  - Verifica `pending_token` (HMAC, `intent: "onboard"`).
  - Si venía `invite` adentro del `pending_token`, vuelve a validar y **setea rol** (`admin_cliente` si corresponde).
  - Crea usuario con `password` **unusable** y retorna tokens con claims útiles.

### 2.4 `POST /api/auth/oauth/invite/issue/` **(nuevo)**

- **Permisos**: `IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)`
- **Pide**:
  ```json
  {
    "role": "admin_cliente",        // o "usuario_final"
    "cliente_id": 1,                // requerido p/ super_admin; ignorado si admin de otro cliente
    "email": "alguien@ejemplo.com", // opcional (vincula invite a un mail concreto)
    "ttl_seconds": 86400            // opcional (default 7 días)
  }
  ```
- **Hace**: firma un **invite token** HMAC con payload:
  ```jsonc
  {
    "v": 1,
    "intent": "invite",
    "cliente_id": 1,
    "role": "admin_cliente",
    "email": "alguien@ejemplo.com", // opcional
    "issued_by": 2,                 // user.id que emitió
    "ts": 1712345678,               // timestamp
    "exp": ...                      // por TTL
  }
  ```
- **Responde**: `{ "invite": "<token_invite>" }`

---

## 3) Cambios de código clave en `auth_core`

### 3.1 `views.py`

- **`OAuthStateView`**: ahora acepta `invite` en el body y lo inyecta al `state`.
- **`OAuthCallbackView`**:
  - Normaliza `cliente_id` del `state` a `int` y valida.
  - Valida invite (si vino) y **promueve** usuario existente a `admin_cliente` si `role=admin_cliente`.
  - En caso de usuario inexistente, pasa el `invite` dentro del `pending_token` hacia `/onboard`.
- **`OnboardView`**:
  - Lee `invite` del `pending_token` y, si corresponde, crea el usuario con `tipo_usuario="admin_cliente"`.
  - `set_unusable_password()` para usuarios OAuth.
- **`IssueInviteView`**: endpoint nuevo para emitir invites firmados.
- **Helper `_issue_tokens_for_user()`**: agrega claims al access token:
  - `email`, `tipo_usuario`, `cliente_id`.

### 3.2 `urls.py`

Rutas añadidas/confirmadas:
```py
path("oauth/state/", OAuthStateView.as_view(), name="oauth_state"),
path("oauth/callback/", OAuthCallbackView.as_view(), name="oauth_callback"),
path("oauth/onboard/", OnboardView.as_view(), name="onboard"),
path("oauth/invite/issue/", IssueInviteView.as_view(), name="invite_issue"),
```

### 3.3 `oauth.py`

`GoogleOIDCConfig` leé variables de entorno y `validate()` que:
- `GOOGLE_CLIENT_ID/SECRET` presentes
- `GOOGLE_ISSUER` esperado (`https://accounts.google.com`)
- `GOOGLE_JWKS_URL` válida
- `OAUTH_REDIRECT_URI` comienza con `http(s)://`
- `STATE_HMAC_SECRET` longitud >= 32

### 3.4 Tenancy por subdominio

- `OAuthStateView` resuelve `cliente_id` por `host` usando `ClienteDominio`.
- Si `TENANT_STRICT_HOST=True` y no hay dominio, responde `unknown_host`.
- Alternativa: `TENANT_DEFAULT_CLIENTE_ID` cuando `strict=False`.

---

## 4) Variables de entorno (OAuth/Invites)

**Backend (Django):**
```env
# OIDC (Google)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_ISSUER=https://accounts.google.com
GOOGLE_JWKS_URL=https://www.googleapis.com/oauth2/v3/certs
OAUTH_REDIRECT_URI=https://tuapp.com/oauth/google/callback

# State / Invite signing
STATE_HMAC_SECRET=...min-32-chars...

# Features / Rules
FEATURE_OAUTH_INVITES=true
OAUTH_ALLOWED_EMAIL_DOMAIN=*             # o tu dominio (p.ej. condor.ai.solutions)
OAUTH_REQUIRE_EMAIL_VERIFIED=true        # recomendado

# Tenancy
TENANT_STRICT_HOST=true
TENANT_DEFAULT_CLIENTE_ID=               # solo si strict=false
```

**Frontend (runtime `config.js`):**
```js
window.RUNTIME_CONFIG = {
  API_BASE_URL: "https://tuapp.com/api",
  GOOGLE_CLIENT_ID: "...",
  OAUTH_REDIRECT_URI: "https://tuapp.com/oauth/google/callback"
}
```

---

## 5) Cómo emitir y usar un invite

### 5.1 Obtener token de un admin

```bash
# (admin_cliente o super_admin)
TOKENS=$(curl -sX POST https://tuapp.com/api/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@admin.com","password":"admin123"}')
ACCESS=$(echo "$TOKENS" | jq -r .access)
```

### 5.2 Emitir invite (admin de su cliente)

```bash
INVITE=$(
  curl -sX POST https://tuapp.com/api/auth/oauth/invite/issue/ \
    -H "Authorization: Bearer $ACCESS" \
    -H "Content-Type: application/json" \
    -d '{"role":"admin_cliente","email":"future.admin@example.com","ttl_seconds":86400}' \
  | jq -r '.invite'
)
echo "https://tuapp.com/login?invite=$INVITE"
```

> **Notas**:
> - Un **admin_cliente** no debe enviar `cliente_id`: el sistema usará el del propio admin.
> - Un **super_admin** **debe** enviar `cliente_id` explícito:
>   ```bash
>   -d '{"role":"admin_cliente","cliente_id":1,"email":"..."}'
>   ```

### 5.3 Consumir invite

1. Compartí la URL `https://tuapp.com/login?invite=<TOKEN>` con la persona invitada.
2. La persona hace **Login con Google**.
3. Si ya tenía usuario:
   - Se **promueve** a `admin_cliente` (si aún no lo era) y entra a `/admin`.
4. Si no tenía usuario:
   - Se deriva a `/signup` para completar datos; al finalizar se crea como `admin_cliente`.

---

## 6) Errores frecuentes y cómo leerlos

- `unknown_host` (al pedir `state`): falta registrar el host en `ClienteDominio` o `TENANT_STRICT_HOST=true` sin default.
- `state_invalid` / `nonce_mismatch`: expirada la ventana o manipulación del state.
- `email_domain_not_allowed`: correo fuera de `OAUTH_ALLOWED_EMAIL_DOMAIN`.
- `email_not_verified`: la cuenta de Google no tiene email verificado.
- `tenant_mismatch`: invite/usuario y subdominio resuelto pertenecen a distintos `cliente_id`.
- `invite_email_mismatch`: el invite estaba atado a un email distinto al del ID Token.
- `invite_invalid` / `invite_invalid_intent`: token invite mal formado o vencido.

Los logs ya incluyen prefijos útiles:
- `[OAUTH STATE] ...`
- `[OAUTH CB] ...`
- `[ONBOARD] ...`
- `[INVITE ISSUE] ...`

---

## 7) Seguridad / buenas prácticas

- Usar `STATE_HMAC_SECRET` **largo** y rotarlo si es necesario.
- No extender TTL innecesariamente (`state`: 5 min, `invite`: 1–7 días).
- Mantener `OAUTH_REQUIRE_EMAIL_VERIFIED=true`.
- Los **invites** no otorgan privilegios cross-tenant.
- Solo **super_admin** puede emitir invites para **cualquier** cliente; **admin_cliente** solo para **su** cliente.

---

## 8) Referencias rápidas (funciones clave)

- `_issue_tokens_for_user(user, return_to="/")`: genera `{ok, access, refresh, user, return_to}` con claims útiles.
- `OAuthStateView.post`: arma `state` con `host`, `cliente_id`, `nonce`, `invite?` (opcional).
- `OAuthCallbackView.post`: valida OIDC + invite, promueve si corresponde, o deriva a onboarding.
- `OnboardView.post`: crea usuario con `tipo_usuario` desde invite; `set_unusable_password()`.
- `IssueInviteView.post`: firma invite con `sign_state()` (HMAC con `SECRET_KEY`).

---

**Fin.**  
Cualquier ajuste (por ejemplo, nuevos roles) se centraliza en `IssueInviteView` (emisión) y en la lógica de `OAuthCallbackView`/`OnboardView` (lectura/efectos del invite).
