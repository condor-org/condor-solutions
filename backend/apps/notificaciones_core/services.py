# apps/notificaciones_core/services.py
import logging
from typing import Iterable, Mapping
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import NotificationEvent, Notification
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
import os
try:
    import boto3
    from botocore.config import Config as _BotoConfig
    from botocore.exceptions import ClientError as _BotoClientError
except Exception:  # boto3 puede no estar instalado en dev
    boto3 = None
    _BotoConfig = None
    _BotoClientError = Exception

logger = logging.getLogger(__name__)
Usuario = get_user_model()

# --- Email/SES config (feature flag) ---
NOTIF_EMAIL_ENABLED = getattr(settings, "NOTIF_EMAIL_ENABLED", False)
SES_REGION = getattr(settings, "AWS_REGION", os.getenv("AWS_REGION", "us-east-1"))
SES_FROM = getattr(settings, "NOTIF_EMAIL_FROM", os.getenv("SES_FROM", "notificaciones@cnd-ia.com"))
SES_CONFIGURATION_SET = getattr(settings, "SES_CONFIGURATION_SET", None)  # opcional para métricas/track

# Tipos estandarizados
TYPE_CANCELACIONES_TURNOS = "CANCELACIONES_TURNOS"
TYPE_RESERVA_TURNO = "RESERVA_TURNO"
TYPE_RESERVA_ABONO = "RESERVA_ABONO"
TYPE_CANCELACION_TURNO = "CANCELACION_TURNO"
TYPE_ABONO_RENOVADO = "ABONO_RENOVADO"
TYPE_BONIFICACION_CREADA = "BONIFICACION_CREADA"
TYPE_ABONO_RECORDATORIO = "ABONO_RECORDATORIO"


def _json_safe(obj):
    """
    Normaliza a tipos JSON-serializables (Decimal, date, time, UUID, etc.).
    Devuelve dict/list primitivos que Django/psycopg2 pueden guardar en JSONB.
    """
    try:
        return json.loads(json.dumps(obj, cls=DjangoJSONEncoder))
    except Exception:
        # último recurso: si no se pudo serializar, devolvemos {} o el valor original
        return {} if isinstance(obj, dict) else obj

def _send_email_ses(*, to: list[str] | tuple[str, ...], subject: str, text: str = "", html: str | None = None, tags: dict | None = None):
    """
    Envío resiliente vía Amazon SES.
    - Usa boto3 si está disponible; si no, loggea y sale.
    - No levanta excepción (no rompe el flujo de notificaciones in-app).
    """
    if not NOTIF_EMAIL_ENABLED:
        logger.debug("[notif.email][skip-disabled] to=%s subj=%s", to, subject)
        return
    if not boto3:
        logger.error("[notif.email][disabled-boto3-missing] to=%s subj=%s", to, subject)
        return
    if not to:
        logger.warning("[notif.email][skip-no-dest]")
        return

    client = boto3.client(
        "ses",
        region_name=SES_REGION,
        config=_BotoConfig(retries={"max_attempts": 3, "mode": "standard"}) if _BotoConfig else None,
    )

    body: dict = {}
    if html:
        body["Html"] = {"Data": html, "Charset": "UTF-8"}
    body["Text"] = {"Data": text or "", "Charset": "UTF-8"}

    kwargs = {
        "Source": SES_FROM,
        "Destination": {"ToAddresses": list(to)},
        "Message": {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": body,
        },
    }
    if SES_CONFIGURATION_SET:
        kwargs["ConfigurationSetName"] = SES_CONFIGURATION_SET
    if tags:
        kwargs["Tags"] = [{"Name": str(k), "Value": str(v)} for k, v in tags.items()]

    # Backoff simple con 5 intentos
    delay = 1.0
    for attempt in range(1, 6):
        try:
            resp = client.send_email(**kwargs)
            mid = resp.get("MessageId")
            logger.info("[notif.email][sent] id=%s to=%s subj=%s", mid, to, subject)
            return
        except _BotoClientError as e:  # type: ignore
            code = getattr(e, "response", {}).get("Error", {}).get("Code")
            retryable = code in {"Throttling", "ThrottlingException", "ServiceUnavailable", "InternalFailure"}
            logger.warning("[notif.email][fail] code=%s attempt=%s to=%s subj=%s", code, attempt, to, subject, exc_info=True)
            if retryable and attempt < 5:
                try:
                    import time
                    time.sleep(delay)
                    delay *= 2
                except Exception:
                    pass
                continue
            break
        except Exception:
            logger.exception("[notif.email][unexpected-error] to=%s subj=%s", to, subject)
            break

def publish_event(*, topic: str, actor, cliente_id: int | None, metadata: dict | None = None) -> NotificationEvent:
    md = _json_safe(metadata or {})
    ev = NotificationEvent.objects.create(
        topic=topic,
        actor=actor if getattr(actor, "id", None) else None,
        cliente_id=cliente_id,
        metadata=md,
    )
    logger.info(
        "[notif.event] created event_id=%s topic=%s cliente=%s meta_keys=%s",
        ev.id, ev.topic, ev.cliente_id, list(md.keys()) if isinstance(md, dict) else []
    )
    return ev


