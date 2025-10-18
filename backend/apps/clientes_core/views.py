# apps/clientes_core/views.py

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from apps.clientes_core.models import Cliente, ClienteDominio
from apps.clientes_core.serializers import ClienteSerializer
from apps.common.permissions import EsSuperAdmin


class ClienteViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    API de solo lectura exclusiva para superadmin.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated & EsSuperAdmin]


@api_view(['GET'])
@permission_classes([AllowAny])
def tenant_config(request):
    """
    Endpoint para obtener la configuración del tenant basada en el hostname.
    Usado por nginx para determinar qué tipo de frontend servir.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # LOG: Headers recibidos
    logger.error(f"[TENANT_CONFIG] Headers recibidos:")
    logger.error(f"[TENANT_CONFIG] HTTP_X_TENANT_HOST: {request.META.get('HTTP_X_TENANT_HOST', 'NO ENCONTRADO')}")
    logger.error(f"[TENANT_CONFIG] HTTP_HOST: {request.META.get('HTTP_HOST', 'NO ENCONTRADO')}")
    logger.error(f"[TENANT_CONFIG] REMOTE_ADDR: {request.META.get('REMOTE_ADDR', 'NO ENCONTRADO')}")
    
    hostname = request.META.get('HTTP_X_TENANT_HOST', request.META.get('HTTP_HOST', ''))
    
    logger.error(f"[TENANT_CONFIG] Hostname extraído: '{hostname}'")
    
    if not hostname:
        logger.error(f"[TENANT_CONFIG] ERROR: No hostname provided")
        return JsonResponse({
            'error': 'No hostname provided',
            'tipo_fe': 'padel'  # default
        }, status=400)
    
    try:
        logger.error(f"[TENANT_CONFIG] Buscando ClienteDominio con hostname='{hostname}' y activo=True")
        
        # Buscar el cliente por hostname
        cliente_dominio = ClienteDominio.objects.select_related('cliente').get(
            hostname=hostname,
            activo=True
        )
        
        cliente = cliente_dominio.cliente
        
        logger.error(f"[TENANT_CONFIG] ✅ Cliente encontrado: {cliente.nombre} (ID: {cliente.id})")
        logger.error(f"[TENANT_CONFIG] ✅ Cliente tipo_fe: {cliente.tipo_fe}")
        logger.error(f"[TENANT_CONFIG] ✅ Cliente tipo_cliente: {cliente.tipo_cliente}")
        
        return JsonResponse({
            'tipo_fe': cliente.tipo_fe,
            'nombre': cliente.nombre,
            'tipo_cliente': cliente.tipo_cliente,
            'theme': cliente.theme,
            'color_primario': cliente.color_primario,
            'color_secundario': cliente.color_secundario,
            'hostname': hostname
        })
        
    except ClienteDominio.DoesNotExist:
        logger.error(f"[TENANT_CONFIG] ❌ ClienteDominio.DoesNotExist para hostname='{hostname}'")
        
        # Log todos los ClienteDominio existentes para debug
        dominios_existentes = ClienteDominio.objects.filter(activo=True).values('hostname', 'cliente__nombre')
        logger.error(f"[TENANT_CONFIG] Dominios existentes en DB:")
        for dominio in dominios_existentes:
            logger.error(f"[TENANT_CONFIG]   - {dominio['hostname']} -> {dominio['cliente__nombre']}")
        
        # Si no se encuentra el cliente, devolver configuración por defecto
        logger.error(f"[TENANT_CONFIG] Devolviendo configuración por defecto")
        return JsonResponse({
            'tipo_fe': 'padel',  # default
            'nombre': 'Condor',
            'tipo_cliente': 'padel',
            'theme': 'classic',
            'color_primario': '#F44336',
            'color_secundario': '#000000',
            'hostname': hostname,
            'default': True
        })
