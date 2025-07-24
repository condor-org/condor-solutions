# apps/turnos_core/views.py

from rest_framework.generics import ListAPIView, CreateAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from django.db import models
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from apps.turnos_core.models import Prestador, Disponibilidad
from apps.turnos_core.serializers import PrestadorSerializer
from apps.turnos_core.serializers import PrestadorDisponibleSerializer


from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.turnos_core.models import (
    Lugar, BloqueoTurnos, Turno, Prestador, Disponibilidad
)
from apps.turnos_core.serializers import (
    LugarSerializer,
    BloqueoTurnosSerializer,
    TurnoSerializer,
    TurnoReservaSerializer,
    TurnoDisponibleSerializer,
    PrestadorSerializer, 
    PrestadorConUsuarioSerializer,
    DisponibilidadSerializer
)
from django.db.models import Q

from apps.common.permissions import (
    EsSuperAdmin,
    EsAdminDeSuCliente,
    EsPrestador,
    EsDelMismoCliente,
)


# --- EXISTENTES ---
class TurnoListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TurnoSerializer

    def get_queryset(self):
        usuario = self.request.user

        if usuario.is_superuser:
            return Turno.objects.all().select_related("usuario", "servicio", "lugar")

        if hasattr(usuario, "tipo_usuario") and usuario.tipo_usuario == "empleado_cliente":
            return Turno.objects.filter(
                content_type=ContentType.objects.get_for_model(Prestador),
                object_id__in=Prestador.objects.filter(user=usuario).values_list("id", flat=True)
            ).select_related("usuario", "servicio", "lugar")

        return Turno.objects.filter(
            usuario=usuario
        ).select_related("usuario", "servicio", "lugar")


class TurnoReservaView(CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TurnoReservaSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        turno = serializer.save()
        return Response({"message": "Turno reservado exitosamente", "turno_id": turno.id})


@extend_schema(
    description="Devuelve turnos libres para un prestador en una sede específica y fecha opcional.",
    parameters=[
        OpenApiParameter("prestador_id", int, OpenApiParameter.QUERY, description="ID del prestador"),
        OpenApiParameter("lugar_id", int, OpenApiParameter.QUERY, description="ID de la sede"),
        OpenApiParameter("fecha", str, OpenApiParameter.QUERY, description="Fecha (YYYY-MM-DD)")
    ]
)
class TurnosDisponiblesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        prestador_id = self.kwargs.get("prestador_id") or query_params.get("prestador_id")
        lugar_id = query_params.get("lugar_id")
        fecha_str = query_params.get("fecha")

        if not prestador_id or not lugar_id:
            return Response({"error": "prestador_id y lugar_id son obligatorios."}, status=400)

        filtros = {
            "usuario__isnull": True,
            "object_id": prestador_id,
            "lugar_id": lugar_id,
        }

        if fecha_str:
            fecha = parse_date(fecha_str)
            if not fecha:
                return Response({"error": "Formato de fecha inválido (usar YYYY-MM-DD)."}, status=400)
            filtros["fecha"] = fecha

        ahora = now()
        fecha_actual = ahora.date()
        hora_actual = ahora.time()

        turnos = Turno.objects.filter(**filtros).filter(
            Q(fecha__gt=fecha_actual) |
            Q(fecha=fecha_actual, hora__gt=hora_actual)
        ).order_by("fecha", "hora")

        return Response(TurnoSerializer(turnos, many=True).data)



# --- PERMISOS: GET cualquiera autenticado, el resto solo admin ---
class SoloAdminEditar(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and (
            request.user.tipo_usuario in {"super_admin", "admin_cliente"}
        )


class LugarViewSet(viewsets.ModelViewSet):
    queryset = Lugar.objects.all()
    serializer_class = LugarSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [SoloAdminEditar]


class BloqueoTurnosViewSet(viewsets.ModelViewSet):
    queryset = BloqueoTurnos.objects.all()
    serializer_class = BloqueoTurnosSerializer
    permission_classes = [IsAuthenticated, EsSuperAdmin | EsAdminDeSuCliente]


# --- NUEVAS VISTAS ---

class PrestadorViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente | EsPrestador)]

    def get_queryset(self):
        user = self.request.user

        if user.tipo_usuario == "super_admin":
            return Prestador.objects.all()

        if user.tipo_usuario == "admin_cliente":
            return Prestador.objects.filter(user__cliente=user.cliente)

        if user.tipo_usuario == "empleado_cliente":
            return Prestador.objects.filter(user=user)

        return Prestador.objects.none()
    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {})["request"] = self.request
        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return PrestadorConUsuarioSerializer
        return PrestadorSerializer

    def perform_destroy(self, instance):
        usuario = instance.user
        instance.delete()
        usuario.delete()


class DisponibilidadViewSet(viewsets.ModelViewSet):
    serializer_class = DisponibilidadSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente | EsPrestador)]

    def get_queryset(self):
        user = self.request.user

        if user.tipo_usuario == "super_admin":
            return Disponibilidad.objects.all()

        if user.tipo_usuario == "admin_cliente":
            return Disponibilidad.objects.filter(prestador__cliente=user.cliente)

        if user.tipo_usuario == "empleado_cliente":
            return Disponibilidad.objects.filter(prestador__user=user)

        return Disponibilidad.objects.none()


class GenerarTurnosView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        data = request.data
        prestador_id = data.get("prestador_id")
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")

        if not prestador_id or not fecha_inicio or not fecha_fin:
            return Response({"error": "Faltan parámetros requeridos."}, status=400)

        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido (usar YYYY-MM-DD)."}, status=400)

        total = generar_turnos_para_prestador(
            prestador_id=prestador_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        return Response({"message": f"{total} turnos generados."})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prestadores_disponibles(request):
    lugar_id = request.query_params.get("lugar_id")
    if not lugar_id:
        return Response([], status=200)

    prestadores = Prestador.objects.filter(
        activo=True,
        disponibilidades__lugar_id=lugar_id,
    ).distinct()

    serializer = PrestadorDisponibleSerializer(prestadores, many=True, context={"request": request})
    return Response(serializer.data)
