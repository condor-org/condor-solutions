# apps/turnos_core/services/cancelaciones_admin.py
# ------------------------------------------------------------------------------
# Servicio de cancelaciones administrativas en lote.
# - Filtra turnos por cliente/sede/prestador y rango fecha/hora.
# - Apunta SOLO a turnos en estado "reservado".
# - Soporta `dry_run` (no muta BD) para previsualizar impacto.
# - Emite bonificación al usuario cuando corresponde.
# - Idempotencia: evita reprocesar turnos ya cancelados y registra evento.
# - Notifica a los usuarios afectados vía in-app notifications.
# ------------------------------------------------------------------------------

import logging
import uuid
from datetime import datetime, time
from typing import Iterable, Dict, Any, List, Optional

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.turnos_core.models import Turno, Prestador, CancelacionAdmin, Lugar
from apps.turnos_core.services.bonificaciones import emitir_bonificacion_automatica
from apps.notificaciones_core.services import (
    publish_event,
    notify_inapp,
    TYPE_CANCELACIONES_TURNOS,
)

logger = logging.getLogger(__name__)
Usuario = get_user_model()


def _parse_hora(h: Optional[str | time]) -> Optional[time]:
    """
    Normaliza hora:
      - Acepta time o str "HH:MM".
      - Devuelve time o None.
    """
    # CHANGED: aceptar time o str "HH:MM"
    if not h:
        return None
    if isinstance(h, time):
        return h
    return datetime.strptime(h, "%H:%M").time()


def _admins_de_cliente(cliente_id: int) -> Iterable[Usuario]:
    """
    Helper para consultar admins de cliente (incluye super_admin).
    *No se usa directamente en este flujo de notificación final, pero
     queda disponible para futuras extensiones (p.e. avisos internos).*
    """
    return Usuario.objects.filter(
        cliente_id=cliente_id, is_super_admin=True
    ).only("id", "cliente_id")


