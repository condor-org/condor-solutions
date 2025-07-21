# 📄 Contexto App Turnos Pádel

**Objetivo:** Aplicación web que permite a alumnos reservar clases de pádel mediante pago con comprobante, y a administradores gestionar profesores, sedes, horarios y pagos mediante un panel administrativo.

## 🛠️ Tecnologías

* **Backend:**

  * Framework: Django (Python).
  * Apps:

    * `turnos_padel_core`: Lógica del negocio específica de pádel.
    * `turnos_core`: Gestión genérica de turnos y sedes.
    * `pagos_core`: Gestión de comprobantes y pagos asociados.
    * `auth_core`: Gestión de usuarios y autenticación.
* **Frontend:**

  * React (SPA).
  * Librería UI: Shadcn UI.
  * Animaciones: Framer Motion.
* **Base de datos:** PostgreSQL (asumido).
* **OCR/Regex:** Para extracción y validación de datos en comprobantes.
* **Testing:** Pytest.

## 🔄 Arquitectura

* **Frontend:**

  * Aplicación SPA.
  * Consume APIs REST publicadas por el backend.
  * Comunica principalmente con `turnos_padel_core`, que actúa como fachada del backend.

* **Backend:**

  * `turnos_padel_core` expone las APIs y coordina la lógica específica del negocio.
  * Se apoya en las apps core:

    * `turnos_core`: Turnos y sedes.
    * `pagos_core`: Pagos y validación de comprobantes.
    * `auth_core`: Usuarios y permisos.

## 📦 Funcionalidades Principales

### Alumnos:

* Selección de sede y profesor.
* Visualización de turnos disponibles (verde) y ocupados (rojo).
* Reserva de turno con carga de comprobante de pago.
* Timer de 15 minutos para carga del comprobante.
* Validación automática del comprobante mediante OCR y reglas predefinidas.
* Recepción de confirmación o rechazo del pago.

### Administradores:

* Gestión CRUD de:

  * Profesores.
  * Sedes.
  * Disponibilidades horarias.
* Creación automática de turnos según disponibilidad del profesor.
* Visualización general del calendario de reservas.
* Gestión manual de reservas y turnos (liberación, bloqueo, asignación directa).
* Revisión y gestión de comprobantes subidos.
* Panel administrativo responsive y modular.

### Validación de Pagos:

* Subida de comprobantes en formato imagen o PDF.
* Extracción de datos usando OCR y expresiones regulares.
* Comparación automática con los parámetros esperados (CBU, alias, monto).
* Detección de duplicados mediante hash del archivo.
* Estado del pago: pendiente, pre-aprobado, rechazado, confirmado.

## 🚧 Módulos Pendientes

* Vista y funcionalidades para profesores (panel propio).
* Validación manual y rechazo de pagos desde backend y frontend.
* Implementación del módulo "Mi perfil" para que el alumno consulte reservas y comprobantes subidos.
* Mejoras UX del módulo administrativo y en el flujo de reservas.
* Exportación de reportes de reservas y pagos.

---

> **Documento de contexto detallado para compartir en nuevos chats o con nuevos colaboradores.**
