
# Documentación de Endpoints: `apps/pagos_core/views.py`

Este documento describe todos los endpoints disponibles en el módulo `pagos_core.views`, incluyendo métodos, descripciones, datos devueltos y permisos de acceso.

---

## 1. **`GET /api/pagos/`** – `ComprobanteView`
- **Descripción**: Lista los comprobantes disponibles según el tipo de usuario.
- **Devuelve**: Lista de comprobantes (`ComprobantePagoSerializer`).
- **Acceso**:
  - `super_admin`: ve todos.
  - `admin_cliente`: solo los de su cliente.
  - `empleado_cliente`: solo los turnos donde es prestador.
  - `usuario_final`: solo los turnos donde es el usuario.

---

## 2. **`POST /api/pagos/`** – `ComprobanteView`
- **Descripción**: Sube un nuevo comprobante para un turno.
- **Body**: `turno_id`, `archivo` (PDF/JPG/PNG/...)
- **Devuelve**: ID del comprobante, ID del turno, datos extraídos.
- **Acceso**: cualquier usuario autenticado con permisos válidos sobre el turno.

---

## 3. **`GET /api/pagos/<id>/download/`** – `ComprobanteDownloadView`
- **Descripción**: Permite descargar el archivo del comprobante si el usuario tiene permisos.
- **Devuelve**: Archivo del comprobante (PDF/JPG/...).
- **Acceso**:
  - `super_admin`: acceso total.
  - `usuario_final`: solo si el comprobante es suyo.
  - Bloquea si el comprobante no tiene archivo.

---

## 4. **`PATCH /api/pagos/<id>/<aprobar|rechazar>/`** – `ComprobanteAprobarRechazarView`
- **Descripción**: Aprueba o rechaza un comprobante.
- **Acción `aprobar`**: marca como válido.
- **Acción `rechazar`**: lo invalida y libera el turno asociado.
- **Acceso**: solo `admin_cliente` o `super_admin`.

---

## 5. **`GET /api/pagos/configuracion/`** – `ConfiguracionPagoView`
- **Descripción**: Obtiene la configuración de pago actual.
- **Devuelve**: Datos como CBU, alias, monto esperado, etc.
- **Acceso**: cualquier usuario autenticado.

---

## 6. **`PUT /api/pagos/configuracion/`** – `ConfiguracionPagoView`
- **Descripción**: Modifica la configuración de pago del cliente.
- **Acceso**: solo `admin_cliente` o `super_admin`.

---

## 7. **`GET /api/pagos/pendientes/count/`** – `PagosPendientesCountView`
- **Descripción**: Devuelve la cantidad de comprobantes pendientes (no válidos).
- **Devuelve**: `{ "count": <int> }`
- **Acceso**: solo `admin_cliente` o `super_admin`.

---

## Notas:
- Todos los endpoints usan autenticación JWT.
- Las validaciones aseguran que los comprobantes pertenezcan al mismo cliente que el usuario autenticado.
- El campo `cliente` es obligatorio en `ComprobantePago`, y se infiere del `usuario` en la mayoría de los casos.
- La subida de comprobantes pasa por OCR y validaciones estrictas (monto, CBU/alias, fecha, vencimiento).
