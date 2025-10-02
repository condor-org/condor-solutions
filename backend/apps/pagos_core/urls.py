# apps/pagos_core/urls.py
from django.urls import path
from apps.pagos_core.views import (
    ComprobanteView,
    ComprobanteDownloadView,
    ComprobanteAprobarRechazarView,
    ComprobanteAprobarLoteView,
    PagosPendientesCountView,
    ComprobanteAbonoView,
)

# Endpoints principales del módulo de pagos:
# Manejan comprobantes (upload/descarga/aprobación), configuración de pagos y métricas.
urlpatterns = [
    path("comprobantes/", ComprobanteView.as_view(), name="comprobante-view"),
    # ➜ Subida/listado de comprobantes de pago asociados a turnos individuales.

    path("comprobantes/<int:pk>/descargar/", ComprobanteDownloadView.as_view(), name="comprobante-download"),
    # ➜ Permite descargar el archivo original del comprobante almacenado.

    path("comprobantes/<int:pk>/<str:action>/", ComprobanteAprobarRechazarView.as_view(), name="comprobante-aprobar-rechazar"),
    # ➜ Acciones de backoffice: aprobar o rechazar un comprobante (valida/actualiza estado de reserva/pago).

    path("comprobantes/aprobar-lote/", ComprobanteAprobarLoteView.as_view(), name="comprobante-aprobar-lote"),
    # ➜ Aprobación en lote de múltiples comprobantes.

    path("pendientes/", PagosPendientesCountView.as_view(), name="pagos-pendientes"),
    # ➜ Devuelve métricas: cantidad de comprobantes pendientes de revisión para admins.

    path("comprobantes-abono/", ComprobanteAbonoView.as_view(), name="comprobante-abono-upload"),
    # ➜ Upload de comprobantes específicamente para abonos mensuales (flujo separado de turnos).
]
