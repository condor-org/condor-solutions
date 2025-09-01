# apps/turnos_core/utils.py
# ------------------------------------------------------------------------------
# Utilidades de negocio para turnos:
# - Validación de bloqueos administrativos (esta_bloqueado)
# - Políticas de cancelación por anticipación (cumple_politica_cancelacion)
# ------------------------------------------------------------------------------

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from .models import BloqueoTurnos
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

def esta_bloqueado(recurso, lugar, fecha):
    """
    Devuelve True si el recurso (ej. un Prestador) está bloqueado en esa fecha.

    ► Reglas:
      - Un BloqueoTurnos aplica si:
        * activo=True
        * rango [fecha_inicio, fecha_fin] contiene la fecha
        * mismo recurso (via GenericFK content_type + object_id)
        * y (lugar == lugar solicitado) OR (lugar es null → bloqueo global del recurso)
    ► Entradas:
      - recurso: instancia de modelo bloqueable (ej. Prestador)
      - lugar: sede específica a validar
      - fecha: date de turno
    ► Salida:
      - bool (True si está bloqueado, False si no)
    """
    ct = ContentType.objects.get_for_model(recurso.__class__)
    return BloqueoTurnos.objects.filter(
        content_type=ct,
        object_id=recurso.id,
        activo=True,
        fecha_inicio__lte=fecha,
        fecha_fin__gte=fecha
    ).filter(
        Q(lugar=lugar) | Q(lugar__isnull=True)  # bloqueo específico o global
    ).exists()


def cumple_politica_cancelacion(turno):
    """
    Verifica si un turno cumple la política de cancelación.

    ► Regla actual (hardcoded):
      - Solo se permite cancelar hasta 6 horas antes del turno.
    ► Entradas:
      - turno: instancia Turno (usa .fecha y .hora)
    ► Salida:
      - bool (True si cumple, False si no)
    """
    ahora = make_aware(datetime.now())
    dt_turno = make_aware(datetime.combine(turno.fecha, turno.hora))
    return dt_turno - ahora >= timedelta(hours=6)
