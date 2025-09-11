# apps/turnos_core/services/bonificaciones.py
# ------------------------------------------------------------------------------
# Servicio de emisión, consulta, uso y administración de "TurnoBonificado".
# - Emisión automática (por cancelación válida) y manual (por admin).
# - Consultas de bonos vigentes (con vencimiento opcional).
# - Aplicación de bono a un turno (marca como usado y referencia al turno).
# - Utilidad para eliminar un bono puntual (control manual).
# - Publica eventos y notifica in-app al usuario cuando se emite un bono.
# - Todas las mutaciones críticas van dentro de transacciones atómicas.
# ------------------------------------------------------------------------------

from datetime import timedelta
from django.utils import timezone
from django.db import models, transaction
from apps.turnos_core.models import TurnoBonificado, Turno
import logging
from decimal import Decimal, InvalidOperation
from apps.notificaciones_core.services import (
    publish_event,
    notify_inapp,
)

TYPE_BONIFICACION_CREADA = "BONIFICACION_CREADA"

logger = logging.getLogger(__name__)




# -----------------------------
# HELPER
# -----------------------------


def _resolver_valor_por_lugar_y_tipo(lugar, tipo_turno):
    """
    Devuelve Decimal (precio) para la combinación (sede/lugar, tipo_turno) usando:
      TipoClasePadel.configuracion_sede.sede == lugar  AND  TipoClasePadel.codigo == tipo_turno

    - Usa iexact para el código (x1/x2/x3/x4).
    - Considera sólo tipos activos.
    - Logs claros si no encuentra config por sede o por tipo.
    """
    # Acepta objeto Lugar o id
    sede_id = lugar if isinstance(lugar, int) else getattr(lugar, "id", None)
    code = (str(tipo_turno).strip() if tipo_turno else None)

    if not sede_id or not code:
        logger.warning(
            "[BONIFICACION][_resolver_valor] faltan datos sede_id=%s tipo=%s", sede_id, code
        )
        return None

    try:
        from apps.turnos_padel.models import TipoClasePadel, ConfiguracionSedePadel

        # Validar que exista configuración para la sede (por claridad en logs)
        existe_conf = ConfiguracionSedePadel.objects.filter(sede_id=sede_id).exists()
        if not existe_conf:
            logger.warning(
                "[BONIFICACION][_resolver_valor] la sede_id=%s no tiene ConfiguracionSedePadel",
                sede_id,
            )

        # Buscar el precio del tipo en esa sede (solo activos)
        precio = (
            TipoClasePadel.objects
            .filter(
                configuracion_sede__sede_id=sede_id,
                codigo__iexact=code,
                activo=True,
            )
            .values_list("precio", flat=True)
            .first()
        )

        if precio is None:
            logger.warning(
                "[BONIFICACION][_resolver_valor] sin TipoClasePadel activo para sede_id=%s codigo=%s",
                sede_id, code
            )
        else:
            logger.debug(
                "[BONIFICACION][_resolver_valor] OK sede_id=%s codigo=%s -> precio=%s",
                sede_id, code, precio
            )
        return precio

    except Exception:
        logger.exception(
            "[BONIFICACION][_resolver_valor] error resolviendo precio sede_id=%s tipo=%s",
            sede_id, code
        )
        return None

# -----------------------------
# EMISIÓN DE BONIFICACIONES
# -----------------------------

