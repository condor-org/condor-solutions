# turnos_core/management/commands/generar_turnos_mensuales.py
# ------------------------------------------------------------------------------
# Genera slots de turnos para TODOS los prestadores activos para:
#   - Mes actual  (desde hoy hasta último día del mes)
#   - Mes siguiente (del 1 al último día)
#
# Idempotente:
# - La generación usa unique_together + ignore_conflicts en el service.
# - El marcado de reservado_para_abono se hace con UPDATE por rango (safe).
# ------------------------------------------------------------------------------

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date, time as dtime
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.turnos_core.models import Prestador, Turno
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Genera turnos disponibles (mes actual desde hoy + mes siguiente) y marca franjas de abono."

    def handle(self, *args, **kwargs):
        hoy = timezone.localdate()

        # ► Ventana 1: Mes actual → [hoy, último día del mes]
        fecha_inicio_actual = hoy
        fecha_fin_actual = _ultimo_dia_del_mes(hoy)

        # ► Ventana 2: Mes siguiente → [1°, último día del próximo mes]
        fecha_inicio_siguiente = _primer_dia_mes_siguiente(hoy)
        fecha_fin_siguiente = _ultimo_dia_del_mes(fecha_inicio_siguiente)

        total_generados = 0
        total_marcados = 0

        ct_prestador = ContentType.objects.get_for_model(Prestador)
        horas_abono = _horas_reservadas_para_abono()  # [07:00, 08:00, ..., 11:00, 14:00, ..., 17:00]

        for prestador in Prestador.objects.filter(activo=True):
            logger.info("[CRON] Generando turnos para prestador %s (%s)", prestador.id, prestador)

            # Generación idempotente
            creados_actual = generar_turnos_para_prestador(
                prestador.id, fecha_inicio_actual, fecha_fin_actual, estado="disponible"
            )
            creados_siguiente = generar_turnos_para_prestador(
                prestador.id, fecha_inicio_siguiente, fecha_fin_siguiente, estado="disponible"
            )
            total_generados += (creados_actual + creados_siguiente)

            # Marcar franjas de abono (idempotente, solo "disponible")
            marcados_act = _marcar_reservado_para_abono(
                ct_prestador, prestador.id, fecha_inicio_actual, fecha_fin_actual, horas_abono
            )
            marcados_sig = _marcar_reservado_para_abono(
                ct_prestador, prestador.id, fecha_inicio_siguiente, fecha_fin_siguiente, horas_abono
            )
            total_marcados += (marcados_act + marcados_sig)

        logger.info("[CRON] Total turnos generados: %s | Franjas de abono marcadas: %s", total_generados, total_marcados)


def _primer_dia_mes_siguiente(fecha: date) -> date:
    return date(fecha.year + 1, 1, 1) if fecha.month == 12 else date(fecha.year, fecha.month + 1, 1)

def _ultimo_dia_del_mes(fecha: date) -> date:
    from calendar import monthrange
    ultimo = monthrange(fecha.year, fecha.month)[1]
    return date(fecha.year, fecha.month, ultimo)

def _horas_reservadas_para_abono():
    # 07..11 (incluye 11-12) y 14..17 (incluye 17-18)
    horas = [7, 8, 9, 10, 11, 14, 15, 16, 17]
    return [dtime(h, 0, 0) for h in horas]

def _marcar_reservado_para_abono(ct_prestador, prestador_id: int, desde: date, hasta: date, horas):
    """
    Marca reservado_para_abono=True en turnos DISPONIBLES del prestador
    dentro [desde, hasta] y con hora en 'horas'. Idempotente.
    """
    updated = (
        Turno.objects
        .filter(
            content_type=ct_prestador,
            object_id=prestador_id,
            fecha__range=(desde, hasta),
            hora__in=horas,
            estado="disponible",
        )
        .exclude(reservado_para_abono=True)
        .update(reservado_para_abono=True)
    )
    if updated:
        logger.debug(
            "[CRON] Prestador %s: reservado_para_abono=True en %s turnos (%s→%s)",
            prestador_id, updated, desde, hasta
        )
    return updated
