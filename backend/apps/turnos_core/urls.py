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
    path("prestador/mio/", prestador_actual),
    path("", include(router.urls)),
    
]
