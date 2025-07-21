# condor_core/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from condor_core.views import swagger_ui_view
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from apps.auth_core.views import CustomTokenObtainPairView
schema_view = get_schema_view(
    openapi.Info(
        title="API Condor",
        default_version='v1',
        description="Documentación de la API Condor",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],  # 👈 Evita que Swagger bloquee el esquema
)

urlpatterns = [
    # 🔗 Swagger JSON para el template
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # 🔍 Swagger UI personalizado
    path('docs/', swagger_ui_view, name='swagger-ui'),

    # 🛠 Admin
    path('admin/', admin.site.urls),

    # 🔐 JWT
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 📦 Apps
    path('api/pagos/', include('apps.pagos_core.urls')),
    path('api/turnos/', include('apps.turnos_core.urls')),
    path('api/padel/', include('apps.turnos_padel.urls')),
    path('api/auth/', include('apps.auth_core.urls')),
]
