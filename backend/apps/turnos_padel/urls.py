# apps/turnos_padel/urls.py
from rest_framework.routers import DefaultRouter
from .views import SedePadelViewSet, ConfiguracionSedePadelViewSet, TipoClasePadelViewSet

router = DefaultRouter()
router.register(r'sedes', SedePadelViewSet, basename='sedes-padel')
router.register(r'configuracion', ConfiguracionSedePadelViewSet, basename='configuracion-padel')
router.register(r'tipos-clase', TipoClasePadelViewSet, basename='tipos-clase-padel')

urlpatterns = router.urls
