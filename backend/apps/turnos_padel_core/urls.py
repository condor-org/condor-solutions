# apps/turnos_padel_core/urls.py

from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    ProfesorViewSet,
    ProfesorBloqueoViewSet,
    GenerarTurnosView,
    ProfesoresDisponiblesView,  # <-- IMPORTANTE: importá la nueva view
)

# Routers principales
router = routers.DefaultRouter()
router.register(r'profesores', ProfesorViewSet, basename='profesores')

# Routers anidados para bloqueos
profesores_router = routers.NestedDefaultRouter(router, r'profesores', lookup='profesor')
profesores_router.register(r'bloqueos', ProfesorBloqueoViewSet, basename='profesor-bloqueos')

urlpatterns = [
    path('generar-turnos/', GenerarTurnosView.as_view(), name='generar-turnos'),
    path('profesores-disponibles/', ProfesoresDisponiblesView.as_view(), name='profesores-disponibles'),
    path('', include(router.urls)),
    path('', include(profesores_router.urls)),
]
