# apps/turnos_core/services/turnos.py
# ------------------------------------------------------------------------------
# Servicios para generación de turnos (idempotente por SW + por DB).
# - Evita pasado (clamp a hoy y salta horas vencidas del día actual)
# - Aware datetimes para comparaciones TZ-seguras
# - Idempotencia fuerte:
#     a) pre-filtra lo que ya existe (software)
#     b) bulk_create(ignore_conflicts=True) (DB)  <-- por si el constraint sí existe
# - Logging claro: intentados, ya_existian, a_crear, creados, conflictos
# ------------------------------------------------------------------------------
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Turno, Disponibilidad, Prestador
import logging

logger = logging.getLogger(__name__)


def generar_turnos_para_prestador(
    prestador_id,
    fecha_inicio,
    fecha_fin,
    duracion_minutos=60,
    estado="disponible",
):
    """
    Genera slots de Turno para un prestador según sus Disponibilidades activas,
    dentro del rango [fecha_inicio, fecha_fin] inclusive.

    Reglas:
      - Genera sólo en días/hora que coinciden con disponibilidades activas.
      - No asigna tipo_turno ni usuario.
      - No crea pasado (clamp a hoy y no genera horas ya vencidas hoy).

    Idempotencia:
      - SW: pre-filtra slots ya existentes para ese día/lugar/prestador/hora.
      - DB: bulk_create(..., ignore_conflicts=True) por si el unique_together está OK.

    Retorna:
      - int: cantidad realmente creada en esta invocación.
    """
    if fecha_inicio > fecha_fin:
        logger.warning(
            "[turnos.generar][skip] Rango inválido: desde=%s > hasta=%s (prestador_id=%s)",
            fecha_inicio, fecha_fin, prestador_id
        )
        return 0

    hoy = timezone.localdate()
    ahora_local = timezone.localtime()  # aware
    fecha_inicio_efectiva = max(fecha_inicio, hoy)

    tz = timezone.get_current_timezone()
    content_type = ContentType.objects.get_for_model(Prestador)
    total_generados = 0

    disponibilidades = (
        Disponibilidad.objects
        .filter(prestador_id=prestador_id, activo=True)
        .select_related("prestador", "lugar")
    )

    for disp in disponibilidades:
        dias = _dias_para(disponibilidad=disp, desde=fecha_inicio_efectiva, hasta=fecha_fin)
        if not dias:
            logger.debug(
                "[turnos.generar][disp] Sin días en rango. disp_id=%s prestador_id=%s rango=[%s..%s]",
                disp.id, prestador_id, fecha_inicio_efectiva, fecha_fin
            )
            continue

        for dia in dias:
            # --- construir datetimes AWARE en la TZ actual ---
            hora_actual_dt = timezone.make_aware(datetime.combine(dia, disp.hora_inicio), tz)
            hora_final_dt  = timezone.make_aware(datetime.combine(dia, disp.hora_fin), tz)

            # Día actual: saltar horas ya vencidas
            if dia == hoy:
                if hora_final_dt <= ahora_local.replace(microsecond=0):
                    logger.debug(
                        "[turnos.generar][skip-dia] Franja ya finalizada hoy. disp_id=%s dia=%s",
                        disp.id, dia
                    )
                    continue
                while (
                    hora_actual_dt < ahora_local
                    and (hora_actual_dt + timedelta(minutes=duracion_minutos)) <= hora_final_dt
                ):
                    hora_actual_dt += timedelta(minutes=duracion_minutos)

            # --- Construir candidatos de ese día (todas las horas en malla) ---
            candidatos = []
            cursor = hora_actual_dt
            while (cursor + timedelta(minutes=duracion_minutos)) <= hora_final_dt:
                candidatos.append(cursor.time())  # sólo la hora; fecha/lugar/prestador son fijos en este loop
                cursor += timedelta(minutes=duracion_minutos)

            if not candidatos:
                continue

            # --- IDEMPOTENCIA POR SOFTWARE ---
            # Horas que ya existen para (fecha=dia, lugar=disp.lugar, prestador) → no se recrean
            existentes_horas = set(
                Turno.objects.filter(
                    fecha=dia,
                    lugar=disp.lugar,
                    content_type=content_type,
                    object_id=prestador_id,
                ).values_list("hora", flat=True)
            )

            horas_a_crear = [h for h in candidatos if h not in existentes_horas]

            intentados      = len(candidatos)
            ya_existian     = len(existentes_horas.intersection(candidatos))
            a_crear         = len(horas_a_crear)

            if a_crear == 0:
                logger.info(
                    "[turnos.generar][disp] prestador_id=%s disp_id=%s lugar_id=%s dia=%s "
                    "intentados=%s ya_existian=%s a_crear=0 creados=0 conflictos=0 estado=%s rango=[%s..%s] dur=%s",
                    prestador_id, disp.id, disp.lugar_id, dia,
                    intentados, ya_existian, estado, disp.hora_inicio, disp.hora_fin, duracion_minutos
                )
                continue

            nuevos = [
                Turno(
                    fecha=dia,
                    hora=h,
                    lugar=disp.lugar,
                    content_type=content_type,
                    object_id=prestador_id,
                    estado=estado,
                )
                for h in horas_a_crear
            ]

            # --- IDEMPOTENCIA POR DB (si existe unique_together correcto) ---
            creados_objs = Turno.objects.bulk_create(nuevos, ignore_conflicts=True)
            creados = len(creados_objs)
            conflictos = a_crear - creados  # si el constraint existe, serán los colisionados por races

            total_generados += creados

            logger.info(
                "[turnos.generar][disp] prestador_id=%s disp_id=%s lugar_id=%s dia=%s "
                "intentados=%s ya_existian=%s a_crear=%s creados=%s conflictos=%s estado=%s rango=[%s..%s] dur=%s",
                prestador_id, disp.id, disp.lugar_id, dia,
                intentados, ya_existian, a_crear, creados, conflictos,
                estado, disp.hora_inicio, disp.hora_fin, duracion_minutos
            )

    logger.info(
        "[turnos.generar][done] prestador_id=%s desde=%s(hoy=%s) hasta=%s duracion_min=%s total_generados=%s estado=%s",
        prestador_id, fecha_inicio_efectiva, hoy, fecha_fin, duracion_minutos, total_generados, estado
    )
    return total_generados


def _dias_para(disponibilidad, desde, hasta):
    """
    Devuelve todas las fechas entre 'desde' y 'hasta' (inclusive)
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
