# apps/ethe_medica/services/asignacion_turnos.py

from django.db import transaction
from django.utils import timezone
from apps.turnos_core.models import Turno
from apps.ethe_medica.models import Medico, Paciente
import logging

logger = logging.getLogger(__name__)


def reservar_turno_paciente(paciente, turno_id, medico_reservador):
    """
    Reserva un turno para un paciente.
    Reutiliza lógica de ReservarTurnoAdminView de turnos_core.
    
    Args:
        paciente: instancia de Paciente
        turno_id: int
        medico_reservador: instancia de Medico (quien reserva, puede ser distinto al prestador)
    
    Returns:
        Turno reservado
    """
    with transaction.atomic():
        # 1. Validar que turno esté disponible
        turno = Turno.objects.select_for_update().get(id=turno_id)
        
        if turno.estado != "disponible":
            raise ValueError("El turno no está disponible")
        
        if turno.usuario_id is not None:
            raise ValueError("El turno ya fue reservado")
        
        # 2. Validar que médico del turno pueda atender categoría del paciente
        prestador_turno = turno.recurso
        medico_turno = Medico.objects.filter(prestador=prestador_turno).first()
        
        if not medico_turno:
            raise ValueError("No se encontró médico para este turno")
        
        # Verificar que el médico puede atender la categoría del paciente
        categoria_medico = {
            "C1": "C1",
            "C2": "C2", 
            "C3": "C3"
        }
        
        categoria_requerida = categoria_medico.get(paciente.categoria_actual)
        if not categoria_requerida or categoria_requerida not in medico_turno.categorias:
            raise ValueError(f"El médico no puede atender pacientes de categoría {paciente.categoria_actual}")
        
        # 3. Reservar turno (actualizar usuario, estado)
        turno.usuario = paciente.user
        turno.estado = "reservado"
        turno.tipo_turno = f"consulta_{paciente.categoria_actual.lower()}"
        turno.save()
        
        logger.info(
            f"[ETHE] Turno reservado: {turno} para paciente {paciente} "
            f"por médico {medico_reservador}"
        )
        
        # 4. Notificar al paciente (implementar notificaciones)
        # TODO: Implementar sistema de notificaciones
        
        # 5. Retornar turno
        return turno


def validar_turno_para_paciente(turno, paciente):
    """
    Valida que un turno sea apropiado para un paciente.
    
    Args:
        turno: instancia de Turno
        paciente: instancia de Paciente
    
    Returns:
        dict con resultado de validación
    """
    # 1. Verificar que centro del turno puede atender categoría del paciente
    if not turno.lugar.puede_atender_categoria(paciente.categoria_actual):
        return {
            "valido": False,
            "error": f"El centro {turno.lugar} no puede atender pacientes de categoría {paciente.categoria_actual}"
        }
    
    # 2. Verificar que médico (prestador) tiene categoría adecuada
    prestador = turno.recurso
    medico = Medico.objects.filter(prestador=prestador).first()
    
    if not medico:
        return {
            "valido": False,
            "error": "No se encontró médico para este turno"
        }
    
    # 3. Verificar que médico tiene Medico.categorias correcta
    categoria_medico = {
        "C1": "C1",
        "C2": "C2",
        "C3": "C3"
    }
    
    categoria_requerida = categoria_medico.get(paciente.categoria_actual)
    if not categoria_requerida or categoria_requerida not in medico.categorias:
        return {
            "valido": False,
            "error": f"El médico {medico} no puede atender pacientes de categoría {paciente.categoria_actual}"
        }
    
    return {
        "valido": True,
        "medico": medico,
        "centro": turno.lugar
    }


def obtener_turnos_disponibles_para_paciente(paciente, centro, fecha_inicio, fecha_fin):
    """
    Obtiene turnos disponibles para un paciente según su categoría.
    
    Args:
        paciente: instancia de Paciente
        centro: instancia de Lugar
        fecha_inicio: date
        fecha_fin: date
    
    Returns:
        dict con turnos agrupados por médico
    """
    from apps.ethe_medica.services.flujo_pacientes import obtener_turnos_disponibles_para_paciente as obtener_turnos_base
    
    # Reutilizar función del módulo flujo_pacientes
    return obtener_turnos_base(paciente, centro, fecha_inicio, fecha_fin)


def cancelar_turno_paciente(turno, motivo=""):
    """
    Cancela un turno de un paciente.
    
    Args:
        turno: instancia de Turno
        motivo: str (opcional)
    
    Returns:
        Turno cancelado
    """
    with transaction.atomic():
        turno = Turno.objects.select_for_update().get(id=turno.id)
        
        if turno.estado != "reservado":
            raise ValueError("El turno no está reservado")
        
        # Liberar turno
        turno.usuario = None
        turno.estado = "disponible"
        turno.tipo_turno = None
        turno.save()
        
        logger.info(
            f"[ETHE] Turno cancelado: {turno} - Motivo: {motivo}"
        )
        
        return turno


def reprogramar_turno_paciente(turno_original, nuevo_turno_id, medico_reservador):
    """
    Reprograma un turno de un paciente.
    
    Args:
        turno_original: instancia de Turno (turno actual)
        nuevo_turno_id: int (nuevo turno)
        medico_reservador: instancia de Medico
    
    Returns:
        dict con turnos (anterior y nuevo)
    """
    with transaction.atomic():
        # Obtener paciente del turno original
        paciente = Paciente.objects.get(user=turno_original.usuario)
        
        # Cancelar turno original
        turno_anterior = cancelar_turno_paciente(turno_original, "Reprogramación")
        
        # Reservar nuevo turno
        turno_nuevo = reservar_turno_paciente(paciente, nuevo_turno_id, medico_reservador)
        
        logger.info(
            f"[ETHE] Turno reprogramado: {turno_anterior} → {turno_nuevo} "
            f"para paciente {paciente}"
        )
        
        return {
            "turno_anterior": turno_anterior,
            "turno_nuevo": turno_nuevo,
            "paciente": paciente
        }
