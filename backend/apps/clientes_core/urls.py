from rest_framework.routers import DefaultRouter
from apps.clientes_core.views import ClienteViewSet

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='clientes')

urlpatterns = router.urls
