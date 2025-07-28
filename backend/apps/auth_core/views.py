# apps/auth_core/views.py

from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import viewsets, filters
from django.contrib.auth import get_user_model

from .serializers import RegistroSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer
from .models import Usuario

from apps.common.permissions import EsSuperAdmin, EsAdminDeSuCliente

import logging
logger = logging.getLogger(__name__)

User = get_user_model()


class RegistroView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistroSerializer
    permission_classes = []  # Público


class MiPerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        logger.debug(f"[YO VIEW] Petición recibida. user.is_authenticated={user.is_authenticated}")
        logger.debug(f"[YO VIEW] user.id={user.id}, email={user.email} si autenticado.")
        logger.debug(f"[YO VIEW] user.token={getattr(user, 'auth_token', 'no_token')}")

        data = {
            "id": user.id,
            "email": user.email,
            "telefono": user.telefono,
            "tipo_usuario": user.tipo_usuario,
            "cliente_id": user.cliente_id,
        }

        logger.debug(f"[YO VIEW] Respondiendo datos: {data}")

        return Response(data)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        logger.debug(f"[TOKEN REQUEST] Datos recibidos: {request.data}")
        return super().post(request, *args, **kwargs)


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'email', 'tipo_usuario']

    def get_queryset(self):
        user = self.request.user

        if user.tipo_usuario == 'super_admin':
            return Usuario.objects.all()

        if user.tipo_usuario == 'admin_cliente' and user.cliente:
            return Usuario.objects.filter(cliente=user.cliente)

        return Usuario.objects.none()
