# apps/ethe_medica/services/establecimientos.py

from django.db import transaction
from django.contrib.auth import get_user_model
from apps.turnos_core.models import Lugar, Prestador, Disponibilidad
from apps.ethe_medica.models import Establecimiento, CentroAtencion, JerarquiaCentro, Medico
import logging

logger = logging.getLogger(__name__)
Usuario = get_user_model()


def crear_establecimiento_completo(cliente, admin_establecimiento, datos_establecimiento, centros_config):
    """
    Crea un establecimiento con todos sus centros de atención.
    
    Args:
        cliente: Cliente ETHE
        admin_establecimiento: Usuario admin del establecimiento
        datos_establecimiento: dict con datos del establecimiento
        centros_config: list de dicts con configuración de centros
    
    Returns:
        Establecimiento creado
    """
    with transaction.atomic():
        # 1. Crear establecimiento
        establecimiento = Establecimiento.objects.create(
            cliente=cliente,
            admin_establecimiento=admin_establecimiento,
            **datos_establecimiento
        )
        
        # 2. Crear centros de atención
        centros_creados = []
        for centro_config in centros_config:
            # Crear Lugar
            lugar = Lugar.objects.create(
                cliente=cliente,
                nombre=centro_config["nombre_lugar"],
                direccion=datos_establecimiento["direccion"],  # Misma dirección
                telefono=datos_establecimiento["telefono"],    # Mismo teléfono
                referente=centro_config["referente"],
                categorias_centro_ethe=centro_config["categorias"]
            )
            
            # Crear CentroAtencion
            centro = CentroAtencion.objects.create(
                establecimiento=establecimiento,
                lugar=lugar,
                categorias=centro_config["categorias"],
                nombre_centro=centro_config["nombre_centro"]
            )
            
            centros_creados.append(centro)
        
        # 3. Crear jerarquías automáticamente
        crear_jerarquias_automaticas(centros_creados)
        
        logger.info(f"[ETHE] Establecimiento creado: {establecimiento} con {len(centros_creados)} centros")
        
        return establecimiento


def crear_jerarquias_automaticas(centros):
    """Crea jerarquías automáticamente entre centros"""
    centros_c1 = [c for c in centros if "C1" in c.categorias]
    centros_c2 = [c for c in centros if "C2" in c.categorias]
    centros_c3 = [c for c in centros if "C3" in c.categorias]
    
    jerarquias_creadas = []
    
    # C1 → C2
    for c1 in centros_c1:
        for c2 in centros_c2:
            jerarquia = JerarquiaCentro.objects.create(
                centro_origen=c1,
                centro_destino=c2,
                categoria_origen="C1",
                categoria_destino="C2",
                prioridad=1
            )
            jerarquias_creadas.append(jerarquia)
    
    # C2 → C3
    for c2 in centros_c2:
        for c3 in centros_c3:
            jerarquia = JerarquiaCentro.objects.create(
                centro_origen=c2,
                centro_destino=c3,
                categoria_origen="C2",
                categoria_destino="C3",
                prioridad=1
            )
            jerarquias_creadas.append(jerarquia)
    
    logger.info(f"[ETHE] Jerarquías creadas: {len(jerarquias_creadas)}")
    return jerarquias_creadas


def crear_medico_completo(email, nombre, apellido, categorias, matricula, centro, especialidad_medica="", telefono=""):
    """
    Crea un médico completo con usuario, prestador y disponibilidades.
    
    Args:
        email: Email del médico
        nombre: Nombre del médico
        apellido: Apellido del médico
        categorias: Lista de categorías ["M1", "M2", "M3"]
        matricula: Matrícula del médico
        centro: CentroAtencion donde trabajará
        especialidad_medica: Especialidad médica
        telefono: Teléfono del médico
    
    Returns:
        Medico creado
    """
    with transaction.atomic():
        # 1. Crear Usuario
        user = Usuario.objects.create_user(
            email=email,
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            tipo_usuario="medico_m1",  # Default, se actualizará según categorías
            cliente=centro.establecimiento.cliente
        )
        
        # 2. Crear Prestador
        prestador = Prestador.objects.create(
            user=user,
            cliente=centro.establecimiento.cliente,
            especialidad=especialidad_medica,
            nombre_publico=f"{nombre} {apellido}"
        )
        
        # 3. Crear Medico
        medico = Medico.objects.create(
            user=user,
            prestador=prestador,
            categorias=categorias,
            matricula=matricula,
            especialidad_medica=especialidad_medica
        )
        
        # 4. Crear disponibilidades básicas (Lunes a Viernes, 9:00-17:00)
        for dia in range(0, 5):  # Lunes a Viernes
            Disponibilidad.objects.create(
                prestador=prestador,
                lugar=centro.lugar,
                dia_semana=dia,
                hora_inicio="09:00",
                hora_fin="17:00",
                activo=True
            )
        
        logger.info(f"[ETHE] Médico creado: {medico} en {centro}")
        return medico


