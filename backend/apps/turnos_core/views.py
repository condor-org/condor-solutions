# apps/turnos_core/views.py

# Built-in
from datetime import datetime

from apps.turnos_core.services.bonificaciones import emitir_bonificacion_automatica, bonificaciones_vigentes
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied


# Django
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils.timezone import now, localtime 
from django.contrib.auth import get_user_model
from django.utils import timezone as tz
from zoneinfo import ZoneInfo  # Python 3.9+


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
    TurnoBonificado,
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
    CancelarTurnoSerializer,
    CancelacionPorSedeSerializer,
    CancelacionPorPrestadorSerializer,
)

# App imports - Servicios
from apps.turnos_core.services.turnos import generar_turnos_para_prestador
import logging

logger = logging.getLogger(__name__)


from apps.turnos_padel.models import TipoClasePadel

from apps.turnos_core.services.cancelaciones_admin import cancelar_turnos_admin
from apps.notificaciones_core.services import publish_event, notify_inapp, TYPE_CANCELACION_TURNO


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

        upcoming = self.request.query_params.get("upcoming")
        if (upcoming or "").lower() in {"1", "true", "sí", "si"}:
            ahora = localtime()
            hoy = ahora.date()
            hora = ahora.time()
            qs = qs.filter(Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora))

        return qs.order_by("fecha", "hora")

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



        ahora_ar = tz.now().astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
        hoy = ahora_ar.date()
        hora = ahora_ar.time().replace(microsecond=0)

        ct_prestador = ContentType.objects.get_for_model(Prestador)

        turnos = (
            Turno.objects
            .filter(
                content_type=ct_prestador,
                object_id=int(prestador_id),
                lugar_id=int(lugar_id),
                estado__in=["disponible", "reservado"],
            )
            .filter(
                Q(fecha__gt=hoy) |
                (Q(fecha=hoy) & Q(hora__gte=hora))
            )
            .order_by("fecha", "hora")
        )


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

        from django.db import transaction

        creados = 0
        with transaction.atomic():
            for t in turnos_afectados.select_for_update():
                # cancelar
                t.estado = "cancelado"
                t.save(update_fields=["estado"])

                # si el turno se reservó con bono → NO re-emitir
                if TurnoBonificado.objects.filter(usado_en_turno=t).exists():
                    continue

                # si fue pago y conocemos tipo_turno → emitir del mismo tipo
                if t.tipo_turno and t.usuario_id:
                    try:
                        emitir_bonificacion_automatica(
                            usuario=t.usuario,
                            turno_original=t,
                            motivo="Cancelación por bloqueo/admin",
                        )
                        creados += 1
                    except Exception:
                        logger.exception(
                            "[admin.cancel_masiva][bono][fail] turno=%s user=%s tipo=%s",
                            t.id, t.usuario_id, t.tipo_turno
                        )

        return Response({
            "message": f"{turnos_afectados.count()} turnos cancelados.",
            "bonificaciones_emitidas": creados
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

class CancelarTurnoView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        ser = CancelarTurnoSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            logger.warning("[turnos.cancelar][invalid] user=%s errors=%s", request.user.id, ser.errors)
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        turno = ser.validated_data["turno"]

        with transaction.atomic():
            # 🔒 lock por carrera
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
                .filter(usado_en_turno=turno)  # ajustá este filtro si tu esquema es distinto
                .first()
            )

            # 🔓 Liberar el slot
            turno.usuario = None
            turno.estado = "disponible"
            turno.save(update_fields=["usuario", "estado"])

            bono_creado = False
            # 🎯 Reglas de emisión:
            try:
                if bonificacion_usada:
                    # Si se reservó con bono:
                    # - Usuario cancela => NO emitir
                    # - Admin cancela => SÍ emitir (devolución)
                    if es_admin and usuario_original:
                        emitir_bonificacion_automatica(
                            usuario=usuario_original,
                            turno_original=turno,
                            motivo="Cancelación administrativa (devolución de bono)",
                        )
                        bono_creado = True
                else:
                    # Si NO se reservó con bono: se aplica la política general previa
                    # (el serializer ya debió validar la política)
                    if usuario_original:
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
        try:
            # Solo si la cancelación fue iniciada por el usuario final o empleado_cliente actuando sobre su propio turno.
            if not es_admin:
                _notify_cancelacion_usuario(turno=turno, actor=request.user)
        except Exception:
            logger.exception("[turnos.cancelar][notif_admin][fail] turno=%s", turno.id)

        return Response({
            "message": "Turno cancelado y liberado.",
            "bonificacion_creada": bono_creado
        }, status=200)

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

    serializer = PrestadorSerializer(prestadores, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prestador_actual(request):
    user = request.user
    prestador = Prestador.objects.filter(user=user).first()
    if not prestador:
        return Response({"detail": "No se encontró un prestador asociado a este usuario"}, status=404)
    return Response({"id": prestador.id})

