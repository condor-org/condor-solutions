# apps/turnos_padel/services/abonos.py
from calendar import monthrange
from datetime import date
import logging
from typing import Dict, List

from django.db import transaction, models
from django.utils import timezone

from apps.turnos_core.models import Turno
from apps.turnos_padel.models import AbonoMes
from apps.turnos_padel.serializers import AbonoMesSerializer
from rest_framework import serializers
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_padel.utils import proximo_mes
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

logger = logging.getLogger(__name__)


def _tipo_code(tipo_clase) -> str:
    """
    TipoClasePadel NO tiene 'nombre'; usa 'codigo' (x1/x2/x3/x4).
    Dejamos fallback por compatibilidad si alguna vez existiera 'nombre'.
    """
    code = (getattr(tipo_clase, "codigo", "") or "").strip().lower()
    if code in {"x1", "x2", "x3", "x4"}:
        return code
    nombre_norm = (getattr(tipo_clase, "nombre", "") or "").strip().lower()
    mapping = {
        "individual": "x1", "2 personas": "x2", "3 personas": "x3", "4 personas": "x4",
        "x1": "x1", "x2": "x2", "x3": "x3", "x4": "x4",
    }
    return mapping.get(nombre_norm)


def _fechas_mes_actual_desde_hoy(anio: int, mes: int, dia_semana: int) -> List[date]:
    """
    Fechas del mes (weekday=dia_semana), filtrando desde HOY inclusive
    si el mes consultado es el mes actual.
    """
    hoy = timezone.localdate()
    fechas = AbonoMesSerializer._fechas_del_mes_por_dia_semana(anio, mes, dia_semana)
    if anio == hoy.year and mes == hoy.month:
        fechas = [f for f in fechas if f >= hoy]
    return fechas


def _fetch_turnos_map(
    fechas: List[date],
    sede,
    prestador_id: int,
    hora,
    for_update: bool = False
) -> Dict[date, Turno]:
    """
    Devuelve {fecha: Turno} para la franja indicada.
    Con 'for_update=True' hace SELECT ... FOR UPDATE (dentro de transacción).
    """
    qs = Turno.objects.filter(
        fecha__in=fechas,
        hora=hora,
        lugar=sede,
        content_type__model="prestador",
        object_id=prestador_id
    ).only("id", "fecha", "estado")

    if for_update:
        qs = qs.select_for_update()

    return {t.fecha: t for t in qs}


def _resumen_precio_abono(abono: AbonoMes) -> float:
    """
    Monto sugerido mensual para UI:
    - Preferimos precio del tipo de ABONO de la sede si existe.
    - Si no hay, fallback al precio del tipo de CLASE (lo más razonable que tenemos).
    """
    ref = getattr(abono, "tipo_abono", None) or getattr(abono, "tipo_clase", None)
    return float(getattr(ref, "precio", 0) or 0)


