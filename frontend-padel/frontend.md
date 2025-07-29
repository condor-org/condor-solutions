# 📘 Frontend - Especificación Técnica (v1)

## ✅ Estructura principal

Framework: **React**
Autenticación: JWT (via `axiosAuth`)
Routing: `react-router-dom` con `ProtectedRoute`

---

## ✅ 📂 Componentes clave

### 🔹 App.jsx

* Define rutas públicas y protegidas.
* Carga `AuthProvider`.
* Incluye `Navbar` y `ToastContainer`.

**Rutas públicas:** `/login`, `/registro`

**Protegidas:**

* `/admin` → `AdminDashboard`
* `/jugador` → `JugadorDashboard`
* `/reservar` → `ReservarTurno`
* `/perfil` → `PerfilPage`

Fallback: `NotFoundPage`

---

### 🔹 Navbar.jsx

* Muestra enlaces según `tipo_usuario`.
* Botón de logout.
* Oculta barra en `/login` y `/registro`.

---

### 🔹 axiosAuth.js

* Configura `axios` con `Authorization: Bearer <token>`.
* Base URL: `process.env.REACT_APP_API_BASE_URL`.
* Si `REACT_APP_DEBUG_LOG_REQUESTS` está en `true` se registran en consola las
  peticiones y respuestas de la API.

---

### 🔹 ProtectedRoute.jsx

* Envuelve rutas protegidas.
* Redirige a `/login` si no hay sesión o rol no autorizado.

---

### 🔹 Card.jsx

* Card de métricas: título, valor, icono opcional.
* Usado en dashboards.

---

## ✅ 📂 Pages y vistas

### 🔹 LoginPage.jsx

* Formulario de login.
* Llama `AuthContext.login`.
* Guarda user en localStorage.
* Redirige según `tipo_usuario`.

### 🔹 RegistroPage.jsx

* Formulario de registro alumno (`tipo_usuario` forzado a "jugador").
* POST `/api/auth/registro/`.
* Redirige a `/login` tras éxito.

### 🔹 PerfilPage.jsx

* Placeholder: "Perfil de Usuario".

### 🔹 AdminDashboard.jsx

* Muestra métricas: usuarios, turnos activos, pagos pendientes.
* Renderiza `<GenerarTurnosAdmin />`.

### 🔹 GenerarTurnosAdmin.jsx

* Formulario: año, mes, duración.
* POST `/api/padel/generar-turnos/`.
* Muestra detalle por profesor.

### 🔹 JugadorDashboard.jsx

* Bienvenida con email del usuario.
* Tarjetas: turnos reservados, pagos realizados, próximo turno.
* Botón: abre `<ReservarTurno />` inline.

### 🔹 ReservarTurno.jsx

* Usa `react-big-calendar`.
* Selección sede → carga profesores → carga turnos disponibles.
* Clic en turno libre → selecciona → muestra input de archivo.
* POST `/api/turnos/turnos/reservar/` con comprobante.

---

## ✅ 📂 Estilos

### 🔹 App.css

* Define estilos globales, navbar, formularios, cards.
* Clases: `.navbar`, `.card`, `.reserva-calendario`, `.archivo-preview`, `.generar-turnos-admin`.

---

## ✅ 📂 Contexto de autenticación

* Contexto `AuthContext` (no subido, asumido): maneja login, logout, user, accessToken.
* Usa localStorage para guardar user y tokens.

---

## ✅ Dependencias clave

* `axios`
* `react-router-dom`
* `react-toastify`
* `react-big-calendar`
* `date-fns`

---

## ✅ 📂 TODO y mejoras

* Implementar historial reservas alumno.
* Vista admin: lista de comprobantes con acción aprobar/rechazar.
* Vista perfil de usuario real.
* Optimizar cronología de estados en `ReservarTurno` (timer frontend opcional).

---

**Autor:** Ignacio Luque — Proyecto CONDOR — 2025
