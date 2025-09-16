# apps/notificaciones_core/services.py
import logging
from typing import Iterable, Mapping
from datetime import date, time
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.template.loader import render_to_string
import json
import os

try:
    # boto3 puede no estar instalado en dev
    import boto3
    from botocore.config import Config as _BotoConfig
    from botocore.exceptions import ClientError as _BotoClientError
except Exception:
    boto3 = None
    _BotoConfig = None
    _BotoClientError = Exception

logger = logging.getLogger(__name__)
Usuario = get_user_model()

# Evitar import circular: Prestador sólo para chequeo de tipo del GFK "recurso"
try:
    from apps.turnos_core.models import Prestador  # type: ignore
except Exception:
    Prestador = type("PrestadorPlaceholder", (), {})  # fallback innocuo


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
                    import time as _t
                    _t.sleep(delay)
                    delay *= 2
                except Exception:
                    pass
                continue
            break
        except Exception:
            logger.exception("[notif.email][unexpected-error] to=%s subj=%s", to, subject)
            break


def publish_event(*, topic: str, actor, cliente_id: int | None, metadata: dict | None = None):
    from .models import NotificationEvent  # local import para evitar ciclos
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


# -----------------------
# Helpers de presentación
# -----------------------

def _public_base_url() -> str:
    """URL pública del frontend para armar CTA en mails."""
    return getattr(settings, "PUBLIC_APP_BASE_URL", "https://lob-padel.cnd-ia.com").rstrip("/")


def _template_base_name_for(notif_type: str) -> str:
    """Mapea el tipo de notificación al nombre base de la plantilla de email."""
    return {
        TYPE_RESERVA_TURNO: "reserva_turno",
        TYPE_CANCELACION_TURNO: "cancelacion_turno",
        TYPE_RESERVA_ABONO: "reserva_abono",
        TYPE_ABONO_RENOVADO: "abono_renovado",
        TYPE_BONIFICACION_CREADA: "bonificacion_creada",
        TYPE_CANCELACIONES_TURNOS: "cancelaciones_turnos",
        TYPE_ABONO_RECORDATORIO: "abono_recordatorio",
    }.get(notif_type, "generic")


def _human_tipo_clase(val: str | None) -> str:
    """
    Normaliza el tipo de turno para mostrar al usuario.
    x1/x2/x3/x4 -> textos humanos. Si ya viene humanizado, lo deja tal cual.
    """
    s = (val or "").strip().lower()
    return {
        "x1": "clase individual",
        "x2": "clase para 2 personas",
        "x3": "clase para 3 personas",
        "x4": "clase para 4 personas",
    }.get(s, val or "")


def _nombre_completo(user) -> str:
    if not user:
        return "Usuario"
    nombre = (getattr(user, "nombre", "") or getattr(user, "first_name", "")).strip()
    apellido = (getattr(user, "apellido", "") or getattr(user, "last_name", "")).strip()
    full = f"{nombre} {apellido}".strip()
    return full or getattr(user, "email", "") or "Usuario"


def _safe_date_str(d: date | None, fmt: str = "%d/%m/%Y") -> str:
    try:
        return d.strftime(fmt) if d else ""
    except Exception:
        return ""


def _safe_time_str(t: time | None, fmt: str = "%H:%M") -> str:
    try:
        return t.strftime(fmt) if t else ""
    except Exception:
        return ""


def _prestador_display_from_turno(turno) -> str:
    """
    Si el GFK 'recurso' del turno es un Prestador, devuelve un nombre mostrable.
    Usa 'nombre_publico' y si no, cae al usuario vinculado.
    """
    try:
        recurso = getattr(turno, "recurso", None)
        if recurso and isinstance(recurso, Prestador):
            # 1) nombre público si está
            if getattr(recurso, "nombre_publico", None):
                return recurso.nombre_publico
            # 2) si no, del user asociado
            u = getattr(recurso, "user", None)
            if u:
                return _nombre_completo(u)
    except Exception:
        logger.debug("[notif.ctx][prestador-fallback]", exc_info=True)
    return ""