def precheck_abono_franja(abono: AbonoMes) -> Dict:
    """
    ✅ FASE 1 (Verificación, sin reservar ni bloquear):
    - Verifica que existan todos los turnos necesarios:
      * Mes ACTUAL: desde HOY inclusive.
      * Mes SIGUIENTE: todas las fechas del weekday.
    - Verifica que NINGUNO esté en 'reservado'.
    - No modifica filas.
    - Si algo falla, levanta ValueError con detalle.
    - Devuelve resumen para UI.
    """
    tipo_turno_code = _tipo_code(abono.tipo_clase)
    if not tipo_turno_code:
        raise ValueError("Tipo de clase inválido para el abono.")

    # Fechas (sin locks)
    fechas_actual = _fechas_mes_actual_desde_hoy(abono.anio, abono.mes, abono.dia_semana)
    prox_anio, prox_mes = proximo_mes(abono.anio, abono.mes)
    fechas_prox = AbonoMesSerializer._fechas_del_mes_por_dia_semana(prox_anio, prox_mes, abono.dia_semana)

    mapa_actual = _fetch_turnos_map(fechas_actual, abono.sede, abono.prestador_id, abono.hora, for_update=False)
    mapa_prox = _fetch_turnos_map(fechas_prox, abono.sede, abono.prestador_id, abono.hora, for_update=False)

    # Faltantes / Reservados (ACTUAL)
    faltan_act = [f for f in fechas_actual if f not in mapa_actual]
    if faltan_act:
        logger.warning("[abono.precheck][fail.actual.missing] abono? sede=%s prestador=%s faltan=%s",
                       abono.sede_id, abono.prestador_id, len(faltan_act))
        raise ValueError("Faltan turnos generados en el mes actual para esa franja.")

    reservados_act = [t for t in mapa_actual.values() if t.estado == "reservado"]
    if reservados_act:
        logger.warning("[abono.precheck][fail.actual.taken] sede=%s prestador=%s ids=%s",
                       abono.sede_id, abono.prestador_id, [t.id for t in reservados_act])
        raise ValueError("Hay turnos reservados en el mes actual para esa franja.")

    # Faltantes / Reservados (PRÓXIMO)
    faltan_prox = [f for f in fechas_prox if f not in mapa_prox]
    if faltan_prox:
        logger.warning("[abono.precheck][fail.next.missing] sede=%s prestador=%s faltan=%s",
                       abono.sede_id, abono.prestador_id, len(faltan_prox))
        raise ValueError("Faltan turnos generados en el mes siguiente para esa franja.")

    reservados_prox = [t for t in mapa_prox.values() if t.estado == "reservado"]
    if reservados_prox:
        logger.warning("[abono.precheck][fail.next.taken] sede=%s prestador=%s ids=%s",
                       abono.sede_id, abono.prestador_id, [t.id for t in reservados_prox])
        raise ValueError("Hay turnos reservados en el mes siguiente para esa franja.")

    disponibles_act = [t for t in mapa_actual.values() if t.estado == "disponible"]
    cancelados_act = [t for t in mapa_actual.values() if t.estado == "cancelado"]
    disponibles_prox = [t for t in mapa_prox.values() if t.estado == "disponible"]
    cancelados_prox = [t for t in mapa_prox.values() if t.estado == "cancelado"]

    resumen = {
        "total_fechas_mes_actual": len(fechas_actual),
        "reservados_mes_actual": 0,
        "disponibles_mes_actual": len(disponibles_act),
        "cancelados_mes_actual": len(cancelados_act),
        "total_fechas_mes_siguiente": len(fechas_prox),
        "prioridad_mes_siguiente": 0,
        "disponibles_mes_siguiente": len(disponibles_prox),
        "cancelados_mes_siguiente": len(cancelados_prox),
        "monto_sugerido": _resumen_precio_abono(abono),
    }

    logger.debug(
        "[abono.precheck] hoy=%s anio=%s mes=%s dsem=%s -> actual_total=%s prox=%s",
        timezone.localdate(), abono.anio, abono.mes, abono.dia_semana,
        resumen["total_fechas_mes_actual"], resumen["total_fechas_mes_siguiente"]
    )
    return resumen


