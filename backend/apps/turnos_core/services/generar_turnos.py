# apps/turnos_core/services/generacion.py
from datetime import date, time as dtime
from calendar import monthrange
import logging

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.turnos_core.models import Prestador, Turno
from apps.turnos_core.services.turnos import generar_turnos_para_prestador

logger = logging.getLogger(__name__)

def _primer_dia_mes_siguiente(fecha: date) -> date:
    return date(fecha.year + 1, 1, 1) if fecha.month == 12 else date(fecha.year, fecha.month + 1, 1)

def _ultimo_dia_mes(fecha: date) -> date:
    ultimo = monthrange(fecha.year, fecha.month)[1]
    return date(fecha.year, fecha.month, ultimo)

def _horas_reservadas_para_abono():
    # 07..11 (incluye 11-12) y 14..17 (incluye 17-18)
    horas = [7, 8, 9, 10, 11, 14, 15, 16, 17]
    return [dtime(h, 0, 0) for h in horas]

def _marcar_reservado_para_abono(ct_prestador, prestador_id: int, desde: date, hasta: date, horas):
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
    return updated

def generar_turnos_mes_actual_y_siguiente(*, cliente_id=None, prestador_id=None):
    """
    Genera turnos para el mes actual (desde hoy) y el mes siguiente.
    Idempotente y además marca reservado_para_abono=True en 07–11 y 14–17.
    Puede acotarse por cliente_id o por prestador_id.
    """
    hoy = timezone.localdate()

    fi_actual = hoy
    ff_actual = _ultimo_dia_mes(hoy)

    fi_siguiente = _primer_dia_mes_siguiente(hoy)
    ff_siguiente = _ultimo_dia_mes(fi_siguiente)

    qs = Prestador.objects.filter(activo=True)
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if prestador_id:
        qs = qs.filter(id=prestador_id)

    ct_prestador = ContentType.objects.get_for_model(Prestador)
    horas_abono = _horas_reservadas_para_abono()

    total_generados = 0
    total_marcados = 0
    detalle = []

    for p in qs:
        c1 = generar_turnos_para_prestador(p.id, fi_actual, ff_actual, estado="disponible")
        c2 = generar_turnos_para_prestador(p.id, fi_siguiente, ff_siguiente, estado="disponible")
        m1 = _marcar_reservado_para_abono(ct_prestador, p.id, fi_actual, ff_actual, horas_abono)
        m2 = _marcar_reservado_para_abono(ct_prestador, p.id, fi_siguiente, ff_siguiente, horas_abono)

        total_generados += (c1 + c2)
        total_marcados += (m1 + m2)
        detalle.append({
            "prestador_id": p.id,
            "creados": c1 + c2,
            "franjas_marcadas": m1 + m2,
        })

    logger.info(
        "[generar_turnos_mes_actual_y_siguiente] prestadores=%s generados=%s marcados=%s",
        qs.count(), total_generados, total_marcados
    )
    return {
        "turnos_generados": total_generados,
        "franjas_marcadas": total_marcados,
        "prestadores_afectados": len(detalle),
        "detalle": detalle,
    }