def _render_inapp_copy(notif_type: str, ctx: dict) -> tuple[str, str, str]:
    """
    Render mínimo sin plantillas (MVP). Devuelve (title, body, deeplink_path).
    ctx debe traer lo necesario según notif_type.
    """
    # Acepta tanto el enum como el string usado en el cron
    if notif_type in (TYPE_ABONO_RECORDATORIO, "abono_recordatorio"):
        # ctx esperado (flexible):
        #   abono_id, vence_el (YYYY-MM-DD), dias (int: 7 o 1),
        #   tipo (x1..x4 opcional), sede_nombre?, prestador?, hora?, dia_semana_text?
        dias = ctx.get("dias")
        vence_el = ctx.get("vence_el")
        tipo = ctx.get("tipo") or ctx.get("tipo_clase_codigo")  # x1..x4 u otro alias
        sede = ctx.get("sede_nombre")
        prestador = ctx.get("prestador")
        hora = ctx.get("hora")
        dsem = ctx.get("dia_semana_text")

        # Título claro según el caso
        if dias == 1:
            title = "¡Tu abono vence mañana!"
        elif dias == 7:
            title = "Tu abono vence en 7 días"
        else:
            title = "Recordatorio: vencimiento de tu abono"

        # Cuerpo con detalles (solo si existen en el contexto)
        partes = []
        if tipo:
            partes.append(f"Abono {tipo}")
        if sede:
            partes.append(f"en {sede}")
        if prestador:
            partes.append(f"con {prestador}")
        if hora:
            partes.append(f"a las {hora}")
        if dsem:
            partes.append(f"({dsem})")
        if vence_el:
            partes.append(f"• vence el {vence_el}")

        body = " ".join(partes) if partes else "Tu abono está por vencer."
        # Llevamos al usuario directo a su sección de abonos/renovación
        return title, body, "/abonos"

    # ------- NUEVO: Estado de abono (renovado / no renovado) -------
    # Compatibilidad con el string que manda el cron ("abono_estado")
    if notif_type in ("abono_estado", TYPE_ABONO_RENOVADO):
        # ctx flexible:
        #   mensaje? (si viene del cron), tipo?, anio?, mes?, sede_nombre?, prestador?, hora?, dia_semana_text?
        msg = ctx.get("mensaje")
        tipo = ctx.get("tipo")
        anio = ctx.get("anio"); mes = ctx.get("mes")
        sede = ctx.get("sede_nombre"); prestador = ctx.get("prestador")
        hora = ctx.get("hora"); dsem = ctx.get("dia_semana_text")

        # Si viene un mensaje literal desde el cron, lo priorizamos
        if msg:
            title = "Estado de tu abono"
            body = msg
            return title, body, "/abonos"

        # Si no, intentamos render más rico (ej.: renovado)
        title = "Estado de tu abono"
        partes = []
        if tipo: partes.append(f"Abono {tipo}")
        if anio and mes: partes.append(f"para {mes}/{anio}")
        if sede: partes.append(f"en {sede}")
        if prestador: partes.append(f"con {prestador}")
        if hora: partes.append(f"a las {hora}")
        if dsem: partes.append(f"({dsem})")
        body = " ".join(partes) if partes else "Actualizamos el estado de tu abono."
        return title, body, "/abonos"
    
    if notif_type == TYPE_BONIFICACION_CREADA:
        # Contexto esperado (flexible): 
        #   bonificacion_id, tipo_turno (x1/x2/x3/x4 o alias), motivo, valido_hasta,
        #   turno_id (opcional si proviene de cancelación), fecha, hora, sede_nombre.
        tipo = ctx.get("tipo_turno") or ctx.get("tipo") or ""
        motivo = ctx.get("motivo")
        vence = ctx.get("valido_hasta")
        fecha = ctx.get("fecha")
        hora = ctx.get("hora")
        sede = ctx.get("sede_nombre")

        title = "Nueva bonificación disponible"

        partes = []
        if tipo:
            partes.append(f"tipo {tipo}")
        if sede:
            partes.append(f"para {sede}")
        if fecha and hora:
            partes.append(f"(origen: {fecha} {hora})")
        if motivo:
            partes.append(f"— {motivo}")
        if vence:
            partes.append(f"• vence {vence}")

        body = " ".join(partes) if partes else "Podés usarla para reservar tu próximo turno."
        # Para usuarios finales, link directo a sus bonificaciones
        return title, body, "/bonificaciones"

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
    # Usamos on_commit para no enviar hasta que la tx quede confirmada
    from django.db import transaction as _tx
    to_send_queue: list[tuple[list[str], str, str, str | None, dict | None]] = []

    created = 0
    now = timezone.now()
    for u in recipients:
        raw_ctx = context_by_user.get(u.id, {})
        ctx = _json_safe(raw_ctx)  # ← Normalizamos el contexto
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
            "metadata": ctx,  # ← ctx ya es JSON-safe
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
            # Encolamos envío de email solo para notificaciones nuevas
            try:
                recipient_email = getattr(u, "email", None)
            except Exception:
                recipient_email = None
            if recipient_email:
                # Reutilizamos title/body como subject/text; html mínimo opcional
                html = f"<p>{body}</p>" if body else None
                # Etiquetas útiles para métricas por tenant y tipo
                tags = {"type": notif_type}
                if getattr(u, "cliente_id", None) is not None:
                    tags["cliente_id"] = str(getattr(u, "cliente_id"))
                to_send_queue.append(([recipient_email], title, body or "", html, tags))
        else:
            logger.debug(
                "[notif.inapp][skip-dedupe] user=%s type=%s event_id=%s key=%s",
                u.id, notif_type, event.id, dedupe_key
            )

    def _flush_email_queue():
        for to, subject, text, html, tags in to_send_queue:
            try:
                _send_email_ses(to=to, subject=subject, text=text, html=html, tags=tags)
            except Exception:
                logger.exception("[notif.email][queue-send-error] to=%s subj=%s", to, subject)

    _tx.on_commit(_flush_email_queue)

    try:
        total = len(recipients)
    except TypeError:
        total = None
    logger.info(
        "[notif.inapp] event_id=%s type=%s created=%s total_recipients=%s",
        event.id, notif_type, created, total if total is not None else "?"
    )
    return created
