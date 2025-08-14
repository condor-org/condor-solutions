# apps/pagos_core/urls.py

from django.urls import path
from apps.pagos_core.views import (
    ComprobanteView,
    ComprobanteDownloadView,
    ComprobanteAprobarRechazarView,
    ConfiguracionPagoView,
    PagosPendientesCountView,
    ComprobanteAbonoView,
)

urlpatterns = [
    path("comprobantes/", ComprobanteView.as_view(), name="comprobante-view"),
    path("comprobantes/<int:pk>/descargar/", ComprobanteDownloadView.as_view(), name="comprobante-download"),
    path("comprobantes/<int:pk>/<str:action>/", ComprobanteAprobarRechazarView.as_view(), name="comprobante-aprobar-rechazar"),
    path('configuracion/', ConfiguracionPagoView.as_view(), name='configuracion-pago'),
    path('pendientes/', PagosPendientesCountView.as_view(), name='pagos-pendientes'),
    path("comprobantes-abono/", ComprobanteAbonoView.as_view(), name="comprobante-abono-upload"),
]
