# Flujos técnicos FE ↔ BE

## 1. Reserva de un turno
- FE: desde `frontend-padel/src/pages/user/ReservarTurno.jsx` abre `ReservaPagoModal` y envía FormData con `turno_id`, `tipo_clase_id`, opcional `bonificacion_id` y `archivo` (comprobante).
- API: POST `/api/turnos/reservar/`
- BE: validaciones clave
  - Turno existe y está `disponible` (lock `SELECT ... FOR UPDATE`).
  - `tipo_clase_id` válido y de la misma sede del turno; `codigo` ∈ {x1..x4}.
  - `bonificacion_id` opcional: del usuario, vigente, no usada y de igual `tipo_turno` (acepta alias). Si se pasa, se consume.
  - Precio: `TipoClasePadel.precio`. Resta = max(precio − bono.valor, 0).
  - Si `restante > 0` → exige `archivo` y crea comprobante via `ComprobanteService.upload_comprobante`.
  - Efecto: asigna usuario, `estado="reservado"`, `tipo_turno` según clase; notifica admins in-app.
- Respuesta esperada
  - 200: `{ "message": "Turno reservado exitosamente", "turno_id": <int> }`
  - Errores 400/409 con detalle por campo.
  
TODO: confirmar mapping exacto alias↔código en UI (ver `TurnoReservaSerializer`).

## 2. Cancelación de un turno
- FE: en “Mis reservas” de `ReservarTurno.jsx` envía `{ turno_id }` a cancelar; advierte si fue reservado con bonificación.
- API: POST `/api/turnos/cancelar/`
- BE: validaciones clave
  - Dueño del turno; `estado="reservado"`; cumple política (`cumple_politica_cancelacion`).
  - Desasocia comprobante si existe: marca `valido=false`, borra vínculo y rechaza `PagoIntento` activos.
  - Efecto: libera slot (`usuario=NULL`, `estado="disponible"`). Bonificación:
    - Si NO usó bono → emite bonificación automática (mismo tipo).
    - Si usó bono → solo admins devuelven bono; usuario final no recibe.
  - Notifica a admins si cancela usuario.
- Respuesta esperada
  - 200: `{ "message": "Turno cancelado y liberado.", "bonificacion_creada": <bool> }`
  
TODO: documentar política de cancelación exacta (`backend/apps/turnos_core/utils.py`).

## 3. Reserva de abono mensual
- FE: `frontend-padel/src/pages/user/ReservarAbono.jsx`
  - Consulta disponibilidad: `GET /api/padel/abonos/disponibles/?sede_id=&prestador_id=&dia_semana=&anio=&mes=&tipo_codigo=&hora?`
  - Abre `ReservaPagoModalAbono`; envía FormData a reservar: `sede`, `prestador`, `dia_semana`, `hora`, `tipo_clase`, `anio`, `mes`, `bonificaciones_ids[]`, opcional `archivo`. Renovación envía además `abono_id`.
- API: POST `/api/padel/abonos/reservar/` (alias de create). Alternativa: POST `/api/padel/abonos/`.
- BE: validaciones clave (service `validar_y_confirmar_abono`)
  - Verifica franja completa: mes actual (>= hoy) y mes siguiente (todas las fechas) sin reservados ni faltantes.
  - Bonos: del usuario, vigentes, tipo coincide; suma `valor` y marca usados.
  - Calcula `restante = precio_abono − sum(valor_bonos)`; si `restante > 0` requiere `archivo` y crea comprobante con monto exacto.
  - Reserva actual y fija prioridad próxima (`confirmar_y_reservar_abono`); setea `fecha_limite_renovacion`.
  - Notifica admins del cliente.
- Respuesta esperada
  - 201: Abono detalle + `resumen` con contadores (`reservados_mes_actual`, `prioridad_mes_siguiente`, `monto_sugerido`).
  
TODO: confirmar uso de `monto/monto_esperado` del payload en BE (actualmente backend calcula montos).

## 4. Renovación automática
- Cron/Servicio
  - `backend/apps/turnos_padel/management/commands/abonos_diario.py`
  - Tareas: recordatorios T-7/T-1 y, pasado el último turno del ciclo, aplicar transición.
- Lógica principal
  - Si `abono.renovado == True`: crea abono del próximo mes (estado `pagado`), promueve prioridad → reservados del nuevo.
  - Si `abono.renovado == False`: libera todos los turnos en prioridad.
- Efectos sobre turnos (prioridad → reservados, liberaciones)
  - Promoción: `abono_mes_prioridad=None`, `abono_mes_reservado=<nuevo>`. Liberación: `estado="disponible"`, `usuario=NULL`, `tipo_turno=NULL`.

