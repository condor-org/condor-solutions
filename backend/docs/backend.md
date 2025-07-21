# 📘 Backend - Especificación Técnica (v1)

## ✅ apps.auth\_core

### 🔹 Models

* **Usuario**
  Extiende `AbstractUser`
  Campos clave: `email (unique)`, `telefono`, `tipo_usuario` (`jugador` o `admin`)

### 🔹 Serializers

* **RegistroSerializer**
  Registra `jugador` (tipo forzado)
  Genera username si falta
* **CustomTokenObtainPairSerializer**
  Extiende payload con `username`, `email`, `tipo_usuario`

### 🔹 Views

* **RegistroView**
  `POST /api/auth/registro/` (público)
* **CustomTokenObtainPairView**
  `POST /api/token/`
* **MiPerfilView**
  `GET /api/auth/yo/` (requiere JWT)

### 🔹 URLs

```http
POST /api/auth/registro/
POST /api/token/
POST /api/token/refresh/
GET  /api/auth/yo/
```

---

## ✅ apps.turnos\_core

### 🔹 Models

* **Turno**
  fecha, hora, estado (`pendiente`, `confirmado`, `cancelado`)
  `usuario` → User FK
  `servicio` (opcional)
  `GenericForeignKey` → `Profesor` en Padel
* **Lugar**
  nombre, dirección, referente

### 🔹 Serializers

* **TurnoSerializer**
  Para listados generales
* **TurnoReservaSerializer**
  Valida reserva única
* **TurnoDisponibleSerializer**
  Filtra turnos libres
* **LugarSerializer**
  Info básica sede

### 🔹 Views

* **TurnoListView**
  `GET /api/turnos/turnos/` (requiere auth)
* **TurnosDisponiblesView**
  `GET /api/turnos/turnos/disponibles/`
* **TurnoReservaView**
  `POST /api/turnos/turnos/reservar/`
* **LugarListView**
  `GET /api/turnos/sedes/`

### 🔹 URLs

```http
GET  /api/turnos/turnos/
GET  /api/turnos/turnos/disponibles/
POST /api/turnos/turnos/reservar/
GET  /api/turnos/sedes/
```

---

## ✅ apps.pagos\_core

### 🔹 Models

* **PagoIntento**
  monto\_esperado, alias\_destino, tiempo\_expiracion, estado
* **ComprobantePago**
  Archivo, hash, OCR info, link a `Turno`
* **ConfiguracionPago**
  Alias, CBU, monto esperado

### 🔹 Serializers

* **ComprobanteUploadSerializer**
  Validaciones de archivo, tamaño, duplicados
* **ComprobantePagoSerializer**
  CRUD comprobante existente

### 🔹 Views

* **ComprobanteView**
  `POST /api/comprobantes/` → subir comprobante
  `GET /api/comprobantes/` → lista (admin o alumno)
* **ComprobanteDownloadView**
  `GET /api/comprobantes/<id>/descargar/`

### 🔹 URLs

```http
POST /api/comprobantes/
GET  /api/comprobantes/
GET  /api/comprobantes/<id>/descargar/
```

---

## ✅ apps.turnos\_padel\_core

### 🔹 Models

* **Profesor**
  Nombre, email, especialidad, activo
  FK a `Lugar` vía `Disponibilidad`
* **Disponibilidad**
  profesor\_id, lugar\_id, día\_semana, hora\_inicio, hora\_fin

### 🔹 Serializers

* **ProfesorDisponibleSerializer**
  Info pública de profesores
* **DisponibilidadSerializer**
  Detalle de franjas horarias

### 🔹 Views

* **ProfesoresDisponiblesView**
  `GET /api/padel/profesores-disponibles/?lugar_id=`
* **DisponibilidadesPorProfesorView**
  `GET /api/padel/profesores/<id>/disponibilidades/`
* **GenerarTurnosView**
  `POST /api/padel/generar-turnos/` (solo admin)

### 🔹 URLs

```http
GET  /api/padel/profesores-disponibles/?lugar_id=
GET  /api/padel/profesores/<id>/disponibilidades/
POST /api/padel/generar-turnos/
```

---

## 📌 Notas Generales

* **Auth:** JWT (`rest_framework_simplejwt`).
* **OCR:** Backend propio (`ComprobanteService`).
* **Faltante:** Cron para limpiar `PagoIntento` vencido.
* **Sugerencia:** `ConfiguracionPago` debería ser por sede (`Lugar`).

---

**Autor:** Ignacio Luque — Proyecto CONDOR — 2025
