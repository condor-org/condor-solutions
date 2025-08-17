from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Turno, Disponibilidad, Prestador
from apps.turnos_core.utils import esta_bloqueado
import logging

logger = logging.getLogger(__name__)

def generar_turnos_para_prestador(prestador_id, fecha_inicio, fecha_fin, duracion_minutos=60, estado="disponible"):
    """
    Genera turnos para un prestador según sus disponibilidades activas,
    entre fecha_inicio y fecha_fin (inclusive). Omite días bloqueados.

    Notas:
    - Idempotente: usa bulk_create(ignore_conflicts=True) para no duplicar si se re-ejecuta.
    - No setea tipo_turno: eso se define al reservar, no al generar slots.
    - Si estado='reservado', se generan como bloqueados (sin usuario).
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
                    estado=estado,
                ))
                hora_actual += timedelta(minutes=duracion_minutos)

            if not nuevos:
                continue

            creados = Turno.objects.bulk_create(nuevos, ignore_conflicts=True)
            total_generados += len(creados)

    logger.info(
        "[turnos.generar][done] prestador_id=%s desde=%s hasta=%s duracion_min=%s total_generados=%s estado=%s",
        prestador_id, fecha_inicio, fecha_fin, duracion_minutos, total_generados, estado
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
