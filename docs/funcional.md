# Documentación funcional (Condor)

## 1. Conceptos clave
- Turno: slot de clase en una sede con un prestador. Estados: "disponible" | "reservado" | "cancelado". Puede estar bloqueado para abonos (`reservado_para_abono`) y/o vinculado a un abono (`abono_mes_reservado` / `abono_mes_prioridad`).
- Abono: suscripción mensual (AbonoMes) definida por sede, prestador, día de semana, hora y tipo de clase (`x1..x4`). Al reservar: toma turnos restantes del mes actual (>= hoy) y asigna prioridad del mes siguiente. Campo `renovado` indica intención de renovar; `fecha_limite_renovacion` cierra el ciclo.
- Bonificación: crédito (`TurnoBonificado`) con `valor`, `tipo_turno` (x1..x4 o alias) y `valido_hasta`. Se puede usar como pago total o parcial en reservas de turnos/abonos; se marca como usada al aplicarse.
- Comprobante: constancia de pago validada por backend (OCR). Para turnos se crea con `ComprobanteService.upload_comprobante`, y para abonos con `ComprobanteService.validar_y_crear_comprobante_abono`. Se invalida y desasocia al cancelar.

## 2. Flujo de un turno
- Selección → Reserva → Pago (bono/comprobante) → Cancelación (puede emitir bono)
- Reserva: usuario elige un turno "disponible", envía `tipo_clase` y opcionalmente una bonificación. Backend calcula precio−bono y, si hay restante, exige comprobante exacto. Marca bono usado y cambia a "reservado".
- Cancelación: libera el slot. Si la reserva no usó bonificación, emite bonificación automática; si usó bonificación, solo cancelaciones administrativas devuelven bono equivalente.
  
TODO: confirmar ventana exacta de cancelación permitida (`backend/apps/turnos_core/utils.py`).

## 3. Flujo de un abono
- Turnos del mes + prioridad próximo → Renovación → Cancelaciones
- Reserva: valida franja completa (mes actual desde hoy + mes siguiente). Reserva disponibles del mes actual y fija prioridad en el siguiente. Si restante > 0, exige comprobante; consume bonificaciones aplicadas.
- Renovación: el usuario marca `renovado` antes de vencer. El proceso diario promueve prioridad → reservados y crea el nuevo abono pagado; si no renovó, libera prioridad.

## 4. Políticas
- Cancelación: permitida solo si `cumple_politica_cancelacion(turno)`.
  
  TODO: documentar regla concreta (horas límite/penalidad) (`backend/apps/turnos_core/utils.py`).
- Bonificaciones: aplican solo al mismo `tipo_turno` (acepta alias: x1=individual, x2=2 personas, x3=3 personas, x4=4 personas). Se consumen al reservar turno/abono. En cancelación de turno: si no se usó bono → se emite; si se usó bono → solo admins devuelven.
- Renovación: día posterior al último turno reservado del ciclo actual:
  - `renovado = true` → se crea abono del mes siguiente (pagado) y se promueve prioridad → reservados.
  - `renovado = false` → se liberan las prioridades.