@transaction.atomic
def confirmar_y_reservar_abono(abono: AbonoMes, comprobante_abono=None) -> Dict:
    """
    ✅ FASE 2 (Confirmación y reserva, con locks):
    - Re-verifica bajo SELECT ... FOR UPDATE que todo siga OK.
    - Si falla (alguien reservó en el medio / faltan turnos), levanta ValueError.
    - Si pasa, RESERVA:
        * Mes actual: reserva turnos DISPONIBLES, setea abono_mes_reservado.
        * Mes siguiente: reserva turnos DISPONIBLES, setea abono_mes_prioridad.
    - Setea fecha_limite_renovacion. NO toca 'estado' del abono (lo define el endpoint de pagos).
    - Devuelve resumen (para adjuntar a la respuesta del endpoint).
    """
    tipo_turno_code = _tipo_code(abono.tipo_clase)
    if not tipo_turno_code:
        raise ValueError("Tipo de clase inválido para el abono.")

    fechas_actual = _fechas_mes_actual_desde_hoy(abono.anio, abono.mes, abono.dia_semana)
    prox_anio, prox_mes = proximo_mes(abono.anio, abono.mes)
    fechas_prox = AbonoMesSerializer._fechas_del_mes_por_dia_semana(prox_anio, prox_mes, abono.dia_semana)

    # Re-check con locks
    mapa_actual = _fetch_turnos_map(fechas_actual, abono.sede, abono.prestador_id, abono.hora, for_update=True)
    mapa_prox = _fetch_turnos_map(fechas_prox, abono.sede, abono.prestador_id, abono.hora, for_update=True)

    faltan_act = [f for f in fechas_actual if f not in mapa_actual]
    if faltan_act:
        logger.warning("[abono.reserve][fail.actual.missing] abono=%s faltan=%s", abono.id, len(faltan_act))
        raise ValueError("Faltan turnos generados en el mes actual para esa franja.")

    if any(t.estado == "reservado" for t in mapa_actual.values()):
        raise ValueError("Hay turnos ya reservados en el mes actual para esa franja.")

    faltan_prox = [f for f in fechas_prox if f not in mapa_prox]
    if faltan_prox:
        logger.warning("[abono.reserve][fail.next.missing] abono=%s faltan=%s", abono.id, len(faltan_prox))
        raise ValueError("Faltan turnos generados en el mes siguiente para esa franja.")

    if any(t.estado == "reservado" for t in mapa_prox.values()):
        raise ValueError("Hay turnos ya reservados en el mes siguiente para esa franja.")

    disponibles_act = [t for t in mapa_actual.values() if t.estado == "disponible"]
    cancelados_act = [t for t in mapa_actual.values() if t.estado == "cancelado"]
    disponibles_prox = [t for t in mapa_prox.values() if t.estado == "disponible"]
    cancelados_prox = [t for t in mapa_prox.values() if t.estado == "cancelado"]

    # Reservar MES ACTUAL (solo disponibles)
    for t in disponibles_act:
        t.usuario = abono.usuario
        t.estado = "reservado"
        t.tipo_turno = tipo_turno_code
        t.abono_mes_reservado = abono
        if comprobante_abono:
            t.comprobante_abono = comprobante_abono
            t.save(update_fields=["usuario", "estado", "tipo_turno", "abono_mes_reservado", "comprobante_abono"])
        else:
            t.save(update_fields=["usuario", "estado", "tipo_turno", "abono_mes_reservado"])

    # Reservar MES SIGUIENTE (prioridad) — solo disponibles
    for t in disponibles_prox:
        t.usuario = abono.usuario
        t.estado = "reservado"
        t.tipo_turno = tipo_turno_code
        t.abono_mes_prioridad = abono
        t.save(update_fields=["usuario", "estado", "tipo_turno", "abono_mes_prioridad"])

    # Vincular M2M y fecha límite (no cambiar 'estado' acá)
    abono.turnos_reservados.set(disponibles_act)
    abono.turnos_prioridad.set(disponibles_prox)

    last_day = monthrange(abono.anio, abono.mes)[1]
    abono.fecha_limite_renovacion = date(abono.anio, abono.mes, last_day)
    abono.save(update_fields=["fecha_limite_renovacion"])

    resumen = {
        "total_fechas_mes_actual": len(fechas_actual),
        "reservados_mes_actual": len(disponibles_act),
        "cancelados_mes_actual": len(cancelados_act),
        "total_fechas_mes_siguiente": len(fechas_prox),
        "prioridad_mes_siguiente": len(disponibles_prox),
        "cancelados_mes_siguiente": len(cancelados_prox),
        "monto_sugerido": _resumen_precio_abono(abono),
    }

    logger.info(
        "[abono.reserve][ok] abono=%s user=%s sede=%s prestador=%s actual(res=%s,canc=%s) prox(prio=%s,canc=%s) vence=%s monto_sugerido=%s",
        abono.id, abono.usuario_id, abono.sede_id, abono.prestador_id,
        resumen["reservados_mes_actual"], resumen["cancelados_mes_actual"],
        resumen["prioridad_mes_siguiente"], resumen["cancelados_mes_siguiente"],
        abono.fecha_limite_renovacion, resumen["monto_sugerido"]
    )
    return resumen


