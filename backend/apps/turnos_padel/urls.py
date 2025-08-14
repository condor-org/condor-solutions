# apps/turnos_padel/urls.py
from rest_framework.routers import DefaultRouter
from .views import SedePadelViewSet, ConfiguracionSedePadelViewSet, TipoClasePadelViewSet, AbonoMesViewSet

router = DefaultRouter()
router.register(r'sedes', SedePadelViewSet, basename='sedes-padel')
router.register(r'configuracion', ConfiguracionSedePadelViewSet, basename='configuracion-padel')
router.register(r'tipos-clase', TipoClasePadelViewSet, basename='tipos-clase-padel')
router.register(r'abonos', AbonoMesViewSet, basename='abonomes')

urlpatterns = router.urls
