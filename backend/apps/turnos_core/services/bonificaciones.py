# apps/turnos_core/services/bonificaciones.py
# ------------------------------------------------------------------------------
# Servicio de emisión, consulta, uso y administración de "TurnoBonificado".
# - Emisión automática (por cancelación válida) y manual (por admin).
# - Consultas de bonos vigentes (con vencimiento opcional).
# - Aplicación de bono a un turno (marca como usado y referencia al turno).
# - Utilidad para eliminar un bono puntual (control manual).
# - Publica eventos y notifica in-app al usuario cuando se emite un bono.
# - Todas las mutaciones críticas van dentro de transacciones atómicas.
# ------------------------------------------------------------------------------

from datetime import timedelta
from django.utils import timezone
from django.db import models, transaction
from apps.turnos_core.models import TurnoBonificado, Turno
import logging
from apps.notificaciones_core.services import (
    publish_event,
    notify_inapp,
)

TYPE_BONIFICACION_CREADA = "BONIFICACION_CREADA"

logger = logging.getLogger(__name__)

# -----------------------------
# EMISIÓN DE BONIFICACIONES
# -----------------------------

@transaction.atomic
def emitir_bonificacion_automatica(usuario, turno_original, motivo="Cancelación válida", valido_hasta=None):
    """
    Emite un bono automáticamente asociado a un turno cancelado.
    ► Regla de negocio:
      - Requiere que el turno_original tenga tipo_turno seteado (x1/x2/x3/x4).
      - El bono hereda ese tipo_turno para respetar equivalencia (misma clase).
      - Se marca 'generado_automaticamente=True' y se deja audit trail (motivo/validez).
      - Publica evento y envía notificación in-app al usuario (best-effort).

    ► Entradas:
      - usuario: User dueño del crédito.
      - turno_original: Turno cancelado que origina la bonificación.
      - motivo (str): razón visible en auditoría/notificación.
      - valido_hasta (date|None): fecha de expiración opcional.

    ► Salida:
      - TurnoBonificado creado.

    ► Transaccionalidad:
      - Atómico: creación de bono y side effects coherentes en caso de error.
    """
    if not getattr(turno_original, "tipo_turno", None):
        raise ValueError("turno_original.tipo_turno es requerido para emitir bonificación automática.")

    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        turno_original=turno_original,
        motivo=motivo,
        generado_automaticamente=True,
        valido_hasta=valido_hasta,
        tipo_turno=turno_original.tipo_turno,  # << clave: mantiene equivalencia del tipo
    )
    logger.info(
        "[BONIFICACION][auto] user=%s turno=%s tipo=%s",
        getattr(usuario, "id", None), getattr(turno_original, "id", None), getattr(turno_original, "tipo_turno", None)
    )
    try:
        ev = publish_event(
            topic="bonificaciones.automatica",
            actor=usuario,
            cliente_id=getattr(usuario, "cliente_id", None),
            metadata={
                "bonificacion_id": bono.id,
                "turno_original": turno_original.id,
                "tipo_turno": str(turno_original.tipo_turno),
                "motivo": motivo,
            },
        )
        notify_inapp(
            event=ev,
            recipients=[usuario],
            notif_type=TYPE_BONIFICACION_CREADA,
            severity="info",
            context_by_user={
                usuario.id: {
                    "bonificacion_id": bono.id,
                    "tipo_turno": str(turno_original.tipo_turno),
                }
            },
        )
        logger.info("[notif][bonif.auto] user=%s bono=%s", getattr(usuario, "id", None), bono.id)
    except Exception:
        # Notificaciones son best-effort: si fallan no se revierte la emisión.
        logger.exception("[notif][bonif.auto][fail] bono=%s", bono.id)
    return bono


