# apps/auth_core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    MiPerfilView, UsuarioViewSet,
    OAuthStateView, OAuthCallbackView, OnboardView, IssueInviteView,
    CambiarRolView,
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path("yo/", MiPerfilView.as_view(), name="yo"),
    path("cambiar-rol/", CambiarRolView.as_view(), name="cambiar_rol"),
    path("oauth/state/", OAuthStateView.as_view(), name="oauth_state"),
    path("oauth/callback/", OAuthCallbackView.as_view(), name="oauth_callback"),
    path("oauth/onboard/", OnboardView.as_view(), name="onboard"),
    path("oauth/invite/issue/", IssueInviteView.as_view(), name="invite_issue"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # <- SIEMPRE
    path("", include(router.urls)),
]