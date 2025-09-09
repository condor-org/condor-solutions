# Built-in
from datetime import datetime
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
)

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
)

logger = logging.getLogger(__name__)


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

        if usuario.is_superuser:
            qs = Turno.objects.all().select_related("usuario", "lugar")
        elif getattr(usuario, "tipo_usuario", None) == "empleado_cliente":
            qs = Turno.objects.filter(
                content_type=ContentType.objects.get_for_model(Prestador),
                object_id__in=Prestador.objects.filter(user=usuario).values_list("id", flat=True)
            ).select_related("usuario", "lugar")
        else:
            qs = Turno.objects.filter(usuario=usuario).select_related("usuario", "lugar")

        # --- filtros opcionales ---
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        upcoming = (self.request.query_params.get("upcoming") or "").lower()
        if upcoming in {"1", "true", "sí", "si"}:
            ahora = localtime()
            hoy = ahora.date()
            hora = ahora.time()
            qs = qs.filter(Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora))

        # 🔒 Para usuarios finales: SIEMPRE mostrar sólo clases sueltas
        # (excluir cualquier turno que provenga de un abono)
        if getattr(usuario, "tipo_usuario", None) == "usuario_final":
            qs = qs.filter(
                reservado_para_abono=False,
                abono_mes_reservado__isnull=True,
                abono_mes_prioridad__isnull=True,
                comprobante_abono__isnull=True,
            )

        return qs.order_by("fecha", "hora")


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
        # al final de create(), antes del return
        try:
            from apps.notificaciones_core.services import publish_event, notify_inapp, TYPE_RESERVA_TURNO
            from django.contrib.auth import get_user_model
            Usuario = get_user_model()

            turno = serializer.instance
            cliente_id = getattr(request.user, "cliente_id", None)

            ev = publish_event(
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

            # 🔹 Solo admins del cliente (sin superadmin)
            admins = Usuario.objects.filter(
                cliente_id=cliente_id,
                tipo_usuario="admin_cliente",
            ).only("id", "cliente_id")

            ctx = {
                a.id: {
                    "usuario": getattr(request.user, "email", None),
                    "fecha": str(turno.fecha),
                    "hora": str(turno.hora)[:5],
                    "sede_nombre": getattr(turno.lugar, "nombre", None),
                    "prestador": getattr(getattr(turno, "recurso", None), "nombre_publico", None),
                } for a in admins
            }

            notify_inapp(
                event=ev,
                recipients=admins,
                notif_type=TYPE_RESERVA_TURNO,
                context_by_user=ctx,
                severity="info",
            )
        except Exception:
            logger.exception("[notif][turno_reserva][fail]")

        return Response({"message": "Turno reservado exitosamente", "turno_id": turno.id})


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
        return request.user.is_authenticated and (
            request.user.tipo_usuario in {"super_admin", "admin_cliente"}
        )


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

        if user.tipo_usuario == "super_admin":
            return Disponibilidad.objects.all()

        if user.tipo_usuario == "admin_cliente":
            return Disponibilidad.objects.filter(prestador__cliente=user.cliente)

        if user.tipo_usuario == "empleado_cliente":
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
        data = request.data or {}

        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        prestador_id = data.get("prestador_id")
        duracion_minutos = data.get("duracion_minutos", 60)

        if not fecha_inicio or not fecha_fin:
            return Response({"error": "Faltan parámetros: fecha_inicio y fecha_fin."}, status=400)

        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido (usar YYYY-MM-DD)."}, status=400)

        if fecha_inicio > fecha_fin:
            return Response({"error": "Rango de fechas inválido: fecha_inicio > fecha_fin."}, status=400)

        # No crear pasado
        hoy = timezone.localdate()
        if fecha_inicio < hoy:
            fecha_inicio = hoy

        try:
            duracion_minutos = int(duracion_minutos)
            if duracion_minutos <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            return Response({"error": "duracion_minutos debe ser un entero positivo."}, status=400)

        qs = Prestador.objects.filter(cliente=user.cliente, activo=True)
        if prestador_id:
            qs = qs.filter(id=prestador_id)
        prestadores = list(qs)

        if not prestadores:
            return Response({"turnos_generados": 0, "profesores_afectados": 0, "detalle": []}, status=200)

        total = 0
        detalle = []

        logger.info(
            "[turnos.generar][start] user_id=%s cliente_id=%s rango=[%s..%s] dur=%s prestador_id=%s trace=%s",
            getattr(user, "id", None), getattr(user, "cliente_id", None),
            fecha_inicio, fecha_fin, duracion_minutos, prestador_id, trace_id
        )

        try:
            for p in prestadores:
                creados = generar_turnos_para_prestador(
                    prestador_id=p.id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    duracion_minutos=duracion_minutos,
                    estado="disponible",
                )
                total += creados
                detalle.append({"profesor_id": p.id, "nombre": p.nombre_publico, "turnos": creados})

            logger.info("[turnos.generar][done] trace=%s total=%s profesores=%s", trace_id, total, len(detalle))
            return Response(
                {"turnos_generados": total, "profesores_afectados": len(detalle), "detalle": detalle, "trace_id": trace_id},
                status=200
            )
        except Exception as e:
            logger.exception("[turnos.generar][error] trace=%s %s", trace_id, e)
            return Response({"error": "No se pudieron generar turnos.", "trace_id": trace_id}, status=500)
# ------------------------------------------------------------------------------
# POST /turnos/bonificaciones/crear-manual/  → Emitir bonificación manual
# - Permisos: super_admin | admin_cliente.
# - Body: usuario_id, tipo_turno (x1..x4 o alias), motivo?, valido_hasta?
# - Side-effects: evento + notificación al usuario.
# ------------------------------------------------------------------------------
class CrearBonificacionManualView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.tipo_usuario not in ["super_admin", "admin_cliente"]:
            return Response({"detail": "No autorizado"}, status=403)

        serializer = CrearTurnoBonificadoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bono = serializer.save()
        return Response({"message": "Bonificación creada correctamente."}, status=201)


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
        if request.user.tipo_usuario == "admin_cliente" and sede.cliente_id != request.user.cliente_id:
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
            if request.user.tipo_usuario == "admin_cliente" and cliente_id != request.user.cliente_id:
                return Response({"detail": "No autorizado para esta sede"}, status=403)
        else:
            # Validar tenancy por prestador si no hay sede_id
            from apps.turnos_core.models import Prestador
            prest = Prestador.objects.select_related("cliente").filter(id=prestador_id).first()
            if not prest: return Response({"detail": "Prestador no encontrado"}, status=404)
            cliente_id = prest.cliente_id
            if request.user.tipo_usuario == "admin_cliente" and prest.cliente_id != request.user.cliente_id:
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

    data = [
        {
            "id": b.id,
            "motivo": b.motivo,
            "tipo_turno": b.tipo_turno,
            "fecha_creacion": b.fecha_creacion,
            "valido_hasta": b.valido_hasta,
        }
        for b in qs
    ]
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
