# apps/turnos_padel/urls.py

from rest_framework.routers import DefaultRouter
from .views import (
    SedePadelViewSet,
    ConfiguracionSedePadelViewSet,
    TipoClasePadelViewSet,
    AbonoMesViewSet,
    TipoAbonoPadelViewSet,
)

# Router DRF que expone los endpoints principales de la app de Padel.
# Cada ViewSet gestiona un recurso específico (sede, configuraciones, clases, abonos, etc.).
router = DefaultRouter()

# ---- Endpoints públicos de la app ----
router.register(r'sedes', SedePadelViewSet, basename='sedes-padel')  
# Gestión de sedes de pádel (lugares físicos habilitados)

router.register(r'configuracion', ConfiguracionSedePadelViewSet, basename='configuracion-padel')  
# Configuraciones específicas por sede (ej. alias, CBU, reglas de reserva)

router.register(r'tipos-clase', TipoClasePadelViewSet, basename='tipos-clase-padel')  
# Catálogo de tipos de clases (individual, 2 personas, grupales, etc.)

router.register(r'abonos', AbonoMesViewSet, basename='abonomes')  
# Gestión de abonos mensuales: creación, reserva y renovación

router.register(r'tipos-abono', TipoAbonoPadelViewSet, basename='tipos-abono-padel')  
# Tipología de abonos disponibles (ej. mensual, trimestral, etc.)

# URLs finales expuestas al router.
urlpatterns = router.urls
