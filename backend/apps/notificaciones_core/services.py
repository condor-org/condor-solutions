# apps/notificaciones_core/services.py
import logging
from typing import Iterable, Mapping
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import NotificationEvent, Notification

logger = logging.getLogger(__name__)
Usuario = get_user_model()

# Tipos estandarizados
TYPE_CANCELACIONES_TURNOS = "CANCELACIONES_TURNOS"
TYPE_RESERVA_TURNO = "RESERVA_TURNO"
TYPE_RESERVA_ABONO = "RESERVA_ABONO"
TYPE_CANCELACION_TURNO = "CANCELACION_TURNO"
TYPE_ABONO_RENOVADO = "ABONO_RENOVADO"


def publish_event(*, topic: str, actor, cliente_id: int | None, metadata: dict | None = None) -> NotificationEvent:
    ev = NotificationEvent.objects.create(
        topic=topic,
        actor=actor if getattr(actor, "id", None) else None,
        cliente_id=cliente_id,
        metadata=metadata or {},
    )
    logger.info(
        "[notif.event] created event_id=%s topic=%s cliente=%s meta_keys=%s",
        ev.id, ev.topic, ev.cliente_id, list((metadata or {}).keys())
    )
    return ev


def _render_inapp_copy(notif_type: str, ctx: dict) -> tuple[str, str, str]:
    """
    Render mínimo sin plantillas (MVP). Devuelve (title, body, deeplink_path).
    ctx debe traer lo necesario según notif_type.
    """
    if notif_type == TYPE_CANCELACIONES_TURNOS:
        n = ctx.get("n_cancelados", 1)
        sede = ctx.get("sede_nombre") or "la sede"
        f1 = ctx.get("fecha_desde")
        f2 = ctx.get("fecha_hasta")
        n_bonos = ctx.get("n_bonos", n)
        title = f"Se cancelaron {n} turno(s) en {sede}"
        body = f"Entre {f1} y {f2}. Acreditamos {n_bonos} bono(s)."
        # Para usuarios finales los llevamos a su sección de bonificaciones
        return title, body, "/bonificaciones"

    if notif_type == TYPE_RESERVA_TURNO:
        usuario = ctx.get("usuario") or "Usuario"
        fecha = ctx.get("fecha")
        hora = ctx.get("hora")
        sede = ctx.get("sede_nombre") or "sede"
        prestador = ctx.get("prestador") or ""
        title = "Nueva reserva de turno"
        body = f"{usuario} reservó {fecha} {hora} en {sede}{f' con {prestador}' if prestador else ''}."
        # Vista de admin para revisar reservas del día
        return title, body, f"/admin/reservas?fecha={fecha}"

    if notif_type == TYPE_RESERVA_ABONO:
        # Contexto esperado desde _notify_abono_admin(...)
        usuario = ctx.get("usuario") or "Usuario"
        tipo = ctx.get("tipo") or ""                 # x1/x2/x3/x4 (o alias)
        abono_id = ctx.get("abono_id")
        sede = ctx.get("sede_nombre")
        prestador = ctx.get("prestador")
        hora = ctx.get("hora")
        dia_semana_text = ctx.get("dia_semana_text")

        title = f"Nuevo abono {tipo}".strip()
        # Si tenemos datos enriquecidos, armamos un cuerpo más útil
        if sede or prestador or hora or dia_semana_text:
            partes = []
            if sede:
                partes.append(f"en {sede}")
            if prestador:
                partes.append(f"con {prestador}")
            if hora:
                partes.append(f"a las {hora}")
            if dia_semana_text:
                partes.append(f"({dia_semana_text})")
            detalles = " ".join(partes)
            body = f"{usuario} confirmó un abono {tipo} {detalles}."
        else:
            body = f"{usuario} confirmó un abono. Ver detalle."
        deeplink = f"/admin/abonos/{abono_id}" if abono_id else "/admin/abonos"
        return title, body, deeplink

    if notif_type == TYPE_ABONO_RENOVADO:
        # Notificación pensada para admins cuando corre la renovación automática
        usuario = ctx.get("usuario") or "Usuario"
        tipo = ctx.get("tipo") or ""
        abono_id = ctx.get("abono_id")
        sede = ctx.get("sede_nombre")
        prestador = ctx.get("prestador")
        hora = ctx.get("hora")
        dia_semana_text = ctx.get("dia_semana_text")
        anio = ctx.get("anio")
        mes = ctx.get("mes")

        title = f"Abono renovado {tipo}".strip()

        partes = []
        if anio and mes:
            partes.append(f"para {mes}/{anio}")
        if sede:
            partes.append(f"en {sede}")
        if prestador:
            partes.append(f"con {prestador}")
        if hora:
            partes.append(f"a las {hora}")
        if dia_semana_text:
            partes.append(f"({dia_semana_text})")

        detalles = " ".join(partes)
        body = f"{usuario} renovó su abono {tipo} {detalles}.".strip()
        deeplink = f"/admin/abonos/{abono_id}" if abono_id else "/admin/abonos"
        return title, body, deeplink

    if notif_type == TYPE_CANCELACION_TURNO:
        usuario = ctx.get("usuario") or "Usuario"
        fecha = ctx.get("fecha")
        hora = ctx.get("hora")
        sede = ctx.get("sede_nombre") or "sede"
        prestador = ctx.get("prestador") or ""
        body_tail = f" en {sede}{f' con {prestador}' if prestador else ''}."
        title = "Cancelación de turno"
        body = f"{usuario} canceló el turno del {fecha} {hora}{body_tail}"
        return title, body, f"/admin/reservas?fecha={fecha}"

    # fallback
    return "Notificación", "", "/"


@transaction.atomic
def notify_inapp(
    *,
    event: NotificationEvent,
    recipients: Iterable[Usuario],
    notif_type: str,
    context_by_user: Mapping[int, dict],
    severity: str = "info",
) -> int:
    """
    Crea notificaciones in-app por usuario con idempotencia por dedupe_key.
    Retorna cantidad efectivamente creadas (nuevas).
    """
    created = 0
    now = timezone.now()
    for u in recipients:
        ctx = context_by_user.get(u.id, {})
        title, body, deeplink = _render_inapp_copy(notif_type, ctx)
        dedupe_key = f"user:{u.id}|event:{event.id}|type:{notif_type}"
        defaults = {
            "event": event,
            "cliente_id": getattr(u, "cliente_id", None),
            "type": notif_type,
            "severity": severity,
            "title": title,
            "body": body,
            "deeplink_path": deeplink,
            "unread": True,
            "metadata": ctx,
            "created_at": now,
        }
        obj, obj_created = Notification.objects.get_or_create(
            recipient=u, dedupe_key=dedupe_key, defaults=defaults
        )
        if obj_created:
            created += 1
            logger.debug(
                "[notif.inapp][created] user=%s type=%s event_id=%s key=%s",
                u.id, notif_type, event.id, dedupe_key
            )
        else:
            logger.debug(
                "[notif.inapp][skip-dedupe] user=%s type=%s event_id=%s key=%s",
                u.id, notif_type, event.id, dedupe_key
            )

    # Evitamos evaluar dos veces un QuerySet/generador al loguear
    try:
        total = len(recipients)  # si es lista/QuerySet
    except TypeError:
        total = None
    logger.info(
        "[notif.inapp] event_id=%s type=%s created=%s total_recipients=%s",
        event.id, notif_type, created, total if total is not None else "?"
    )
    return created