def obtener_centros_siguientes(centro_origen, categoria_paciente):
    """
    Obtiene centros disponibles para derivación según la categoría del paciente.
    
    Args:
        centro_origen: CentroAtencion de origen
        categoria_paciente: str ("C1", "C2", "C3")
    
    Returns:
        list de dicts con centros disponibles
    """
    if categoria_paciente == "C1":
        categoria_destino = "C2"
    elif categoria_paciente == "C2":
        categoria_destino = "C3"
    else:
        return []
    
    jerarquias = JerarquiaCentro.objects.filter(
        centro_origen=centro_origen,
        categoria_destino=categoria_destino,
        activo=True
    ).select_related("centro_destino", "centro_destino__lugar")
    
    centros_validos = []
    for jerarquia in jerarquias:
        centro_destino = jerarquia.centro_destino
        if centro_destino.puede_atender_categoria(categoria_destino):
            # Verificar que tenga médicos disponibles
            if tiene_medicos_disponibles(centro_destino, categoria_destino):
                centros_validos.append({
                    "centro": centro_destino,
                    "prioridad": jerarquia.prioridad,
                    "distancia": jerarquia.distancia_km
                })
    
    # Ordenar por prioridad
    centros_validos.sort(key=lambda x: x["prioridad"], reverse=True)
    
    return centros_validos


def tiene_medicos_disponibles(centro, categoria):
    """
    Verifica si un centro tiene médicos disponibles para una categoría.
    
    Args:
        centro: CentroAtencion
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


def obtener_establecimientos_por_cliente(cliente):
    """
    Obtiene todos los establecimientos de un cliente con sus centros.
    
    Args:
        cliente: Cliente ETHE
    
    Returns:
        QuerySet de Establecimiento
    """
    return Establecimiento.objects.filter(
        cliente=cliente,
        activo=True
    ).prefetch_related("centros_ethe", "centros_ethe__lugar")


def obtener_centros_por_categoria(cliente, categoria):
    """
    Obtiene todos los centros de una categoría específica.
    
    Args:
        cliente: Cliente ETHE
        categoria: str ("C1", "C2", "C3")
    
    Returns:
        QuerySet de CentroAtencion
    """
    return CentroAtencion.objects.filter(
        establecimiento__cliente=cliente,
        categorias__contains=[categoria],
        activo=True
    ).select_related("establecimiento", "lugar")


def crear_red_centros_automatica(cliente):
    """
    Crea automáticamente la red de centros para un cliente.
    """
    establecimientos = Establecimiento.objects.filter(cliente=cliente, activo=True)
    
    for establecimiento in establecimientos:
        centros = establecimiento.centros_ethe.filter(activo=True)
        
        # Agrupar por categorías
        centros_c1 = [c for c in centros if "C1" in c.categorias]
        centros_c2 = [c for c in centros if "C2" in c.categorias]
        centros_c3 = [c for c in centros if "C3" in c.categorias]
        
        # Crear jerarquías C1→C2
        for c1 in centros_c1:
            for c2 in centros_c2:
                JerarquiaCentro.objects.get_or_create(
                    centro_origen=c1,
                    centro_destino=c2,
                    defaults={
                        "categoria_origen": "C1",
                        "categoria_destino": "C2",
                        "prioridad": 1
                    }
                )
        
        # Crear jerarquías C2→C3
        for c2 in centros_c2:
            for c3 in centros_c3:
                JerarquiaCentro.objects.get_or_create(
                    centro_origen=c2,
                    centro_destino=c3,
                    defaults={
                        "categoria_origen": "C2",
                        "categoria_destino": "C3",
                        "prioridad": 1
                    }
                )
    
    logger.info(f"[ETHE] Red de centros creada para cliente {cliente}")
