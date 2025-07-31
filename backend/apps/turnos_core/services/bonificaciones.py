# apps/turnos_core/services/bonificaciones.py

from datetime import timedelta
from django.utils import timezone
from django.db import models, transaction
from apps.turnos_core.models import TurnoBonificado, Turno
import logging

logger = logging.getLogger(__name__)


# -----------------------------
# EMISIÓN DE BONIFICACIONES
# -----------------------------

@transaction.atomic
def emitir_bonificacion_automatica(usuario, turno_original, motivo="Cancelación válida", valido_hasta=None):
    """
    Emite un turno bonificado automáticamente, asociado a un turno original cancelado.
    """
    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        turno_original=turno_original,
        motivo=motivo,
        generado_automaticamente=True,
        valido_hasta=valido_hasta
    )
    logger.info(f"[BONIFICACION] Automática creada para {usuario} desde turno {turno_original.id}")
    return bono


@transaction.atomic
def emitir_bonificacion_manual(admin_user, usuario, motivo="Bonificación manual", valido_hasta=None):
    """
    Permite al admin emitir un turno bonificado sin turno original asociado.
    """
    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        motivo=motivo,
        generado_automaticamente=False,
        emitido_por=admin_user,
        valido_hasta=valido_hasta
    )
    logger.info(f"[BONIFICACION] Manual creada por {admin_user} para {usuario}")
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
def usar_bonificacion(usuario, turno):
    """
    Aplica la primera bonificación vigente del usuario al turno dado.
    Marca el turno como reservado y la bonificación como usada.
    """
    bono = bonificaciones_vigentes(usuario).first()

    if not bono:
        logger.info(f"[BONIFICACION] Usuario {usuario} intentó usar bono pero no tiene disponibles.")
        return None

    bono.usado = True
    bono.usado_en_turno = turno
    bono.save(update_fields=["usado", "usado_en_turno"])

    logger.info(f"[BONIFICACION] Usuario {usuario} usó bonificación ID {bono.id} en turno {turno.id}")
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
