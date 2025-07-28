# Documentación de Endpoints: `apps/auth_core/views.py`

Este documento describe todos los endpoints disponibles en el módulo `auth_core`, incluyendo métodos, descripciones, datos devueltos y permisos de acceso.

---

## 1. **`POST /api/auth/registro/`** – `RegistroView`
- **Descripción**: Crea un nuevo usuario. Siempre se crea como `usuario_final` (sin cliente asociado).
- **Devuelve**: ID y email del nuevo usuario.
- **Acceso**: Público (sin autenticación).

---

## 2. **`GET /api/auth/yo/`** – `MiPerfilView`
- **Descripción**: Devuelve los datos del usuario autenticado actual.
- **Devuelve**: ID, email, teléfono, tipo_usuario, cliente_id.
- **Acceso**: Requiere autenticación JWT.

---

## 3. **`POST /api/auth/token/`** – `CustomTokenObtainPairView`
- **Descripción**: Obtiene token de acceso y refresh a partir del email y password.
- **Devuelve**: Access token, refresh token y datos del usuario.
- **Acceso**: Público.

---

## 4. **`POST /api/auth/token/refresh/`**
- **Descripción**: Refresca el token de acceso con el token de refresh.
- **Devuelve**: Nuevo access token.
- **Acceso**: Público.

---

## 5. **`/api/auth/usuarios/`** – `UsuarioViewSet`
- **Métodos**: GET, POST, PUT, DELETE.
- **Descripción**:
  - GET: Lista usuarios del mismo cliente o todos si es super_admin.
  - POST: Crea un usuario con el cliente forzado según quién lo crea.
  - PUT/DELETE: Actualiza o elimina un usuario.
- **Devuelve**: Datos completos del usuario.
- **Acceso**:
  - Requiere autenticación.
  - Solo `super_admin` y `admin_cliente`.

---

## Notas:
- Todos los endpoints que requieren autenticación usan JWT.
- Los usuarios creados desde el endpoint de registro son siempre tipo `usuario_final`.
- Los permisos y filtros garantizan que los `admin_cliente` solo gestionen usuarios de su cliente.
