from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.turnos_core.views import (
    TurnoListView,
    TurnoReservaView,
    TurnosDisponiblesView,
    LugarViewSet,
    BloqueoTurnosViewSet,
)

router = DefaultRouter()
router.register(r'sedes', LugarViewSet, basename='sedes')
router.register(r'bloqueos-turnos', BloqueoTurnosViewSet, basename='bloqueos-turnos')

urlpatterns = [
    path("", TurnoListView.as_view(), name="turno-list"),
    path("reservar/", TurnoReservaView.as_view(), name="turno-reserva"),
    path("disponibles/", TurnosDisponiblesView.as_view(), name="turno-disponibles"),
    path("", include(router.urls)),  # Aquí incluís las rutas CRUD para sedes
]