@transaction.atomic
def emitir_bonificacion_automatica(usuario, turno_original, motivo="Cancelación válida", valido_hasta=None):
    """
    Emite un bono automáticamente asociado a un turno cancelado.
    """
    if not getattr(turno_original, "tipo_turno", None):
        raise ValueError("turno_original.tipo_turno es requerido para emitir bonificación automática.")

    # 🔎 NUEVO: congelar el valor del bono según la sede y el tipo
    valor = _resolver_valor_por_lugar_y_tipo(turno_original.lugar, turno_original.tipo_turno)
    if valor is None:
        logger.warning(
            "[BONIFICACION][auto] valor no resuelto para turno=%s lugar=%s tipo=%s",
            getattr(turno_original, "id", None),
            getattr(turno_original.lugar, "id", None) if getattr(turno_original, "lugar", None) else None,
            getattr(turno_original, "tipo_turno", None),
        )

    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        turno_original=turno_original,
        motivo=motivo,
        generado_automaticamente=True,
        valido_hasta=valido_hasta,
        tipo_turno=turno_original.tipo_turno,
        valor=valor,  # 💰 ahora se persiste el precio
    )
    logger.info(
        "[BONIFICACION][auto] user=%s turno=%s tipo=%s valor=%s",
        getattr(usuario, "id", None), getattr(turno_original, "id", None),
        getattr(turno_original, "tipo_turno", None), valor
    )
    try:
        ev = publish_event(
            topic="bonificaciones.automatica",
            actor=usuario,
            cliente_id=getattr(usuario, "cliente_id", None),
            metadata={
                "bonificacion_id": bono.id,
                "turno_original": turno_original.id,
                "tipo_turno": str(turno_original.tipo_turno),
                "motivo": motivo,
                "valor": str(valor) if valor is not None else None,  # útil para auditoría
            },
        )
        notify_inapp(
            event=ev,
            recipients=[usuario],
            notif_type=TYPE_BONIFICACION_CREADA,
            severity="info",
            context_by_user={
                usuario.id: {
                    "bonificacion_id": bono.id,
                    "tipo_turno": str(turno_original.tipo_turno),
                    "valor": str(valor) if valor is not None else None,
                }
            },
        )
        logger.info("[notif][bonif.auto] user=%s bono=%s", getattr(usuario, "id", None), bono.id)
    except Exception:
        logger.exception("[notif][bonif.auto][fail] bono=%s", bono.id)
    return bono


@transaction.atomic
def emitir_bonificacion_manual(
    admin_user,
    usuario,
    *,
    sede,               # ← requerido (Lugar o id)
    tipo_clase_id,      # ← requerido (ID de TipoClasePadel)
    motivo="Bonificación manual",
    valido_hasta=None,
):
    """
    Emite una bonificación manual EXIGIENDO sede y tipo_clase.
    - Valida que el TipoClasePadel pertenezca a la sede indicada.
    - Setea tipo_turno con tc.codigo (x1/x2/x3/x4).
    - Congela valor con tc.precio.
    """
    # Normalizar sede
    sede_obj = None
    if isinstance(sede, int):
        try:
            sede_obj = Lugar.objects.only("id").get(pk=sede)
        except ObjectDoesNotExist:
            raise ValueError(f"Sede/Lugar id={sede} no existe")
    else:
        sede_obj = sede
    if not getattr(sede_obj, "id", None):
        raise ValueError("Parámetro 'sede' inválido (se esperaba Lugar o id)")

    # Traer TipoClasePadel y validar pertenencia a la sede
    try:
        from apps.turnos_padel.models import TipoClasePadel
        tc = (TipoClasePadel.objects
              .select_related("configuracion_sede__sede")
              .only("id", "codigo", "precio", "activo", "configuracion_sede__sede_id")
              .get(pk=tipo_clase_id, activo=True))
    except ObjectDoesNotExist:
        raise ValueError(f"TipoClasePadel id={tipo_clase_id} no existe o no está activo")

    if tc.configuracion_sede.sede_id != sede_obj.id:
        raise ValueError(
            f"TipoClasePadel id={tipo_clase_id} no pertenece a la sede id={sede_obj.id}"
        )

    # Congelar datos del tipo
    tipo_turno = str(tc.codigo).lower()
    valor = tc.precio

    # Crear bono
    bono = TurnoBonificado.objects.create(
        usuario=usuario,
        motivo=motivo,
        generado_automaticamente=False,
        emitido_por=admin_user,
        valido_hasta=valido_hasta,
        tipo_turno=tipo_turno,
        valor=valor,
    )

    logger.info(
        "[BONIFICACION][manual] admin=%s user=%s sede=%s tipo_clase_id=%s tipo=%s valor=%s bono=%s",
        getattr(admin_user, "id", None),
        getattr(usuario, "id", None),
        sede_obj.id,
        tipo_clase_id,
        tipo_turno,
        valor,
        bono.id,
    )

    # Eventos / notificación (igual que antes, con metadatos extra)
    try:
        ev = publish_event(
            topic="bonificaciones.manual",
            actor=admin_user,
            cliente_id=getattr(usuario, "cliente_id", None),
            metadata={
                "bonificacion_id": bono.id,
                "sede_id": sede_obj.id,
                "tipo_clase_id": tipo_clase_id,
                "tipo_turno": tipo_turno,
                "motivo": motivo,
                "valor": str(valor),
            },
        )
        notify_inapp(
            event=ev,
            recipients=[usuario],
            notif_type=TYPE_BONIFICACION_CREADA,
            severity="info",
            context_by_user={
                usuario.id: {
                    "bonificacion_id": bono.id,
                    "sede_id": sede_obj.id,
                    "tipo_clase_id": tipo_clase_id,
                    "tipo_turno": tipo_turno,
                    "valor": str(valor),
                }
            },
        )
        logger.info("[notif][bonif.manual] user=%s bono=%s", getattr(usuario, "id", None), bono.id)
    except Exception:
        logger.exception("[notif][bonif.manual][fail] bono=%s", bono.id)

    return bono


