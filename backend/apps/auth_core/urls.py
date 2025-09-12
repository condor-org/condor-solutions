# apps/auth_core/urls.py
from django.urls import path, include
from .views import (
    RegistroView, MiPerfilView, CustomTokenObtainPairView, UsuarioViewSet,
    OAuthStateView, OAuthCallbackView, OnboardView, IssueInviteView, 
)
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("yo/", MiPerfilView.as_view(), name="yo"),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("oauth/state/", OAuthStateView.as_view(), name="oauth_state"),
    path("oauth/callback/", OAuthCallbackView.as_view(), name="oauth_callback"),
    path("oauth/onboard/", OnboardView.as_view(), name="onboard"),
    path("oauth/invite/issue/", IssueInviteView.as_view(), name="invite_issue"),
    
    path("", include(router.urls)),
]