def build_ctx_reserva_usuario(turno, usuario) -> dict:
    """
    Contexto seguro para el mail al USUARIO cuando reserva un turno.
    No levanta excepciones si faltan datos.
    """
    sede = getattr(turno, "lugar", None)
    ctx = {
        "audience": "user",
        "usuario": _nombre_completo(usuario),
        "fecha": _safe_date_str(getattr(turno, "fecha", None)),
        "hora": _safe_time_str(getattr(turno, "hora", None)),
        "sede_nombre": getattr(sede, "nombre", "") if sede else "",
        "sede_direccion": getattr(sede, "direccion", "") if sede else "",
        "prestador": _prestador_display_from_turno(turno),
        "tipo_turno": _human_tipo_clase(getattr(turno, "tipo_turno", "")),
        "reserva_id": getattr(turno, "id", None),
        "politicas_breve": "Podés cancelar hasta 12 h antes sin cargo.",
        # "force_url": "/mis-reservas",  # opcional para forzar CTA
    }
    return ctx


# -----------------------
# Render de copies (in-app / email)
# -----------------------

def _render_email_copy(notif_type: str, ctx: dict) -> tuple[str, str, str]:
    """
    Devuelve (subject, text, html) renderizados desde templates.
    - Soporta variantes por audiencia con ctx['audience'] = 'user' | 'admin'.
    - Fallback a generic.* y, si no hay, arma un HTML/TXT básico.
    - Siempre agrega saludo corporativo "Saludos! LOB Padel".
    """
    title, body, deeplink = _render_inapp_copy(notif_type, ctx or {})
    url = (ctx.get("force_url") or (_public_base_url() + (deeplink or "/")))

    base = _template_base_name_for(notif_type)
    audience = (ctx or {}).get("audience")
    names_to_try = [f"{base}__{audience}", base] if audience else [base]

    # Humanizamos tipos en el contexto que va al template
    _ctx = dict(ctx or {})
    for k in ("tipo", "tipo_turno", "tipo_clase_codigo"):
        if k in _ctx:
            _ctx[k] = _human_tipo_clase(_ctx.get(k))

    tctx = {
        "title": title or "Notificación",
        "body": body or "",
        "deeplink": deeplink,
        "url": url,
        "ctx": _ctx,
        "tenant": getattr(settings, "PUBLIC_CLIENTE_NAME", "Condor"),
        "brand_color": getattr(settings, "PUBLIC_BRAND_COLOR", "#111827"),
        "year": timezone.now().year,
    }

    text = html = None
    for name in names_to_try:
        try:
            html = html or render_to_string(f"emails/{name}.html", tctx).strip()
        except Exception:
            pass
        try:
            text = text or render_to_string(f"emails/{name}.txt", tctx).strip()
        except Exception:
            pass
        if text and html:
            break

    # Fallbacks + saludo
    if not text:
        text = f"""{tctx['title']}

{tctx['body']}

Abrir: {url}

Saludos!
LOB Padel"""
    else:
        text = text.rstrip() + "\n\nSaludos!\nLOB Padel"

    if not html:
        html = f"""<h2>{tctx['title']}</h2><p>{tctx['body']}</p><p><a href="{url}">Abrir</a></p><br><br>Saludos!<br><b>LOB Padel</b>"""
    else:
        html = html.rstrip() + "<br><br>Saludos!<br><b>LOB Padel</b>"

    subject = tctx["title"]
    return subject, text, html


