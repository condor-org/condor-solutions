# apps/turnos_core/services/turnos.py

from datetime import date, datetime, timedelta
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Turno, Disponibilidad, Prestador
from apps.turnos_core.utils import esta_bloqueado


def generar_turnos_para_prestador(prestador_id, fecha_inicio, fecha_fin, duracion_minutos=60):
    """
    Genera turnos disponibles para un prestador según sus disponibilidades activas,
    entre fecha_inicio y fecha_fin (inclusive).
    Omite días bloqueados.
    """
    content_type = ContentType.objects.get_for_model(Prestador)
    total_generados = 0

    disponibilidades = Disponibilidad.objects.filter(prestador_id=prestador_id, activo=True)

    for disp in disponibilidades:
        dias = _dias_para(disponibilidad=disp, desde=fecha_inicio, hasta=fecha_fin)

        for dia in dias:
            prestador = disp.prestador
            sede = disp.lugar

            if esta_bloqueado(prestador, sede, dia):
                continue

            hora_actual = datetime.combine(dia, disp.hora_inicio)
            hora_final = datetime.combine(dia, disp.hora_fin)

            while hora_actual + timedelta(minutes=duracion_minutos) <= hora_final:
                ya_existe = Turno.objects.filter(
                    fecha=hora_actual.date(),
                    hora=hora_actual.time(),
                    content_type=content_type,
                    object_id=prestador_id,
                    lugar=disp.lugar
                ).exists()

                if not ya_existe:
                    Turno.objects.create(
                        fecha=hora_actual.date(),
                        hora=hora_actual.time(),
                        lugar=disp.lugar,
                        content_type=content_type,
                        object_id=prestador_id,
                        estado="disponible"
                    )
                    total_generados += 1

                hora_actual += timedelta(minutes=duracion_minutos)

    print(f"✅ Turnos generados: {total_generados}")
    return total_generados

def _dias_para(disponibilidad, desde, hasta):
    """
    Devuelve una lista de fechas entre `desde` y `hasta` que coinciden con el día de semana de la disponibilidad.
    """
    actual = desde
    dias = []

    while actual <= hasta:
        if actual.weekday() == disponibilidad.dia_semana:
            dias.append(actual)
        actual += timedelta(days=1)

    return dias
