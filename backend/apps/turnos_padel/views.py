# apps/turnos_padel/views.py
from rest_framework import viewsets, status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.response import Response 
from apps.common.permissions import (
    EsAdminDeSuCliente,
    EsSuperAdmin,
    SoloLecturaUsuariosFinalesYEmpleados
)
from apps.turnos_core.models import Lugar, Turno, TurnoBonificado
from apps.turnos_padel.models import ConfiguracionSedePadel, TipoClasePadel, AbonoMes
from apps.turnos_padel.serializers import (
    SedePadelSerializer,
    ConfiguracionSedePadelSerializer,
    TipoClasePadelSerializer,
    AbonoMesSerializer,
    AbonoMesDetailSerializer
)

from django.db import transaction

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from rest_framework.request import Request
from rest_framework.parsers import JSONParser
from io import BytesIO
import json
from apps.turnos_padel.services.abonos import reservar_abono_mes_actual_y_prioridad
import logging
logger = logging.getLogger(__name__)

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

class AbonoMesViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        logger.info("[AbonoMesViewSet:get_queryset] Usuario: %s (%s)", user.id, user.tipo_usuario)

        if user.tipo_usuario == "super_admin":
            return AbonoMes.objects.all()
        elif user.tipo_usuario == "admin_cliente":
            return AbonoMes.objects.filter(sede__cliente=user.cliente)
        return AbonoMes.objects.filter(usuario=user)

    def get_serializer_class(self):
        if self.action in ["retrieve", "list"]:
            return AbonoMesDetailSerializer
        return AbonoMesSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        logger.info("[AbonoMesViewSet:create] Usuario: %s (%s)", user.id, user.tipo_usuario)
        logger.debug("[AbonoMesViewSet:create] Data original: %s", request.data)

        # Si es usuario final, fuerza su propio ID como usuario
        data = request.data.copy()
        if user.tipo_usuario == "usuario_final":
            usuario_id = data.get("usuario")
            if usuario_id and int(usuario_id) != user.id:
                return Response({"detail": "No podés crear abonos para otro usuario."}, status=403)
            data["usuario"] = user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        logger.debug("[AbonoMesViewSet:create] Serializer validado: %s", serializer.validated_data)

        abono, resumen = self.perform_create(serializer)

        # Serializamos de nuevo para incluir relaciones y campos calculados
        resp_serializer = self.get_serializer(abono)
        payload = resp_serializer.data
        payload["resumen"] = resumen
        payload["monto_sugerido"] = resumen.get("monto_sugerido")

        logger.info("[AbonoMesViewSet:create] Abono creado exitosamente con turnos")
        return Response(payload, status=status.HTTP_201_CREATED, headers=self.get_success_headers(payload))

    @transaction.atomic
    def perform_create(self, serializer):
        abono = serializer.save()
        logger.info("[AbonoMesViewSet:perform_create] Abono ID %s creado", abono.id)

        try:
            abono, resumen = reservar_abono_mes_actual_y_prioridad(abono)
            return abono, resumen
        except ValueError as e:
            logger.warning("[AbonoMesViewSet:perform_create] Error al reservar turnos: %s", str(e))
            raise serializers.ValidationError({"detalle": str(e)})
