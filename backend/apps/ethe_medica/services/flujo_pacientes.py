# apps/ethe_medica/services/flujo_pacientes.py

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.turnos_core.models import Prestador
from apps.ethe_medica.models import Medico, Paciente, ResultadoTest, CentroAtencion, JerarquiaCentro
import logging

logger = logging.getLogger(__name__)
Usuario = get_user_model()


def ingresar_paciente_c1(datos_paciente, resultado_pocus, resultado_fib4, medico, centro):
    """
    Ingresa un paciente al sistema desde un centro C1.
    
    Args:
        datos_paciente: dict con datos del paciente
        resultado_pocus: str ("NORMAL" o "HG") - OBLIGATORIO
        resultado_fib4: str ("NR" o "R") - OBLIGATORIO
        medico: instancia de Medico
        centro: instancia de Lugar
    
    Returns:
        dict con paciente creado, tests registrados, categoria asignada
    """
    # 1. Validar que POCUS sea HG (sino no ingresa)
    if resultado_pocus != ResultadoTest.POCUS_HG:
        return {
            "ingresado": False,
            "motivo": "POCUS normal - no ingresa al sistema"
        }
    
    with transaction.atomic():
        # 2. Crear Usuario con rol 'paciente'
        user = Usuario.objects.create(
            email=datos_paciente["email"],
            nombre=datos_paciente["nombre"],
            apellido=datos_paciente["apellido"],
            telefono=datos_paciente["telefono"],
            tipo_usuario="paciente",
            cliente=medico.user.cliente
        )
        
        # 3. Crear Paciente
        paciente = Paciente.objects.create(
            user=user,
            categoria_actual="C1",  # Temporal, se actualizará según FIB4
            documento=datos_paciente["documento"],
            centro_ingreso=centro,
            medico_ingreso=medico,
            domicilio_calle=datos_paciente["domicilio_calle"],
            domicilio_ciudad=datos_paciente["domicilio_ciudad"],
            domicilio_provincia=datos_paciente["domicilio_provincia"],
            domicilio_codigo_postal=datos_paciente.get("domicilio_codigo_postal", ""),
            telefono_contacto=datos_paciente["telefono"],
            email_seguimiento=datos_paciente["email"],
            fecha_nacimiento=datos_paciente["fecha_nacimiento"],
            obra_social=datos_paciente.get("obra_social", "")
        )
        
        # 4. Registrar ResultadoTest (POCUS)
        test_pocus = ResultadoTest.objects.create(
            paciente=paciente,
            tipo_test="POCUS",
            resultado=resultado_pocus,
            fecha_realizacion=timezone.now(),
            centro=centro,
            medico=medico
        )
        
        # 5. Registrar ResultadoTest (FIB4) - OBLIGATORIO
        test_fib4 = ResultadoTest.objects.create(
            paciente=paciente,
            tipo_test="FIB4",
            resultado=resultado_fib4,
            fecha_realizacion=timezone.now(),
            centro=centro,
            medico=medico
        )
        
        # 6. Determinar categoría
        categoria_final = "C1"  # Default
        centros_disponibles = []
        
        if resultado_fib4 == ResultadoTest.FIB4_R:
            categoria_final = "C2"
            # Buscar centros C2 disponibles
            centros_disponibles = obtener_centros_disponibles_para_paciente(paciente, "C2")
        elif resultado_fib4 == ResultadoTest.FIB4_NR:
            categoria_final = "C1"
        
        # Actualizar categoría del paciente
        paciente.cambiar_categoria(categoria_final, f"Resultado FIB4: {resultado_fib4}")
        
        logger.info(
            f"[ETHE] Paciente ingresado: {paciente} - Categoría: {categoria_final} - Centro: {centro}"
        )
        
        return {
            "ingresado": True,
            "paciente": paciente,
            "categoria": categoria_final,
            "centros_disponibles": centros_disponibles,
            "tests_registrados": [test_pocus, test_fib4]
        }


