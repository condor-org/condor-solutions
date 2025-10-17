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
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_padel.utils import proximo_mes
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

logger = logging.getLogger(__name__)

from apps.notificaciones_core.services import (
    publish_event,
    notify_inapp,
    TYPE_RESERVA_ABONO,   
    TYPE_ABONO_RENOVADO,  
)
from django.contrib.auth import get_user_model



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
    Incluye lógica de anticipación mínima para el día actual.
    """
    # Configuración de anticipación mínima (en horas)
    HORAS_ANTICIPACION_MINIMA = 1
    
    hoy = timezone.localdate()
    ahora = timezone.now()
    
    fechas = AbonoMesSerializer._fechas_del_mes_por_dia_semana(anio, mes, dia_semana)
    
    if anio == hoy.year and mes == hoy.month:
        # Para el mes actual, filtrar fechas futuras con anticipación
        fechas_futuras = []
        for fecha in fechas:
            if fecha > hoy:
                # Fechas futuras: incluir todas
                fechas_futuras.append(fecha)
            elif fecha == hoy:
                # Día actual: verificar anticipación mínima
                # Solo incluir si hay al menos HORAS_ANTICIPACION_MINIMA horas restantes
                hora_actual = ahora.hour
                if hora_actual < (24 - HORAS_ANTICIPACION_MINIMA):  # Ej: antes de las 23:00 para 1h de anticipación
                    fechas_futuras.append(fecha)
                # Si es muy tarde, no incluir el día actual
            # Si fecha < hoy, no incluir (ya pasó)
        
        fechas = fechas_futuras
    
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

def _notify_abono_admin(abono, actor, evento="creado", extra=None):
    """
    evento: 'creado' | 'renovado'
    Notifica a admin_cliente y super_admin del cliente dueño de la sede del abono.
    """
    logger.info("[notif.abono] evento=%s abono=%s", evento, getattr(abono, "id", None))
    try:
        Usuario = get_user_model()
        cliente_id = getattr(abono.sede, "cliente_id", None)
        tipo_code = _tipo_code(abono.tipo_clase)
        hora_txt = str(abono.hora)[:5] if abono.hora else None
        DSEM = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

        ev = publish_event(
            topic="abonos.reserva_confirmada" if evento == "creado" else "abonos.renovado",
            actor=actor,
            cliente_id=cliente_id,
            metadata={
                "abono_id": abono.id,
                "usuario": getattr(abono.usuario, "email", None),
                "sede_id": abono.sede_id,
                "prestador_id": abono.prestador_id,
                "anio": abono.anio, "mes": abono.mes, "dia_semana": abono.dia_semana,
                "hora": hora_txt,
                "tipo": tipo_code,
                "monto": abono.monto,
                **(extra or {}),
            },
        )

        admins = Usuario.objects.filter(
            cliente_id=cliente_id,
            is_super_admin=True  # super_admin global
        ).only("id", "cliente_id")

        ctx = {
            a.id: {
                "abono_id": abono.id,
                "usuario": getattr(abono.usuario, "email", None),
                "tipo": tipo_code,
                "sede_nombre": getattr(abono.sede, "nombre", None),
                "prestador": getattr(abono.prestador, "nombre_publico", None) or getattr(abono.prestador, "nombre", None),
                "hora": hora_txt,
                "dia_semana_text": DSEM[abono.dia_semana] if 0 <= abono.dia_semana <= 6 else "",
                **(extra or {}),
            } for a in admins
        }

        notify_inapp(
            event=ev,
            recipients=admins,
            notif_type=TYPE_RESERVA_ABONO if evento == "creado" else TYPE_ABONO_RENOVADO,
            context_by_user=ctx,
            severity="info",
        )
    except Exception:
        logger.exception("[notif][abono][%s][fail]", evento)


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
    logger.info("[abonos.confirmar_y_reservar][inicio] abono_id=%s usuario_id=%s sede_id=%s prestador_id=%s tiene_comprobante=%s", 
               abono.id, abono.usuario_id, abono.sede_id, abono.prestador_id, bool(comprobante_abono))
    # Para abonos personalizados, tipo_clase es null
    if abono.configuracion_personalizada:
        # Para abonos personalizados, usar el primer tipo de clase de la configuración
        if not abono.configuracion_personalizada:
            raise ValueError("Configuración personalizada vacía para el abono.")
        tipo_turno_code = abono.configuracion_personalizada[0].get('codigo', 'x1')
    else:
        # Para abonos normales, validar tipo_clase
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
        Turno.objects.select_for_update().filter(abono_mes_prioridad=abono_anterior)
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
def validar_y_confirmar_abono(data, bonificaciones_ids, archivo, request, forzar_admin=False):
    """
    Reglas:
      - Se recalcula todo en backend.
      - Cada bonificación vale el precio de la TipoClasePadel (de la sede).
      - restante = precio_abono - (n_bonos_aplicables * precio_tipo_clase)
      - Si restante <= 0: no hace falta comprobante → marcar bonos usados y reservar.
      - Si restante  > 0: debe venir comprobante por EXACTO ese restante; salvo override admin.
      - Override admin: si el caller es super_admin/admin_cliente y forzar_admin=True → no exige comprobante.
    """
    
    abono_id = (data.get("abono_id") or "").strip() if hasattr(data, "get") else None
    if abono_id:
        return _validar_y_confirmar_renovacion(
            abono_id=abono_id,
            bonificaciones_ids=bonificaciones_ids,
            archivo=archivo,
            request=request,
            forzar_admin=forzar_admin,
        )
    
    from apps.turnos_core.models import TurnoBonificado

    serializer = AbonoMesSerializer(data=data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    logger.info("[abonos.validar_y_confirmar][serializer_ok] serializer validado correctamente")

    vdata = dict(serializer.validated_data)   # datos validados
    abono = AbonoMes(**vdata)                 # instancia sin guardar

    logger.info("[abonos.validar_y_confirmar][abono_creado] usuario=%s sede=%s prestador=%s anio=%s mes=%s dsem=%s hora=%s tipo_clase=%s config_personalizada=%s", 
               abono.usuario_id, abono.sede_id, abono.prestador_id, abono.anio, abono.mes, 
               abono.dia_semana, abono.hora, abono.tipo_clase_id, abono.configuracion_personalizada)

    # ¿quién llama?
    user = getattr(request, "user", None)
    from apps.auth_core.utils import get_rol_actual_del_jwt
    rol_actual = get_rol_actual_del_jwt(request)
    caller_es_admin = bool(user and (user.is_super_admin or rol_actual == "admin_cliente"))
    omitir_archivo = caller_es_admin and bool(forzar_admin)

    # 1) Precios dinámicos basados en turnos del mes
    precio_abono = calcular_precio_abono_dinamico(abono, abono.anio, abono.mes)
    
    # Asignar el monto calculado al abono
    abono.monto = precio_abono
    
    logger.info("[abonos.validar_y_confirmar][precio_calculado] precio_abono=%.2f", precio_abono)
    
    # Para abonos normales, usar precio del tipo_clase
    if abono.tipo_clase:
        precio_turno = float(abono.tipo_clase.precio)
        code = (getattr(abono.tipo_clase, "codigo", "") or "").strip().lower()
        code_alias = {"x1": "individual", "x2": "2 personas", "x3": "3 personas", "x4": "4 personas"}.get(code, "")
    else:
        # Para abonos personalizados, usar precio promedio o el primer tipo
        precio_turno = 0
        code = ""
        code_alias = "personalizado"

    # 2) Traer bonificaciones válidas del USUARIO DESTINO (sin filtro por tipo)
    bonificaciones_ids = bonificaciones_ids or []
    bonos_qs = (
        TurnoBonificado.objects
        .select_for_update()
        .only("id", "valor", "tipo_turno", "valido_hasta", "usado", "usuario_id")
        .filter(
            id__in=bonificaciones_ids,
            usuario=abono.usuario,   # 👈 beneficiario real del abono
            usado=False,
        )
        .filter(
            models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=timezone.localdate())
        )
        # Ya no filtramos por tipo_turno - las bonificaciones son universales
    )
    bonos = list(bonos_qs)

    # 3) Validar y sumar valor de cada bonificación
    try:
        valores_bonos = [float(b.valor) for b in bonos]
    except (TypeError, ValueError):
        raise serializers.ValidationError({"bonificaciones": "Hay bonificaciones sin valor numérico válido."})
    if any(v < 0 for v in valores_bonos):
        raise serializers.ValidationError({"bonificaciones": "Hay bonificaciones con valor negativo."})

    valor_bonos = sum(valores_bonos)
    restante = max(precio_abono - valor_bonos, 0.0)

    logger.info("[abonos.validar_y_confirmar][bonificaciones] bonos_aplicados=%s valor_bonos=%.2f restante=%.2f", 
               len(bonos), valor_bonos, restante)

    # >>> FIX: asegurar que 'abono' tenga ID antes de crear el comprobante <<<
    # (No cambia ninguna otra parte del flujo)
    if restante > 0 and not omitir_archivo and not abono.pk:
        abono.save()

    # 4) Si hay restante > 0, exigir comprobante por ese EXACTO monto (salvo override admin)
    comprobante_abono = None
    logger.info("[abonos.validar_y_confirmar][comprobante_check] restante=%.2f omitir_archivo=%s tiene_archivo=%s", 
               restante, omitir_archivo, bool(archivo))
    
    if restante > 0 and not omitir_archivo:
        if not archivo:
            raise serializers.ValidationError({"comprobante": "Falta comprobante para cubrir el monto restante."})
        
        logger.info("[abonos.validar_y_confirmar][comprobante] llamando ComprobanteService con abono_id=%s monto_esperado=%.2f", 
                   abono.id, restante)
        
        # validar y crear comprobante por el RESTANTE (sin tocar turnos todavía)
        try:
            comprobante_abono = ComprobanteService.validar_y_crear_comprobante_abono(
                abono=abono,
                file_obj=archivo,
                usuario=abono.usuario,   # 👈 beneficiario, no el admin
                monto_esperado=restante,
            )
        except DjangoValidationError as e:
            logger.error("[abonos.validar_y_confirmar][comprobante_error] ERROR real del comprobante: %s", str(e))
            raise serializers.ValidationError({"comprobante": "Comprobante no válido"})

    logger.info(
        "[abonos.validar_y_confirmar] actor_id=%s role=%s forzar_admin=%s omitir_archivo=%s restante=%.2f tiene_archivo=%s",
        getattr(user, "id", None),
        getattr(user, "tipo_usuario", None),
        bool(forzar_admin),
        omitir_archivo,
        restante,
        bool(archivo),
    )

    # 5) Persistir abono y reservar (pone locks, setea relaciones, etc.)
    # (Si ya se guardó antes por el fix, esto es idempotente)
    abono.save()
    logger.info("[abonos.validar_y_confirmar][confirmar_y_reservar] llamando confirmar_y_reservar_abono con abono_id=%s", abono.id)
    resumen = confirmar_y_reservar_abono(
        abono=abono,
        comprobante_abono=comprobante_abono
    )

    # 6) Marcar bonificaciones como usadas si aplicaron (en ambos escenarios)
    if bonos:
        for b in bonos:
            b.usado = True
            b.usado_en_abono = abono
            b.save(update_fields=["usado", "usado_en_abono"])

    return abono, resumen


# === NUEVO ===
@transaction.atomic
def _validar_y_confirmar_renovacion(*, abono_id, bonificaciones_ids, archivo, request, forzar_admin=False):
    """
    Renovación: marca el abono como 'renovado', consume bonificaciones y
    registra comprobante si corresponde. NO reserva turnos (eso lo hace el cron).
    Idempotente: si ya estaba renovado no falla.
    """
    from apps.turnos_core.models import TurnoBonificado

    # Traigo sólo la fila base y la bloqueo; evito outer joins del manager
    try:
        abono = (
            AbonoMes.objects
            .select_related(None)            # evita select_related por defecto
            .prefetch_related(None)          # evita prefetch por defecto
            .select_for_update(of=('self',)) # FOR UPDATE OF sólo sobre AbonoMes
            .get(id=int(abono_id))
        )
    except (AbonoMes.DoesNotExist, ValueError, TypeError):
        raise serializers.ValidationError({"detail": "Abono no encontrado."})

    # Autorización mínima
    user = getattr(request, "user", None)
    if getattr(user, "tipo_usuario", None) == "usuario_final" and abono.usuario_id != getattr(user, "id", None):
        raise serializers.ValidationError({"detail": "No autorizado para renovar este abono."})

    from apps.auth_core.utils import get_rol_actual_del_jwt
    rol_actual = get_rol_actual_del_jwt(request)
    caller_es_admin = bool(user and (user.is_super_admin or rol_actual == "admin_cliente"))
    omitir_archivo = caller_es_admin and bool(forzar_admin)

    # Precios "server source of truth" - usar cálculo dinámico
    # Para renovaciones, usar año y mes de la renovación, no del abono original
    anio_renovacion = int(request.data.get("anio", abono.anio))
    mes_renovacion = int(request.data.get("mes", abono.mes))
    
    # Para renovaciones personalizadas, usar la nueva configuración del payload
    configuracion_personalizada = request.data.get("configuracion_personalizada")
    print(f"[DEBUG] configuracion_personalizada del payload: {configuracion_personalizada}")
    if configuracion_personalizada:
        # Parsear JSON string si es necesario
        if isinstance(configuracion_personalizada, str):
            import json
            configuracion_personalizada = json.loads(configuracion_personalizada)
        # Crear un abono temporal con la nueva configuración para el cálculo
        abono_temp = type('AbonoTemp', (), {
            'id': abono.id,  # Agregar id para el log
            'configuracion_personalizada': configuracion_personalizada,
            'tipo_clase': None,
            'monto': None
        })()
        precio_abono = calcular_precio_abono_dinamico(abono_temp, anio_renovacion, mes_renovacion)
    else:
        precio_abono = calcular_precio_abono_dinamico(abono, anio_renovacion, mes_renovacion)

    # Bonificaciones válidas del usuario (universales)
    # Para renovaciones, no importa el tipo de clase - las bonificaciones son por monto
    logger.info("[abonos.validar_y_confirmar][bonificaciones_inicio] bonificaciones_ids=%s usuario_id=%s", 
               bonificaciones_ids, abono.usuario_id)

    bonos_qs = (
        TurnoBonificado.objects
        .select_for_update()
        .only("id", "valor", "tipo_turno", "valido_hasta", "usado", "usuario_id")
        .filter(
            id__in=(bonificaciones_ids or []),
            usuario=abono.usuario,
            usado=False,
        )
        .filter(models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=timezone.localdate()))
        # Ya no filtramos por tipo_turno - las bonificaciones son universales
    )
    bonos = list(bonos_qs)
    
    logger.info("[abonos.validar_y_confirmar][bonificaciones_encontradas] bonos_encontrados=%s", len(bonos))

    # Sumar valor real de cada bonificación (no el precio de la clase)
    try:
        valores_bonos = [float(b.valor) for b in bonos]
    except (TypeError, ValueError):
        raise serializers.ValidationError({"bonificaciones": "Hay bonificaciones sin valor numérico válido."})
    if any(v < 0 for v in valores_bonos):
        raise serializers.ValidationError({"bonificaciones": "Hay bonificaciones con valor negativo."})

    restante = max(precio_abono - sum(valores_bonos), 0.0)

    # Comprobante (sólo si hace falta y no hay override admin)
    comprobante_abono = None
    if restante > 0 and not omitir_archivo:
        if not archivo:
            raise serializers.ValidationError({"comprobante": "Falta comprobante para cubrir el monto restante."})
        try:
            comprobante_abono = ComprobanteService.validar_y_crear_comprobante_abono(
                abono=abono,
                file_obj=archivo,
                usuario=abono.usuario,
                monto_esperado=restante,
            )
        except DjangoValidationError as e:
            logger.error("[abonos._validar_y_confirmar_renovacion][comprobante_error] ERROR real del comprobante: %s", str(e))
            raise serializers.ValidationError({"comprobante": "Comprobante no válido"})

    # Si hay comprobante, asociarlo a los turnos en prioridad de este abono (idempotente)
    if comprobante_abono:
        turnos_prio = list(
            Turno.objects
            .select_for_update()
            .filter(abono_mes_prioridad=abono, comprobante_abono__isnull=True)
            .only("id")
        )
        for t in turnos_prio:
            t.comprobante_abono = comprobante_abono
            t.save(update_fields=["comprobante_abono"])

    # Consumir bonificaciones aplicadas
    if bonos:
        for b in bonos:
            b.usado = True
            b.usado_en_abono = abono
            b.save(update_fields=["usado", "usado_en_abono"])

    # Marcar renovado (idempotente)
    if not abono.renovado:
        abono.renovado = True
        abono.save(update_fields=["renovado"])

    # Resumen para la UI (no reservamos nada acá)
    resumen = {
        "reservados_mes_actual": 0,
        "prioridad_mes_siguiente": abono.turnos_prioridad.count(),
        "monto_sugerido": float(precio_abono),
        "renovado": True,
    }

    logger.info(
        "[abonos.renovacion] abono=%s renovado=%s bonos=%s restante=%.2f",
        abono.id, True, len(bonos), restante
    )

    return abono, resumen


def calcular_precio_abono_dinamico(abono, anio, mes):
    """Calcula el precio dinámico basado en turnos disponibles del mes"""
    
    if abono.configuracion_personalizada:
        # Para abonos personalizados: suma precios de cada tipo * cantidad
        total = 0
        for config in abono.configuracion_personalizada:
            try:
                from apps.turnos_padel.models import TipoClasePadel
                tipo_clase = TipoClasePadel.objects.get(id=config['tipo_clase_id'])
                subtotal = float(tipo_clase.precio) * config['cantidad']
                total += subtotal
            except (TipoClasePadel.DoesNotExist, KeyError, ValueError) as e:
                continue
        return total
    elif abono.tipo_clase:
        # Para abonos normales: precio del tipo_clase * turnos del mes
        turnos_mes = contar_turnos_del_mes(anio, mes, abono.dia_semana)
        precio = float(abono.tipo_clase.precio) * turnos_mes
        return precio
    else:
        precio = float(abono.monto) if abono.monto else 0.0
        return precio


def contar_turnos_del_mes(anio, mes, dia_semana):
    """Cuenta los turnos disponibles para el día de la semana en el mes"""
    from datetime import date
    hoy = date.today()
    
    # Contar días del mes que caen en el día de la semana
    from calendar import Calendar
    cal = Calendar(firstweekday=0)
    fechas = []
    for week in cal.monthdatescalendar(anio, mes):
        for d in week:
            if d.month == mes and d.weekday() == dia_semana:
                fechas.append(d)
    
    # Solo fechas futuras
    fechas_futuras = [f for f in fechas if f >= hoy]
    return len(fechas_futuras)
