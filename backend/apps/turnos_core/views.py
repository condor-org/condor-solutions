# apps/turnos_core/views.py
from rest_framework.generics import ListAPIView, CreateAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Lugar
from apps.turnos_core.serializers import LugarSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, permissions
from .models import BloqueoTurnos
from .serializers import BloqueoTurnosSerializer
from django.utils.timezone import now
from django.db import models

from apps.turnos_core.models import Turno
from apps.turnos_core.serializers import (
    TurnoSerializer,
    TurnoReservaSerializer,
    TurnoDisponibleSerializer,
)


class TurnoListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TurnoSerializer

    def get_queryset(self):
        usuario = self.request.user

        if usuario.is_superuser:
            return Turno.objects.all().select_related("usuario", "servicio", "lugar")

        if hasattr(usuario, "tipo_usuario") and usuario.tipo_usuario == "profesor":
            return Turno.objects.filter(
                servicio__responsable=usuario
            ).select_related("usuario", "servicio", "lugar")

        # Si es jugador → devuelve solo sus turnos reservados
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
    description="Devuelve turnos libres para un profesor en una sede específica y fecha opcional.",
    parameters=[
        OpenApiParameter("profesor_id", int, OpenApiParameter.QUERY, description="ID del profesor"),
        OpenApiParameter("lugar_id", int, OpenApiParameter.QUERY, description="ID de la sede"),
        OpenApiParameter("fecha", str, OpenApiParameter.QUERY, description="Fecha (YYYY-MM-DD)")
    ]
)
class TurnosDisponiblesView(ListAPIView):
    serializer_class = TurnoDisponibleSerializer

    def get_queryset(self):
        query_params = self.request.query_params

        profesor_id = query_params.get("profesor_id")
        lugar_id = query_params.get("lugar_id")
        fecha_str = query_params.get("fecha")  # opcional

        if not profesor_id or not lugar_id:
            raise ValidationError("profesor_id y lugar_id son obligatorios.")

        filtros = {
            "usuario__isnull": True,
            "object_id": profesor_id,
            "lugar_id": lugar_id,
        }

        if fecha_str:
            fecha = parse_date(fecha_str)
            if not fecha:
                raise ValidationError("Formato de fecha inválido (usar YYYY-MM-DD).")
            filtros["fecha"] = fecha

        qs = Turno.objects.filter(**filtros)

        # 🔥 FILTRADO de turnos pasados y actuales
        ahora = now()
        fecha_actual = ahora.date()
        hora_actual = ahora.time()

        qs = qs.filter(
            models.Q(fecha__gt=fecha_actual) |
            models.Q(fecha=fecha_actual, hora__gt=hora_actual)
        )

        return qs.order_by("fecha", "hora")

# --- PERMISOS: GET cualquiera autenticado, el resto solo admin ---
class SoloAdminEditar(IsAdminUser):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return super().has_permission(request, view)


class LugarViewSet(viewsets.ModelViewSet):
    queryset = Lugar.objects.all()
    serializer_class = LugarSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [SoloAdminEditar]  # Cambiado acá


class BloqueoTurnosViewSet(viewsets.ModelViewSet):
    queryset = BloqueoTurnos.objects.all()
    serializer_class = BloqueoTurnosSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
