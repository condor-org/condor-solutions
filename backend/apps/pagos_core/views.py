# apps/pagos_core/views.py

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.filters import OrderingFilter

from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import PermissionDenied
import logging

from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.pagos_core.models import ComprobantePago, ComprobanteAbono, PagoIntento
from apps.pagos_core.serializers import ComprobantePagoSerializer, ComprobanteUploadSerializer, ComprobanteAbonoUploadSerializer
from apps.pagos_core.filters import ComprobantePagoFilter
from .models import ConfiguracionPago
from .serializers import ConfiguracionPagoSerializer

from apps.common.permissions import EsAdminDeSuCliente, EsSuperAdmin

from django.db import transaction

from apps.turnos_padel.models import AbonoMes
from apps.turnos_core.models import Turno, TurnoBonificado
from apps.turnos_padel.services.abonos import reservar_abono_mes_actual_y_prioridad


class ComprobanteView(ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ComprobanteUploadSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ComprobantePagoFilter
    ordering_fields = ["created_at", "valido"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ComprobanteUploadSerializer
        return ComprobantePagoSerializer

    def get_queryset(self):
        usuario = self.request.user
        qs = ComprobantePago.objects.select_related("turno", "turno__usuario", "turno__lugar")

        if usuario.tipo_usuario == "super_admin":
            qs = qs
        elif usuario.tipo_usuario == "admin_cliente" and usuario.cliente_id:
            qs = qs.filter(cliente=usuario.cliente)
        elif usuario.tipo_usuario == "empleado_cliente":
            qs = qs.filter(turno__usuario=usuario)
        else:  # usuario_final
            qs = qs.filter(turno__usuario=usuario)

        # 🔥 ACÁ ESTÁ EL FILTRO QUE FALTABA
        if self.request.query_params.get("solo_preaprobados") == "true":
            qs = qs.filter(valido=False)

        return qs




    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comprobante = serializer.save()
        return Response({
            "mensaje": "✅ Comprobante recibido y validado correctamente",
            "datos_extraidos": comprobante.datos_extraidos,
            "turno_id": comprobante.turno.id,
            "id_comprobante": comprobante.id
        }, status=status.HTTP_201_CREATED)

class ComprobanteDownloadView(APIView):
    queryset = ComprobantePago.objects.none()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        logger = logging.getLogger(__name__)
        logger.debug("Descarga de comprobante %s solicitada por %s (%s)", pk, request.user, getattr(request.user, "tipo_usuario", ""))

        try:
            comprobante = ComprobanteService.download_comprobante(
                comprobante_id=int(pk),
                usuario=request.user
            )
            logger.debug("Comprobante encontrado: %s archivo=%s", comprobante.id, comprobante.archivo)

            if not comprobante.archivo or not comprobante.archivo.storage.exists(comprobante.archivo.name):
                logger.error("Archivo no encontrado en storage: %s", comprobante.archivo.name)
                return Response({"error": "Archivo no encontrado en disco"}, status=404)

            return FileResponse(
                comprobante.archivo.open("rb"),
                as_attachment=True,
                filename=comprobante.archivo.name.split("/")[-1]
            )

        except PermissionDenied as e:
            logger.debug("PermissionDenied: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            logger.debug("Error inesperado: %s", e)
            return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)

class ComprobanteAprobarRechazarView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    @transaction.atomic
    def patch(self, request, pk, action):
        logger = logging.getLogger(__name__)
        logger.debug("[PATCH] Acción '%s' sobre comprobante ID=%s", action, pk)

        # 1) Intentar con ComprobantePago (turno individual)
        try:
            comprobante = ComprobantePago.objects.get(pk=pk)
            logger.debug("[PATCH] ComprobantePago encontrado: ID=%s", comprobante.id)

            turno = comprobante.turno
            intento = PagoIntento.objects.filter(
                content_type__model="comprobantepago",
                object_id=comprobante.id
            ).first()
            if intento:
                logger.debug("[PATCH] IntentoPago asociado encontrado: ID=%s", intento.id)
            else:
                logger.debug("[PATCH] No se encontró intento de pago asociado")

            if action == 'aprobar':
                comprobante.valido = True
                comprobante.save(update_fields=["valido"])
                logger.debug("[APROBAR] ComprobantePago %s marcado como válido", comprobante.id)

                if intento:
                    intento.estado = "confirmado"
                    intento.save(update_fields=["estado"])
                    logger.debug("[APROBAR] IntentoPago %s marcado como confirmado", intento.id)

                return Response({"mensaje": "✅ Comprobante aprobado"})

            elif action == 'rechazar':
                comprobante.valido = False
                comprobante.save(update_fields=["valido"])
                logger.debug("[RECHAZAR] ComprobantePago %s marcado como inválido", comprobante.id)

                if intento:
                    intento.estado = "rechazado"
                    intento.save(update_fields=["estado"])
                    logger.debug("[RECHAZAR] IntentoPago %s marcado como rechazado", intento.id)

                if turno:
                    logger.debug(
                        "[RECHAZAR] Liberando turno %s: estado actual=%s, usuario actual=%s",
                        turno.id, turno.estado, turno.usuario_id,
                    )
                    turno.usuario = None
                    turno.estado = 'disponible'
                    turno.save(update_fields=["usuario", "estado"])
                    logger.debug("[RECHAZAR] Turno %s liberado correctamente", turno.id)

                return Response({"mensaje": "❌ Comprobante rechazado y turno liberado"})

            logger.warning("[PATCH] Acción inválida: '%s'", action)
            return Response({"error": "Acción no válida. Usa 'aprobar' o 'rechazar'."}, status=400)

        except ComprobantePago.DoesNotExist:
            logger.debug("[PATCH] No es ComprobantePago. Probando ComprobanteAbono...")

        # 2) Intentar con ComprobanteAbono (abono mensual)
        try:
            comprobante_abono = ComprobanteAbono.objects.select_related("abono_mes").get(pk=pk)
            logger.debug("[PATCH] ComprobanteAbono encontrado: ID=%s", comprobante_abono.id)

            intento = PagoIntento.objects.filter(
                content_type__model="comprobanteabono",
                object_id=comprobante_abono.id
            ).first()
            if intento:
                logger.debug("[PATCH][abono] IntentoPago asociado encontrado: ID=%s", intento.id)
            else:
                logger.debug("[PATCH][abono] No se encontró intento de pago asociado")

            abono = comprobante_abono.abono_mes

            if action == 'aprobar':
                comprobante_abono.valido = True
                comprobante_abono.save(update_fields=["valido"])
                logger.debug("[APROBAR][abono] ComprobanteAbono %s marcado como válido", comprobante_abono.id)

                if intento:
                    intento.estado = "confirmado"
                    intento.save(update_fields=["estado"])
                    logger.debug("[APROBAR][abono] IntentoPago %s marcado como confirmado", intento.id)

                # Nota: la reserva (mes actual + prioridad) ya ocurrió al subir el comprobante.
                abono.estado = "pagado"
                abono.save(update_fields=["estado"])
                logger.debug("[APROBAR][abono] AbonoMes %s marcado como pagado", abono.id)

                return Response({"mensaje": "✅ Comprobante de abono aprobado"})

            elif action == 'rechazar':
                comprobante_abono.valido = False
                comprobante_abono.save(update_fields=["valido"])
                logger.debug("[RECHAZAR][abono] ComprobanteAbono %s marcado como inválido", comprobante_abono.id)

                if intento:
                    intento.estado = "rechazado"
                    intento.save(update_fields=["estado"])
                    logger.debug("[RECHAZAR][abono] IntentoPago %s marcado como rechazado", intento.id)

                # Liberar turnos: mes actual (con comprobante) + prioridad (sin comprobante)
                from apps.turnos_core.models import Turno  # import local para evitar ciclos

                liberados_actual = 0
                liberados_prio = 0

                with transaction.atomic():
                    # 1) Mes actual: todos los turnos con este comprobante_abono
                    turnos_actual = Turno.objects.select_for_update().filter(comprobante_abono=comprobante_abono)
                    for t in turnos_actual:
                        t.usuario = None
                        t.estado = "disponible"
                        t.tipo_turno = None
                        t.comprobante_abono = None
                        t.save(update_fields=["usuario", "estado", "tipo_turno", "comprobante_abono"])
                        liberados_actual += 1

                    # 2) Mes próximo (prioridad): los del M2M del abono (no tienen comprobante)
                    prio_ids = list(abono.turnos_prioridad.values_list("pk", flat=True))
                    if prio_ids:
                        turnos_prio = Turno.objects.select_for_update().filter(pk__in=prio_ids)
                        for t in turnos_prio:
                            t.usuario = None
                            t.estado = "disponible"
                            t.tipo_turno = None
                            t.save(update_fields=["usuario", "estado", "tipo_turno"])
                            liberados_prio += 1

                    # Limpiar M2M del abono
                    abono.turnos_reservados.clear()
                    abono.turnos_prioridad.clear()

                    # Estado final del abono → cancelado (no “creado”)
                    abono.estado = "cancelado"
                    abono.save(update_fields=["estado"])

                logger.debug(
                    "[RECHAZAR][abono] AbonoMes %s cancelado. Liberados actual=%s prio=%s",
                    abono.id, liberados_actual, liberados_prio
                )
                return Response({"mensaje": "❌ Comprobante de abono rechazado. Turnos liberados y abono cancelado."})

            logger.warning("[PATCH][abono] Acción inválida: '%s'", action)
            return Response({"error": "Acción no válida. Usa 'aprobar' o 'rechazar'."}, status=400)

        except ComprobanteAbono.DoesNotExist:
            logger.warning("[PATCH] Comprobante no encontrado (pago o abono): ID=%s", pk)
            return Response({"error": "No encontrado"}, status=404)

class ConfiguracionPagoPermission(BasePermission):
    """
    Permitir GET a cualquier autenticado, pero solo admin_cliente o super_admin puede PUT/PATCH.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.tipo_usuario in {"admin_cliente", "super_admin"}

class ConfiguracionPagoView(RetrieveUpdateAPIView):
    queryset = ConfiguracionPago.objects.all()
    serializer_class = ConfiguracionPagoSerializer
    permission_classes = [ConfiguracionPagoPermission]
    authentication_classes = [JWTAuthentication]

    def get_object(self):
        cliente = self.request.user.cliente
        obj, created = ConfiguracionPago.objects.get_or_create(
            cliente=cliente,
            defaults={
                'destinatario': 'NOMBRE DESTINATARIO',
                'cbu': '0000000000000000000000',
                'alias': 'ALIAS_DESTINATARIO',
                'monto_esperado': 0,
                'tiempo_maximo_minutos': 60,
            }
        )
        return obj

class PagosPendientesCountView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    def get(self, request):
        count = ComprobantePago.objects.filter(cliente=request.user.cliente, valido=False).count()
        return Response({"count": count})

class ComprobanteAbonoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)

        ser = ComprobanteAbonoUploadSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        comprobante = ser.save()
        abono = comprobante.abono_mes

        logger.info(
            "[abono.comprobante.upload] abono=%s user=%s sede=%s prestador=%s %s-%02d %s@%s",
            abono.id, request.user.id, abono.sede_id, abono.prestador_id,
            abono.anio, abono.mes, abono.get_dia_semana_display(), abono.hora
        )

        # 🔒 Reservar mes actual (pagado, con comprobante) + mes siguiente (prioridad, sin comprobante)
        try:
            from apps.turnos_padel.services.abonos import reservar_abono_mes_actual_y_prioridad
            reservar_abono_mes_actual_y_prioridad(abono, comprobante_abono=comprobante)
        except Exception as e:
            # Rollback coherente: si falla la reserva, eliminamos intento y comprobante
            PagoIntento.objects.filter(
                content_type__model="comprobanteabono",
                object_id=comprobante.id
            ).delete()
            comprobante.delete()
            logger.exception("[abono.reserve][fail] abono=%s err=%s", abono.id, str(e))
            return Response(
                {"detail": f"No se pudo reservar el abono: {str(e)}"},
                status=status.HTTP_409_CONFLICT
            )

        logger.info(
            "[abono.reserve][ok] abono=%s reservados=%s prioridad=%s vence=%s",
            abono.id, abono.turnos_reservados.count(), abono.turnos_prioridad.count(), abono.fecha_limite_renovacion
        )

        return Response({
            "mensaje": "✅ Comprobante de abono recibido. Turnos reservados para este mes y prioridad para el próximo.",
            "abono_mes_id": abono.id,
            "comprobante_abono_id": comprobante.id,
            "reservados": abono.turnos_reservados.count(),
            "prioridad": abono.turnos_prioridad.count(),
            "vence": str(abono.fecha_limite_renovacion),
        }, status=status.HTTP_201_CREATED)
