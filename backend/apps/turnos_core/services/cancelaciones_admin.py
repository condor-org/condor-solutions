# apps/turnos_core/services/cancelaciones_admin.py

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


def _parse_hora(h: Optional[str]) -> Optional[time]:
    if not h:
        return None
    return datetime.strptime(h, "%H:%M").time()


def _admins_de_cliente(cliente_id: int) -> Iterable[Usuario]:
    """
    (Reservado para futuros avisos al staff) — hoy no se usa.
    """
    return Usuario.objects.filter(
        cliente_id=cliente_id, tipo_usuario__in=["admin_cliente", "super_admin"]
    ).only("id", "cliente_id")


def cancelar_turnos_admin(
    *,
    accion_por: Usuario,
    cliente_id: int,
    sede_id: Optional[int],
    prestador_ids: Optional[List[int]],
    fecha_inicio,  # date
    fecha_fin,     # date
    hora_inicio: Optional[str] = None,
    hora_fin: Optional[str] = None,
    motivo: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Cancela turnos en el rango indicado. **SIEMPRE** emite bonificación para turnos con usuario.
    Devuelve un resumen y, si no es dry_run, crea NotificationEvent + notificaciones a usuarios afectados.
    """
    event_uuid = uuid.uuid4()
    hi = _parse_hora(hora_inicio)
    hf = _parse_hora(hora_fin)

    ct_prestador = ContentType.objects.get_for_model(Prestador)

    # --- base queryset multi-tenant ---
    filtros = Q(fecha__range=[fecha_inicio, fecha_fin]) & Q(lugar__cliente_id=cliente_id)
    if sede_id:
        filtros &= Q(lugar_id=sede_id)
    if prestador_ids:
        filtros &= Q(content_type=ct_prestador, object_id__in=prestador_ids)
    if hi and hf:
        filtros &= Q(hora__gte=hi, hora__lte=hf)
    elif hi:
        filtros &= Q(hora__gte=hi)
    elif hf:
        filtros &= Q(hora__lte=hf)

    # Recuperamos solo IDs para después lockear sin joins
    qs_ids = list(Turno.objects.filter(filtros).values_list("id", flat=True))

    logger.info(
        "[cancel.admin][start] event_id=%s cliente=%s sede=%s prestadores=%s fechas=%s..%s horas=%s..%s universe=%s dry_run=%s",
        event_uuid, cliente_id, sede_id, prestador_ids, fecha_inicio, fecha_fin,
        hora_inicio, hora_fin, len(qs_ids), dry_run
    )

    per_user: Dict[int, Dict[str, Any]] = {}   # user_id -> {n_cancelados, n_bonos, sede_nombre, fecha_desde, fecha_hasta}
    detalle: List[Dict[str, Any]] = []         # muestra por turno procesado
    tot = {
        "universe": len(qs_ids),
        "procesados": 0,
        "reservados": 0,
        "cancelados": 0,
        "bonos_emitidos": 0,
        "saltados_idempotencia": 0,
        "errores": 0,
    }

    CHUNK = 200

    def _add_user(u_id: int, sede_nombre: str) -> None:
        if u_id not in per_user:
            per_user[u_id] = {
                "n_cancelados": 0,
                "n_bonos": 0,
                "sede_nombre": sede_nombre or "",
                "fecha_desde": str(fecha_inicio),
                "fecha_hasta": str(fecha_fin),
            }

    for i in range(0, len(qs_ids), CHUNK):
        bloque_ids = qs_ids[i : i + CHUNK]

        with transaction.atomic():
            # ⚠️ Lock SOLO la tabla Turno (sin joins) para evitar:
            # "FOR UPDATE cannot be applied to the nullable side of an outer join"
            turnos = list(
                Turno.objects.filter(id__in=bloque_ids)
                .select_for_update(of=("self",), skip_locked=True)
                .only("id", "estado", "usuario_id", "lugar_id", "tipo_turno")
            )

            # Mapear nombres de sedes sin N+1
            lugar_ids = {t.lugar_id for t in turnos if t.lugar_id}
            lugar_map = {
                l.id: l.nombre
                for l in Lugar.objects.filter(id__in=lugar_ids).only("id", "nombre")
            } if lugar_ids else {}

            for t in turnos:
                tot["procesados"] += 1

                # Idempotencia por turno
                if CancelacionAdmin.objects.filter(turno=t).exists():
                    tot["saltados_idempotencia"] += 1
                    detalle.append({
                        "turno_id": t.id,
                        "estado_previo": t.estado,
                        "usuario_id": t.usuario_id,
                        "emitio_bono": False,
                        "razon_skip": "idempotente",
                    })
                    continue

                usuario_id = t.usuario_id
                sede_nombre = lugar_map.get(t.lugar_id, "")
                emitio_bono = False
                bono_id = None
                tipo_turno = (t.tipo_turno or "x1").lower()  # fallback robusto y preciso

                try:
                    # Emitimos bono SIEMPRE si hay usuario
                    if usuario_id:
                        tot["reservados"] += 1
                        if not dry_run:
                            bono = emitir_bonificacion_automatica(
                                usuario_id=usuario_id,   # admite usuario o usuario_id (según tu firma)
                                turno_original=t,
                                motivo=motivo or "Cancelación administrativa",
                            )
                            emitio_bono = True
                            bono_id = getattr(bono, "id", None)
                            tot["bonos_emitidos"] += 1

                        _add_user(usuario_id, sede_nombre)
                        per_user[usuario_id]["n_cancelados"] += 1
                        per_user[usuario_id]["n_bonos"] += 1

                    # Cancelar el turno (liberar usuario) — en real; en dry-run solo contabilizamos
                    if not dry_run:
                        t.usuario_id = None
                        t.estado = "cancelado"
                        t.save(update_fields=["usuario_id", "estado"])

                        CancelacionAdmin.objects.create(
                            turno=t,
                            accion_por=accion_por,
                            usuario_afectado_id=usuario_id,
                            motivo=motivo or "",
                            event_id=event_uuid,
                            bonificacion_emitida=emitio_bono,
                            bonificacion_id=bono_id,
                            tipo_turno_usado=tipo_turno,
                            metadata={},
                        )

                    tot["cancelados"] += 1

                    detalle.append({
                        "turno_id": t.id,
                        "estado_previo": t.estado,
                        "usuario_id": usuario_id,
                        "emitio_bono": bool(emitio_bono) and not dry_run,
                        "bono_id": bono_id if not dry_run else None,
                        "razon_skip": None,
                    })

                except Exception as e:
                    logger.exception("[cancel.admin][turno][fail] t=%s err=%s", t.id, str(e))
                    tot["errores"] += 1

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
        "detalle_muestra": detalle[:50],  # limitar payload
    }

    if dry_run:
        logger.info("[cancel.admin][dry_run][end] event_id=%s resumen=%s", event_uuid, resumen["totales"])
        return resumen

    # --- evento + notificaciones in-app por usuario afectado ---
    ev = publish_event(
        topic="turnos.cancelacion_admin",
        actor=accion_por,
        cliente_id=cliente_id,
        metadata={
            "sede_id": sede_id,
            "prestador_ids": prestador_ids or [],
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "motivo": motivo,
            "resumen": resumen["totales"],
        },
    )

    user_ids = list(per_user.keys())
    recipients = Usuario.objects.filter(id__in=user_ids).only("id", "cliente_id")
    ctx_by_user = {uid: per_user[uid] for uid in user_ids}

    notify_inapp(
        event=ev,
        recipients=recipients,
        notif_type=TYPE_CANCELACIONES_TURNOS,
        context_by_user=ctx_by_user,
        severity="warning",
    )

    logger.info(
        "[cancel.admin][end] event_id=%s cancelados=%s usuarios=%s",
        ev.id, tot["cancelados"], len(user_ids)
    )
    return resumen
