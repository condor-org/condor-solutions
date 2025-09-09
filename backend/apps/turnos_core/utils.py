# apps/turnos_core/utils.py
# ------------------------------------------------------------------------------
# Utilidades de negocio para turnos:
# - Políticas de cancelación por anticipación (cumple_politica_cancelacion)
# ------------------------------------------------------------------------------

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

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
