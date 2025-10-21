# apps/auth_core/services.py
"""
Servicios para el sistema de autenticación con email/contraseña.
"""

import random
import logging
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from apps.notificaciones_core.services import _send_email_ses

logger = logging.getLogger(__name__)


def send_verification_code_email(email: str, codigo: str, intent: str, cliente_nombre: str):
    """
    Envía email con código de verificación usando el sistema existente.
    """
    # Determinar el tipo de notificación según el intent
    notif_type = "verificacion_registro" if intent == "registro" else "verificacion_reset"
    
    # Contexto para el template
    ctx = {
        "codigo": codigo,
        "email": email,
        "intent": intent,
        "cliente_nombre": cliente_nombre,
        "expira_en": "10 minutos",
        "tenant": cliente_nombre,
        "brand_color": getattr(settings, "PUBLIC_BRAND_COLOR", "#111827"),
        "year": timezone.now().year,
    }
    
    # Renderizar templates
    try:
        html = render_to_string(f"emails/{notif_type}.html", ctx).strip()
    except:
        html = None
    
    try:
        text = render_to_string(f"emails/{notif_type}.txt", ctx).strip()
    except:
        text = None
    
    # Fallback si no hay templates
    if not html:
        html = f"""
        <!doctype html>
        <html><body style="font-family: system-ui, -apple-system, Segoe UI, Roboto;">
          <div style="max-width:600px;margin:auto;border:1px solid #eee;border-radius:12px;padding:24px">
            <h2 style="margin:0 0 12px 0">Código de Verificación</h2>
            <p>Tu código de verificación es:</p>
            <div style="font-size:32px;font-weight:bold;text-align:center;background:#f5f5f5;padding:20px;border-radius:8px;margin:20px 0;letter-spacing:4px">
              {codigo}
            </div>
            <p>Este código expira en {ctx['expira_en']}.</p>
            <p style="margin-top:28px">Saludos!<br><b>{cliente_nombre}</b></p>
          </div>
          <p style="text-align:center;color:#888;font-size:12px">© {ctx['year']} {cliente_nombre}</p>
        </body></html>
        """
    
    if not text:
        text = f"""
Código de Verificación

Tu código de verificación es: {codigo}

Este código expira en {ctx['expira_en']}.

Saludos!
{cliente_nombre}
        """
    
    # Enviar email
    subject = f"Código de verificación - {cliente_nombre}"
    _send_email_ses(
        to=[email],
        subject=subject,
        text=text,
        html=html,
        tags={"type": "verification", "intent": intent}
    )
    
    logger.info(f"[VERIFICATION EMAIL] Enviado código {codigo} a {email} para {intent}")


def generate_verification_code() -> str:
    """
    Genera un código de verificación de 6 dígitos.
    """
    return str(random.randint(100000, 999999))


def cleanup_expired_codes():
    """
    Limpia códigos de verificación expirados.
    """
    from .models import CodigoVerificacion
    
    expired = CodigoVerificacion.objects.filter(
        expira__lt=timezone.now()
    )
    count = expired.count()
    expired.delete()
    
    logger.info(f"[CLEANUP] Eliminados {count} códigos expirados")
    return count