# -----------------------------
# CONSULTAS DE BONIFICACIONES
# -----------------------------

def bonificaciones_vigentes(usuario):
    """
    Devuelve queryset de bonos vigentes (no usados y no vencidos).
    ► Regla:
      - usado=False
      - valido_hasta is null OR valido_hasta >= hoy
    ► Uso:
      - Base para filtros adicionales (por tipo, etc.).
    """
    hoy = timezone.now().date()
    return TurnoBonificado.objects.filter(
        usuario=usuario,
        usado=False
    ).filter(
        models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=hoy)
    )

def bonificaciones_vigentes_por_tipo(usuario, tipo_turno):
    """
    Azúcar sintáctico: vigentes filtradas por tipo_turno exacto.
    """
    return bonificaciones_vigentes(usuario).filter(tipo_turno=tipo_turno)


def tiene_bonificaciones_disponibles(usuario):
    """
    True si el usuario posee al menos un bono vigente sin usar.
    (Consulta eficiente: .exists())
    """
    return bonificaciones_vigentes(usuario).exists()


def cantidad_bonificaciones(usuario):
    """
    Conteo de bonos vigentes disponibles.
    """
    return bonificaciones_vigentes(usuario).count()


# -----------------------------
# APLICACIÓN DE BONIFICACIÓN
# -----------------------------

@transaction.atomic
def usar_bonificacion(usuario, turno, tipo_turno=None):
    """
    Marca como usada la primera bonificación vigente (opcionalmente filtrada por tipo).
    ► Flujo:
      - Obtiene bonificaciones vigentes del usuario (opcionalmente por tipo_turno).
      - Toma la primera (orden natural de DB).
      - Setea usado=True y referencia usado_en_turno.
      - Devuelve el bono aplicado o None si no había disponible.

    ► Entradas:
      - usuario: dueño del bono.
      - turno: turno a asociar.
      - tipo_turno (str|None): si se pasa, filtra por ese tipo exacto.

    ► Salida:
      - TurnoBonificado | None

    ► Transaccionalidad:
      - Atómico para evitar carreras en consumo de bono.
    """
    qs = bonificaciones_vigentes(usuario)
    if tipo_turno:
        qs = qs.filter(tipo_turno=tipo_turno)

    bono = qs.first()
    if not bono:
        logger.info("[BONIFICACION][usar][no_disp] user=%s tipo=%s", getattr(usuario, "id", None), tipo_turno)
        return None

    bono.usado = True
    bono.usado_en_turno = turno
    bono.save(update_fields=["usado", "usado_en_turno"])

    logger.info(
        "[BONIFICACION][usar] user=%s bono=%s turno=%s tipo=%s valor=%s",
        getattr(usuario, "id", None), bono.id, getattr(turno, "id", None),
        bono.tipo_turno, bono.valor
    )
    return bono
    
# -----------------------------
# UTILIDADES AVANZADAS (opcional)
# -----------------------------

@transaction.atomic
def eliminar_bonificacion(bonificacion_id, motivo_admin="Eliminada por administrador"):
    """
    Elimina una bonificación específica (control administrativo).
    ► Notas:
      - No hay eventos/alertas asociadas por ahora (solo logging).
      - Devuelve True si eliminó, False si no existía.
    """
    try:
        bono = TurnoBonificado.objects.get(pk=bonificacion_id)
        logger.warning("[BONIFICACION] Bonificación %s eliminada. Motivo: %s", bono.id, motivo_admin)
        bono.delete()
        return True
    except TurnoBonificado.DoesNotExist:
        return False
