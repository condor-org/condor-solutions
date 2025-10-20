# Built-in
import logging
from zoneinfo import ZoneInfo  # Python 3.9+
import uuid
# Django
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.timezone import now, localtime

from datetime import date, timedelta

# Django REST Framework
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied as DRFPermissionDenied,
)
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
    Disponibilidad,
    Lugar,
    Prestador,
    Turno,
    TurnoBonificado,
)
from apps.pagos_core.models import ComprobantePago, PagoIntento
from apps.turnos_padel.models import TipoClasePadel

# App imports - Serializers
from apps.turnos_core.serializers import (
    DisponibilidadSerializer,
    LugarSerializer,
    PrestadorConUsuarioSerializer,
    PrestadorDetailSerializer,
    TurnoReservaSerializer,
    TurnoSerializer,
    CrearTurnoBonificadoSerializer,
    CancelarTurnoSerializer,
    CancelacionPorSedeSerializer,
    CancelacionPorPrestadorSerializer,
    ToggleReservadoParaAbonoSerializer,
)


from rest_framework import serializers
from django.db import transaction

# App imports - Servicios
from apps.turnos_core.services.bonificaciones import (
    emitir_bonificacion_automatica,
    bonificaciones_vigentes,
)
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
from apps.turnos_core.services.cancelaciones_admin import cancelar_turnos_admin
from apps.notificaciones_core.services import (
    publish_event,
    notify_inapp,
    TYPE_CANCELACION_TURNO,
    TYPE_RESERVA_TURNO,              # 👈 nuevo
    build_ctx_reserva_usuario,       # 👈 nuevo
)
from apps.turnos_core.services.generar_turnos import (
    generar_turnos_mes_actual_y_siguiente,
)

logger = logging.getLogger(__name__)


class ToggleReservadoParaAbonoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        ser = ToggleReservadoParaAbonoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        turno_id = ser.validated_data["turno_id"]
        nuevo_flag = ser.validated_data["reservado_para_abono"]

        with transaction.atomic():
            try:
                # 🔒 sin joins aquí
                turno = (
                    Turno.objects
                    .filter(pk=turno_id)
                    .select_for_update(of=('self',))  # asegura que el FOR UPDATE solo apunte a Turno
                    .only("id", "estado", "reservado_para_abono", "lugar_id","fecha", "hora")
                    .get()
                )
            except Turno.DoesNotExist:
                return Response({"detail": "Turno no encontrado."}, status=404)

            # Tenancy: admin_cliente solo dentro de su cliente (sin outer join)
            if not request.user.is_super_admin:
                from apps.auth_core.utils import get_rol_actual_del_jwt
                rol_actual = get_rol_actual_del_jwt(request)
                
                if rol_actual == "admin_cliente":
                    cliente_actual = getattr(request, 'cliente_actual', None)
                    if not cliente_actual or not Lugar.objects.filter(id=turno.lugar_id, cliente_id=cliente_actual.id).exists():
                        return Response({"detail": "No autorizado para esta sede."}, status=403)

            if turno.estado != "disponible":
                return Response({"detail": "El turno no está disponible."}, status=400)

            turno.reservado_para_abono = bool(nuevo_flag)
            turno.save(update_fields=["reservado_para_abono"])

        return Response({
            "ok": True,
            "turno": {
                "id": turno.id,
                "fecha": str(turno.fecha),
                "hora": str(turno.hora),
                "estado": turno.estado,
                "reservado_para_abono": turno.reservado_para_abono,
            }
        }, status=200)


# ------------------------------------------------------------------------------
# GET /turnos/  → Listar turnos visibles (según rol) con filtros opcionales
# - Permisos: Autenticado.
# - Filtros: ?estado=... ; ?upcoming=true|1 (aplica desde ahora en adelante)
# - Superadmin: todos los turnos. Empleado_cliente: de sus prestadores. Usuario final: los propios.
# - Respuesta: lista ordenada por fecha/hora.
# ------------------------------------------------------------------------------
class TurnoListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TurnoSerializer

    def get_queryset(self):
        usuario = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Importar y usar la función helper
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.request)

        # Super admin (usar nuevo campo)
        if usuario.is_super_admin:
            qs = Turno.objects.all().select_related("usuario", "lugar")

        # Admin del cliente → TODOS los turnos de su cliente
        elif rol_actual == "admin_cliente" and cliente_actual:
            qs = (
                Turno.objects
                .filter(lugar__cliente_id=cliente_actual.id)
                .select_related("usuario", "lugar")
            )

        # Empleado (prestador) → sus propios turnos
        elif rol_actual == "empleado_cliente":
            from django.contrib.contenttypes.models import ContentType
            ct_prestador = ContentType.objects.get_for_model(Prestador)
            qs = (
                Turno.objects
                .filter(content_type=ct_prestador, object_id__in=Prestador.objects.filter(user=usuario).values_list("id", flat=True))
                .select_related("usuario", "lugar")
            )

        # Usuario final → sus turnos (y más abajo se filtran no-abonos)
        else:
            qs = Turno.objects.filter(usuario=usuario).select_related("usuario", "lugar")

        # filtros opcionales
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        upcoming = (self.request.query_params.get("upcoming") or "").lower()
        if upcoming in {"1", "true", "sí", "si"}:
            ahora = localtime()
            hoy = ahora.date()
            hora = ahora.time()
            qs = qs.filter(Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora))

        # 🔒 usuarios finales: ocultar turnos de abonos
        if rol_actual == "usuario_final":
            qs = qs.filter(
                reservado_para_abono=False,
                abono_mes_reservado__isnull=True,
                abono_mes_prioridad__isnull=True,
                comprobante_abono__isnull=True,
            )

        return qs.order_by("fecha", "hora")