def cancelar_turnos_admin(
    *,
    accion_por: Usuario,
    cliente_id: int,
    sede_id: Optional[int],
    prestador_ids: Optional[List[int]],
    fecha_inicio,  # date
    fecha_fin,     # date
    hora_inicio: Optional[str | time] = None,
    hora_fin: Optional[str | time] = None,
    motivo: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Cancela turnos en el rango indicado y devuelve un resumen.

    ► Reglas clave:
      - SOLO procesa turnos en estado 'reservado'.
      - Emite bonificación automática al usuario **solo** si:
          * el turno tiene usuario (obvio) y
          * el tipo_turno está definido (lo setea la reserva).
        Además agrega "(compensación)" al motivo si estaba reservado con bono.
      - `dry_run=True` → no muta BD (no cancela ni emite bonos) y devuelve métrica simulada.

    ► Filtros soportados:
      - cliente_id (multi-tenant hard filter),
      - sede_id (opcional),
      - prestador_ids (opcional),
      - fecha_inicio..fecha_fin (obligatorio),
      - hora_inicio..hora_fin (opcionales, pueden venir como "HH:MM" o time).

    ► Idempotencia:
      - Evita reprocesar turnos ya cancelados usando CancelacionAdmin existente
        y el estado del turno (usuario=None o estado="cancelado").
      - get_or_create(CancelacionAdmin) y merge suave de metadata en reintentos.

    ► Concurrencia:
      - Procesa en bloques (CHUNK=200).
      - select_for_update(of=("self",), skip_locked=True) para evitar deadlocks
        y permitir ejecución concurrente sobre subconjuntos.

    ► Notificaciones:
      - Si NO es dry_run: publica evento y envía notificaciones in-app a cada usuario afectado,
        con un pequeño resumen por usuario (n_cancelados / n_bonos / sede_nombre / rango).
    """
    event_uuid = uuid.uuid4()
    hi = _parse_hora(hora_inicio)
    hf = _parse_hora(hora_fin)

    ct_prestador = ContentType.objects.get_for_model(Prestador)

    # --- Base queryset multi-tenant (SIEMPRE scoping por cliente) ---
    filtros = Q(fecha__range=[fecha_inicio, fecha_fin]) & Q(lugar__cliente_id=cliente_id)
    if sede_id:
        filtros &= Q(lugar_id=sede_id)
    if prestador_ids:
        filtros &= Q(content_type=ct_prestador, object_id__in=prestador_ids)
    # Rango horario (si llegan ambas, se usa banda cerrada; si una, solo mínimo o máximo)
    if hi and hf:
        filtros &= Q(hora__gte=hi, hora__lte=hf)
    elif hi:
        filtros &= Q(hora__gte=hi)
    elif hf:
        filtros &= Q(hora__lte=hf)

    # Universo total en rango (cualquier estado) para métrica de referencia.
    qs_ids_universo = list(Turno.objects.filter(filtros).values_list("id", flat=True))

    # SOLO ids de "reservado" (los que realmente pueden ser procesados).
    # CHANGED: ids SOLO de reservados para procesar
    qs_ids_reservados = list(Turno.objects.filter(filtros, estado="reservado").values_list("id", flat=True))

    logger.info(
        "[cancel.admin][start] event_id=%s cliente=%s sede=%s prestadores=%s fechas=%s..%s horas=%s..%s universe=%s reservados=%s dry_run=%s",
        event_uuid, cliente_id, sede_id, prestador_ids, fecha_inicio, fecha_fin,
        hora_inicio, hora_fin, len(qs_ids_universo), len(qs_ids_reservados), dry_run
    )

    # Acumuladores para métricas y reporte:
    per_user: Dict[int, Dict[str, Any]] = {}   # user_id -> {n_cancelados, n_bonos, sede_nombre, fecha_desde, fecha_hasta}
    detalle: List[Dict[str, Any]] = []         # muestra acotada por turno procesado
    tot = {
        "universe": len(qs_ids_universo),      # total en rango (cualquier estado)
        "procesados": 0,                        # iterados realmente en loop
        "reservados": len(qs_ids_reservados),   # CHANGED: conteo exacto de reservados
        "cancelados": 0,                        # efectivamente cancelados
        "bonos_emitidos": 0,                    # bonos emitidos
        "saltados_idempotencia": 0,             # ya cancelados/registrados
        "errores": 0,                           # excepciones por turno
    }

    CHUNK = 200  # tamaño de lote: balancea locks/tiempo de transacción

    def _add_user(u_id: int, sede_nombre: str) -> None:
        """Inicializa el bucket de métricas por usuario si no existe."""
        if u_id not in per_user:
            per_user[u_id] = {
                "n_cancelados": 0,
                "n_bonos": 0,
                "sede_nombre": sede_nombre or "",
                "fecha_desde": str(fecha_inicio),
                "fecha_hasta": str(fecha_fin),
            }

    # Procesamiento en bloques para minimizar locks largos y memory footprint.
    for i in range(0, len(qs_ids_reservados), CHUNK):
      bloque_ids = qs_ids_reservados[i : i + CHUNK]

      # Transacción por bloque: cada lote es atómico y aislado del resto.
      with transaction.atomic():
          # Lock por fila para coherencia (evita carreras con otros procesos de cancelación/reserva).
          turnos = list(
              Turno.objects.filter(id__in=bloque_ids)
              .select_for_update(of=("self",), skip_locked=True)
              .only("id", "estado", "usuario_id", "lugar_id", "tipo_turno")
          )

          # Cache local de nombres de sedes para enriquecer métricas/ctx de notificación.
          lugar_ids = {t.lugar_id for t in turnos if t.lugar_id}
          lugar_map = {
              l.id: l.nombre
              for l in Lugar.objects.filter(id__in=lugar_ids).only("id", "nombre")
          } if lugar_ids else {}

          # Precómputo: detectar turnos "reservados con bono" (una sola query).
          from apps.turnos_core.models import TurnoBonificado
          bonos_usados = set(
              TurnoBonificado.objects.filter(
                  usado_en_turno_id__in=[t.id for t in turnos]
              ).values_list("usado_en_turno_id", flat=True)
          )

          for t in turnos:
            tot["procesados"] += 1

            # 1) Seguridad/consistencia: solo procesar reservados.
            if t.estado != "reservado":
                detalle.append({
                    "turno_id": t.id,
                    "estado_previo": t.estado,
                    "usuario_id": t.usuario_id,
                    "emitio_bono": False,
                    "bono_id": None,
                    "razon_skip": "no_reservado",
                })
                continue

            # 2) Idempotencia REAL: si ya hay CancelacionAdmin y el turno quedó cancelado/libre, saltar.
            if CancelacionAdmin.objects.filter(turno_id=t.id).exists() and (t.usuario_id is None or t.estado == "cancelado"):
                tot["saltados_idempotencia"] += 1
                detalle.append({
                    "turno_id": t.id,
                    "estado_previo": t.estado,
                    "usuario_id": t.usuario_id,
                    "emitio_bono": False,
                    "bono_id": None,
                    "razon_skip": "ya_cancelado",
                })
                continue

            usuario_id = t.usuario_id
            sede_nombre = lugar_map.get(t.lugar_id, "")
            emitio_bono = False
            bono_id = None

            tipo_turno = t.tipo_turno or None
            reservado_con_bono = t.id in bonos_usados

            try:
                # Bonificación solo si hay usuario (y tipo_turno se usa en metadata/registro).
                puede_emitir_bono = bool(usuario_id)

                if not dry_run:
                    # 3) Emisión de bonificación (si corresponde) ANTES de cancelar el turno.
                    if puede_emitir_bono:
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        usuario_obj = User.objects.only("id").get(id=usuario_id)

                        motivo_emision = (motivo or "Cancelación administrativa")
                        if reservado_con_bono:
                            motivo_emision += " (compensación)"

                        bono = emitir_bonificacion_automatica(
                            usuario=usuario_obj,
                            turno_original=t,
                            motivo=motivo_emision,
                        )
                        emitio_bono = True
                        bono_id = getattr(bono, "id", None)
                        tot["bonos_emitidos"] += 1

                    # 4) Cancelar el turno (libera slot y persiste estado)
                    t.usuario_id = None
                    t.estado = "cancelado"
                    t.save(update_fields=["usuario_id", "estado"])

                    # 5) Registrar CancelacionAdmin: idempotencia + auditoría + metadata.
                    meta_base = {"reservado_con_bono": reservado_con_bono}
                    ca, created = CancelacionAdmin.objects.get_or_create(
                        turno=t,
                        defaults={
                            "accion_por": accion_por,
                            "usuario_afectado_id": usuario_id,
                            "motivo": (motivo or "Cancelación administrativa"),
                            "event_id": event_uuid,
                            "bonificacion_emitida": emitio_bono,
                            "bonificacion_id": bono_id,
                            "tipo_turno_usado": (str(tipo_turno).lower() if tipo_turno else None),
                            "metadata": meta_base,
                        },
                    )

                    if not created:
                        # Si ya existía, actualizamos datos mínimos y marcamos reintentos.
                        logger.warning(
                            "[cancel.admin][idempotencia-reuse] turno=%s usando CancelacionAdmin existente id=%s",
                            t.id, ca.id
                        )
                        meta = dict(ca.metadata or {})
                        meta.update(meta_base)
                        meta["reintentos"] = int(meta.get("reintentos", 0)) + 1

                        updates = {"event_id": event_uuid, "metadata": meta}
                        if motivo:
                            updates["motivo"] = motivo
                        if emitio_bono and not ca.bonificacion_emitida:
                            updates["bonificacion_emitida"] = True
                            updates["bonificacion_id"] = bono_id
                        if not ca.tipo_turno_usado and tipo_turno:
                            updates["tipo_turno_usado"] = str(tipo_turno).lower()

                        for k, v in updates.items():
                            setattr(ca, k, v)
                        ca.save(update_fields=list(updates.keys()))

                # Métricas por usuario para el reporte/notificación.
                if usuario_id:
                    _add_user(usuario_id, sede_nombre)
                    per_user[usuario_id]["n_cancelados"] += 1
                    if puede_emitir_bono:
                        per_user[usuario_id]["n_bonos"] += 1

                tot["cancelados"] += 1

                # Muestra de detalle por turno (limitada más abajo).
                detalle.append({
                    "turno_id": t.id,
                    "estado_previo": "reservado",
                    "usuario_id": usuario_id,
                    "emitio_bono": bool(emitio_bono) and not dry_run,
                    "bono_id": bono_id if not dry_run else None,
                    "razon_skip": None,
                })

            except Exception as e:
                # Errores controlados por turno: se registran y se continúa con el resto.
                logger.exception("[cancel.admin][turno][fail] t=%s err=%s", t.id, str(e))
                tot["errores"] += 1

    # Resumen agregado (si dry_run: no se generaron efectos secundarios).
    resumen = {
        "event_id": str(event_uuid),
        "totales": {
            "en_rango": tot["universe"],
            "procesados": tot["procesados"],
            "reservados": tot["reservados"],
            "cancelados": tot["cancelados"],
            "bonificaciones_emitidas": tot["bonos_emitidos"],
            "saltados_idempotencia": tot["saltados_idempotencia"],
            "errores": tot["errores"],
        },
        "usuarios_afectados": {str(k): v for k, v in per_user.items()},
        "detalle_muestra": detalle[:50],  # se limita para no inflar payload/logs
    }

    if dry_run:
        logger.info("[cancel.admin][dry_run][end] event_id=%s resumen=%s", event_uuid, resumen["totales"])
        return resumen

    # --- Evento + notificaciones in-app por usuario afectado (solo si no es dry_run) ---
    ev = publish_event(
        topic="turnos.cancelacion_admin",
        actor=accion_por,
        cliente_id=cliente_id,
        metadata={
            "sede_id": sede_id,
            "prestador_ids": prestador_ids or [],
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "hora_inicio": (hi.isoformat() if hi else None),
            "hora_fin": (hf.isoformat() if hf else None),
            "motivo": motivo,
            "resumen": resumen["totales"],
        },
    )

    # Recipients y contexto por usuario (métricas sintetizadas).
    user_ids = list(per_user.keys())
    recipients = Usuario.objects.filter(id__in=user_ids).only("id", "cliente_id")
    ctx_by_user = {uid: per_user[uid] for uid in user_ids}

    try:
        created_notifs = notify_inapp(
            event=ev,
            recipients=recipients,
            notif_type=TYPE_CANCELACIONES_TURNOS,
            context_by_user=ctx_by_user,
            severity="warning",
        )
        logger.info("[cancel.admin][notifs] event_id=%s created=%s recipients=%s", ev.id, created_notifs, len(user_ids))
    except Exception:
        logger.exception("[cancel.admin][notifs][fail] event_id=%s", ev.id)

    logger.info(
        "[cancel.admin][end] event_id=%s cancelados=%s usuarios=%s",
        ev.id, tot["cancelados"], len(user_ids)
    )
    return resumen