def liberar_abono_por_vencimiento(abono: AbonoMes):
    """Libera los turnos en prioridad de un abono vencido."""
    for turno in abono.turnos_prioridad.all():
        turno.estado = "disponible"
        turno.abono_mes_prioridad = None
        turno.usuario = None
        turno.tipo_turno = None
        turno.save()


@transaction.atomic
def procesar_renovacion_de_abono(abono_anterior: AbonoMes):
    """
    Cron (1er día del mes):
    - renovado == False  → libera todos los turnos en prioridad.
    - renovado == True   → crea abono nuevo (pagado), promueve prioridad→reservados,
                           y reserva prioridad del mes siguiente del nuevo abono.
    """
    # Tomo prioridad con lock
    turnos_prio = list(
        abono_anterior.turnos_prioridad.select_for_update().all()
    )

    # Si NO renueva → liberar prioridad
    if not abono_anterior.renovado:
        for t in turnos_prio:
            t.estado = "disponible"
            t.abono_mes_prioridad = None
            t.usuario = None
            t.tipo_turno = None
            t.save(update_fields=["estado", "abono_mes_prioridad", "usuario", "tipo_turno"])
        abono_anterior.turnos_prioridad.clear()
        return

    # Sí renueva → validar que prioridad siga intacta
    for t in turnos_prio:
        if t.estado != "reservado" or t.abono_mes_prioridad_id != abono_anterior.id:
            raise ValueError(
                f"Turno {t.id} no está reservado en prioridad para abono {abono_anterior.id}"
            )

    # Crear abono nuevo (mes siguiente) como PAGADO
    anio_nuevo, mes_nuevo = proximo_mes(abono_anterior.anio, abono_anterior.mes)
    abono_nuevo = AbonoMes.objects.create(
        usuario=abono_anterior.usuario,
        sede=abono_anterior.sede,
        prestador=abono_anterior.prestador,
        dia_semana=abono_anterior.dia_semana,
        hora=abono_anterior.hora,
        tipo_clase=abono_anterior.tipo_clase,
        tipo_abono=getattr(abono_anterior, "tipo_abono", None),
        anio=anio_nuevo,
        mes=mes_nuevo,
        monto=abono_anterior.monto,
        estado="pagado",  # ← regla: solo se crea abono si está pagado
    )

    # Promover prioridad → reservados del nuevo abono
    for t in turnos_prio:
        t.abono_mes_prioridad = None
        t.abono_mes_reservado = abono_nuevo
        t.save(update_fields=["abono_mes_prioridad", "abono_mes_reservado"])
    abono_nuevo.turnos_reservados.set(turnos_prio)
    abono_anterior.turnos_prioridad.clear()

    # Fecha límite de renovación del nuevo (último día de su mes)
    last_day = monthrange(anio_nuevo, mes_nuevo)[1]
    abono_nuevo.fecha_limite_renovacion = date(anio_nuevo, mes_nuevo, last_day)
    abono_nuevo.save(update_fields=["fecha_limite_renovacion"])

    # Reservar PRIORIDAD del mes siguiente del nuevo abono
    tipo_turno_code = _tipo_code(abono_nuevo.tipo_clase)
    prox2_anio, prox2_mes = proximo_mes(anio_nuevo, mes_nuevo)
    fechas_prox2 = AbonoMesSerializer._fechas_del_mes_por_dia_semana(
        prox2_anio, prox2_mes, abono_nuevo.dia_semana
    )

    mapa_prox2 = _fetch_turnos_map(
        fechas_prox2,
        abono_nuevo.sede,
        abono_nuevo.prestador_id,
        abono_nuevo.hora,
        for_update=True
    )

    faltan_prox2 = [f for f in fechas_prox2 if f not in mapa_prox2]
    if faltan_prox2:
        logger.warning(
            "[abono.renovar][fail.next.missing] abono_nuevo=%s faltan=%s",
            abono_nuevo.id, len(faltan_prox2)
        )
        raise ValueError("Faltan turnos generados en el mes siguiente para esa franja.")

    if any(t.estado == "reservado" for t in mapa_prox2.values()):
        logger.warning(
            "[abono.renovar][fail.next.taken] abono_nuevo=%s", abono_nuevo.id
        )
        raise ValueError("Hay turnos reservados en el mes siguiente para esa franja.")

    disponibles_prox2 = [t for t in mapa_prox2.values() if t.estado == "disponible"]
    for t in disponibles_prox2:
        t.usuario = abono_nuevo.usuario
        t.estado = "reservado"
        t.tipo_turno = tipo_turno_code
        t.abono_mes_prioridad = abono_nuevo
        t.save(update_fields=["usuario", "estado", "tipo_turno", "abono_mes_prioridad"])

    abono_nuevo.turnos_prioridad.set(disponibles_prox2)

    logger.info(
        "[abono.renovar][ok] anterior=%s nuevo=%s res_act=%s prio_sig=%s",
        abono_anterior.id,
        abono_nuevo.id,
        len(turnos_prio),
        len(disponibles_prox2)
    )




