# apps/clientes_core/views.py

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from apps.clientes_core.models import Cliente
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
