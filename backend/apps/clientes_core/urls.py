from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.clientes_core.views import ClienteViewSet, tenant_config

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='clientes')

urlpatterns = [
    path('tenant/config/', tenant_config, name='tenant-config'),
] + router.urls
