# apps/turnos_padel/services/abonos.py
from calendar import monthrange
from datetime import date
import logging
from django.db import transaction
from apps.turnos_core.models import Turno
from apps.turnos_padel.models import AbonoMes
from apps.turnos_padel.serializers import AbonoMesSerializer
from apps.turnos_padel.utils import proximo_mes

logger = logging.getLogger(__name__)

def _tipo_code(tipo_clase) -> str:
    nombre_norm = (getattr(tipo_clase, "nombre", "") or "").strip().lower()
    mapping = {
        "individual": "x1", "x1": "x1",
        "2 personas": "x2", "x2": "x2",
        "3 personas": "x3", "x3": "x3",
        "4 personas": "x4", "x4": "x4",
    }
    return mapping.get(nombre_norm)

def _proximo_mes(anio: int, mes: int) -> tuple[int, int]:
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)

@transaction.atomic
def reservar_abono_mes_actual_y_prioridad(abono: AbonoMes, comprobante_abono=None):
    """
    Estricto:
    - Para cada fecha del mes actual y del mes siguiente debe existir un Turno
      (mismo prestador/sede/hora) y ninguno puede estar en 'reservado'.
    - Reservamos SOLO los que están en 'disponible'.
    - Los 'cancelado' se dejan tal cual (hueco para reemplazo/bono).
    Devuelve (abono, resumen_dict) para ajustar UI/precio.
    """
    tipo_turno_code = _tipo_code(abono.tipo_clase)
    if not tipo_turno_code:
        raise ValueError("Tipo de clase inválido para el abono.")

    # Fechas por mes
    fechas_actual = AbonoMesSerializer._fechas_del_mes_por_dia_semana(abono.anio, abono.mes, abono.dia_semana)
    prox_anio, prox_mes = proximo_mes(abono.anio, abono.mes)
    fechas_prox = AbonoMesSerializer._fechas_del_mes_por_dia_semana(prox_anio, prox_mes, abono.dia_semana)

    def _fetch_map(fechas):
        qs = (Turno.objects.select_for_update()
              .filter(fecha__in=fechas, hora=abono.hora, lugar=abono.sede,
                      content_type__model="prestador", object_id=abono.prestador_id)
              .only("id","fecha","estado"))
        return {t.fecha: t for t in qs}

    # --- Validación estricta MES ACTUAL ---
    mapa_actual = _fetch_map(fechas_actual)
    faltan_act = [f for f in fechas_actual if f not in mapa_actual]
    if faltan_act:
        logger.warning("[abono.reserve][fail.actual.missing] abono=%s faltan=%s", abono.id, len(faltan_act))
        raise ValueError("Faltan turnos generados en el mes actual para esa franja.")

    reservados_act = [t for t in mapa_actual.values() if t.estado == "reservado"]
    if reservados_act:
        ids = [t.id for t in reservados_act]
        logger.warning("[abono.reserve][fail.actual.taken] abono=%s turnos_reservados=%s", abono.id, ids)
        raise ValueError("Hay turnos ya reservados en el mes actual para esa franja.")

    disponibles_act = [t for t in mapa_actual.values() if t.estado == "disponible"]
    cancelados_act  = [t for t in mapa_actual.values() if t.estado == "cancelado"]

    # --- Validación estricta MES SIGUIENTE ---
    mapa_prox = _fetch_map(fechas_prox) if fechas_prox else {}
    faltan_prox = [f for f in fechas_prox if f not in mapa_prox]
    if faltan_prox:
        logger.warning("[abono.reserve][fail.next.missing] abono=%s faltan=%s", abono.id, len(faltan_prox))
        raise ValueError("Faltan turnos generados en el mes siguiente para esa franja.")

    reservados_prox = [t for t in mapa_prox.values() if t.estado == "reservado"]
    if reservados_prox:
        ids = [t.id for t in reservados_prox]
        logger.warning("[abono.reserve][fail.next.taken] abono=%s turnos_reservados=%s", abono.id, ids)
        raise ValueError("Hay turnos ya reservados en el mes siguiente para esa franja.")

    disponibles_prox = [t for t in mapa_prox.values() if t.estado == "disponible"]
    cancelados_prox  = [t for t in mapa_prox.values() if t.estado == "cancelado"]

    # --- Reservar mes actual (solo disponibles) ---
    for t in disponibles_act:
        t.usuario = abono.usuario
        t.estado = "reservado"
        t.tipo_turno = tipo_turno_code
        t.abono_mes_reservado = abono
        if comprobante_abono:
            t.comprobante_abono = comprobante_abono
            t.save(update_fields=["usuario","estado","tipo_turno","abono_mes_reservado","comprobante_abono"])
        else:
            t.save(update_fields=["usuario","estado","tipo_turno","abono_mes_reservado"])

    # --- Reservar mes siguiente como prioridad (solo disponibles) ---
    for t in disponibles_prox:
        t.usuario = abono.usuario
        t.estado = "reservado"
        t.tipo_turno = tipo_turno_code
        t.abono_mes_prioridad = abono
        t.save(update_fields=["usuario","estado","tipo_turno","abono_mes_prioridad"])

    # --- Actualizar Abono: M2M + estado/fecha límite ---
    abono.turnos_reservados.set(disponibles_act)   # solo los efectivamente reservados
    abono.turnos_prioridad.set(disponibles_prox)   # solo los efectivamente reservados como prioridad
    abono.estado = "pagado"
    last_day = monthrange(abono.anio, abono.mes)[1]
    abono.fecha_limite_renovacion = date(abono.anio, abono.mes, last_day)
    abono.save(update_fields=["estado", "fecha_limite_renovacion"])

    resumen = {
        "total_fechas_mes_actual": len(fechas_actual),
        "reservados_mes_actual": len(disponibles_act),
        "cancelados_mes_actual": len(cancelados_act),
        "total_fechas_mes_siguiente": len(fechas_prox),
        "prioridad_mes_siguiente": len(disponibles_prox),
        "cancelados_mes_siguiente": len(cancelados_prox),
        "monto_sugerido": float(abono.tipo_clase.precio) * len(disponibles_act),
    }

    logger.info(
        "[abono.reserve][ok] abono=%s user=%s sede=%s prestador=%s actual(res=%s,canc=%s) prox(prio=%s,canc=%s) vence=%s",
        abono.id, abono.usuario_id, abono.sede_id, abono.prestador_id,
        resumen["reservados_mes_actual"], resumen["cancelados_mes_actual"],
        resumen["prioridad_mes_siguiente"], resumen["cancelados_mes_siguiente"],
        abono.fecha_limite_renovacion
    )
    return abono, resumen