def procesar_resultado_fibroscan(paciente, resultado, medico, centro, turno=None):
    """
    Procesa resultado de FIBROSCAN y actualiza categoría del paciente.
    
    Args:
        paciente: instancia de Paciente
        resultado: str ("BAJO", "INTERMEDIO", "ALTO")
        medico: instancia de Medico
        centro: instancia de Lugar
        turno: instancia de Turno (opcional)
    
    Returns:
        dict con nueva categoría, centros disponibles si aplica
    """
    with transaction.atomic():
        # 1. Registrar ResultadoTest (FIBROSCAN)
        test_fibroscan = ResultadoTest.objects.create(
            paciente=paciente,
            tipo_test="FIBROSCAN",
            resultado=resultado,
            fecha_realizacion=timezone.now(),
            centro=centro,
            medico=medico,
            turno=turno
        )
        
        # 2. Determinar nueva categoría
        categoria_anterior = paciente.categoria_actual
        nueva_categoria = None
        centros_disponibles = []
        
        if resultado == ResultadoTest.FIBROSCAN_BAJO:
            nueva_categoria = "C1"
        elif resultado == ResultadoTest.FIBROSCAN_INTERMEDIO:
            nueva_categoria = "C2"
        elif resultado == ResultadoTest.FIBROSCAN_ALTO:
            nueva_categoria = "C3"
            # Buscar centros C3 disponibles
            centros_disponibles = obtener_centros_disponibles_para_paciente(paciente, "C3")
        
        # 3. Actualizar Paciente.categoria_actual
        if nueva_categoria and nueva_categoria != categoria_anterior:
            paciente.cambiar_categoria(nueva_categoria, f"Resultado FIBROSCAN: {resultado}")
        
        logger.info(
            f"[ETHE] FIBROSCAN procesado: {paciente} - {categoria_anterior} → {nueva_categoria}"
        )
        
        return {
            "test_registrado": test_fibroscan,
            "categoria_anterior": categoria_anterior,
            "categoria_nueva": nueva_categoria,
            "centros_disponibles": centros_disponibles
        }


def obtener_centros_disponibles_para_paciente(paciente, categoria_destino):
    """
    Obtiene centros disponibles según la categoría del paciente.
    
    Args:
        paciente: instancia de Paciente
        categoria_destino: str ("C2" o "C3")
    
    Returns:
        list de CentroAtencion disponibles
    """
    # Buscar el centro de atención de origen
    centro_origen = CentroAtencion.objects.filter(
        lugar=paciente.centro_ingreso
    ).first()
    
    if not centro_origen:
        return []
    
    # Obtener jerarquías activas
    jerarquias = JerarquiaCentro.objects.filter(
        centro_origen=centro_origen,
        categoria_destino=categoria_destino,
        activo=True
    ).select_related("centro_destino", "centro_destino__lugar")
    
    # Filtrar por categoría destino
    centros_candidatos = []
    for jerarquia in jerarquias:
        centro_destino = jerarquia.centro_destino
        if centro_destino.puede_atender_categoria(categoria_destino):
            # Verificar que tenga médicos disponibles
            if tiene_medicos_disponibles(centro_destino, categoria_destino):
                centros_candidatos.append({
                    "centro": centro_destino,
                    "prioridad": jerarquia.prioridad
                })
    
    # Ordenar por prioridad
    centros_candidatos.sort(key=lambda x: x["prioridad"], reverse=True)
    
    return [item["centro"] for item in centros_candidatos]


def tiene_medicos_disponibles(centro, categoria):
    """
    Verifica si un centro tiene médicos disponibles para una categoría.
    
    Args:
        centro: instancia de CentroAtencion
        categoria: str ("C1", "C2", "C3")
    
    Returns:
        bool
    """
    # Mapear categoría a tipo de médico
    categoria_medico = {
        "C1": "C1",
        "C2": "C2", 
        "C3": "C3"
    }
    
    medico_categoria = categoria_medico.get(categoria)
    if not medico_categoria:
        return False
    
    # Buscar médicos con esa categoría que tengan disponibilidad en el centro
    medicos = Medico.objects.filter(
        categorias__contains=[medico_categoria],
        activo=True,
        prestador__disponibilidades__lugar=centro.lugar,
        prestador__disponibilidades__activo=True
    ).distinct()
    
    return medicos.exists()


def obtener_turnos_disponibles_para_paciente(paciente, centro, fecha_inicio, fecha_fin):
    """
    Obtiene turnos disponibles para un paciente según su categoría.
    
    Args:
        paciente: instancia de Paciente
        centro: instancia de CentroAtencion
        fecha_inicio: date
        fecha_fin: date
    
    Returns:
        dict con turnos agrupados por médico
    """
    from apps.turnos_core.models import Turno
    
    # 1. Obtener categoría del paciente
    categoria = paciente.categoria_actual
    
    # 2. Filtrar médicos que pueden atender esa categoría
    categoria_medico = {
        "C1": "C1",
        "C2": "C2",
        "C3": "C3"
    }
    
    medico_categoria = categoria_medico.get(categoria)
    if not medico_categoria:
        return {}
    
    medicos = Medico.objects.filter(
        categorias__contains=[medico_categoria],
        activo=True,
        prestador__disponibilidades__lugar=centro.lugar,
        prestador__disponibilidades__activo=True
    ).distinct()
    
    # 3. Obtener turnos disponibles en el centro
    turnos_por_medico = {}
    
    for medico in medicos:
        turnos = Turno.objects.filter(
            recurso=medico.prestador,
            lugar=centro.lugar,
            estado="disponible",
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).order_by("fecha", "hora")
        
        if turnos.exists():
            turnos_por_medico[medico] = turnos
    
    return turnos_por_medico
