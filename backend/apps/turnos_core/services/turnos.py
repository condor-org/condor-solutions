# apps/turnos_core/services/turnos.py

from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Turno, Disponibilidad, Prestador
from apps.turnos_core.utils import esta_bloqueado
import logging

logger = logging.getLogger(__name__)

def generar_turnos_para_prestador(prestador_id, fecha_inicio, fecha_fin, duracion_minutos=60):
    """
    Genera turnos 'disponible' para un prestador según sus disponibilidades activas,
    entre fecha_inicio y fecha_fin (inclusive). Omite días bloqueados.

    Notas:
    - Idempotente: usa bulk_create(ignore_conflicts=True) para no duplicar si se re-ejecuta.
    - No setea tipo_turno: eso se define al reservar, no al generar slots.
    - Mantiene el mismo límite de franja que tu implementación original
      (la franja final es EXCLUSIVA: no se crea turno que termine justo en hora_fin).
    """
    content_type = ContentType.objects.get_for_model(Prestador)
    total_generados = 0

    disponibilidades = (
        Disponibilidad.objects
        .filter(prestador_id=prestador_id, activo=True)
        .select_related("prestador", "lugar")
    )

    for disp in disponibilidades:
        dias = _dias_para(disponibilidad=disp, desde=fecha_inicio, hasta=fecha_fin)

        for dia in dias:
            prestador = disp.prestador
            sede = disp.lugar

            if esta_bloqueado(prestador, sede, dia):
                logger.debug(
                    "[turnos.generar][skip_bloqueo] prestador_id=%s sede_id=%s fecha=%s",
                    prestador_id, getattr(sede, "id", None), dia
                )
                continue

            hora_actual = datetime.combine(dia, disp.hora_inicio)
            hora_final = datetime.combine(dia, disp.hora_fin)

            nuevos = []
            while hora_actual + timedelta(minutes=duracion_minutos) <= hora_final:
                nuevos.append(Turno(
                    fecha=hora_actual.date(),
                    hora=hora_actual.time(),
                    lugar=disp.lugar,
                    content_type=content_type,
                    object_id=prestador_id,
                    estado="disponible",
                ))
                hora_actual += timedelta(minutes=duracion_minutos)

            if not nuevos:
                logger.debug(
                    "[turnos.generar][sin_slots] prestador_id=%s sede_id=%s fecha=%s",
                    prestador_id, getattr(sede, "id", None), dia
                )
                continue

            # Idempotente / safe contra concurrencia: evita duplicados por unique_together
            creados = Turno.objects.bulk_create(nuevos, ignore_conflicts=True)
            total_generados += len(creados)

            logger.debug(
                "[turnos.generar][dia] prestador_id=%s sede_id=%s fecha=%s generados=%s solicitados=%s",
                prestador_id, getattr(sede, "id", None), dia, len(creados), len(nuevos)
            )

    logger.info(
        "[turnos.generar][done] prestador_id=%s desde=%s hasta=%s duracion_min=%s total_generados=%s",
        prestador_id, fecha_inicio, fecha_fin, duracion_minutos, total_generados
    )
    return total_generados

def _dias_para(disponibilidad, desde, hasta):
    """
    Devuelve las fechas entre 'desde' y 'hasta' (inclusive)
    cuyo weekday coincide con disponibilidad.dia_semana.
    """
    dias = []
    d = desde
    objetivo = int(disponibilidad.dia_semana)
    while d <= hasta:
        if d.weekday() == objetivo:
            dias.append(d)
        d += timedelta(days=1)
    return dias