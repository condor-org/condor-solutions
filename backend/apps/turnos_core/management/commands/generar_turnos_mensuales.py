from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from apps.turnos_core.models import Prestador
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Genera turnos para todos los prestadores hasta 2 meses desde hoy"

    def handle(self, *args, **kwargs):
        hoy = timezone.localdate()
        fecha_inicio = hoy
        fecha_fin = _ultimo_dia_del_mes(_proximo_mes(hoy))

        logger.info("[CRON] Generando turnos desde %s hasta %s", fecha_inicio, fecha_fin)

        total_generados_global = 0
        for prestador in Prestador.objects.filter(activo=True):
            creados = generar_turnos_para_prestador(prestador.id, fecha_inicio, fecha_fin)
            logger.info("[CRON] Prestador %s (%s): %s turnos generados", prestador.id, prestador, creados)
            total_generados_global += creados

        logger.info("[CRON] Total turnos generados: %s", total_generados_global)


def _proximo_mes(fecha: date) -> date:
    return date(fecha.year + 1, 1, 1) if fecha.month == 12 else date(fecha.year, fecha.month + 1, 1)

def _ultimo_dia_del_mes(fecha: date) -> date:
    from calendar import monthrange
    ultimo_dia = monthrange(fecha.year, fecha.month)[1]
    return date(fecha.year, fecha.month, ultimo_dia)
