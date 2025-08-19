from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.turnos_padel.models import AbonoMes
from apps.turnos_padel.services.abonos import (
    reservar_abono_mes_actual_y_prioridad,
    liberar_abono_por_vencimiento,
    procesar_renovacion_de_abono
)
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Procesa abonos: crea nuevos por renovación o libera los vencidos"

    def handle(self, *args, **kwargs):
        hoy = timezone.localdate()
        anio, mes = hoy.year, hoy.month
        logger.info("[ABONOS] Iniciando procesamiento de abonos para %04d-%02d", anio, mes)

        # Paso 1: Procesar abonos del MES ANTERIOR
        anterior_anio, anterior_mes = _mes_anterior(anio, mes)
        abonos_anteriores = AbonoMes.objects.filter(anio=anterior_anio, mes=anterior_mes)

        renovados = 0
        vencidos = 0
        errores = 0

        for abono in abonos_anteriores:
            try:
                if abono.estado == "pagado" and getattr(abono, "renovado", False):
                    logger.info("[ABONOS] Renovando abono %s → creando nuevo abono y promoviendo turnos", abono.id)
                    procesar_renovacion_de_abono(abono)
                    renovados += 1
                else:
                    logger.info("[ABONOS] Vencido sin renovación: liberando prioridad del abono %s", abono.id)
                    liberar_abono_por_vencimiento(abono)
                    vencidos += 1
            except Exception as e:
                logger.exception("[ABONOS] Error procesando abono anterior %s: %s", abono.id, str(e))
                errores += 1

        logger.info("[ABONOS] Abonos anteriores: %s renovados, %s vencidos, %s errores", renovados, vencidos, errores)

        logger.info("[ABONOS] Finalizado: total errores: %s", errores)


def _mes_anterior(anio, mes):
    if mes == 1:
        return anio - 1, 12
    return anio, mes - 1
