# turnos_core/management/commands/generar_turnos_mensuales.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from apps.turnos_core.models import Prestador
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Genera turnos para todos los prestadores: el mes actual  y el mes siguiente como disponibles"

    def handle(self, *args, **kwargs):
        hoy = timezone.localdate()

        # Mes actual → turnos disponibles
        fecha_inicio_actual = hoy
        fecha_fin_actual = _ultimo_dia_del_mes(hoy)

        # Mes siguiente → turnos disponibles
        fecha_inicio_siguiente = _proximo_mes(hoy)
        fecha_fin_siguiente = _ultimo_dia_del_mes(fecha_inicio_siguiente)

        total_generados = 0

        for prestador in Prestador.objects.filter(activo=True):
            logger.info(f"[CRON] Generando para prestador {prestador.id} ({prestador})")

            creados_actual = generar_turnos_para_prestador(
                prestador.id, fecha_inicio_actual, fecha_fin_actual,
                estado="disponible"
            )
            creados_siguiente = generar_turnos_para_prestador(
                prestador.id, fecha_inicio_siguiente, fecha_fin_siguiente,
                estado="disponible"  
            )

            total_generados += creados_actual + creados_siguiente

        logger.info("[CRON] Total turnos generados: %s", total_generados)


def _proximo_mes(fecha: date) -> date:
    return date(fecha.year + 1, 1, 1) if fecha.month == 12 else date(fecha.year, fecha.month + 1, 1)

def _ultimo_dia_del_mes(fecha: date) -> date:
    from calendar import monthrange
    ultimo_dia = monthrange(fecha.year, fecha.month)[1]
    return date(fecha.year, fecha.month, ultimo_dia)
