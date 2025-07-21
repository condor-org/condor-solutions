# apps/turnos_padel_core/services/generador.py
from datetime import date, datetime, timedelta
from calendar import monthrange
from django.contrib.contenttypes.models import ContentType

from apps.turnos_core.models import Turno
from apps.turnos_padel.models import Disponibilidad, Profesor
from apps.turnos_core.utils import esta_bloqueado  # Importa la función util

def generar_turnos_del_mes(anio, mes, duracion_minutos=60, profesor_id=None):
    """
    Genera turnos a partir de las disponibilidades activas para el mes dado,
    omitiendo días/señas bloqueados.
    """
    dias_en_mes = monthrange(anio, mes)[1]
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, dias_en_mes)
    user_ct = ContentType.objects.get(model="profesor")  # 'profesor' es el modelo recurso

    disponibilidades = Disponibilidad.objects.filter(activo=True)

    if profesor_id:
        disponibilidades = disponibilidades.filter(profesor_id=profesor_id)

    total_generados = 0

    for disp in disponibilidades:
        dias = _dias_para(disponibilidad=disp, desde=fecha_inicio, hasta=fecha_fin)

        for dia in dias:
            # Verificamos bloqueo
            profesor = disp.profesor
            sede = disp.lugar
            if esta_bloqueado(profesor, sede, dia):
                # Omitimos este día porque está bloqueado
                continue

            hora_actual = datetime.combine(dia, disp.hora_inicio)
            hora_final = datetime.combine(dia, disp.hora_fin)

            while hora_actual + timedelta(minutes=duracion_minutos) <= hora_final:
                turno_existe = Turno.objects.filter(
                    fecha=hora_actual.date(),
                    hora=hora_actual.time(),
                    object_id=disp.profesor_id,
                    lugar=disp.lugar
                ).exists()

                if not turno_existe:
                    Turno.objects.create(
                        fecha=hora_actual.date(),
                        hora=hora_actual.time(),
                        lugar=disp.lugar,
                        servicio=None,  # Opcional: setear servicio si corresponde
                        content_type=user_ct,
                        object_id=disp.profesor_id,
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
