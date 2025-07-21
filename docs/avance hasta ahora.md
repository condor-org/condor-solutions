# 📊 Informe de Avance - App Gestión Turnos de Pádel

## 🎯 Objetivo General

Desarrollar una aplicación web que permita gestionar reservas de turnos de pádel, administrando profesores, sedes y pagos mediante comprobantes.

---

## 👥 Tipos de Usuario

- **Super Admin**: Dueño de la aplicación.
- **Admin**: Dueño del negocio de pádel.
- **Profesor**: Instructor de pádel (módulo en desarrollo futuro).
- **Alumno**: Cliente final que reserva turnos.

---

## ⚙️ Lógica Funcional

1. **Alumnos**:
   - Eligen sede, profesor y semana.
   - Visualizan turnos libres (verde) y ocupados (rojo).
   - Seleccionan un turno libre.
   - Visualizan alias y monto a pagar con un **timer de 15 minutos** para subir un comprobante de pago.
   - Suben comprobante y, si es validado correctamente, el turno queda reservado.

2. **Admins**:
   - Gestionan profesores, alumnos y sedes.
   - Agregan profesores con disponibilidades específicas por sede.
   - Pueden:
     - Crear turnos automáticamente según disponibilidades.
     - Reservar turnos sin comprobante.
     - Liberar turnos manualmente.

3. **Profesores**:
   - Módulo aún no implementado.

---

## 🛠️ Backend - Estado Actual

### Apps Principales

- **turnos_core**: Gestión de turnos genéricos.
- **pagos_core**: Gestión de pagos y comprobantes.
- **auth_core**: Gestión de usuarios.
- **turnos_padel_core**: Lógica específica de pádel (profesores, sedes).

---

### Modelos Implementados

- **auth_core.Usuario**:
  - Extiende `AbstractUser` (email como campo principal).
  - Añade teléfono y tipo_usuario.

- **turnos_core**:
  - `Lugar`: Sedes.
  - `Servicio`: Servicios generales asociados.
  - `Turno`: Soporte genérico para reserva de turnos (estado, fecha, hora, etc.).

- **pagos_core**:
  - `PagoIntento`: Controla intentos de pago (con timeout).
  - `ComprobantePago`: Controla comprobantes subidos, permite extraer datos OCR.
  - `ConfiguracionPago`: Define alias, CBU y monto esperado.

- **turnos_padel_core**:
  - `Profesor`: Datos de profesores y sedes vinculadas.
  - `Disponibilidad`: Definición de días y horarios de cada profesor por sede.

---

### Endpoints Definidos

- **Autenticación JWT**:
  - `/api/token/`
  - `/api/token/refresh/`

- **Sedes**:
  - GET `/api/turnos/sedes/`

- **Turnos Generales**:
  - GET `/api/turnos/turnos/disponibles/`
  - POST `/api/turnos/turnos/reservar/`

- **Turnos Padel**:
  - GET `/api/padel/profesores-disponibles/`
  - GET `/api/padel/profesores/<profesor_id>/disponibilidades/`
  - POST `/api/padel/generar-turnos/`

- **Comprobantes**:
  - POST `/api/comprobantes/`
  - GET `/api/comprobantes/<id>/descargar/`

- **Auth**:
  - POST `/api/auth/login/`
  - POST `/api/auth/register/`
  - GET `/api/auth/me/`

---

## 🧪 Sistema de Validación de Pagos

- OCR y regex para extraer datos (monto, CBU, nombre, fecha, etc.).
- Validación automática del comprobante contra `ConfiguracionPago`.
- Lógica de rechazo y pre-aprobación implementada.
- Tests automatizados mediante **Pytest**.

---

## 🎨 Frontend - Estado Actual

- Migrado a **React + Tailwind CSS + Framer Motion**.
- Diseño modular y profesional.
- Funcionalidades clave:
  - Visualización de turnos libres/ocupados.
  - Reserva con carga de comprobante.
  - Timer de 15 minutos.
  - Panel administrativo:
    - Gestión de profesores, sedes y disponibilidades.
    - Reservas y liberación de turnos.
  - Sistema responsive.

---

## 🔍 Pendientes / Próximos Pasos

- Implementar vista y panel de control para **Profesores**.
- Mejorar validación de comprobantes (detección de duplicados, más reglas).
- Completar lógica de rechazo manual y validación manual de pagos.
- Mejoras UX en gestión de disponibilidades (popup y alineación).
- Agregar exportación / reportes para admins.
- Refinar visualización de reservas pasadas y próximas para alumnos.

---

## 📁 Organización de Backend

```bash
apps/
├── auth_core/
├── pagos_core/
├── turnos_core/
├── turnos_padel_core/
