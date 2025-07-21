# apps/auth_core/urls.py

from django.urls import path, include
from .views import RegistroView, MiPerfilView, CustomTokenObtainPairView, UsuarioViewSet
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("yo/", MiPerfilView.as_view(), name="yo"),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),   # <-- CRUD usuarios solo admin
]
