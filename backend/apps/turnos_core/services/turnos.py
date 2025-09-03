# apps/turnos_core/services/turnos.py

from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Turno, Disponibilidad, Prestador
from apps.turnos_core.utils import esta_bloqueado
import logging

logger = logging.getLogger(__name__)

def generar_turnos_para_prestador(prestador_id, fecha_inicio, fecha_fin, duracion_minutos=60, estado="disponible"):
    """
    Genera slots de Turno para un prestador según sus Disponibilidades activas,
    dentro del rango [fecha_inicio, fecha_fin] inclusive.

    ► Regla de negocio:
      - Solo se generan slots en días/hora que coinciden con las Disponibilidades activas del prestador.
      - Se omiten fechas que estén bloqueadas (esta_bloqueado(prestador, sede, fecha) == True).
      - No se define 'tipo_turno' en esta etapa (eso se asigna al reservar).
      - Si 'estado' = 'reservado', los slots quedan marcados como ocupados (sin usuario) para usos de bloqueo.

    ► Idempotencia:
      - Usa bulk_create(..., ignore_conflicts=True) + unique_together del modelo Turno
        para no duplicar slots si se re-ejecuta con los mismos parámetros.

    ► Entradas:
      - prestador_id (int): ID del Prestador.
      - fecha_inicio, fecha_fin (date): rango de generación (inclusive).
      - duracion_minutos (int): longitud de cada slot (e.g. 60).
      - estado (str): estado inicial del turno: 'disponible' (default) o 'reservado'.

    ► Salida:
      - int: cantidad de turnos efectivamente creados (no cuenta los que se ignoraron por conflicto).

    ► Logging:
      - Info final con totals y parámetros clave para auditoría.
    """
    content_type = ContentType.objects.get_for_model(Prestador)
    total_generados = 0

    # Disponibilidades activas del prestador (con sede para filtrar por bloqueos).
    disponibilidades = (
        Disponibilidad.objects
        .filter(prestador_id=prestador_id, activo=True)
        .select_related("prestador", "lugar")
    )

    for disp in disponibilidades:
        # Todas las fechas del rango que coinciden con el día de semana de la disponibilidad.
        dias = _dias_para(disponibilidad=disp, desde=fecha_inicio, hasta=fecha_fin)

        for dia in dias:
            prestador = disp.prestador
            sede = disp.lugar

            # Saltar días bloqueados a nivel prestador/sede.
            if esta_bloqueado(prestador, sede, dia):
                continue

            # Ventana horaria del día según disponibilidad.
            hora_actual = datetime.combine(dia, disp.hora_inicio)
            hora_final = datetime.combine(dia, disp.hora_fin)

            nuevos = []
            # Generar slots de 'duracion_minutos' hasta completar la franja.
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

            # Idempotencia por unique_together(fecha, hora, content_type, object_id).
            creados = Turno.objects.bulk_create(nuevos, ignore_conflicts=True)
            total_generados += len(creados)

    logger.info(
        "[turnos.generar][done] prestador_id=%s desde=%s hasta=%s duracion_min=%s total_generados=%s estado=%s",
        prestador_id, fecha_inicio, fecha_fin, duracion_minutos, total_generados, estado
    )
    return total_generados


def _dias_para(disponibilidad, desde, hasta):
    """
    Devuelve todas las fechas entre 'desde' y 'hasta' (inclusive)
    cuyo weekday coincide con disponibilidad.dia_semana.

    ► Uso:
      - Helper puro (sin DB) para expandir un patrón semanal en fechas concretas.
      - Mantiene inclusividad del rango y es determinista.
    """
    dias = []
    d = desde
    objetivo = int(disponibilidad.dia_semana)
    while d <= hasta:
        if d.weekday() == objetivo:
            dias.append(d)
        d += timedelta(days=1)
    return dias
