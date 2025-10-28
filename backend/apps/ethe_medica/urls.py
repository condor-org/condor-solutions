# apps/ethe_medica/urls.py

from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    MedicoViewSet,
    PacienteViewSet,
    ResultadoTestViewSet,
    EstablecimientoViewSet,
    CentroAtencionViewSet,
    JerarquiaCentroViewSet,
    ProtocoloSeguimientoViewSet,
    SeguimientoPacienteViewSet,
    DashboardView,
    ReservarTurnoView,
    DashboardMedicoC1View,
    DashboardMedicoC2View,
    DashboardMedicoC3View,
    DashboardEstablecimientoView,
    DashboardMinistroView,
    EstablecimientosMinistroView,
    CrearAdminEstablecimientoView,
    AsignarAdminEstablecimientoView,
    CentrosDisponiblesView,
    CentrosSuperioresView,
    ReservarTurnoDerivacionView
)

# Router DRF que expone los endpoints principales de la app ETHE
router = DefaultRouter()

# ---- Endpoints de gestión ----
router.register(r'medicos', MedicoViewSet, basename='medicos-ethe')
router.register(r'pacientes', PacienteViewSet, basename='pacientes-ethe')
router.register(r'tests', ResultadoTestViewSet, basename='tests-ethe')
router.register(r'establecimientos', EstablecimientoViewSet, basename='establecimientos-ethe')
router.register(r'centros', CentroAtencionViewSet, basename='centros-ethe')
router.register(r'jerarquias', JerarquiaCentroViewSet, basename='jerarquias-ethe')
router.register(r'protocolos', ProtocoloSeguimientoViewSet, basename='protocolos-ethe')
router.register(r'seguimientos', SeguimientoPacienteViewSet, basename='seguimientos-ethe')

# Endpoints custom
urlpatterns = [
    path('dashboard/estadisticas-generales/', DashboardView.as_view(), name='dashboard-general'),
    path('dashboard/medico-c1/', DashboardMedicoC1View.as_view(), name='dashboard-medico-c1'),
    path('dashboard/medico-m1/', DashboardMedicoC1View.as_view(), name='dashboard-medico-m1'),  # Alias para compatibilidad
    path('dashboard/medico-c2/', DashboardMedicoC2View.as_view(), name='dashboard-medico-c2'),
    path('dashboard/medico-m2/', DashboardMedicoC2View.as_view(), name='dashboard-medico-m2'),  # Alias para compatibilidad
    path('dashboard/medico-c3/', DashboardMedicoC3View.as_view(), name='dashboard-medico-c3'),
    path('dashboard/medico-m3/', DashboardMedicoC3View.as_view(), name='dashboard-medico-m3'),  # Alias para compatibilidad
    path('dashboard/establecimiento/', DashboardEstablecimientoView.as_view(), name='dashboard-establecimiento'),
    path('dashboard/ministro/', DashboardMinistroView.as_view(), name='dashboard-ministro'),
    path('turnos/reservar/', ReservarTurnoView.as_view(), name='reservar-turno'),
    
    # Gestión de establecimientos para admin ministro
    path('ministro/establecimientos/', EstablecimientosMinistroView.as_view(), name='establecimientos-ministro'),
    path('ministro/crear-admin-establecimiento/', CrearAdminEstablecimientoView.as_view(), name='crear-admin-establecimiento'),
    path('ministro/asignar-admin-establecimiento/<int:establecimiento_id>/', AsignarAdminEstablecimientoView.as_view(), name='asignar-admin-establecimiento'),
    
    # Endpoint para derivación de pacientes
    path('centros-disponibles/', CentrosDisponiblesView.as_view(), name='centros-disponibles'),
    path('derivacion/centros-superiores/', CentrosSuperioresView.as_view(), name='centros-superiores'),
    path('derivacion/reservar-turno/', ReservarTurnoDerivacionView.as_view(), name='reservar-turno-derivacion'),
] + router.urls
