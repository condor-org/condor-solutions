from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.turnos_padel.models import AbonoMes
from apps.turnos_padel.services.abonos import (
    reservar_abono_mes_actual_y_prioridad,
    liberar_abono_por_vencimiento
)
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Procesa todos los abonos del mes: vencimiento y reservas según renovación"

    def handle(self, *args, **kwargs):
        hoy = timezone.localdate()
        anio, mes = hoy.year, hoy.month
        logger.info("[ABONOS] Procesando abonos del %04d-%02d", anio, mes)

        abonos = AbonoMes.objects.filter(anio=anio, mes=mes)

        vencidos = 0
        renovados = 0
        errores = 0

        for abono in abonos:
            try:
                if abono.estado == "pagado":
                    logger.info("[ABONOS] Renovado: abono %s (usuario=%s)", abono.id, abono.usuario)
                    reservar_abono_mes_actual_y_prioridad(abono, abono.comprobante_abono)
                    renovados += 1
                else:
                    liberar_abono_por_vencimiento(abono)
                    vencidos += 1
            except Exception as e:
                logger.exception("[ABONOS] Error procesando abono %s: %s", abono.id, str(e))
                errores += 1

        logger.info("[ABONOS] Finalizado: %s renovados, %s vencidos, %s con errores", renovados, vencidos, errores)