def liberar_abono_por_vencimiento(abono):
    """
    Libera todos los turnos en prioridad de un abono vencido.
    """
    for turno in abono.turnos_prioridad.all():
        turno.estado = "disponible"
        turno.abono_mes_prioridad = None
        turno.usuario = None
        turno.tipo_turno = None
        turno.save()

@transaction.atomic
def procesar_renovacion_de_abono(abono_anterior: AbonoMes):
    """
    Si el abono anterior tiene `renovado = True`, se crea un nuevo abono con mismos datos:
    - Se pasan los turnos prioridad del anterior como reservados.
    - Se reservan nuevos turnos prioridad en el mes siguiente.
    """
    anio, mes = proximo_mes(abono_anterior.anio, abono_anterior.mes)

    abono_nuevo = AbonoMes.objects.create(
        usuario=abono_anterior.usuario,
        sede=abono_anterior.sede,
        prestador=abono_anterior.prestador,
        dia_semana=abono_anterior.dia_semana,
        hora=abono_anterior.hora,
        tipo_clase=abono_anterior.tipo_clase,
        anio=anio,
        mes=mes,
        monto=abono_anterior.monto,  
        estado="pagado",             
    )

    # 1. Promover turnos prioridad → reservados
    turnos_prioridad = abono_anterior.turnos_prioridad.all()
    for turno in turnos_prioridad:
        turno.abono_mes_prioridad = None
        turno.abono_mes_reservado = abono_nuevo
        turno.save(update_fields=["abono_mes_prioridad", "abono_mes_reservado"])

    abono_nuevo.turnos_reservados.set(turnos_prioridad)
    abono_anterior.turnos_prioridad.clear()

    # 2. Reservar nuevos turnos como prioridad (para el mes siguiente)
    try:
        reservar_abono_mes_actual_y_prioridad(abono_nuevo)
    except Exception as e:
        logger.warning("[ABONOS] Falló reserva de turnos prioridad para abono renovado %s: %s", abono_nuevo.id, str(e))