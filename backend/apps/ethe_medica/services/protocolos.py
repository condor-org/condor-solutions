# apps/ethe_medica/services/protocolos.py

from datetime import date, timedelta
from django.utils import timezone
from apps.ethe_medica.models import ProtocoloSeguimiento, SeguimientoPaciente, Paciente
import logging

logger = logging.getLogger(__name__)


def programar_seguimientos_paciente(paciente):
    """
    Programa seguimientos automáticos según el protocolo de la categoría.
    
    Args:
        paciente: instancia de Paciente
    
    Returns:
        list de SeguimientoPaciente creados
    """
    # 1. Obtener protocolo según categoría
    try:
        protocolo = ProtocoloSeguimiento.objects.get(
            categoria_paciente=paciente.categoria_actual,
            activo=True
        )
    except ProtocoloSeguimiento.DoesNotExist:
        logger.warning(
            f"[ETHE] No hay protocolo activo para categoría {paciente.categoria_actual}"
        )
        return []
    
    # 2. Calcular próximas fechas de seguimiento
    seguimientos_creados = []
    hoy = timezone.localdate()
    
    # Programar seguimientos para los próximos 6 meses
    for i in range(1, 7):  # 1, 2, 3, 4, 5, 6 meses
        fecha_programada = hoy + timedelta(days=protocolo.frecuencia_dias * i)
        
        # Verificar si ya existe un seguimiento para esa fecha
        if not SeguimientoPaciente.objects.filter(
            paciente=paciente,
            protocolo=protocolo,
            fecha_programada=fecha_programada
        ).exists():
            
            seguimiento = SeguimientoPaciente.objects.create(
                paciente=paciente,
                protocolo=protocolo,
                fecha_programada=fecha_programada
            )
            
            seguimientos_creados.append(seguimiento)
    
    logger.info(
        f"[ETHE] Seguimientos programados: {len(seguimientos_creados)} para paciente {paciente}"
    )
    
    return seguimientos_creados


def verificar_seguimientos_pendientes():
    """
    CRON job: verifica seguimientos pendientes y envía notificaciones.
    """
    hoy = timezone.localdate()
    
    # Buscar seguimientos pendientes que vencen hoy o ya vencieron
    seguimientos_pendientes = SeguimientoPaciente.objects.filter(
        estado="PENDIENTE",
        fecha_programada__lte=hoy
    ).select_related("paciente", "protocolo")
    
    notificaciones_enviadas = 0
    seguimientos_vencidos = 0
    
    for seguimiento in seguimientos_pendientes:
        # Verificar si ya venció (más de 3 días de retraso)
        dias_retraso = (hoy - seguimiento.fecha_programada).days
        
        if dias_retraso > 3:
            # Marcar como no asistió
            seguimiento.estado = "NO_ASISTIO"
            seguimiento.observaciones = f"Vencido hace {dias_retraso} días"
            seguimiento.save()
            seguimientos_vencidos += 1
            
            logger.warning(
                f"[ETHE] Seguimiento vencido: {seguimiento} - {dias_retraso} días de retraso"
            )
        else:
            # Enviar recordatorio
            enviar_recordatorio_seguimiento(seguimiento)
            notificaciones_enviadas += 1
    
    logger.info(
        f"[ETHE] Seguimientos verificados: {notificaciones_enviadas} recordatorios, "
        f"{seguimientos_vencidos} vencidos"
    )
    
    return {
        "notificaciones_enviadas": notificaciones_enviadas,
        "seguimientos_vencidos": seguimientos_vencidos,
        "total_verificados": seguimientos_pendientes.count()
    }


def enviar_recordatorio_seguimiento(seguimiento):
    """
    Envía recordatorio de seguimiento a paciente.
    
    Args:
        seguimiento: instancia de SeguimientoPaciente
    """
    # TODO: Implementar sistema de notificaciones
    # Por ahora solo log
    logger.info(
        f"[ETHE] Recordatorio enviado: {seguimiento.paciente} - "
        f"Protocolo {seguimiento.protocolo.nombre} - "
        f"Fecha: {seguimiento.fecha_programada}"
    )


def marcar_seguimiento_realizado(seguimiento, observaciones=""):
    """
    Marca un seguimiento como realizado.
    
    Args:
        seguimiento: instancia de SeguimientoPaciente
        observaciones: str (opcional)
    
    Returns:
        SeguimientoPaciente actualizado
    """
    seguimiento.estado = "REALIZADO"
    seguimiento.fecha_realizada = timezone.now()
    seguimiento.observaciones = observaciones
    seguimiento.save()
    
    logger.info(
        f"[ETHE] Seguimiento realizado: {seguimiento.paciente} - "
        f"Protocolo {seguimiento.protocolo.nombre}"
    )
    
    return seguimiento


