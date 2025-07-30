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
from apps.pagos_core.models import ComprobantePago
from apps.pagos_core.serializers import ComprobantePagoSerializer, ComprobanteUploadSerializer
from apps.pagos_core.filters import ComprobantePagoFilter
from .models import ConfiguracionPago
from .serializers import ConfiguracionPagoSerializer

from apps.common.permissions import EsAdminDeSuCliente, EsSuperAdmin
from apps.pagos_core.models import PagoIntento 
from django.db import transaction


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


# apps/pagos_core/views.py

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

        try:
            comprobante = ComprobantePago.objects.get(pk=pk)
            logger.debug("[PATCH] Comprobante encontrado: ID=%s", comprobante.id)
        except ComprobantePago.DoesNotExist:
            logger.warning("[PATCH] Comprobante no encontrado: ID=%s", pk)
            return Response({"error": "No encontrado"}, status=404)

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
            logger.debug("[APROBAR] Comprobante %s marcado como válido", comprobante.id)

            if intento:
                intento.estado = "confirmado"
                intento.save(update_fields=["estado"])
                logger.debug("[APROBAR] IntentoPago %s marcado como confirmado", intento.id)

            return Response({"mensaje": "✅ Comprobante aprobado"})

        elif action == 'rechazar':
            comprobante.valido = False
            comprobante.save(update_fields=["valido"])
            logger.debug("[RECHAZAR] Comprobante %s marcado como inválido", comprobante.id)

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
                turno.save()

                logger.debug("[RECHAZAR] Turno %s liberado correctamente", turno.id)

            return Response({"mensaje": "❌ Comprobante rechazado y turno liberado"})

        logger.warning("[PATCH] Acción inválida: '%s'", action)
        return Response({"error": "Acción no válida. Usa 'aprobar' o 'rechazar'."}, status=400)


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