class TurnosAgendaAdminView(APIView):
    """
    GET /turnos/agenda/?scope=day|week|month&date=YYYY-MM-DD&estado=&sede_id=&prestador_id=&include_abonos=0|1
    - super_admin: todo
    - admin_cliente: sólo su cliente
    - empleado_cliente: sólo sus turnos
    - usuario_final: 403
    Respuesta: { range:{start,end,granularity}, totals:{...}, items:[TurnoSerializer...] }
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if getattr(user, "tipo_usuario", "") == "usuario_final":
            return Response({"detail": "No autorizado"}, status=403)

        scope = (request.query_params.get("scope") or "day").lower()
        dref = parse_date(request.query_params.get("date") or "") or timezone.localdate()

        # rango
        if scope == "week":
            # lunes–domingo de la semana ISO
            start = dref - timedelta(days=(dref.weekday()))
            end = start + timedelta(days=6)
            gran = "week"
        elif scope == "month":
            start = dref.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            gran = "month"
        else:
            start = dref
            end = dref
            gran = "day"

        qs = Turno.objects.select_related("usuario", "lugar")

        # alcance por rol
        if getattr(user, "tipo_usuario", "") == "super_admin" or getattr(user, "is_superuser", False):
            pass
        elif getattr(user, "tipo_usuario", "") == "admin_cliente" and getattr(user, "cliente_id", None):
            qs = qs.filter(lugar__cliente_id=user.cliente_id)
        elif getattr(user, "tipo_usuario", "") == "empleado_cliente":
            ct_prestador = ContentType.objects.get_for_model(Prestador)
            qs = qs.filter(content_type=ct_prestador, object_id__in=Prestador.objects.filter(user=user).values_list("id", flat=True))
        else:
            return Response({"detail": "No autorizado"}, status=403)

        # filtros
        sede_id = request.query_params.get("sede_id")
        if sede_id:
            qs = qs.filter(lugar_id=sede_id)

        prestador_id = request.query_params.get("prestador_id")
        if prestador_id:
            ct_prestador = ContentType.objects.get_for_model(Prestador)
            qs = qs.filter(content_type=ct_prestador, object_id=int(prestador_id))

        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        include_abonos = (request.query_params.get("include_abonos") or "0").lower() in {"1","true","si","sí","y","yes"}
        if not include_abonos:
            qs = qs.filter(
                reservado_para_abono=False,
                abono_mes_reservado__isnull=True,
                abono_mes_prioridad__isnull=True,
                comprobante_abono__isnull=True,
            )

        # rango de fechas (inclusive)
        qs = qs.filter(fecha__gte=start, fecha__lte=end).order_by("fecha", "hora")

        # totales rápidos
        totals = dict(qs.values_list("estado").order_by().annotate(c=models.Count("id")))

        payload = {
            "range": {"start": str(start), "end": str(end), "granularity": gran},
            "totals": {
                "disponible": totals.get("disponible", 0),
                "reservado": totals.get("reservado", 0),
                "cancelado": totals.get("cancelado", 0),
                "total": qs.count(),
            },
            "items": TurnoSerializer(qs, many=True).data,
        }
        return Response(payload, status=200)

class _AdminReservarTurnoSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    usuario_id = serializers.IntegerField()
    tipo_clase_id = serializers.IntegerField(required=False)  # opcional → setea Turno.tipo_turno
    omitir_bloqueo_abono = serializers.BooleanField(required=False, default=False)

class ReservarTurnoAdminView(APIView):
    """
    POST /turnos/admin/reservar/
    Body: { turno_id, usuario_id, tipo_clase_id?, omitir_bloqueo_abono?=false }
    Efecto: asigna usuario y marca estado="reservado" SIN pagos.
    Reglas: 
      - turno debe estar "disponible"
      - tenancy: admin_cliente sólo en su cliente (por sede del turno y usuario)
      - respeta bloqueos de abono salvo que omitir_bloqueo_abono=true
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        ser = _AdminReservarTurnoSerializer(data=request.data); ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        # fetch
        turno = Turno.objects.select_related("lugar").filter(id=vd["turno_id"]).first()
        if not turno:
            return Response({"detail": "Turno no encontrado"}, status=404)

        Usuario = get_user_model()
        usuario = Usuario.objects.only("id", "cliente_id").filter(id=vd["usuario_id"]).first()
        if not usuario:
            return Response({"detail": "Usuario destino no encontrado"}, status=404)

        # tenancy
        if not request.user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or (getattr(turno.lugar, "cliente_id", None) != cliente_actual.id) or (usuario.cliente_id != cliente_actual.id):
                    return Response({"detail": "No autorizado para operar fuera de tu cliente."}, status=403)

        # estado
        if turno.estado != "disponible":
            return Response({"detail": "El turno no está disponible."}, status=400)

        # bloqueo por abono
        if (turno.reservado_para_abono or turno.abono_mes_reservado_id or turno.abono_mes_prioridad_id) and not vd.get("omitir_bloqueo_abono", False):
            return Response({"detail": "Turno bloqueado para abonos."}, status=409)

        # mapear tipo_clase → código (x1..x4) si viene
        tipo_code = None
        tc_id = vd.get("tipo_clase_id")
        if tc_id:
            try:
                from apps.turnos_padel.models import TipoClasePadel
                tc = TipoClasePadel.objects.only("id", "codigo", "configuracion_sede__sede_id").get(id=tc_id)
                # opcional: validar que sede coincida
                if getattr(turno.lugar, "id", None) != getattr(tc.configuracion_sede, "sede_id", None):
                    return Response({"detail": "El tipo de clase no corresponde a la misma sede."}, status=400)
                tipo_code = tc.codigo
            except TipoClasePadel.DoesNotExist:
                return Response({"detail": "Tipo de clase inválido"}, status=400)

        with transaction.atomic():
            # lock y revalidación rápida
            turno = Turno.objects.select_for_update().get(id=turno.id)
            if turno.estado != "disponible":
                return Response({"detail": "El turno ya no está disponible."}, status=409)
            if (turno.reservado_para_abono or turno.abono_mes_reservado_id or turno.abono_mes_prioridad_id) \
                and not vd.get("omitir_bloqueo_abono", False):
                    return Response({"detail": "Turno bloqueado para abonos."}, status=409)
            
            turno.usuario = usuario
            turno.estado = "reservado"
            if tipo_code:
                turno.tipo_turno = tipo_code
            turno.save(update_fields=["usuario", "estado", "tipo_turno", "actualizado_en"])

        return Response({"ok": True, "turno_id": turno.id}, status=200)


class _AdminLiberarTurnoSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    emitir_bonificacion = serializers.BooleanField(required=False, default=False)
    motivo = serializers.CharField(required=False, allow_blank=True)

