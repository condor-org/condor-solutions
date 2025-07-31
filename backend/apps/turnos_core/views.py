# apps/turnos_core/views.py

# Built-in
from datetime import datetime

# Django
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils.timezone import now

# Django REST Framework
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import (
    api_view,
    permission_classes,
    action,
)
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

# drf-spectacular
from drf_spectacular.utils import OpenApiParameter, extend_schema

# App imports - Permisos
from apps.common.permissions import (
    EsAdminDeSuCliente,
    EsDelMismoCliente,
    EsPrestador,
    EsSuperAdmin,
    SoloLecturaUsuariosFinalesYEmpleados,
)

# App imports - Modelos
from apps.turnos_core.models import (
    BloqueoTurnos,
    Disponibilidad,
    Lugar,
    Prestador,
    Turno,
)

# App imports - Serializers
from apps.turnos_core.serializers import (
    BloqueoTurnosSerializer,
    DisponibilidadSerializer,
    LugarSerializer,
    PrestadorConUsuarioSerializer,
    PrestadorDetailSerializer,
    PrestadorSerializer,
    TurnoDisponibleSerializer,
    TurnoReservaSerializer,
    TurnoSerializer,
    CrearTurnoBonificadoSerializer,
)

# App imports - Servicios
from apps.turnos_core.services.turnos import generar_turnos_para_prestador



class TurnoListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TurnoSerializer

    def get_queryset(self):
        usuario = self.request.user

        if usuario.is_superuser:
            return Turno.objects.all().select_related("usuario", "lugar")

        if hasattr(usuario, "tipo_usuario") and usuario.tipo_usuario == "empleado_cliente":
            return Turno.objects.filter(
                content_type=ContentType.objects.get_for_model(Prestador),
                object_id__in=Prestador.objects.filter(user=usuario).values_list("id", flat=True)
            ).select_related("usuario", "lugar")

        return Turno.objects.filter(
            usuario=usuario
        ).select_related("usuario", "lugar")

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
    description="Devuelve turnos para un prestador en una sede específica y fecha opcional.",
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
            estado__in=["disponible", "reservado"],
            fecha__gt=fecha_actual
        ) | Turno.objects.filter(
            **filtros,
            estado__in=["disponible", "reservado"],
            fecha=fecha_actual,
            hora__gt=hora_actual
        )

        turnos = turnos.order_by("fecha", "hora")


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
    serializer_class = LugarSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [SoloAdminEditar]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Lugar.objects.all()

        if hasattr(user, "cliente"):
            return Lugar.objects.filter(cliente=user.cliente)

        return Lugar.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, "cliente"):
            serializer.save(cliente=user.cliente)
        else:
            raise DRFPermissionDenied("No tenés cliente asociado.")


class BloqueoTurnosViewSet(viewsets.ModelViewSet):
    queryset = BloqueoTurnos.objects.all()
    serializer_class = BloqueoTurnosSerializer
    permission_classes = [IsAuthenticated, EsSuperAdmin | EsAdminDeSuCliente]

class PrestadorViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & SoloLecturaUsuariosFinalesYEmpleados]

    def get_queryset(self):
        user = self.request.user
        lugar_id = self.request.query_params.get("lugar_id")

        # Base: todos los prestadores del mismo cliente
        qs = Prestador.objects.filter(cliente=user.cliente, activo=True)

        # Si filtra por sede
        if lugar_id:
            qs = qs.filter(disponibilidades__lugar_id=lugar_id).distinct()

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {})["request"] = self.request
        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PrestadorConUsuarioSerializer
        elif self.action == "retrieve":
            return PrestadorDetailSerializer
        return PrestadorDetailSerializer  

    def perform_destroy(self, instance):
        usuario = instance.user
        instance.delete()
        usuario.delete()

    @action(detail=True, methods=["get", "post", "delete"], url_path="bloqueos")
    def bloqueos(self, request, pk=None):
        """
        GET: Lista bloqueos de un prestador.
        POST: Crea un nuevo bloqueo. Si `lugar` es null, el bloqueo se aplica a todas las sedes del prestador.
              Devuelve los turnos afectados con estado "reservado".
        DELETE: Elimina un bloqueo existente (requiere `id` en body).
        """
        prestador = self.get_object()
        content_type = ContentType.objects.get_for_model(Prestador)

        if request.method == "GET":
            bloqueos = BloqueoTurnos.objects.filter(
                object_id=prestador.id,
                content_type=content_type
            )
            serializer = BloqueoTurnosSerializer(bloqueos, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            data = request.data.copy()
            data["object_id"] = prestador.id
            data["content_type"] = content_type.id
            serializer = BloqueoTurnosSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            bloqueo = serializer.save()

            # Turnos afectados con estado reservado
            turnos_afectados = Turno.objects.filter(
                content_type=content_type,
                object_id=prestador.id,
                fecha__range=[bloqueo.fecha_inicio, bloqueo.fecha_fin],
                estado="reservado",
            )

            # Si el bloqueo es para una sede específica
            if bloqueo.lugar is not None:
                turnos_afectados = turnos_afectados.filter(lugar=bloqueo.lugar)

            serializer_turnos = TurnoSerializer(turnos_afectados, many=True)

            return Response({
                "id": bloqueo.id,
                "turnos_reservados_afectados": serializer_turnos.data
            }, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            bloqueo_id = request.data.get("id")
            if not bloqueo_id:
                return Response({"error": "Debe proveer el ID del bloqueo"}, status=400)
            try:
                bloqueo = BloqueoTurnos.objects.get(
                    id=bloqueo_id,
                    object_id=prestador.id,
                    content_type=content_type
                )

                # Restaurar turnos que fueron cancelados por este bloqueo y tienen usuario asignado
                turnos_afectados = Turno.objects.filter(
                    content_type=content_type,
                    object_id=prestador.id,
                    estado="cancelado",
                    fecha__range=[bloqueo.fecha_inicio, bloqueo.fecha_fin],
                )

                if bloqueo.lugar:
                    turnos_afectados = turnos_afectados.filter(lugar=bloqueo.lugar)

                # Solo restaurar los que tenían usuario asignado
                restaurados = turnos_afectados.filter(usuario__isnull=False)
                restaurados.update(estado="reservado")

                bloqueo.delete()

                return Response({
                    "message": "Bloqueo eliminado",
                    "turnos_restaurados": restaurados.count()
                }, status=200)

            except BloqueoTurnos.DoesNotExist:
                return Response({"error": "Bloqueo no encontrado"}, status=404)

    @action(detail=True, methods=["post"], url_path="forzar_cancelacion_reservados")
    def forzar_cancelacion_reservados(self, request, pk=None):
        """
        Permite cancelar todos los turnos 'reservados' que se solapen
        con un bloqueo asociado a un prestador.

        Requiere que en el body se envíe:
            {
                "bloqueo_id": <ID del bloqueo>
            }

        Si el lugar del bloqueo es null, aplica a *todas* las sedes del prestador.
        """

        bloqueo_id = request.data.get("bloqueo_id")
        if not bloqueo_id:
            return Response({"error": "bloqueo_id es requerido."}, status=400)

        content_type = ContentType.objects.get_for_model(Prestador)

        try:
            bloqueo = BloqueoTurnos.objects.get(
                id=bloqueo_id,
                object_id=pk,
                content_type=content_type
            )
        except BloqueoTurnos.DoesNotExist:
            return Response({"error": "Bloqueo no encontrado para el prestador."}, status=404)

        filtros = {
            "object_id": pk,
            "content_type": content_type,
            "fecha__range": [bloqueo.fecha_inicio, bloqueo.fecha_fin],
            "estado": "reservado"
        }

        # Si tiene lugar específico, lo filtramos también
        if bloqueo.lugar_id:
            filtros["lugar_id"] = bloqueo.lugar_id

        turnos_afectados = Turno.objects.filter(**filtros)

        turnos_afectados.update(estado="cancelado")

        return Response({
            "message": f"{turnos_afectados.count()} turnos cancelados."
        }, status=200)

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
        user = request.user
        data = request.data
        prestador_id = data.get("prestador_id")
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        duracion_minutos = data.get("duracion_minutos", 60)

        if not fecha_inicio or not fecha_fin:
            return Response({"error": "Faltan parámetros requeridos: fecha_inicio y fecha_fin."}, status=400)

        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido (usar YYYY-MM-DD)."}, status=400)

        try:
            duracion_minutos = int(duracion_minutos)
            if duracion_minutos <= 0:
                raise ValueError()
        except ValueError:
            return Response({"error": "duracion_minutos debe ser un número positivo."}, status=400)

        # Determinar lista de prestadores a procesar
        if prestador_id:
            prestadores = Prestador.objects.filter(id=prestador_id, cliente=user.cliente)
        else:
            prestadores = Prestador.objects.filter(cliente=user.cliente, activo=True)

        total = 0
        detalle = []

        for prestador in prestadores:
            cantidad = generar_turnos_para_prestador(
                prestador_id=prestador.id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                duracion_minutos=duracion_minutos
            )
            total += cantidad
            detalle.append({
                "profesor_id": prestador.id,
                "nombre": prestador.nombre_publico,
                "turnos": cantidad
            })

        return Response({
            "turnos_generados": total,
            "profesores_afectados": len(detalle),
            "detalle": detalle
        })

class CrearBonificacionManualView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.tipo_usuario not in ["super_admin", "admin_cliente"]:
            return Response({"detail": "No autorizado"}, status=403)

        serializer = CrearTurnoBonificadoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bono = serializer.save()
        return Response({"message": "Bonificación creada correctamente."}, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bonificaciones_mias(request):
    usuario = request.user
    bonificaciones = usuario.turnos_bonificados.filter(usado=False)

    data = [
        {
            "id": b.id,
            "motivo": b.motivo,
            "fecha_creacion": b.fecha_creacion,
            "valido_hasta": b.valido_hasta,
        }
        for b in bonificaciones
    ]

    return Response(data)


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prestador_actual(request):
    user = request.user
    prestador = Prestador.objects.filter(user=user).first()
    if not prestador:
        return Response({"detail": "No se encontró un prestador asociado a este usuario"}, status=404)
    return Response({"id": prestador.id})

