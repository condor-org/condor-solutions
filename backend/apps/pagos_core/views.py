# apps/pagos_core/views.py

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.filters import OrderingFilter

from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import PermissionDenied

from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.pagos_core.models import ComprobantePago
from apps.pagos_core.serializers import ComprobantePagoSerializer, ComprobanteUploadSerializer
from apps.pagos_core.filters import ComprobantePagoFilter
from .models import ConfiguracionPago
from .serializers import ConfiguracionPagoSerializer


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
        if usuario.is_staff:
            return ComprobantePago.objects.all()
        return ComprobantePago.objects.filter(turno__usuario=usuario)

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
        try:
            comprobante = ComprobanteService.download_comprobante(
                comprobante_id=int(pk),
                usuario=request.user
            )
            return FileResponse(
                comprobante.archivo.open("rb"),
                as_attachment=True,
                filename=comprobante.archivo.name
            )
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)


class ComprobanteAprobarRechazarView(APIView):
    permission_classes = [IsAdminUser]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, pk, action):
        try:
            comprobante = ComprobantePago.objects.get(pk=pk)
        except ComprobantePago.DoesNotExist:
            return Response({"error": "No encontrado"}, status=404)

        turno = comprobante.turno

        if action == 'aprobar':
            comprobante.valido = True
            comprobante.save(update_fields=["valido"])
            return Response({"mensaje": "✅ Comprobante aprobado"})

        elif action == 'rechazar':
            comprobante.valido = False
            comprobante.save(update_fields=["valido"])

            if turno:
                turno.usuario = None
                turno.estado = 'pendiente'
                turno.save(update_fields=["usuario", "estado"])

            return Response({"mensaje": "❌ Comprobante rechazado y turno liberado"})

        else:
            return Response({"error": "Acción no válida. Usa 'aprobar' o 'rechazar'."}, status=400)


# --- CAMBIO ACÁ ---
from rest_framework.permissions import BasePermission, SAFE_METHODS

class ConfiguracionPagoPermission(BasePermission):
    """
    Permitir GET a cualquier autenticado, pero solo admin puede PUT/PATCH.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class ConfiguracionPagoView(RetrieveUpdateAPIView):
    queryset = ConfiguracionPago.objects.all()
    serializer_class = ConfiguracionPagoSerializer
    permission_classes = [ConfiguracionPagoPermission]
    authentication_classes = [JWTAuthentication]

    def get_object(self):
        obj, created = ConfiguracionPago.objects.get_or_create(
            id=1,
            defaults={
                'destinatario': 'Padel Club SRL',
                'cbu': '0000000000000000000000',
                'alias': '',
                'monto_esperado': 0,
                'tiempo_maximo_minutos': 60,
            }
        )
        return obj


class PagosPendientesCountView(APIView):
    permission_classes = [IsAdminUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        count = ComprobantePago.objects.filter(valido=False).count()
        return Response({"count": count})
