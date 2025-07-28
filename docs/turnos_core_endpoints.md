# Documentación de Endpoints: `apps/turnos_core/views.py`

Este documento describe todos los endpoints disponibles en el módulo `turnos_core.views`, incluyendo métodos, descripciones, datos devueltos y permisos de acceso.

---

## 1. **`GET /api/turnos/`** – `TurnoListView`
- **Descripción**: Lista todos los turnos visibles para el usuario autenticado.
- **Devuelve**: Lista de turnos con datos del servicio, recurso, lugar y estado.
- **Acceso**: Cualquier usuario autenticado.
  - Superadmin: ve todos.
  - Empleado cliente: ve turnos suyos.
  - Usuario final: ve turnos donde es el usuario.

---

## 2. **`POST /api/turnos/reservar/`** – `TurnoReservaView`
- **Descripción**: Reserva un turno libre y sube un comprobante de pago.
- **Devuelve**: ID del turno reservado y mensaje de éxito.
- **Acceso**: Cualquier usuario autenticado.

---

## 3. **`GET /api/turnos/disponibles/`** – `TurnosDisponiblesView`
- **Descripción**: Devuelve todos los turnos (disponibles y reservados) futuros para un prestador en una sede, y opcionalmente en una fecha.
- **Parámetros**: `prestador_id`, `lugar_id`, `fecha` (opcional).
- **Devuelve**: Lista de turnos.
- **Acceso**: Cualquier usuario autenticado.

---

## 4. **`/api/turnos/sedes/`** – `LugarViewSet`
- **Métodos**: GET, POST, PUT, DELETE.
- **Descripción**: Gestión de sedes o lugares.
- **Devuelve**: Datos completos de sedes.
- **Acceso**:
  - GET: cualquier usuario autenticado.
  - POST/PUT/DELETE: solo super_admin o admin_cliente.

---

## 5. **`/api/turnos/prestadores/`** – `PrestadorViewSet`
- **Métodos**: GET, POST, PUT, DELETE.
- **Descripción**:
  - GET: Lista los prestadores del cliente actual, con filtro opcional por sede (`lugar_id`).
  - POST/PUT/DELETE: Crear, editar o eliminar prestadores.
- **Devuelve**: Datos extendidos del prestador (usuario embebido y disponibilidades).
- **Acceso**:
  - GET: cualquier usuario autenticado.
  - POST/PUT/DELETE: solo super_admin o admin_cliente.

---

### 5.1 **`GET /api/turnos/prestadores/<id>/bloqueos/`**
- **Descripción**: Lista los bloqueos de turnos definidos para un prestador.
- **Devuelve**: Lista de objetos `BloqueoTurnos`.
- **Acceso**: super_admin o admin_cliente.

### 5.2 **`POST /api/turnos/prestadores/<id>/bloqueos/`**
- **Descripción**: Crea un nuevo bloqueo para el prestador dado.
- **Body**: `fecha_inicio`, `fecha_fin`, `motivo` (opcional), `lugar` (opcional para “todas las sedes”).
- **Devuelve**: Objeto del bloqueo creado y turnos reservados afectados (si los hay).
- **Acceso**: super_admin o admin_cliente.

### 5.3 **`DELETE /api/turnos/prestadores/<id>/bloqueos/`**
- **Descripción**: Elimina un bloqueo por ID para un prestador.
- **Body**: `{ "id": <bloqueo_id> }`
- **Acceso**: super_admin o admin_cliente.

### 5.4 **`POST /api/turnos/prestadores/<id>/forzar_cancelacion_reservados/`**
- **Descripción**: Fuerza la cancelación de todos los turnos reservados afectados por un bloqueo.
- **Body**: `{ "bloqueo_id": <id> }`
- **Devuelve**: Lista de turnos cancelados.
- **Acceso**: super_admin o admin_cliente.

---

## 6. **`/api/turnos/disponibilidades/`** – `DisponibilidadViewSet`
- **Métodos**: GET, POST, PUT, DELETE.
- **Descripción**: Gestiona los horarios disponibles de los prestadores.
- **Devuelve**: Lista de disponibilidades.
- **Acceso**:
  - super_admin: todas.
  - admin_cliente: solo de su cliente.
  - empleado_cliente: solo sus propias disponibilidades.

---

## 7. **`POST /api/turnos/generar-turnos/`** – `GenerarTurnosView`
- **Descripción**: Genera automáticamente turnos en base a disponibilidades para un prestador entre dos fechas.
- **Devuelve**: Cantidad de turnos generados.
- **Acceso**: super_admin o admin_cliente.

---

## Notas:
- Todos los endpoints usan autenticación JWT.
- Se respetan los niveles de acceso definidos por `tipo_usuario`.
- Las relaciones cliente-usuario garantizan el aislamiento de datos.
- El endpoint `prestadores-disponibles/` fue deprecado. Ahora se usa `GET /prestadores/?lugar_id=...` con datos enriquecidos.
