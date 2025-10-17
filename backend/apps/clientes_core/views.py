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
    hostname = request.META.get('HTTP_X_TENANT_HOST', request.META.get('HTTP_HOST', ''))
    
    if not hostname:
        return JsonResponse({
            'error': 'No hostname provided',
            'tipo_fe': 'padel'  # default
        }, status=400)
    
    try:
        # Buscar el cliente por hostname
        cliente_dominio = ClienteDominio.objects.select_related('cliente').get(
            hostname=hostname,
            activo=True
        )
        
        cliente = cliente_dominio.cliente
        
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
        # Si no se encuentra el cliente, devolver configuración por defecto
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
