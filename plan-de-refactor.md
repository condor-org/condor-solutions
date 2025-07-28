# PLAN COMPLETO DE REFACTORIZACIÓN BASE DE DATOS Y CONTROL MULTI-TENANT

## 📅 Contexto

Actualmente el backend es una plataforma modular con microservicios internos (apps Django) que gestionan pagos, turnos, usuarios y próximamente notificaciones, bots y agentes IA.

Este plan busca:

* Escalar profesionalmente a un backend multi-tenant.
* Garantizar seguridad, aislamiento de datos y flexibilidad.
* Evitar reestructuras futuras mediante un diseño robusto desde ahora.

---

## 📊 PLAN DE CAMBIOS

### 1️⃣ Crear modelo `Cliente`

Tabla que representa a cada empresa o cliente que contrata el sistema.

* Campos clave:

  * `nombre`
  * `logo`
  * `color_primario`, `color_secundario`
  * `configuraciones_extras` (campo JSONField opcional para casos extremos)
* Función: identidad visual del cliente y separación lógica en el sistema.

> Importante: El modelo Cliente no debe contener configuraciones funcionales específicas. El cliente es sólo una entidad conceptual y visual.

---

### 2️⃣ Crear configuración específica por core

Cada módulo core debe tener su propia tabla de configuración específica, vinculada a `Cliente`.

* **pagos\_core.ConfiguracionPago**

  * Relación: ForeignKey a Cliente
  * Define parámetros como:

    * `requiere_comprobante`
    * `moneda`
    * `cbu`
    * `alias`

* **notificaciones\_core.ConfiguracionNotificacion**

  * Relación: ForeignKey a Cliente
  * Define:

    * Uso de WhatsApp
    * Proveedor de emails
    * Plantillas específicas

* **turnos\_core.ConfiguracionTurnos**

  * Relación: ForeignKey a Cliente (solo para clientes que usen turnos)
  * Define:

    * Políticas de reservas
    * Reglas de bloqueos automáticos

* **logs\_core.ConfiguracionLogs** (si aplica)

  * Nivel de logging
  * Retención de auditoría

> Resultado: cada cliente tiene configuraciones propias sólo para los módulos que usa, respetando la modularidad del sistema.

---

### 3️⃣ Refactorizar modelo `Usuario` (`auth_core`)

* Agregar:

  * Campo `tipo_usuario` (roles):

    * `super_admin`
    * `admin_cliente`
    * `empleado_cliente`
    * `usuario_final`
  * ForeignKey a `Cliente` (null solo para `super_admin`).
* Beneficio: jerarquía clara de usuarios y segmentación total del acceso.

---

### 4️⃣ Agregar campo `cliente` en modelos principales

Incluir `cliente` como ForeignKey en:

* `turnos_core.Turno`
* `turnos_core.Servicio`
* `pagos_core.PagoIntento`
* `pagos_core.ComprobantePago`
* Futuros modelos de notificaciones, bots y AI agents.

Objetivo: garantizar aislamiento físico de los datos por cliente.

---

### 5️⃣ Aplicar control de acceso multi-tenant

* Definir `Permission Class` en DRF:

  * Permite solo a usuarios autorizados según su `tipo_usuario`.
* Definir `Queryset Mixin` para filtrar resultados por `cliente_id` automáticamente.
* Implementar decorador equivalente para vistas no-API.
* Beneficio: seguridad robusta y descentralizada del control de acceso.

---

### 6️⃣ Configuraciones flexibles

* Mantener un modelo SQL estricto para configuraciones comunes por módulo.
* Usar `configuraciones_extras` en Cliente solo para preferencias visuales o casos ultraespecíficos.
* Configuraciones funcionales específicas gestionadas por cada core.

---

### 7️⃣ Revisión de todos los endpoints del backend

* Recorregir cada endpoint existente para:

  * Verificar que recibe correctamente `cliente_id` desde el usuario autenticado.
  * Adaptar lógicas internas para filtrar o validar datos según el cliente.
  * Aplicar permisos y filtros en cada endpoint sin excepción.
* Objetivo: blindar la API a nivel de datos y seguridad.

---

### 8️⃣ Refactor de migraciones y mantenimiento DB

* Reestructurar migraciones existentes (hacer squash migrations).
* Documentar el esquema de datos resultante.
* Definir estrategia de backups periódicos.
* Configurar monitoreo básico de crecimiento de tablas críticas.

---

### 9️⃣ (Opcional) Logs y auditoría

* Diseñar sistema de logs para:

  * Movimientos críticos de negocio.
  * Acciones sensibles de admins de clientes.
  * Registro de accesos fallidos, usuarios bloqueados y actividades sospechosas.

---

## 📊 RESULTADO FINAL ESPERADO

* Plataforma SaaS multi-tenant real.
* Backend personalizable y controlado por cliente.
* Aislamiento y seguridad de datos garantizados.
* Flexibilidad para escalar y extender con nuevos módulos.
* Estructura sostenible a largo plazo sin necesidad de reestructuras futuras.
