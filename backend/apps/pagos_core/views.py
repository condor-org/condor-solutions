# apps/pagos_core/views.py

from rest_framework import status, serializers
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
from apps.pagos_core.serializers import (
    ComprobantePagoSerializer,
    ComprobanteUploadSerializer,
    ComprobanteAbonoUploadSerializer,
)
from apps.pagos_core.filters import ComprobantePagoFilter

from apps.common.permissions import EsAdminDeSuCliente, EsSuperAdmin

from django.db import transaction

from apps.turnos_padel.models import AbonoMes
from apps.turnos_core.models import Turno, TurnoBonificado
from apps.turnos_padel.services.abonos import confirmar_y_reservar_abono

from decimal import Decimal, InvalidOperation
from apps.turnos_padel.serializers import AbonoMesSerializer
from apps.turnos_core.services.bonificaciones import bonificaciones_vigentes

from django.db.models import Exists, OuterRef
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


class ComprobanteView(ListCreateAPIView):
    """
    🔹 Listado y carga de comprobantes de pago de turnos individuales.

    - GET: listado con filtros por cliente/usuario (scope por rol).
    - POST: subida de comprobante (archivo obligatorio, OCR + validaciones).
    - Query param: `solo_preaprobados=1` → filtra por PagoIntento en estado "pre_aprobado".
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ComprobanteUploadSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ComprobantePagoFilter
    ordering_fields = ["created_at", "valido"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return ComprobanteUploadSerializer if self.request.method == "POST" else ComprobantePagoSerializer

    def get_queryset(self):
        usuario = self.request.user
        qs = (
            ComprobantePago.objects
            .select_related("turno", "turno__usuario", "turno__lugar", "cliente")
            .order_by("-created_at")
        )

        # 🔐 Scope por tipo de usuario
        tu = getattr(usuario, "tipo_usuario", None)
        if tu == "super_admin":
            pass
        elif tu == "admin_cliente" and usuario.cliente_id:
            qs = qs.filter(cliente=usuario.cliente)
        elif tu == "empleado_cliente":
            qs = qs.filter(turno__usuario=usuario)
        else:  # usuario_final
            qs = qs.filter(turno__usuario=usuario)

        # 🔎 Extra: solo comprobantes con intento "pre_aprobado"
        flag = self.request.query_params.get("solo_preaprobados", "").lower() in ("1", "true", "t", "yes")
        if flag:
            ct = ContentType.objects.get_for_model(ComprobantePago)
            intentos_pre = PagoIntento.objects.filter(
                content_type=ct,
                object_id=OuterRef("pk"),
                estado="pre_aprobado",
            )
            qs = qs.annotate(tiene_preaprobado=Exists(intentos_pre)).filter(tiene_preaprobado=True)
        return qs

    def post(self, request, *args, **kwargs):
        """
        ➜ Subida de comprobante de pago.
        - Valida con `ComprobanteUploadSerializer` (OCR + reglas de negocio).
        - Devuelve mensaje de éxito + datos extraídos.
        """
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
    """
    🔹 Descarga segura de archivos de comprobantes.
    - Valida permisos con ComprobanteService.
    - Devuelve FileResponse binario.
    """
    queryset = ComprobantePago.objects.none()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        logger.debug("Descarga de comprobante %s solicitada por %s (%s)", pk, request.user, getattr(request.user, "tipo_usuario", ""))

        try:
            comprobante = ComprobanteService.download_comprobante(comprobante_id=int(pk), usuario=request.user)
            if not comprobante.archivo or not comprobante.archivo.storage.exists(comprobante.archivo.name):
                logger.error("Archivo no encontrado en storage: %s", comprobante.archivo.name)
                return Response({"error": "Archivo no encontrado en disco"}, status=404)

            return FileResponse(
                comprobante.archivo.open("rb"),
                as_attachment=True,
                filename=comprobante.archivo.name.split("/")[-1]
            )
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)


class ComprobanteAprobarRechazarView(APIView):
    """
    🔹 Aprobación o rechazo de comprobantes (admin/super).

    - PATCH /comprobantes/{id}/aprobar/
    - PATCH /comprobantes/{id}/rechazar/
    - Aplica tanto a `ComprobantePago` (turnos individuales) como a `ComprobanteAbono` (abonos mensuales).
    - Actualiza estados en PagoIntento, Turno/AbonoMes según corresponda.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    @transaction.atomic
    def patch(self, request, pk, action):
        logger.debug("[PATCH] Acción '%s' sobre comprobante ID=%s", action, pk)

        # 1) Comprobante de turno individual
        try:
            comprobante = ComprobantePago.objects.get(pk=pk)
            # ... lógica de aprobar/rechazar, actualiza turno y PagoIntento ...
        except ComprobantePago.DoesNotExist:
            logger.debug("[PATCH] No es ComprobantePago. Probando ComprobanteAbono...")

        # 2) Comprobante de abono mensual
        try:
            comprobante_abono = ComprobanteAbono.objects.select_related("abono_mes").get(pk=pk)
            # ... lógica de aprobar/rechazar, actualiza AbonoMes y libera turnos ...
        except ComprobanteAbono.DoesNotExist:
            return Response({"error": "No encontrado"}, status=404)


class PagosPendientesCountView(APIView):
    """
    🔹 Métrica rápida: cantidad de comprobantes pendientes de validación para el cliente.
    - Solo accesible por admin_cliente/super_admin.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    def get(self, request):
        count = ComprobantePago.objects.filter(cliente=request.user.cliente, valido=False).count()
        return Response({"count": count})


class ComprobanteAbonoView(APIView):
    """
    🔹 Confirmación de abono mensual (usuario final).
    - POST con `abono_mes_id`, bonificaciones y comprobante (si neto > 0).
    - Aplica bonos automáticamente a turnos reservados.
    - Estado final: `pagado` si neto=0; `pendiente_validacion` si requiere comprobante.
    - Limpia abono vacío si falla la validación.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _cleanup_abono_si_corresponde(self, user, abono_id, reason=""):
        """
        🔧 Elimina el AbonoMes si no tiene turnos asignados y ocurrió un fallo en confirmación.
        Evita basura en la BD.
        """
        try:
            with transaction.atomic():
                abono = AbonoMes.objects.filter(id=abono_id, usuario=user).first()
                if abono and abono.turnos_reservados.count() == 0 and abono.turnos_prioridad.count() == 0:
                    logger.info("[abono.cleanup] Eliminando abono %s (motivo: %s)", abono_id, reason)
                    abono.delete()
        except Exception as e:
            logger.warning("[abono.cleanup] No se pudo eliminar abono %s: %s", abono_id, str(e))

    def post(self, request, *args, **kwargs):
        """
        ➜ Flujo de confirmación:
        - Verifica abono y precios.
        - Calcula neto = precio_abono - (bonos * precio_clase).
        - Aplica bonificaciones en orden cronológico.
        - Exige comprobante si neto > 0.
        - Retorna estado del abono + resumen (bonos aplicados, neto, etc).
        """
        abono_id = request.data.get("abono_mes_id")
        if not abono_id:
            raise serializers.ValidationError({"abono_mes_id": "Este campo es obligatorio."})

        # ... lógica de cálculo, aplicación de bonos y confirmación ...
