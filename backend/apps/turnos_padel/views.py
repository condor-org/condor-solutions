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
from apps.turnos_core.models import Lugar, Turno, TurnoBonificado
from apps.turnos_padel.models import ConfiguracionSedePadel, TipoClasePadel, AbonoMes
from apps.turnos_padel.serializers import (
    SedePadelSerializer,
    ConfiguracionSedePadelSerializer,
    TipoClasePadelSerializer,
    AbonoMesSerializer
)

from django.db import transaction



# apps/turnos_padel/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from apps.common.permissions import EsAdminDeSuCliente, EsSuperAdmin, SoloLecturaUsuariosFinalesYEmpleados
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
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]  # solo admin crea/edita por ahora
    serializer_class = AbonoMesSerializer
    queryset = AbonoMes.objects.all()

    def get_queryset(self):
        u = self.request.user
        if getattr(u, "tipo_usuario", "") == "super_admin":
            return AbonoMes.objects.all()
        return AbonoMes.objects.filter(sede__cliente=u.cliente)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reservar(self, request, pk=None):
        """
        Reserva en batch los turnos del mes para este abono.
        Reglas:
          - Si el usuario decide usar N Turnos Bonificados (mismo tipo), calculamos monto_a_pagar = monto - N*precio_unitario.
          - Si monto_a_pagar == 0 => reservamos y consumimos TB inmediatamente (sin comprobante).
          - Si monto_a_pagar > 0 => NO reservamos aquí; devolvemos monto_a_pagar para subir comprobante de abono.
        """
        abono = self.get_object()
        usuario = abono.usuario

        # Validación de pertenencia (solo dueño o admin del cliente)
        ureq = request.user
        if ureq.tipo_usuario not in {"super_admin","admin_cliente"} and ureq != usuario:
            return Response({"detail": "No autorizado"}, status=403)

        # mapear tipo_turno (code) desde TipoClasePadel.nombre
        nombre_norm = (abono.tipo_clase.nombre or "").strip().lower()
        mapping = {"individual": "individual", "2 personas": "x2", "3 personas": "x3", "4 personas": "x4"}
        tipo_turno_code = mapping.get(nombre_norm)
        if not tipo_turno_code:
            return Response({"detail":"Tipo de clase inválido para abono."}, status=400)

        # fechas objetivo
        fechas = AbonoMesSerializer._fechas_del_mes_por_dia_semana(abono.anio, abono.mes, abono.dia_semana)
        turnos_qs = Turno.objects.select_for_update().filter(
            fecha__in=fechas, hora=abono.hora, lugar=abono.sede,
            content_type__model="prestador", object_id=abono.prestador_id, estado="disponible"
        )
        if turnos_qs.count() != len(fechas):
            return Response({"detail":"Al menos un turno no está disponible. Operación abortada."}, status=409)

        # TB a usar (opcional en body: {"turnos_bonificados_usar": N})
        tb_usar = int(request.data.get("turnos_bonificados_usar", 0))
        if tb_usar < 0:
            tb_usar = 0
        if tb_usar > len(fechas):
            tb_usar = len(fechas)

        # precio unitario para descontar TB
        unitario = abono.tipo_clase.precio
        monto_a_pagar = max(abono.monto - (tb_usar * unitario), 0)

        # si hay saldo, devolvemos info para subir comprobante de abono
        if monto_a_pagar > 0:
            return Response({
                "monto_a_pagar": float(monto_a_pagar),
                "turnos_bonificados_a_usar": tb_usar,
                "alias": abono.tipo_clase.configuracion_sede.alias,
                "cbu_cvu": abono.tipo_clase.configuracion_sede.cbu_cvu
            }, status=200)

        # monto_a_pagar == 0 => reservar y consumir TB inmediatamente
        with transaction.atomic():
            turnos = list(turnos_qs)
            # consumir TB del mismo tipo
            tbs = list(TurnoBonificado.objects.select_for_update()
                       .filter(usuario=usuario, usado=False, tipo_turno=tipo_turno_code)
                       .order_by("fecha_creacion")[:tb_usar])
            if len(tbs) != tb_usar:
                return Response({"detail":"No hay suficientes Turnos Bonificados disponibles."}, status=409)

            # reservar todos
            for t in turnos:
                t.usuario = usuario
                t.estado = "reservado"
                t.tipo_turno = tipo_turno_code
                t.save(update_fields=["usuario","estado","tipo_turno"])

            # asociar cada TB a un turno (marcar usado)
            for t, tb in zip(turnos, tbs):
                tb.marcar_usado(t)

            abono.estado = "pagado"
            abono.save(update_fields=["estado"])

        logger.info("[abono.reserve.batch][sin_comprobante] abono=%s turnos=%s tb_usados=%s",
                    abono.id, len(turnos), tb_usar)

        return Response({"message":"Abono reservado sin comprobante (100% con Turnos Bonificados)."}, status=201)
