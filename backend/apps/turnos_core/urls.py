# apps/turnos_core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.turnos_core.views import (
    TurnoListView,
    TurnoReservaView,
    TurnosDisponiblesView,
    LugarViewSet,
    BloqueoTurnosViewSet,
    PrestadorViewSet,
    DisponibilidadViewSet,
    GenerarTurnosView,
    prestador_actual,
    CrearBonificacionManualView,
    bonificaciones_mias,
    CancelarTurnoView,
    CancelarPorSedeAdminView,
    CancelarPorPrestadorAdminView,
)


router = DefaultRouter()
router.register(r'sedes', LugarViewSet, basename='sedes')
router.register(r'bloqueos-turnos', BloqueoTurnosViewSet, basename='bloqueos-turnos')
router.register(r'prestadores', PrestadorViewSet, basename='prestadores')
router.register(r'disponibilidades', DisponibilidadViewSet, basename='disponibilidades')

urlpatterns = [
    path("", TurnoListView.as_view(), name="turno-list"),
    path("reservar/", TurnoReservaView.as_view(), name="turno-reserva"),
    path("disponibles/", TurnosDisponiblesView.as_view(), name="turno-disponibles"),
    path("generar/", GenerarTurnosView.as_view(), name="generar-turnos"),
    path("bonificaciones/crear-manual/", CrearBonificacionManualView.as_view(), name="crear-bonificacion-manual"),
    path("bonificados/mios/", bonificaciones_mias, name="bonificaciones-mias"),
    path("turnos/bonificados/mios/<int:tipo_clase_id>/", bonificaciones_mias, name="bonificaciones_mias_por_tipo"),
    path("prestador/mio/", prestador_actual),
    path("cancelar/", CancelarTurnoView.as_view(), name="cancelar-turno"),
    path("", include(router.urls)),
    path("admin/cancelar_por_sede/", CancelarPorSedeAdminView.as_view(), name="cancelar-por-sede"),
    path("prestadores/<int:prestador_id>/cancelar_en_rango/", CancelarPorPrestadorAdminView.as_view(), name="cancelar-por-prestador"),

]
