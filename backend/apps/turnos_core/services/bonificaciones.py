# apps/turnos_core/services/bonificaciones.py

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
    Emite un turno bonificado automáticamente, asociado a un turno original cancelado.
    El bono queda atado al mismo tipo_turno del turno original.
    """
    if not getattr(turno_original, "tipo_turno", None):
        raise ValueError("turno_original.tipo_turno es requerido para emitir bonificación automática.")

    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        turno_original=turno_original,
        motivo=motivo,
        generado_automaticamente=True,
        valido_hasta=valido_hasta,
        tipo_turno=turno_original.tipo_turno,  # << clave
    )
    logger.info(f"[BONIFICACION][auto] user={usuario.id} turno={turno_original.id} tipo={turno_original.tipo_turno}")
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
        logger.info("[notif][bonif.auto] user=%s bono=%s", usuario.id, bono.id)
    except Exception:
        logger.exception("[notif][bonif.auto][fail] bono=%s", bono.id)
    return bono


@transaction.atomic
def emitir_bonificacion_manual(admin_user, usuario, motivo="Bonificación manual", valido_hasta=None, tipo_turno=None):
    """
    Permite al admin emitir un turno bonificado manual, atado a un tipo_turno específico.
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
    logger.info(f"[BONIFICACION][manual] admin={admin_user.id} user={usuario.id} tipo={tipo_turno}")
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
        logger.info("[notif][bonif.manual] user=%s bono=%s", usuario.id, bono.id)
    except Exception:
        logger.exception("[notif][bonif.manual][fail] bono=%s", bono.id)
    return bono



# -----------------------------
# CONSULTAS DE BONIFICACIONES
# -----------------------------

def bonificaciones_vigentes(usuario):
    """
    Retorna los turnos bonificados disponibles y vigentes para el usuario.
    """
    hoy = timezone.now().date()
    return TurnoBonificado.objects.filter(
        usuario=usuario,
        usado=False
    ).filter(
        models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=hoy)
    )

def bonificaciones_vigentes_por_tipo(usuario, tipo_turno):
    return bonificaciones_vigentes(usuario).filter(tipo_turno=tipo_turno)


def tiene_bonificaciones_disponibles(usuario):
    """
    Devuelve True si el usuario tiene al menos un bono vigente sin usar.
    """
    return bonificaciones_vigentes(usuario).exists()


def cantidad_bonificaciones(usuario):
    """
    Cantidad de bonificaciones disponibles para el usuario.
    """
    return bonificaciones_vigentes(usuario).count()


# -----------------------------
# APLICACIÓN DE BONIFICACIÓN
# -----------------------------

@transaction.atomic
def usar_bonificacion(usuario, turno, tipo_turno=None):
    """
    Marca como usada una bonificación vigente. Si se pasa tipo_turno, filtra por ese tipo.
    """
    qs = bonificaciones_vigentes(usuario)
    if tipo_turno:
        qs = qs.filter(tipo_turno=tipo_turno)

    bono = qs.first()
    if not bono:
        logger.info(f"[BONIFICACION][usar][no_disp] user={usuario.id} tipo={tipo_turno}")
        return None

    bono.usado = True
    bono.usado_en_turno = turno
    bono.save(update_fields=["usado", "usado_en_turno"])

    logger.info(f"[BONIFICACION][usar] user={usuario.id} bono={bono.id} turno={turno.id} tipo={bono.tipo_turno}")
    return bono
    
# -----------------------------
# UTILIDADES AVANZADAS (opcional)
# -----------------------------

@transaction.atomic
def eliminar_bonificacion(bonificacion_id, motivo_admin="Eliminada por administrador"):
    """
    Permite eliminar una bonificación específica, opcionalmente por control manual.
    """
    try:
        bono = TurnoBonificado.objects.get(pk=bonificacion_id)
        logger.warning(f"[BONIFICACION] Bonificación {bono.id} eliminada. Motivo: {motivo_admin}")
        bono.delete()
        return True
    except TurnoBonificado.DoesNotExist:
        return False