@transaction.atomic
def emitir_bonificacion_manual(admin_user, usuario, motivo="Bonificación manual", valido_hasta=None, tipo_turno=None):
    """
    Emite un bono manualmente (acción de admin).
    ► Regla de negocio:
      - tipo_turno es obligatorio (x1/x2/x3/x4 o equivalentes ya mapeados).
      - Marca 'generado_automaticamente=False' y guarda 'emitido_por'.
      - Publica evento y notifica in-app al usuario (best-effort).

    ► Entradas:
      - admin_user: User admin que emite el bono.
      - usuario: destinatario.
      - motivo (str): descripción visible.
      - valido_hasta (date|None): expiración.
      - tipo_turno (str): código canónico del turno.

    ► Salida:
      - TurnoBonificado creado.

    ► Transaccionalidad:
      - Atómico.
    """
    if not tipo_turno:
        raise ValueError("tipo_turno es obligatorio para bonificación manual.")

    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        motivo=motivo,
        generado_automaticamente=False,
        emitido_por=admin_user,
        valido_hasta=valido_hasta,
        tipo_turno=tipo_turno,  # << clave
    )
    logger.info(
        "[BONIFICACION][manual] admin=%s user=%s tipo=%s",
        getattr(admin_user, "id", None), getattr(usuario, "id", None), tipo_turno
    )
    try:
        ev = publish_event(
            topic="bonificaciones.manual",
            actor=admin_user,
            cliente_id=getattr(usuario, "cliente_id", None),
            metadata={
                "bonificacion_id": bono.id,
                "tipo_turno": str(tipo_turno),
                "motivo": motivo,
            },
        )
        notify_inapp(
            event=ev,
            recipients=[usuario],
            notif_type=TYPE_BONIFICACION_CREADA,
            severity="info",
            context_by_user={
                usuario.id: {
                    "bonificacion_id": bono.id,
                    "tipo_turno": str(tipo_turno),
                }
            },
        )
        logger.info("[notif][bonif.manual] user=%s bono=%s", getattr(usuario, "id", None), bono.id)
    except Exception:
        logger.exception("[notif][bonif.manual][fail] bono=%s", bono.id)
    return bono


# -----------------------------
# CONSULTAS DE BONIFICACIONES
# -----------------------------

def bonificaciones_vigentes(usuario):
    """
    Devuelve queryset de bonos vigentes (no usados y no vencidos).
    ► Regla:
      - usado=False
      - valido_hasta is null OR valido_hasta >= hoy
    ► Uso:
      - Base para filtros adicionales (por tipo, etc.).
    """
    hoy = timezone.now().date()
    return TurnoBonificado.objects.filter(
        usuario=usuario,
        usado=False
    ).filter(
        models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=hoy)
    )

def bonificaciones_vigentes_por_tipo(usuario, tipo_turno):
    """
    Azúcar sintáctico: vigentes filtradas por tipo_turno exacto.
    """
    return bonificaciones_vigentes(usuario).filter(tipo_turno=tipo_turno)


def tiene_bonificaciones_disponibles(usuario):
    """
    True si el usuario posee al menos un bono vigente sin usar.
    (Consulta eficiente: .exists())
    """
    return bonificaciones_vigentes(usuario).exists()


def cantidad_bonificaciones(usuario):
    """
    Conteo de bonos vigentes disponibles.
    """
    return bonificaciones_vigentes(usuario).count()


# -----------------------------
# APLICACIÓN DE BONIFICACIÓN
# -----------------------------

@transaction.atomic
def usar_bonificacion(usuario, turno, tipo_turno=None):
    """
    Marca como usada la primera bonificación vigente (opcionalmente filtrada por tipo).
    ► Flujo:
      - Obtiene bonificaciones vigentes del usuario (opcionalmente por tipo_turno).
      - Toma la primera (orden natural de DB).
      - Setea usado=True y referencia usado_en_turno.
      - Devuelve el bono aplicado o None si no había disponible.

    ► Entradas:
      - usuario: dueño del bono.
      - turno: turno a asociar.
      - tipo_turno (str|None): si se pasa, filtra por ese tipo exacto.

    ► Salida:
      - TurnoBonificado | None

    ► Transaccionalidad:
      - Atómico para evitar carreras en consumo de bono.
    """
    qs = bonificaciones_vigentes(usuario)
    if tipo_turno:
        qs = qs.filter(tipo_turno=tipo_turno)

    bono = qs.first()
    if not bono:
        logger.info("[BONIFICACION][usar][no_disp] user=%s tipo=%s", getattr(usuario, "id", None), tipo_turno)
        return None

    bono.usado = True
    bono.usado_en_turno = turno
    bono.save(update_fields=["usado", "usado_en_turno"])

    logger.info(
        "[BONIFICACION][usar] user=%s bono=%s turno=%s tipo=%s",
        getattr(usuario, "id", None), bono.id, getattr(turno, "id", None), bono.tipo_turno
    )
    return bono
    
# -----------------------------
# UTILIDADES AVANZADAS (opcional)
# -----------------------------

@transaction.atomic
def eliminar_bonificacion(bonificacion_id, motivo_admin="Eliminada por administrador"):
    """
    Elimina una bonificación específica (control administrativo).
    ► Notas:
      - No hay eventos/alertas asociadas por ahora (solo logging).
      - Devuelve True si eliminó, False si no existía.
    """
    try:
        bono = TurnoBonificado.objects.get(pk=bonificacion_id)
        logger.warning("[BONIFICACION] Bonificación %s eliminada. Motivo: %s", bono.id, motivo_admin)
        bono.delete()
        return True
    except TurnoBonificado.DoesNotExist:
        return False
