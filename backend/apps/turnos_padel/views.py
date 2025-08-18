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
from calendar import Calendar
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

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

    @action(detail=False, methods=["GET"], url_path="disponibles")
    def disponibles(self, request):
        logger.info("[abonos.disponibles] params=%s", dict(request.query_params))
        try:
            sede_id = int(request.query_params.get("sede_id"))
            prestador_id = int(request.query_params.get("prestador_id"))
            dia_semana = int(request.query_params.get("dia_semana"))  # 0..6
            anio = int(request.query_params.get("anio"))
            mes = int(request.query_params.get("mes"))
        except (TypeError, ValueError):
            logger.warning("[abonos.disponibles] Parámetros inválidos")
            return Response({"detail": "Parámetros inválidos"}, status=status.HTTP_400_BAD_REQUEST)

        hora_filtro = request.query_params.get("hora")  # opcional

        sede = Lugar.objects.select_related("cliente").filter(id=sede_id).first()
        if not sede:
            return Response({"detail": "Sede no encontrada"}, status=404)

        user = request.user
        if user.tipo_usuario == "admin_cliente" and sede.cliente_id != getattr(user, "cliente_id", None):
            return Response({"detail": "No autorizado para esta sede"}, status=403)
        if user.tipo_usuario not in ("super_admin", "admin_cliente"):
            if getattr(user, "cliente_id", None) != sede.cliente_id:
                return Response({"detail": "No autorizado"}, status=403)

        tipos_qs = TipoClasePadel.objects.filter(
            configuracion_sede__sede_id=sede_id
        ).only("id", "nombre", "precio")
        tipos_map = [{"id": t.id, "nombre": t.nombre, "precio": t.precio} for t in tipos_qs]

        def fechas_mes(anio_i, mes_i, dsem):
            cal = Calendar(firstweekday=0)
            out = []
            for week in cal.monthdatescalendar(anio_i, mes_i):
                for d in week:
                    if d.month == mes_i and d.weekday() == dsem:
                        out.append(d)
            return out

        def proximo_mes(anio_i, mes_i):
            return (anio_i + 1, 1) if mes_i == 12 else (anio_i, mes_i + 1)

        fechas_actual = fechas_mes(anio, mes, dia_semana)
        prox_anio, prox_mes = proximo_mes(anio, mes)
        fechas_prox = fechas_mes(prox_anio, prox_mes, dia_semana)
        if not fechas_actual and not fechas_prox:
            logger.info("[abonos.disponibles] sin fechas para el día de semana")
            return Response([], status=200)

        fechas_total = fechas_actual + fechas_prox

        try:
            ct_prestador = ContentType.objects.get(app_label="turnos_core", model="prestador")
        except ContentType.DoesNotExist:
            logger.error("[abonos.disponibles] ContentType prestador no encontrado")
            return Response({"detail": "Error de configuración (prestador)"}, status=500)

        base_q = Q(lugar_id=sede_id) & Q(content_type=ct_prestador, object_id=prestador_id) & Q(fecha__in=fechas_total)

        turnos_qs = Turno.objects.filter(base_q).only(
            "id", "fecha", "hora", "estado",
            "abono_mes_reservado", "abono_mes_prioridad", "lugar_id"
        )
        if hora_filtro:
            turnos_qs = turnos_qs.filter(hora=hora_filtro)

        por_hora = {}
        for t in turnos_qs:
            # t.hora es time -> to_str
            h = t.hora.isoformat()
            por_hora.setdefault(h, {})[t.fecha] = t

        horas_libres = []
        for h, mapa in por_hora.items():
            if not all(f in mapa for f in fechas_total):
                continue
            ok = True
            for f in fechas_total:
                t = mapa[f]
                if t.estado != "disponible":
                    ok = False; break
                if getattr(t, "abono_mes_reservado", False) or getattr(t, "abono_mes_prioridad", False):
                    ok = False; break
                if hasattr(t, "bloqueado_para_reservas") and getattr(t, "bloqueado_para_reservas", False):
                    ok = False; break
            if ok:
                horas_libres.append(h)

        horas_libres.sort()

        result = []
        for h in horas_libres:
            for tipo in tipos_map:
                result.append({"hora": h, "tipo_clase": tipo})

        logger.info(
            "[abonos.disponibles] sede=%s prestador=%s dsem=%s anio=%s mes=%s -> horas=%s",
            sede_id, prestador_id, dia_semana, anio, mes, horas_libres
        )
        return Response(result, status=200)