class LiberarTurnoAdminView(APIView):
    """
    POST /turnos/admin/liberar/
    Body: { turno_id, emitir_bonificacion?=false, motivo? }
    Efecto: si está reservado, libera el slot. Opcionalmente emite bonificación
            (devolución) al usuario afectado.
    - Anula/desasocia comprobante/pago como en CancelarTurnoView.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        ser = _AdminLiberarTurnoSerializer(data=request.data); ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        turno = Turno.objects.select_related("lugar", "usuario").filter(id=vd["turno_id"]).first()
        if not turno:
            return Response({"detail": "Turno no encontrado"}, status=404)

        # tenancy
        if not request.user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or getattr(turno.lugar, "cliente_id", None) != cliente_actual.id:
                    return Response({"detail": "No autorizado para esta sede"}, status=403)

        if turno.estado != "reservado":
            # idempotente/benigno: ya libre
            return Response({"ok": True, "message": "El turno no estaba reservado."}, status=200)

        with transaction.atomic():
            turno = Turno.objects.select_for_update().get(id=turno.id)
            if turno.estado != "reservado":
                return Response({"ok": True, "message": "El turno ya no estaba reservado."}, status=200)

            usuario_original = turno.usuario

            # ===== anular pagos/comprobante (misma lógica que CancelarTurnoView) =====
            comp = ComprobantePago.objects.select_for_update().filter(turno=turno).first()
            if comp:
                try:
                    ct = ContentType.objects.get_for_model(ComprobantePago)
                    PagoIntento.objects.filter(
                        content_type=ct, object_id=comp.id, estado__in=["pre_aprobado", "confirmado"]
                    ).update(estado="rechazado")
                    datos = comp.datos_extraidos or {}
                    datos.update({
                        "turno_original": turno.id,
                        "cancelado_en": timezone.now().isoformat(),
                        "motivo_cancelacion": vd.get("motivo") or "Liberación administrativa",
                    })
                    comp.datos_extraidos = datos
                    comp.valido = False
                    comp.turno = None
                    comp.save(update_fields=["datos_extraidos", "valido", "turno"])
                except Exception:
                    return Response({"detail": "No se pudo anular/desasociar el pago."}, status=409)

            # ===== liberar =====
            turno.usuario = None
            turno.estado = "disponible"
            turno.save(update_fields=["usuario", "estado", "actualizado_en"])

        # bonificación opcional
        try:
            if vd.get("emitir_bonificacion") and usuario_original:
                emitir_bonificacion_automatica(
                    usuario=usuario_original,
                    turno_original=turno,
                    motivo=vd.get("motivo") or "Liberación administrativa",
                )
        except Exception:
            logger.exception("[turno.admin_liberar][bono][fail] turno=%s", turno.id)

        return Response({"ok": True, "turno_id": turno.id}, status=200)




# ------------------------------------------------------------------------------
# POST /turnos/reservar/  → Reservar un turno
# - Permisos: Autenticado.
# - Body: turno_id, tipo_clase_id, usar_bonificado(bool), archivo(file si no usa bono)
# - Lógica: valida turno/sede/tipo_clase; consume bono o sube comprobante y crea PagoIntento;
#           confirma reserva (usuario, estado="reservado", tipo_turno x1..x4).
# - Side-effects: evento + notificación in-app a admins del cliente.
# - Respuesta: {"message", "turno_id"}.
# ------------------------------------------------------------------------------
class TurnoReservaView(CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TurnoReservaSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        turno = serializer.save()

        # 🔔 Notificaciones (admins + usuario)
        try:
            from django.contrib.auth import get_user_model
            from apps.notificaciones_core.services import (
                publish_event,
                notify_inapp,
                TYPE_RESERVA_TURNO,
                build_ctx_reserva_usuario,
            )

            Usuario = get_user_model()
            cliente_id = getattr(request.user, "cliente_id", None)

            # -------- Admins del cliente --------
            ev_admin = publish_event(
                topic="turnos.reserva_confirmada",
                actor=request.user,
                cliente_id=cliente_id,
                metadata={
                    "turno_id": turno.id,
                    "fecha": str(turno.fecha),
                    "hora": str(turno.hora)[:5],
                    "sede_id": turno.lugar_id,
                    "usuario": getattr(request.user, "email", None),
                },
            )

            admins = Usuario.objects.filter(
                cliente_id=cliente_id,
                tipo_usuario="admin_cliente",
            ).only("id", "cliente_id")

            ctx_admin = {
                a.id: {
                    "usuario": getattr(request.user, "email", None),
                    "fecha": str(turno.fecha),
                    "hora": str(turno.hora)[:5],
                    "sede_nombre": getattr(turno.lugar, "nombre", None),
                    "prestador": getattr(getattr(turno, "recurso", None), "nombre_publico", None),
                } for a in admins
            }

            notify_inapp(
                event=ev_admin,
                recipients=admins,
                notif_type=TYPE_RESERVA_TURNO,
                context_by_user=ctx_admin,
                severity="info",
            )

            # -------- Usuario final --------
            ev_user = publish_event(
                topic="turnos.reserva_confirmada.usuario",
                actor=request.user,
                cliente_id=cliente_id,
                metadata={"turno_id": turno.id},
            )

            ctx_user = {request.user.id: build_ctx_reserva_usuario(turno, request.user)}

            notify_inapp(
                event=ev_user,
                recipients=[request.user],
                notif_type=TYPE_RESERVA_TURNO,
                context_by_user=ctx_user,
                severity="info",
            )

        except Exception:
            logger.exception("[notif][turno_reserva][fail]")

        return Response(
            {"message": "Turno reservado exitosamente", "turno_id": turno.id}
        )

# ------------------------------------------------------------------------------
# GET /turnos/disponibles/?prestador_id=&lugar_id=&fecha=YYYY-MM-DD
# - Permisos: Autenticado.
# - Función: devuelve slots futuros (estados: disponible/reservado) del prestador en la sede.
# - Tiempo: usa AR local para “hoy desde ahora”.
# - Respuesta: lista serializada de turnos (ordenada por fecha/hora).
# Excluye turnos bloqueados por abono (reservado_para_abono=True)
# ------------------------------------------------------------------------------

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

        # casteo seguro
        try:
            prestador_id = int(prestador_id)
            lugar_id = int(lugar_id)
        except (TypeError, ValueError):
            return Response({"error": "prestador_id y lugar_id deben ser enteros."}, status=400)

        # Fecha opcional
        fecha = None
        if fecha_str:
            fecha = parse_date(fecha_str)
            if not fecha:
                return Response({"error": "Formato de fecha inválido (usar YYYY-MM-DD)."}, status=400)

        # Ventana temporal: hoy (AR) desde ahora y futuro
        ahora_ar = timezone.now().astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
        hoy = ahora_ar.date()
        hora = ahora_ar.time().replace(microsecond=0)

        ct_prestador = ContentType.objects.get_for_model(Prestador)

        qs = (
            Turno.objects
            .filter(
                content_type=ct_prestador,
                object_id=prestador_id,
                lugar_id=lugar_id,
                estado__in=["disponible", "reservado"],
            )
            # ⏱ sólo futuro
            .filter(Q(fecha__gt=hoy) | (Q(fecha=hoy) & Q(hora__gte=hora)))
            # 🚫 excluir turnos bloqueados por abono
            .filter(Q(reservado_para_abono=False) | Q(reservado_para_abono__isnull=True))
        )

        if fecha:
            qs = qs.filter(fecha=fecha)

        turnos = qs.order_by("fecha", "hora")
        return Response(TurnoSerializer(turnos, many=True).data)

# ------------------------------------------------------------------------------
# Permiso auxiliar: SoloAdminEditar
# - GET/SAFE: cualquier autenticado.
# - Mutaciones: solo super_admin / admin_cliente.
# ------------------------------------------------------------------------------
class SoloAdminEditar(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        
        if not request.user.is_authenticated:
            return False
            
        if request.user.is_super_admin:
            return True
            
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual in {"super_admin", "admin_cliente"}


# ------------------------------------------------------------------------------
# ViewSet /turnos/sedes/  → CRUD de sedes (lugares)
# - Permisos: lectura autenticado; escritura solo admins del cliente.
# - Multi-tenant: filtra por cliente del usuario; al crear, fuerza cliente=user.cliente.
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# ViewSet /turnos/prestadores/  → CRUD de prestadores
# - Lectura: autenticado (usuarios finales y empleados: solo lectura).
# - Escritura: admins (crea/actualiza prestador y usuario embebido; borra ambos).
# - Filtro: ?lugar_id= para limitar a una sede con disponibilidad.
# ------------------------------------------------------------------------------
class PrestadorViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & SoloLecturaUsuariosFinalesYEmpleados]

    def get_queryset(self):
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        lugar_id = self.request.query_params.get("lugar_id")

        # Base: todos los prestadores del cliente actual
        if cliente_actual:
            qs = Prestador.objects.filter(cliente=cliente_actual, activo=True)
        else:
            # Fallback al sistema antiguo
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
    
    @transaction.atomic
    def perform_destroy(self, instance):
        request = getattr(self, "request", None)
        force = False
        if request is not None:
            # Soportar ?force=true/1
            qp = request.query_params
            force = str(qp.get("force", "")).lower() in ("1", "true", "t", "yes", "y")

        ct = ContentType.objects.get_for_model(instance.__class__)
        hoy = timezone.localdate()

        # Turnos del prestador (todos / por estado / por abono)
        turnos_qs = Turno.objects.select_for_update().filter(content_type=ct, object_id=instance.id)
        futuros_qs = turnos_qs.filter(fecha__gte=hoy, estado__in=["disponible", "reservado"])
        reservados_qs = turnos_qs.filter(estado="reservado")
        con_abono_qs = turnos_qs.filter(comprobante_abono__isnull=False)

        c_total = turnos_qs.count()
        c_futuros = futuros_qs.count()
        c_reservados = reservados_qs.count()
        c_con_abono = con_abono_qs.count()

        # Regla por defecto (segura): no borrar si hay impacto operativo, salvo force
        if not force and (c_reservados > 0 or c_con_abono > 0):
            raise ValidationError({
                "detail": (
                    "No se puede eliminar el profesor porque hay turnos reservados o vinculados a abonos."
                    "Cancelá los turnos reservdos primero o usá ?force=true para forzar la eliminación (se borrarán los turnos)."
                ),
                "stats": {
                    "turnos_total": c_total,
                    "turnos_futuros": c_futuros,
                    "turnos_reservados": c_reservados,
                    "turnos_con_abono": c_con_abono,
                },
            })

        # Borrado explícito de todos los turnos vinculados a este prestador
        borrados_turnos, _ = turnos_qs.delete()

        # Borramos el Prestador y su usuario
        usuario = instance.user
        instance.delete()
        usuario.delete()

        # Log (usa tu logger de proyecto)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "prestador.eliminado",
            extra={
                "prestador_id": instance.id,
                "user_id": getattr(usuario, "id", None),
                "turnos_borrados": borrados_turnos,
                "force": force,
                "futuros": c_futuros,
                "reservados": c_reservados,
                "con_abono": c_con_abono,
            },
        )

# ------------------------------------------------------------------------------
# ViewSet /turnos/disponibilidades/  → CRUD de disponibilidades
# - Permisos: super_admin | admin_cliente | prestador (solo las suyas).
# - Multi-tenant: filtra por cliente o usuario prestador.
# ------------------------------------------------------------------------------
class DisponibilidadViewSet(viewsets.ModelViewSet):
    serializer_class = DisponibilidadSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente | EsPrestador)]

    def get_queryset(self):
        user = self.request.user

        if user.is_super_admin:
            return Disponibilidad.objects.all()

        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.request)
        
        if rol_actual == "admin_cliente":
            cliente_actual = getattr(self.request, 'cliente_actual', None)
            if cliente_actual:
                return Disponibilidad.objects.filter(prestador__cliente=cliente_actual)
            return Disponibilidad.objects.none()

        if rol_actual == "empleado_cliente":
            return Disponibilidad.objects.filter(prestador__user=user)

        return Disponibilidad.objects.none()


# ------------------------------------------------------------------------------
# POST /turnos/generar/  → Generar turnos según disponibilidades
# - Permisos: super_admin | admin_cliente.
# - Body: fecha_inicio, fecha_fin, duracion_minutos, prestador_id?(opcional).
# - Lógica: idempotente (bulk_create ignore_conflicts), omite días bloqueados.
# - Respuesta: totales + detalle por prestador.
# ------------------------------------------------------------------------------
class GenerarTurnosView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        trace_id = str(uuid.uuid4())[:8]
        user = request.user

        # Opcional: permitir acotar por prestador_id (lo usa el admin desde el panel)
        prestador_id = request.data.get("prestador_id")
        if prestador_id is not None and prestador_id != "":
            try:
                prestador_id = int(prestador_id)
            except (TypeError, ValueError):
                return Response({"error": "prestador_id inválido."}, status=400)
        else:
            prestador_id = None

        # Scope por cliente si es admin_cliente (super_admin no limita)
        cliente_scope = (
            getattr(user, "cliente_id", None)
            if getattr(user, "tipo_usuario", None) == "admin_cliente"
            else None
        )

        try:
            # Llama al service idempotente: genera desde HOY→fin de mes y TODO el mes siguiente,
            # y marca reservado_para_abono en las franjas 07–11 y 14–17.
            res = generar_turnos_mes_actual_y_siguiente(
                cliente_id=cliente_scope,
                prestador_id=prestador_id,
            )

            # Mantener la misma forma que consumía el FE:
            # - 'prestadores_afectados' del service → 'profesores_afectados' en la respuesta
            payload = {
                "turnos_generados": res.get("turnos_generados", 0),
                "profesores_afectados": res.get("prestadores_afectados", 0),
                "detalle": res.get("detalle", []),
                "trace_id": trace_id,
            }
            # Campo extra informativo (no rompe FE si no lo usa):
            if "franjas_marcadas" in res:
                payload["franjas_marcadas"] = res["franjas_marcadas"]

            logger.info(
                "[turnos.generar][ok] trace=%s generados=%s profs=%s",
                trace_id,
                payload["turnos_generados"],
                payload["profesores_afectados"],
            )
            return Response(payload, status=200)

        except Exception as e:
            logger.exception("[turnos.generar][error] trace=%s", trace_id)
            return Response(
                {"error": "No se pudieron generar turnos.", "trace_id": trace_id},
                status=500,
            )# ------------------------------------------------------------------------------

# POST /turnos/bonificaciones/crear-manual/  → Emitir bonificación manual
# - Permisos: super_admin | admin_cliente.
# - Body: usuario_id, tipo_turno (x1..x4 o alias), motivo?, valido_hasta?
# - Side-effects: evento + notificación al usuario.
# ------------------------------------------------------------------------------
class CrearBonificacionManualView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_super_admin:
            pass  # Super admin siempre tiene acceso
        else:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual not in ["super_admin", "admin_cliente"]:
                return Response({"detail": "No autorizado"}, status=403)

        serializer = CrearTurnoBonificadoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bono = serializer.save()
        # Podés devolver más info si querés auditoría frontend
        return Response(
            {
                "message": "Bonificación creada correctamente.",
                "bonificacion_id": bono.id,
                "tipo_turno": bono.tipo_turno,
                "valor": str(bono.valor) if bono.valor is not None else None,
            },
            status=201
        )
# ------------------------------------------------------------------------------
# Helper interno: _notify_cancelacion_usuario
# - Propósito: al cancelar un usuario su turno, avisa a admins del cliente dueño de la sede.
# - Excluye super_admin como destinatario. Maneja contexto por admin.
# - Resiliencia: captura y loguea excepciones, retorna cantidad de notificaciones creadas.
# ------------------------------------------------------------------------------
def _notify_cancelacion_usuario(turno, actor):
    """
    Notifica a los admin_cliente del cliente dueño de la sede del turno que el USUARIO canceló.
    No incluye super_admin (por pedido explícito).
    """
    logger.info(
        "[notif.turno_cancelado_usuario][start] turno=%s actor=%s sede=%s",
        getattr(turno, "id", None), getattr(actor, "id", None), getattr(turno, "lugar_id", None)
    )
    try:
        Usuario = get_user_model()
        cliente_id = getattr(getattr(turno, "lugar", None), "cliente_id", None)
        if not cliente_id:
            logger.warning("[notif.turno_cancelado_usuario][skip] turno=%s sin cliente_id en lugar", getattr(turno, "id", None))
            return 0

        ev = publish_event(
            topic="turnos.cancelacion_usuario",
            actor=actor,
            cliente_id=cliente_id,
            metadata={
                "turno_id": turno.id,
                "fecha": str(turno.fecha),
                "hora": str(turno.hora)[:5],
                "sede_id": turno.lugar_id,
                "usuario": getattr(actor, "email", None),
                "reservado_con_bono": bool(
                    getattr(turno, "bonificacion_usada", None) is not None
                    or False
                ),
            },
        )

        # Solo admin_cliente (excluye super_admin)
        admins = Usuario.objects.filter(
            cliente_id=cliente_id,
            tipo_usuario="admin_cliente"
        ).only("id", "cliente_id")

        # Contexto personalizado por admin (si querés sumar más campos, acá)
        ctx = {
            a.id: {
                "usuario": getattr(actor, "email", None),
                "fecha": str(turno.fecha),
                "hora": str(turno.hora)[:5],
                "sede_nombre": getattr(turno.lugar, "nombre", None),
                "prestador": getattr(getattr(turno, "recurso", None), "nombre_publico", None),
            } for a in admins
        }

        creadas = notify_inapp(
            event=ev,
            recipients=admins,
            notif_type=TYPE_CANCELACION_TURNO,
            context_by_user=ctx,
            severity="info",
        )
        logger.info(
            "[notif.turno_cancelado_usuario][ok] event=%s turno=%s created=%s recipients=%s",
            getattr(ev, "id", None), getattr(turno, "id", None), creadas, admins.count()
        )
        return creadas
    except Exception:
        logger.exception("[notif.turno_cancelado_usuario][fail]")
        return 0


# ------------------------------------------------------------------------------
# POST /turnos/cancelar/  → Cancelar un turno propio
# - Permisos: Autenticado, debe ser dueño del turno y cumplir política de cancelación.
# - Efecto: libera slot (estado="disponible"), evalúa si corresponde emitir bonificación:
#     * Reservado con bono → usuario cancela: NO; admin cancela: SÍ (devolución).  (*admin aplica en otras vistas*)
#     * Reservado SIN bono → SÍ emite bonificación automática (mismo tipo_turno).
# - Side-effects: notifica a admins si quien canceló fue el usuario.
# ------------------------------------------------------------------------------


class CancelarTurnoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CancelarTurnoSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            logger.warning("[turnos.cancelar][invalid] user=%s errors=%s", request.user.id, ser.errors)
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        turno = ser.validated_data["turno"]

        with transaction.atomic():
            # 🔒 Lock del turno
            turno = Turno.objects.select_for_update().get(pk=turno.pk)

            # Revalidar estado por si cambió entre request y lock
            if turno.estado != "reservado":
                return Response({"turno_id": ["El turno ya no está reservado."]}, status=400)

            # Guardamos el usuario al que hay que devolver el crédito si aplica
            usuario_original = turno.usuario

            # ¿quién cancela?
            tipo = getattr(request.user, "tipo_usuario", None)
            es_admin = tipo in ("admin_cliente", "super_admin")

            # ¿fue reservado con bonificación?
            bonificacion_usada = (
                TurnoBonificado.objects
                .filter(usado_en_turno=turno)
                .first()
            )

            # === Anular y desasociar comprobante si existiera ===
            comp = (
                ComprobantePago.objects
                .select_for_update()
                .filter(turno=turno)
                .first()
            )

            if comp:
                # 1) Anular intentos activos ligados a este comprobante (GFK correcto)
                try:
                    ct = ContentType.objects.get_for_model(ComprobantePago)
                    afectados = (
                        PagoIntento.objects
                        .filter(content_type=ct, object_id=comp.id, estado__in=["pre_aprobado", "confirmado"])
                        .update(estado="rechazado")
                    )
                    logger.info(
                        "[turnos.cancelar][pagointento.rechazados] turno=%s comp_id=%s afectados=%s",
                        turno.id, comp.id, afectados
                    )
                except Exception as e:
                    logger.exception("[turnos.cancelar][pagointento.query][fail] turno=%s comp_id=%s err=%s",
                                     turno.id, comp.id, str(e))
                    # Fallar fuerte: no dejamos estado intermedio (turno libre + comp atado)
                    return Response(
                        {"error": "No se pudo anular el pago asociado."},
                        status=status.HTTP_409_CONFLICT,
                    )

                # 2) Marcar comprobante como NO reutilizable y desasociar del turno
                try:
                    # Traza/Auditoría mínima en datos_extraidos
                    datos = comp.datos_extraidos or {}
                    datos.update({
                        "turno_original": turno.id,
                        "cancelado_en": timezone.now().isoformat(),
                        "motivo_cancelacion": "Cancelación de turno",
                    })
                    comp.datos_extraidos = datos
                    comp.valido = False       # <- impedir reutilización
                    comp.turno = None         # <- libera el OneToOne
                    comp.save(update_fields=["datos_extraidos", "valido", "turno"])
                    logger.warning("[turnos.cancelar][comp.desasociado] turno=%s comp_id=%s", turno.id, comp.id)
                except Exception as e:
                    logger.exception("[turnos.cancelar][comp.desasociar][fail] turno=%s comp_id=%s err=%s",
                                     turno.id, comp.id, str(e))
                    # Fallar fuerte: evitar inconsistencias
                    return Response(
                        {"error": "No se pudo desasociar el comprobante."},
                        status=status.HTTP_409_CONFLICT,
                    )
            else:
                logger.info("[turnos.cancelar][comp.none] turno=%s sin comprobante", turno.id)

            # 🔓 Liberar el slot
            turno.usuario = None
            turno.estado = "disponible"
            turno.save(update_fields=["usuario", "estado"])

            bono_creado = False
            # 🎯 Reglas de emisión
            try:
                if bonificacion_usada:
                    # Si se reservó con bono:
                    if es_admin and usuario_original:
                        from apps.turnos_core.services.bonificaciones import emitir_bonificacion_automatica
                        emitir_bonificacion_automatica(
                            usuario=usuario_original,
                            turno_original=turno,
                            motivo="Cancelación administrativa (devolución de bono)",
                        )
                        bono_creado = True
                else:
                    # Si NO se reservó con bono: política general (serializer ya validó)
                    if usuario_original:
                        from apps.turnos_core.services.bonificaciones import emitir_bonificacion_automatica
                        emitir_bonificacion_automatica(
                            usuario=usuario_original,
                            turno_original=turno,
                            motivo="Cancelación con política cumplida",
                        )
                        bono_creado = True
            except Exception as e:
                logger.exception(
                    "[turnos.cancelar][bono][fail] actor=%s turno_id=%s err=%s",
                    request.user.id, turno.id, str(e)
                )

        # Notificación al usuario cuando él mismo cancela (fuera de la transacción)
        try:
            if not es_admin:
                from apps.turnos_core.views import _notify_cancelacion_usuario  # evitar ciclos si aplica
                _notify_cancelacion_usuario(turno=turno, actor=request.user)
        except Exception:
            logger.exception("[turnos.cancelar][notif_admin][fail] turno=%s", turno.id)

        return Response({
            "message": "Turno cancelado y liberado.",
            "bonificacion_creada": bono_creado
        }, status=200)

# ------------------------------------------------------------------------------
# POST /turnos/admin/cancelar_por_sede/  → Cancelaciones masivas por sede
# - Permisos: super_admin | admin_cliente (de la sede).
# - Body: sede_id, fecha_inicio, fecha_fin, hora_inicio?, hora_fin?, prestador_ids?, motivo?, dry_run?=true
# - Lógica: procesa SOLO "reservados"; emite bonificaciones según reglas; crea registro idempotente.
# - Side-effects: evento y notificaciones in-app por usuario afectado (si no dry_run).
# ------------------------------------------------------------------------------
class CancelarPorSedeAdminView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        ser = CancelacionPorSedeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        sede_id = vd["sede_id"]
        sede = Lugar.objects.filter(id=sede_id).select_related("cliente").first()
        if not sede:
            return Response({"detail": "Sede no encontrada"}, status=404)
        if not request.user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or sede.cliente_id != cliente_actual.id:
                    return Response({"detail": "No autorizado para esta sede"}, status=403)

        resumen = cancelar_turnos_admin(
            accion_por=request.user,
            cliente_id=sede.cliente_id,
            sede_id=sede_id,
            prestador_ids=vd.get("prestador_ids") or None,
            fecha_inicio=vd["fecha_inicio"],
            fecha_fin=vd["fecha_fin"],
            hora_inicio=vd.get("hora_inicio"),
            hora_fin=vd.get("hora_fin"),
            motivo=vd.get("motivo") or "Cancelación administrativa",
            dry_run=vd.get("dry_run", True),   # ← ahora sí respeta el boolean
        )
        return Response(resumen, status=200)


# ------------------------------------------------------------------------------
# POST /turnos/prestadores/<prestador_id>/cancelar_en_rango/  → Cancelaciones masivas por prestador
# - Permisos: super_admin | admin_cliente (del tenant o de la sede indicada).
# - Body: fecha_inicio, fecha_fin, hora_inicio?, hora_fin?, sede_id?, motivo?, dry_run?=true
# - Lógica: igual a por sede pero acotando al prestador.
# ------------------------------------------------------------------------------
class CancelarPorPrestadorAdminView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]
    def post(self, request, prestador_id: int):
        ser = CancelacionPorPrestadorSerializer(data=request.data); ser.is_valid(raise_exception=True); vd = ser.validated_data
        cliente_id = request.user.cliente_id
        if vd.get("sede_id"):
            sede = Lugar.objects.filter(id=vd["sede_id"]).first()
            if not sede: return Response({"detail": "Sede no encontrada"}, status=404)
            cliente_id = sede.cliente_id
            if not request.user.is_super_admin:
                from apps.auth_core.utils import get_rol_actual_del_jwt
                rol_actual = get_rol_actual_del_jwt(request)
                
                if rol_actual == "admin_cliente":
                    cliente_actual = getattr(request, 'cliente_actual', None)
                    if not cliente_actual or cliente_id != cliente_actual.id:
                        return Response({"detail": "No autorizado para esta sede"}, status=403)
        else:
            # Validar tenancy por prestador si no hay sede_id
            from apps.turnos_core.models import Prestador
            prest = Prestador.objects.select_related("cliente").filter(id=prestador_id).first()
            if not prest: return Response({"detail": "Prestador no encontrado"}, status=404)
            cliente_id = prest.cliente_id
            if not request.user.is_super_admin:
                from apps.auth_core.utils import get_rol_actual_del_jwt
                rol_actual = get_rol_actual_del_jwt(request)
                
                if rol_actual == "admin_cliente":
                    cliente_actual = getattr(request, 'cliente_actual', None)
                    if not cliente_actual or prest.cliente_id != cliente_actual.id:
                        return Response({"detail": "No autorizado para este prestador"}, status=403)
        logger.info("[CancelacionPorPrestador] user=%s prestador=%s sede=%s rango=%s..%s horas=%s..%s dry_run=%s", request.user.id, prestador_id, vd.get("sede_id"), vd["fecha_inicio"], vd["fecha_fin"], vd.get("hora_inicio"), vd.get("hora_fin"), vd.get("dry_run", True))
        resumen = cancelar_turnos_admin(
            accion_por=request.user,
            cliente_id=cliente_id,
            sede_id=vd.get("sede_id"),
            prestador_ids=[int(prestador_id)],
            fecha_inicio=vd["fecha_inicio"],
            fecha_fin=vd["fecha_fin"],
            hora_inicio=vd.get("hora_inicio"),
            hora_fin=vd.get("hora_fin"),
            motivo=vd.get("motivo") or "Cancelación administrativa",
            dry_run=vd.get("dry_run", True),
        )
        return Response(resumen, status=200)


# ------------------------------------------------------------------------------
# GET /turnos/bonificados/mios/  y  /turnos/bonificados/mios/<tipo_clase_id>/
# - Permisos: Autenticado.
# - Función: devuelve bonificaciones vigentes del usuario (opcional filtro por tipo de clase → x1..x4 con alias).
# - Respuesta: [{id, motivo, tipo_turno, fecha_creacion, valido_hasta}, ...]
# ------------------------------------------------------------------------------
def _tipo_code_y_aliases(tipo_clase_id: int):
    """
    Devuelve (code, aliases_set) para el tipo_clase dado.
    code ∈ {"x1","x2","x3","x4"}.
    """
    try:
        tc = TipoClasePadel.objects.get(pk=tipo_clase_id)
    except TipoClasePadel.DoesNotExist:
        return None, set()

    code = (getattr(tc, "codigo", "") or "").strip().lower()
    if code not in {"x1", "x2", "x3", "x4"}:
        code = None

    inv_aliases = {
        "x1": {"individual"},
        "x2": {"2 personas"},
        "x3": {"3 personas"},
        "x4": {"4 personas"},
    }
    aliases = set(a.lower() for a in inv_aliases.get(code, set()))
    return code, aliases

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bonificaciones_mias(request, tipo_clase_id=None):
    user = request.user

    # Base: SOLO vigentes (respeta valido_hasta) y sin usar
    qs = bonificaciones_vigentes(user).order_by("fecha_creacion")

    # tipo_clase_id puede venir por path o query
    tipo_clase_id = tipo_clase_id or request.query_params.get("tipo_clase_id")
    if tipo_clase_id:
        code, aliases = _tipo_code_y_aliases(int(tipo_clase_id))
        if code:
            cond = Q(tipo_turno__iexact=code)
            for alt in aliases:
                cond |= Q(tipo_turno__iexact=alt)
            qs = qs.filter(cond)
            logger.info(
                "[bonos.mios][filter] user=%s tipo_clase_id=%s code=%s aliases=%s count=%s",
                user.id, tipo_clase_id, code, list(aliases), qs.count()
            )
        else:
            logger.warning(
                "[bonos.mios][tipo_clase_sin_code] user=%s tipo_clase_id=%s",
                user.id, tipo_clase_id
            )

    data = list(qs.values(
        "id",
        "motivo",
        "tipo_turno",
        "fecha_creacion",
        "valido_hasta",
        "valor",          # 👈 NUEVO
    ))
    return Response(data)

# ------------------------------------------------------------------------------
# GET /turnos/prestador/mio/
# - Permisos: Autenticado.
# - Función: retorna el id de Prestador vinculado al usuario logueado (o 404 si no existe).
# ------------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prestador_actual(request):
    user = request.user
    prestador = Prestador.objects.filter(user=user).first()
    if not prestador:
        return Response({"detail": "No se encontró un prestador asociado a este usuario"}, status=404)
    return Response({"id": prestador.id})

# ------------------------------------------------------------------------------
# DELETE /turnos/bonificaciones/{id}/  → Eliminar bonificación específica
# - Permisos: Solo super_admin/admin_cliente.
# - Función: elimina una bonificación específica con motivo administrativo.
# ------------------------------------------------------------------------------
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def eliminar_bonificacion(request, bonificacion_id):
    """
    Elimina una bonificación específica.
    Solo super_admin/admin_cliente pueden eliminar bonificaciones.
    """
    user = request.user
    if user.is_super_admin:
        pass  # Super admin siempre tiene acceso
    else:
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual not in ["super_admin", "admin_cliente"]:
            return Response({"error": "No autorizado"}, status=403)
    
    try:
        from apps.turnos_core.services.bonificaciones import eliminar_bonificacion as eliminar_bonificacion_service
        motivo = request.data.get("motivo", "Eliminada por administrador")
        
        if eliminar_bonificacion_service(bonificacion_id, motivo):
            logger.info(f"[eliminar_bonificacion] Bonificación {bonificacion_id} eliminada por {user.id}")
            return Response({"ok": True, "message": "Bonificación eliminada correctamente"}, status=200)
        else:
            return Response({"error": "Bonificación no encontrada"}, status=404)
    except Exception as e:
        logger.error(f"[eliminar_bonificacion] Error: {str(e)}")
        return Response({"error": "Error eliminando bonificación"}, status=500)

# ------------------------------------------------------------------------------
# GET /turnos/bonificados/usuario/{usuario_id}/  → Bonificaciones de usuario específico
# - Permisos: Solo super_admin/admin_cliente.
# - Función: obtiene bonificaciones de un usuario específico.
# ------------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bonificaciones_usuario(request, usuario_id):
    """
    Obtiene bonificaciones de un usuario específico.
    Solo super_admin/admin_cliente pueden ver bonificaciones de otros usuarios.
    """
    user = request.user
    
    # Super admin siempre tiene acceso
    if user.is_super_admin:
        pass  # Acceso total
    else:
        # Para otros usuarios, verificar el rol actual del JWT
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual not in ["super_admin", "admin_cliente"]:
            return Response({"error": "No autorizado"}, status=403)
    
    try:
        Usuario = get_user_model()
        usuario_target = Usuario.objects.get(id=usuario_id)
        
        # Verificar que el admin puede ver este usuario (mismo cliente)
        if not user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                # Admin_cliente: autorizar si el usuario objetivo pertenece al cliente actual vía UserClient activo
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual:
                    return Response({"error": "No autorizado para ver este usuario"}, status=403)
                from apps.auth_core.models import UserClient
                pertenece = UserClient.objects.filter(
                    usuario=usuario_target,
                    cliente=cliente_actual,
                    activo=True,
                ).exists()
                if not pertenece:
                    return Response({"error": "No autorizado para ver este usuario"}, status=403)
        
        # Obtener bonificaciones del usuario
        qs = bonificaciones_vigentes(usuario_target).order_by("fecha_creacion")
        
        # Filtro opcional por tipo_clase_id
        tipo_clase_id = request.query_params.get("tipo_clase_id")
        if tipo_clase_id:
            code, aliases = _tipo_code_y_aliases(int(tipo_clase_id))
            if code:
                cond = Q(tipo_turno__iexact=code)
                for alt in aliases:
                    cond |= Q(tipo_turno__iexact=alt)
                qs = qs.filter(cond)
        
        data = list(qs.values(
            "id",
            "motivo",
            "tipo_turno",
            "fecha_creacion",
            "valido_hasta",
            "valor",
            "usado",
        ))
        
        logger.info(f"[bonificaciones_usuario] Usuario {usuario_id} tiene {len(data)} bonificaciones")
        return Response(data)
        
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado"}, status=404)
    except Exception as e:
        logger.error(f"[bonificaciones_usuario] Error: {str(e)}")
        return Response({"error": "Error obteniendo bonificaciones"}, status=500)

# ------------------------------------------------------------------------------
# GET /turnos/usuario/{usuario_id}/  → Turnos de usuario específico
# - Permisos: Solo super_admin/admin_cliente.
# - Función: obtiene turnos de un usuario específico.
# ------------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def turnos_usuario(request, usuario_id):
    """
    Obtiene turnos de un usuario específico.
    Solo super_admin/admin_cliente pueden ver turnos de otros usuarios.
    """
    user = request.user
    
    # Super admin siempre tiene acceso
    if user.is_super_admin:
        pass  # Acceso total
    else:
        # Para otros usuarios, verificar el rol actual del JWT
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual not in ["super_admin", "admin_cliente"]:
            return Response({"error": "No autorizado"}, status=403)
    
    try:
        Usuario = get_user_model()
        usuario_target = Usuario.objects.get(id=usuario_id)
        
        # Verificar que el admin puede ver este usuario (mismo cliente)
        if not user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                # Admin_cliente: autorizar si el usuario objetivo pertenece al cliente actual vía UserClient activo
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual:
                    return Response({"error": "No autorizado para ver este usuario"}, status=403)
                from apps.auth_core.models import UserClient
                pertenece = UserClient.objects.filter(
                    usuario=usuario_target,
                    cliente=cliente_actual,
                    activo=True,
                ).exists()
                if not pertenece:
                    return Response({"error": "No autorizado para ver este usuario"}, status=403)
        
        # Obtener turnos del usuario
        qs = Turno.objects.filter(usuario=usuario_target).select_related("usuario", "lugar")
        
        # Filtros opcionales
        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        
        upcoming = request.query_params.get("upcoming", "").lower()
        if upcoming in {"1", "true", "sí", "si"}:
            ahora = localtime()
            hoy = ahora.date()
            hora = ahora.time()
            qs = qs.filter(Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora))
        
        # Filtrar turnos sueltos (no de abonos)
        solo_sueltos = request.query_params.get("solo_sueltos", "").lower()
        if solo_sueltos in {"1", "true", "sí", "si"}:
            qs = qs.filter(
                reservado_para_abono=False,
                abono_mes_reservado__isnull=True,
                abono_mes_prioridad__isnull=True,
                comprobante_abono__isnull=True,
            )
        
        turnos = qs.order_by("fecha", "hora")
        serializer = TurnoSerializer(turnos, many=True)
        
        logger.info(f"[turnos_usuario] Usuario {usuario_id} tiene {len(serializer.data)} turnos")
        return Response(serializer.data)
        
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado"}, status=404)
    except Exception as e:
        logger.error(f"[turnos_usuario] Error: {str(e)}")
        return Response({"error": "Error obteniendo turnos"}, status=500)
