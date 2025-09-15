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

## 5. Admin — Agenda y visualización
- FE: `frontend-padel/src/pages/admin/AgendaAdmin.jsx` consulta y muestra por día/semana/mes.
- API: GET `/api/turnos/agenda/?scope=day|week|month&date=YYYY-MM-DD&sede_id=&prestador_id=&estado?&include_abonos=0|1`
- BE: validaciones clave
  - Roles: `super_admin` todo; `admin_cliente` solo su cliente; `empleado_cliente` solo sus turnos; `usuario_final` 403.
  - Filtros combinables; si `include_abonos=0`, oculta turnos de abonos (prioridad/reservados).
  - Respuesta: `{ range:{start,end,granularity}, totals:{...}, items:[TurnoSerializer...] }`.
- Respuesta esperada
  - 200 con `items`; FE agrupa por fecha para semana/mes.

> [2025-09-15] Cambio: agregado endpoint de Agenda admin (archivo: `backend/apps/turnos_core/views.py`).

## 6. Admin — Reservar turno (sin pago)
- FE: desde AgendaAdmin, modal “Reservar” elige usuario final y tipo de clase; opcional emisión previa de bono manual.
- API: POST `/api/turnos/admin/reservar/`
- BE: validaciones clave
  - `turno_id` debe estar `disponible` y dentro del cliente (tenancy admin_cliente).
  - Respeta bloqueos de abono salvo `omitir_bloqueo_abono=true`.
  - `tipo_clase_id` opcional, debe corresponder a la misma sede; setea `tipo_turno` si viene.
  - Efecto: asigna usuario y marca `reservado` (sin comprobante/pagos).
- Body ejemplo
  - `{ turno_id, usuario_id, tipo_clase_id?, omitir_bloqueo_abono?=false }`
- Respuesta esperada
  - 200: `{ ok: true, turno_id }` o errores 400/403/409.

> [2025-09-15] Cambio: documentado flujo admin reservar (vista: `ReservarTurnoAdminView`).

## 7. Admin — Liberar turno (con devolución opcional)
- FE: AgendaAdmin “Liberar” sobre un turno reservado; toggle “emitir bonificación”.
- API: POST `/api/turnos/admin/liberar/`
- BE: validaciones clave
  - Tenancy por sede para `admin_cliente`.
  - Si había comprobante/pago: rechaza `PagoIntento` activos, marca comprobante `valido=false` y desasocia.
  - Efecto: `usuario=NULL`, `estado="disponible"`; si `emitir_bonificacion=true`, emite bonificación automática al usuario original.
- Body ejemplo
  - `{ turno_id, emitir_bonificacion?=false, motivo? }`
- Respuesta esperada
  - 200: `{ ok: true, turno_id }`.

> [2025-09-15] Cambio: documentado liberar con devolución opcional (vista: `LiberarTurnoAdminView`).

## 8. Admin — Toggle “reservado_para_abono”
- FE: AgendaAdmin permite bloquear/habilitar un turno para abonos vs sueltos.
- API: POST `/api/turnos/admin/marcar_reservado_para_abono/`
- BE: validaciones clave
  - Turno `disponible`; tenancy por sede para `admin_cliente`.
  - Actualiza flag `reservado_para_abono`.
- Body ejemplo
  - `{ turno_id, reservado_para_abono: bool }`
- Respuesta esperada
  - 200: `{ ok: true, turno: { id, fecha, hora, estado, reservado_para_abono } }`.

> [2025-09-15] Cambio: agregado toggle de abonos (vista: `ToggleReservadoParaAbonoView`).

## 9. Admin — Cancelaciones masivas
- FE: `CancelacionesPage.jsx` ejecuta previsualización (dry-run) y luego confirma.
- API:
  - Por sede: POST `/api/turnos/admin/cancelar_por_sede/`
  - Por prestador: POST `/api/turnos/prestadores/<prestador_id>/cancelar_en_rango/`
- BE: validaciones clave
  - Tenancy por sede o por prestador; rango de fechas válido; hora_inicio < hora_fin si ambos.
  - Cancela solo turnos `reservado` en el rango; emite bonificaciones según reglas (devoluciones/admin).
  - `dry_run=true` devuelve resumen sin modificar datos.
- Body ejemplo
  - Sede: `{ sede_id, fecha_inicio, fecha_fin, hora_inicio?, hora_fin?, prestador_ids?[], motivo?, dry_run?=true }`
  - Prestador: `{ fecha_inicio, fecha_fin, hora_inicio?, hora_fin?, sede_id?, motivo?, dry_run?=true }`
- Respuesta esperada
  - 200: `{ totales:{ cancelados, reservados }, detalle_muestra:[{turno_id,...}] }`.

> [2025-09-15] Cambio: documentado flujo de cancelaciones (servicio `cancelar_turnos_admin`).

## 10. Admin — Bonificación manual
- FE: AgendaAdmin puede emitir bono previo a reservar admin.
- API: POST `/api/turnos/bonificaciones/crear-manual/`
- BE: validaciones clave
  - `usuario_id` y `sede_id` del mismo cliente; `tipo_clase_id` activo y de la sede.
  - Efecto: crea `TurnoBonificado` con `valor` según configuración del tipo (ver servicio).
- Body ejemplo
  - `{ usuario_id, sede_id, tipo_clase_id, motivo?, valido_hasta? }`
- Respuesta esperada
  - 201: objeto bonificación.

> [2025-09-15] Cambio: añadido flujo de bono manual (serializer `CrearTurnoBonificadoSerializer`).

## 11. Admin — Abonos (asignar y eliminar)
- FE: `ReservarAbonoAdmin.jsx` asigna abono a un usuario final; `AgendaAdmin.jsx` permite eliminar abonos.
- APIs:
  - Disponibles: GET `/api/padel/abonos/disponibles/?sede_id=&prestador_id=&dia_semana=&anio=&mes=&tipo_codigo=&hora?`
  - Reservar (asignar): POST `/api/padel/abonos/reservar/` con `forzar_admin=true` y `usuario_id`.
  - Eliminar: DELETE `/api/padel/abonos/{id}/` libera todos los turnos vinculados.
- BE: validaciones clave
  - Asignar: franja completa válida; calcula restante; si `forzar_admin=true` puede omitir comprobante. Reserva actual y fija prioridad próxima; notifica admins.
  - Eliminar: limpia `turnos_reservados` y `turnos_prioridad` y borra el AbonoMes (tenancy admin_cliente por sede).
- Body (reservar) ejemplo
  - `{ sede, prestador, dia_semana, hora, tipo_clase, anio, mes, usuario_id, bonificaciones_ids[]?, archivo?, forzar_admin=true }`
- Respuesta esperada
  - 201: detalle del abono + `resumen`. 200 en DELETE con resumen de turnos afectados.

> [2025-09-15] Cambio: incluido flujo admin de abonos (vistas `AbonoMesViewSet`).

## 12. Admin — CRUD de sedes, prestadores y disponibilidades
- Sedes: `GET/POST/PUT/DELETE /api/turnos/sedes/` (ModelViewSet). Lectura autenticados; escritura admins. Cliente se fuerza desde el usuario.
- Prestadores: `GET/POST/PUT/DELETE /api/turnos/prestadores/?lugar_id=`. Escritura admins; lectura autenticados; borra prestador y usuario asociado en delete.
- Disponibilidades: `GET/POST/PUT/DELETE /api/turnos/disponibilidades/`. Permisos: super_admin | admin_cliente | prestador (solo propias).

> [2025-09-15] Cambio: agregado resumen CRUD admin (archivo: `backend/apps/turnos_core/views.py`).
