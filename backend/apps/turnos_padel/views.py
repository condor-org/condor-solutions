# apps/turnos_padel/views.py
from rest_framework import viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.response import Response 
from apps.common.permissions import (
    EsAdminDeSuCliente,
    EsSuperAdmin,
    SoloLecturaUsuariosFinalesYEmpleados
)
from apps.turnos_core.models import Lugar
from apps.turnos_padel.models import ConfiguracionSedePadel, TipoClasePadel
from apps.turnos_padel.serializers import (
    SedePadelSerializer,
    ConfiguracionSedePadelSerializer,
    TipoClasePadelSerializer
)

from django.db import transaction

class SedePadelViewSet(viewsets.ModelViewSet):
    """
    CRUD de sedes con configuración y tipos embebidos.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = SedePadelSerializer

    def get_queryset(self):
        user = self.request.user
        if user.tipo_usuario == "super_admin":
            return Lugar.objects.all().select_related("configuracion_padel").prefetch_related("configuracion_padel__tipos_clase")
        elif user.tipo_usuario == "admin_cliente":
            return Lugar.objects.filter(cliente=user.cliente).select_related("configuracion_padel").prefetch_related("configuracion_padel__tipos_clase")
        return Lugar.objects.none()

    def list(self, request, *args, **kwargs):
        """
        GET: Lista todas las sedes con configuracion_padel y tipos_clase embebidos.
        """
        queryset = self.get_queryset()
        for sede in queryset:
            config, created = ConfiguracionSedePadel.objects.get_or_create(sede=sede, defaults={"alias": "", "cbu_cvu": ""})
            if created:
                for nombre in ["Individual", "2 Personas", "3 Personas", "4 Personas"]:
                    TipoClasePadel.objects.create(configuracion_sede=config, nombre=nombre, precio=0)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        GET: Garantiza configuración en retrieve.a
        """
        instance = self.get_object()
        config, created = ConfiguracionSedePadel.objects.get_or_create(sede=instance, defaults={"alias": "", "cbu_cvu": ""})
        if created:
            for nombre in ["Individual", "2 Personas", "3 Personas", "4 Personas"]:
                TipoClasePadel.objects.create(configuracion_sede=config, nombre=nombre, precio=0)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @transaction.atomic
    def perform_create(self, serializer):
        return serializer.save(cliente=self.request.user.cliente)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ConfiguracionSedePadelViewSet(viewsets.ModelViewSet):
    """
    CRUD de configuraciones de sede pádel.
    🔹 Ahora usa sede_id en la URL para que el frontend no tenga que saber el id interno de configuración.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = ConfiguracionSedePadelSerializer
    lookup_field = "sede_id"  # Buscaremos por sede_id, no por id de configuración

    def get_queryset(self):
        user = self.request.user
        qs = ConfiguracionSedePadel.objects.all()

        if user.tipo_usuario == "admin_cliente":
            qs = qs.filter(sede__cliente=user.cliente)
        elif user.tipo_usuario != "super_admin":
            return ConfiguracionSedePadel.objects.none()

        return qs

    def get_object(self):
        sede_id = self.kwargs.get(self.lookup_field)
        try:
            return ConfiguracionSedePadel.objects.get(sede_id=sede_id)
        except ConfiguracionSedePadel.DoesNotExist:
            raise NotFound(f"La sede con ID {sede_id} no tiene configuración de pádel.")

class TipoClasePadelViewSet(viewsets.ModelViewSet):
    """
    CRUD para tipos de clase. Útil para actualizar precios individualmente.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = TipoClasePadelSerializer

    def get_queryset(self):
        user = self.request.user
        sede_id = self.request.query_params.get("sede_id")

        qs = TipoClasePadel.objects.all()

        # 🔹 Restringir por cliente
        if hasattr(user, "cliente"):
            qs = qs.filter(configuracion_sede__sede__cliente=user.cliente)

        # 🔹 Filtrar por sede si está en query params
        if sede_id:
            qs = qs.filter(configuracion_sede__sede_id=sede_id)

        return qs
