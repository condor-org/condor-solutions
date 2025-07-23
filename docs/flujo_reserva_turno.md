# Flujo completo de reserva de turno con comprobante

Este documento describe el flujo completo de reserva de un turno en la aplicación, desde el frontend hasta que el turno queda efectivamente reservado, incluyendo la verificación del comprobante y la creación del `IntentoPago`.

---

## 1. Frontend: `ReservarTurno.jsx`

### Usuario final:

1. El usuario navega al componente `ReservarTurno.jsx`.
2. Selecciona una sede (`sedeId`) y un profesor (`profesorId`).
3. Se muestran los turnos disponibles en un `FullCalendar`, obtenidos desde:

   * `GET /turnos/prestadores/<id>/turnos/?lugar_id=<id>`
4. El usuario hace clic en un turno disponible:

   * Se abre el `ReservaPagoModal`
   * Se solicita subir un archivo de comprobante de pago
5. Al confirmar, se ejecuta `handleReserva`:

   * Se arma un `FormData` con `turno_id` y `archivo`
   * Se envía a: `POST /turnos/reservar/`

---

## 2. Backend: Endpoint `POST /turnos/reservar/`

View: `TurnoReservaView` (usa `CreateAPIView`)

* Serializer: `TurnoReservaSerializer`

### Etapas:

#### a. `validate()` en el serializer:

* Verifica que:

  * El turno existe y está libre
  * El archivo es válido (tipo, extensión, tamaño)
  * El usuario tiene permiso sobre ese turno (mismo cliente)

#### b. `create()` en el serializer:

* Llama a:

  ```python
  ComprobanteService.upload_comprobante(turno_id, archivo, usuario)
  ```

---

## 3. Servicio: `ComprobanteService.upload_comprobante()`

### Etapas:

1. Verifica que el turno existe y que el usuario tiene permiso.
2. Calcula el hash del archivo y evita duplicados.
3. Obtiene la `ConfiguracionPago` (CBU, alias, monto, vencimiento).
4. Extrae del archivo:

   * Texto OCR (PDF o imagen)
   * Monto
   * Fecha de transferencia
   * CBU o alias
5. Valida los datos extraídos vs la configuración.
6. Si todo es válido:

   * Crea `ComprobantePago` asociado al turno
   * **(Próximamente)** crea un `PagoIntento` en estado `pre_aprobado`

---

## 4. Efecto final

* El comprobante queda guardado y validado.
* El turno se asigna al usuario:

  ```python
  turno.usuario = user
  turno.estado = "reservado"
  turno.save()
  ```
* El frontend recibe respuesta 201 con `datos_extraidos`, `turno_id`, `id_comprobante`
* En ese momento, el turno ya está reservado (aún no confirmado el pago manualmente).

---

## 5. Validación manual (proceso aparte)

* El admin\_cliente puede revisar desde su panel todos los `ComprobantePago` en estado `valido=False`
* Llamando a:

  ```http
  PATCH /pagos/comprobantes/<id>/aprobar/
  PATCH /pagos/comprobantes/<id>/rechazar/
  ```
* Si **aprueba**: `valido=True`
* Si **rechaza**:

  * `valido=False`
  * El turno vuelve a `estado="pendiente"` y sin `usuario`

---

## Clases principales involucradas

* **Frontend:** `ReservarTurno.jsx`, `ReservaPagoModal.jsx`
* **Views:** `TurnoReservaView`, `ComprobanteView`
* **Serializers:** `TurnoReservaSerializer`, `ComprobanteUploadSerializer`
* **Models:** `Turno`, `ComprobantePago`, `ConfiguracionPago`, `PagoIntento`
* **Servicio:** `ComprobanteService`

---

## Futuras mejoras

* Crear explícitamente un objeto `PagoIntento` como parte del flujo.
* Asociarlo con `ComprobantePago` y permitir trazabilidad del ciclo completo.
* Validar también origen/destino, nombre del emisor, etc.

---
