# turnos_core/management/commands/generar_turnos_mensuales.py
# ------------------------------------------------------------------------------
# Management command: genera slots de turnos para TODOS los prestadores activos
# para:
#   - Mes actual  (desde hoy hasta último día del mes)
#   - Mes siguiente (del 1 al último día)
#
# Reglas / consideraciones:
# - Genera SIEMPRE con estado="disponible" (no asigna usuario ni tipo_turno).
# - La idempotencia la provee generar_turnos_para_prestador()
#   vía bulk_create(ignore_conflicts=True) + unique_together del modelo Turno.
# - Loguea por prestador y un total agregado al final para auditoría.
# - Útil para correr en CRON (ej. 1 vez por día/semana) sin duplicar.
# ------------------------------------------------------------------------------

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from apps.turnos_core.models import Prestador
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Genera turnos para todos los prestadores: el mes actual y el mes siguiente como disponibles"

    def handle(self, *args, **kwargs):
        # Punto de referencia temporal (fecha local del servidor)
        hoy = timezone.localdate()

        # ► Ventana 1: Mes actual → [hoy, último día del mes]
        fecha_inicio_actual = hoy
        fecha_fin_actual = _ultimo_dia_del_mes(hoy)

        # ► Ventana 2: Mes siguiente → [día 1, último día del mes siguiente]
        fecha_inicio_siguiente = _proximo_mes(hoy)
        fecha_fin_siguiente = _ultimo_dia_del_mes(fecha_inicio_siguiente)

        total_generados = 0

        # Itera solo prestadores activos (multi-tenant se respeta en generación por content_type/object_id)
        for prestador in Prestador.objects.filter(activo=True):
            logger.info(f"[CRON] Generando para prestador {prestador.id} ({prestador})")

            # Mes actual (estado disponible)
            creados_actual = generar_turnos_para_prestador(
                prestador.id, fecha_inicio_actual, fecha_fin_actual,
                estado="disponible"
            )

            # Mes siguiente (estado disponible)
            creados_siguiente = generar_turnos_para_prestador(
                prestador.id, fecha_inicio_siguiente, fecha_fin_siguiente,
                estado="disponible"
            )

            total_generados += creados_actual + creados_siguiente

        logger.info("[CRON] Total turnos generados: %s", total_generados)


def _proximo_mes(fecha: date) -> date:
    """
    Devuelve el primer día del mes siguiente a 'fecha'.
    Ej.: 2025-01-15 -> 2025-02-01 ; 2025-12-10 -> 2026-01-01
    """
    return date(fecha.year + 1, 1, 1) if fecha.month == 12 else date(fecha.year, fecha.month + 1, 1)

def _ultimo_dia_del_mes(fecha: date) -> date:
    """
    Devuelve el último día del mes de 'fecha'.
    Ej.: 2025-02-10 -> 2025-02-28 (o 29 si bisiesto)
    """
    from calendar import monthrange
    ultimo_dia = monthrange(fecha.year, fecha.month)[1]
    return date(fecha.year, fecha.month, ultimo_dia)