@transaction.atomic
def validar_y_confirmar_abono(data, bonificaciones_ids, archivo, request):
    """
    Reglas:
      - Se recalcula todo en backend.
      - Cada bonificación vale el precio de la TipoClasePadel (de la sede).
      - restante = precio_abono - (n_bonos_aplicables * precio_tipo_clase)
      - Si restante <= 0: no hace falta comprobante → marcar bonos usados y reservar.
      - Si restante  > 0: debe venir comprobante por EXACTO ese restante; si no, error.
    """
    from apps.turnos_core.models import TurnoBonificado

    serializer = AbonoMesSerializer(data=data, context={"request": request})
    serializer.is_valid(raise_exception=True)

    vdata = dict(serializer.validated_data)   # datos validados
    abono = AbonoMes(**vdata)                 # instancia sin guardar

    # 1) Precios desde DB (no confiamos en front)
    precio_abono = float(abono.tipo_abono.precio) if abono.tipo_abono_id else float(abono.monto)
    precio_turno = float(abono.tipo_clase.precio)
    code = (getattr(abono.tipo_clase, "codigo", "") or "").strip().lower()
    code_alias = {"x1": "individual", "x2": "2 personas", "x3": "3 personas", "x4": "4 personas"}.get(code, "")

    # 2) Traer bonificaciones válidas del usuario y del tipo correcto (DB)
    bonificaciones_ids = bonificaciones_ids or []
    bonos_qs = TurnoBonificado.objects.select_for_update().filter(
        id__in=bonificaciones_ids,
        usuario=request.user,
        usado=False,
    ).filter(
        models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=timezone.localdate())
    ).filter(
        models.Q(tipo_turno__iexact=code) | models.Q(tipo_turno__iexact=code_alias)
    )
    bonos = list(bonos_qs)
    n_bonos = len(bonos)

    # 3) Calcular restante
    valor_bonos = n_bonos * precio_turno
    restante = max(precio_abono - valor_bonos, 0.0)

    # 4) Si hay restante > 0, exigir comprobante por ese EXACTO monto
    comprobante_abono = None
    if restante > 0:
        if not archivo:
            raise serializers.ValidationError({"comprobante": "Falta comprobante para cubrir el monto restante."})
        # validar y crear comprobante por el RESTANTE (sin tocar turnos todavía)
        try:
            comprobante_abono = ComprobanteService.validar_y_crear_comprobante_abono(
                abono=abono,
                file_obj=archivo,
                usuario=request.user,
                monto_esperado=restante,
            )
        except DjangoValidationError:
            raise serializers.ValidationError({"comprobante": "Comprobante no válido"})


    # 5) Persistir abono y reservar (pone locks, setea relaciones, etc.)
    abono.save()
    resumen = confirmar_y_reservar_abono(
        abono=abono,
        comprobante_abono=comprobante_abono
    )

    # 6) Marcar bonificaciones como usadas si aplicaron (en ambos escenarios)
    if n_bonos:
        for b in bonos:
            b.usado = True
            b.usado_en_abono = abono
            b.save(update_fields=["usado", "usado_en_abono"])

    return abono, resumen