def _render_inapp_copy(notif_type: str, ctx: dict) -> tuple[str, str, str]:
    """
    Render mínimo sin plantillas (MVP). Devuelve (title, body, deeplink_path).
    ctx debe traer lo necesario según notif_type.
    """
    # Acepta tanto el enum como el string usado en el cron
    if notif_type in (TYPE_ABONO_RECORDATORIO, "abono_recordatorio"):
        dias = ctx.get("dias")
        vence_el = ctx.get("vence_el")
        tipo = _human_tipo_clase(ctx.get("tipo") or ctx.get("tipo_clase_codigo"))
        sede = ctx.get("sede_nombre")
        prestador = ctx.get("prestador")
        hora = ctx.get("hora")
        dsem = ctx.get("dia_semana_text")

        if dias == 1:
            title = "¡Tu abono vence mañana!"
        elif dias == 7:
            title = "Tu abono vence en 7 días"
        else:
            title = "Recordatorio: vencimiento de tu abono"

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
        return title, body, "/abonos"

    # Estado de abono (renovado / no renovado)
    if notif_type in ("abono_estado", TYPE_ABONO_RENOVADO):
        msg = ctx.get("mensaje")
        tipo = _human_tipo_clase(ctx.get("tipo"))
        anio = ctx.get("anio"); mes = ctx.get("mes")
        sede = ctx.get("sede_nombre"); prestador = ctx.get("prestador")
        hora = ctx.get("hora"); dsem = ctx.get("dia_semana_text")

        if msg:
            return "Estado de tu abono", msg, "/abonos"

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
        tipo = _human_tipo_clase(ctx.get("tipo_turno") or ctx.get("tipo") or "")
        motivo = ctx.get("motivo")
        vence = ctx.get("valido_hasta")
        fecha = ctx.get("fecha")
        hora = ctx.get("hora")
        sede = ctx.get("sede_nombre")

        title = "Nueva bonificación disponible"

        partes = []
        if tipo:
            partes.append(tipo)
        if sede:
            partes.append(f"para {sede}")
        if fecha and hora:
            partes.append(f"(origen: {fecha} {hora})")
        if motivo:
            partes.append(f"— {motivo}")
        if vence:
            partes.append(f"• vence {vence}")

        body = " ".join(partes) if partes else "Podés usarla para reservar tu próximo turno."
        return title, body, "/bonificaciones"

    if notif_type == TYPE_CANCELACIONES_TURNOS:
        n = ctx.get("n_cancelados", 1)
        sede = ctx.get("sede_nombre") or "la sede"
        f1 = ctx.get("fecha_desde")
        f2 = ctx.get("fecha_hasta")
        n_bonos = ctx.get("n_bonos", n)
        title = f"Se cancelaron {n} turno(s) en {sede}"
        body = f"Entre {f1} y {f2}. Acreditamos {n_bonos} bono(s)."
        return title, body, "/bonificaciones"

    if notif_type == TYPE_RESERVA_TURNO:
        usuario = ctx.get("usuario") or "Usuario"
        fecha = ctx.get("fecha")
        hora = ctx.get("hora")
        sede = ctx.get("sede_nombre") or "sede"
        prestador = ctx.get("prestador") or ""
        title = "Nueva reserva de turno"
        body = f"{usuario} reservó {fecha} {hora} en {sede}{f' con {prestador}' if prestador else ''}."
        return title, body, f"/admin/reservas?fecha={fecha}"

    if notif_type == TYPE_RESERVA_ABONO:
        usuario = ctx.get("usuario") or "Usuario"
        tipo = _human_tipo_clase(ctx.get("tipo") or "")
        abono_id = ctx.get("abono_id")
        sede = ctx.get("sede_nombre")
        prestador = ctx.get("prestador")
        hora = ctx.get("hora")
        dia_semana_text = ctx.get("dia_semana_text")

        title = f"Nuevo abono {tipo}".strip()
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
        usuario = ctx.get("usuario") or "Usuario"
        tipo = _human_tipo_clase(ctx.get("tipo") or "")
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


# -----------------------
# Creación de notificaciones + envío de emails
# -----------------------

@transaction.atomic
def notify_inapp(
    *,
    event,
    recipients: Iterable[Usuario],
    notif_type: str,
    context_by_user: Mapping[int, dict],
    severity: str = "info",
) -> int:
    """
    Crea notificaciones in-app por usuario con idempotencia por dedupe_key.
    Retorna cantidad efectivamente creadas (nuevas).
    """
    from .models import Notification  # local import para evitar ciclos
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
                subject, text, html = _render_email_copy(notif_type, ctx)

                # Etiquetas útiles para métricas por tenant y tipo
                tags = {"type": notif_type}
                if getattr(u, "cliente_id", None) is not None:
                    tags["cliente_id"] = str(getattr(u, "cliente_id"))

                to_send_queue.append(([recipient_email], subject, text or "", html, tags))
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