def cancelar_seguimiento(seguimiento, motivo=""):
    """
    Cancela un seguimiento.
    
    Args:
        seguimiento: instancia de SeguimientoPaciente
        motivo: str (opcional)
    
    Returns:
        SeguimientoPaciente actualizado
    """
    seguimiento.estado = "CANCELADO"
    seguimiento.observaciones = f"Cancelado: {motivo}"
    seguimiento.save()
    
    logger.info(
        f"[ETHE] Seguimiento cancelado: {seguimiento.paciente} - "
        f"Motivo: {motivo}"
    )
    
    return seguimiento


def obtener_estadisticas_seguimiento(paciente=None, centro=None, fecha_inicio=None, fecha_fin=None):
    """
    Obtiene estadísticas de seguimientos.
    
    Args:
        paciente: instancia de Paciente (opcional)
        centro: instancia de Lugar (opcional)
        fecha_inicio: date (opcional)
        fecha_fin: date (opcional)
    
    Returns:
        dict con estadísticas
    """
    seguimientos = SeguimientoPaciente.objects.all()
    
    if paciente:
        seguimientos = seguimientos.filter(paciente=paciente)
    
    if centro:
        seguimientos = seguimientos.filter(paciente__centro_ingreso=centro)
    
    if fecha_inicio:
        seguimientos = seguimientos.filter(fecha_programada__gte=fecha_inicio)
    
    if fecha_fin:
        seguimientos = seguimientos.filter(fecha_programada__lte=fecha_fin)
    
    total = seguimientos.count()
    realizados = seguimientos.filter(estado="REALIZADO").count()
    pendientes = seguimientos.filter(estado="PENDIENTE").count()
    no_asistio = seguimientos.filter(estado="NO_ASISTIO").count()
    cancelados = seguimientos.filter(estado="CANCELADO").count()
    
    return {
        "total": total,
        "realizados": realizados,
        "pendientes": pendientes,
        "no_asistio": no_asistio,
        "cancelados": cancelados,
        "tasa_asistencia": (realizados / total * 100) if total > 0 else 0
    }


def crear_protocolo_default(categoria_paciente):
    """
    Crea un protocolo por defecto para una categoría.
    
    Args:
        categoria_paciente: str ("C1", "C2", "C3")
    
    Returns:
        ProtocoloSeguimiento creado
    """
    protocolos_default = {
        "C1": {
            "nombre": "PS1",
            "descripcion": "Protocolo de seguimiento para pacientes C1 - Seguimiento básico",
            "frecuencia_dias": 30,  # Cada 30 días
            "configuracion": {
                "tipo_seguimiento": "basico",
                "tests_requeridos": ["POCUS"],
                "notificaciones": True
            }
        },
        "C2": {
            "nombre": "PS2", 
            "descripcion": "Protocolo de seguimiento para pacientes C2 - Seguimiento intermedio",
            "frecuencia_dias": 15,  # Cada 15 días
            "configuracion": {
                "tipo_seguimiento": "intermedio",
                "tests_requeridos": ["FIBROSCAN"],
                "notificaciones": True,
                "recordatorio_dias": 3
            }
        },
        "C3": {
            "nombre": "PS3",
            "descripcion": "Protocolo de seguimiento para pacientes C3 - Seguimiento intensivo", 
            "frecuencia_dias": 7,  # Cada 7 días
            "configuracion": {
                "tipo_seguimiento": "intensivo",
                "tests_requeridos": ["FIBROSCAN", "POCUS"],
                "notificaciones": True,
                "recordatorio_dias": 1,
                "especialista_requerido": True
            }
        }
    }
    
    config = protocolos_default.get(categoria_paciente)
    if not config:
        raise ValueError(f"Categoría {categoria_paciente} no válida")
    
    protocolo = ProtocoloSeguimiento.objects.create(
        categoria_paciente=categoria_paciente,
        nombre=config["nombre"],
        descripcion=config["descripcion"],
        frecuencia_dias=config["frecuencia_dias"],
        configuracion=config["configuracion"]
    )
    
    logger.info(f"[ETHE] Protocolo creado: {protocolo}")
    
    return protocolo
