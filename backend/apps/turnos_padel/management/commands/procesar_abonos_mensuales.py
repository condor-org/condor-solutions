# apps/turnos_padel/management/commands/procesar_abonos_mensuales.py
import logging
import json
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.turnos_padel.models import AbonoMes
from apps.turnos_padel.services.abonos import (
    confirmar_y_reservar_abono,
    procesar_renovacion_de_abono,
)

logger = logging.getLogger(__name__)


def _mes_anterior(fecha):
    if fecha.month == 1:
        return fecha.year - 1, 12
    return fecha.year, fecha.month - 1


class Command(BaseCommand):
    help = (
        "Procesa abonos mensuales:\n"
        " - Aplica (reserva/prioridad) los abonos del mes actual que aún no se aplicaron.\n"
        " - En el cambio de mes, renueva o libera los abonos del mes anterior."
    )

    def handle(self, *args, **kwargs):
        hoy = timezone.localdate()
        anio_prev, mes_prev = _mes_anterior(hoy)

        resumen = {
            "aplicados_mes_actual": 0,
            "renovados": 0,
            "liberados": 0,
            "errores": 0,
        }

        # A) Mes actual: aplicar reservas/prioridad a los no aplicados
        pendientes = (
            AbonoMes.objects.filter(anio=hoy.year, mes=hoy.month, estado="pagado")
            .filter(turnos_reservados__isnull=True, turnos_prioridad__isnull=True)
            .distinct()
        )
        logger.info(
            "[CRON ABONOS] Abonos pendientes de aplicar (mes actual %04d-%02d): %s",
            hoy.year, hoy.month, pendientes.count()
        )

        for ab in pendientes:
            try:
                confirmar_y_reservar_abono(ab)
                resumen["aplicados_mes_actual"] += 1
                logger.info("[CRON ABONOS] aplicado abono=%s user=%s", ab.id, ab.usuario_id)
            except Exception:
                resumen["errores"] += 1
                logger.exception("[CRON ABONOS] fallo al aplicar abono=%s", ab.id)

        # B) Mes anterior: renovar o liberar
        anteriores = AbonoMes.objects.filter(anio=anio_prev, mes=mes_prev, estado="pagado")
        logger.info(
            "[CRON ABONOS] Abonos del mes anterior a procesar (%04d-%02d): %s",
            anio_prev, mes_prev, anteriores.count()
        )

        for ab in anteriores:
            try:
                renovaba = bool(getattr(ab, "renovado", False))
                procesar_renovacion_de_abono(ab)
                if renovaba:
                    resumen["renovados"] += 1
                else:
                    resumen["liberados"] += 1
            except Exception:
                resumen["errores"] += 1
                logger.exception("[CRON ABONOS] fallo al procesar abono=%s", ab.id)

        # Log estructurado + salida legible
        logger.info("[CRON ABONOS] Resumen final", extra={"abonos_resumen": resumen})
        self.stdout.write(self.style.SUCCESS(f"[CRON ABONOS] Resumen final: {json.dumps(resumen, ensure_ascii=False)}"))

        return  # importante: no retornar un dict
