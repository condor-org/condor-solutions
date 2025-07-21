# 📘 Proyecto CONDOR — Estructura Base Limpia (2025)

## ✅ Finalidad

Este archivo documenta **cómo está organizado el proyecto actualmente**, después de la limpieza, para que cualquier dev sepa **qué hay**, **qué se puede borrar** y **qué se va agregando** cuando haga falta.

---

## ✅ FRONTEND

```
frontend/
├── public/
│   └── favicon.ico             # Icono básico
├── src/
│   ├── App.jsx                 # Enrutador principal
│   ├── App.css                 # Estilos base
│   ├── index.js                # Bootstrap ReactDOM
│   ├── index.css               # Estilos globales
│   ├── auth/
│   │   └── AuthContext.js      # Contexto de sesión
│   ├── components/
│   │   ├── Card.jsx            # Card de métricas
│   │   └── Navbar.jsx          # Barra de navegación
│   ├── router/
│   │   └── ProtectedRoute.jsx  # Restricción de rutas por rol
│   ├── utils/
│   │   └── axiosAuth.js        # Axios con Bearer token
│   ├── pages/
│   │   ├── admin/              # Vistas admin (Dashboard, Generar turnos)
│   │   ├── auth/               # Vistas auth (Login, Registro)
│   │   ├── user/               # Vistas jugador (Dashboard, Reserva, Perfil)
│   │   ├── NotFoundPage.jsx    # Fallback 404
├── package.json
├── package-lock.json
```

### 🚩 **Nota:**

* `api/` vacío se elimina si no se usa.
* `manifest.json`, `logo.svg`, `reportWebVitals.js` se eliminaron.
* Todo lo nuevo debe entrar en `pages/` o `components/`.

---

## ✅ BACKEND

```
backend/
├── apps/
│   ├── auth_core/             # Registro/Login/Auth
│   ├── pagos_core/            # Comprobantes, OCR, pagos
│   ├── turnos_core/           # Turnos genéricos y sedes
│   ├── turnos_padel_core/     # Profesores, disponibilidades
├── condor_core/
│   ├── settings/              # base.py, dev.py, prod.py
│   ├── urls.py                # Routing central
│   ├── wsgi.py, asgi.py       # Deploy
│   ├── media/                 # Comprobantes PDF/JPG
├── docker/                    # Dockerfile + docker-compose.yml
├── manage.py
├── requirements.txt
├── db.sqlite3 (solo dev)
├── env/ (virtualenv local)
├── docs/
│   ├── backend.md             # Specs backend
│   ├── frontend.md            # Specs frontend
│   ├── openapi.yaml           # Esquema OpenAPI
│   ├── README.md              # Presentación general
```

### 🚩 **Nota:**

* `colas_core/` y `utils_common/` eliminados.
* `__pycache__/` ignorado.
* Scripts manuales (`get_token.sh`) opcionales.
* Base DB es `sqlite3` solo para pruebas.

---

## ✅ Tests

```
tests/
 ├── auth/
 ├── pagos/
 ├── turnos/
```

* Si no hay tests reales, mantener estructura vacía o usar `pytest` + `factory_boy` cuando se escale.

---

## ✅ Notas finales

* Todo lo que no existe se crea **cuando se necesita**.
* Toda funcionalidad nueva debe documentarse en **backend.md** o **frontend.md**.
* `openapi.yaml` debe mantenerse actualizado.

**Ignacio Luque — Proyecto CONDOR — 2025**
