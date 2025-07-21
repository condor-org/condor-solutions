# apps/auth_core/views.py

from rest_framework.generics import CreateAPIView
from .serializers import RegistroSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework import viewsets, permissions, filters
from .models import Usuario

import logging
logger = logging.getLogger(__name__)


User = get_user_model()

class RegistroView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistroSerializer
    permission_classes = []  # Público

class MiPerfilView(APIView):
    queryset = User.objects.none()
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "telefono": user.telefono,
            "tipo_usuario": user.tipo_usuario,
        })

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        logger.debug(f"[TOKEN REQUEST] Datos recibidos: {request.data}")
        return super().post(request, *args, **kwargs)

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all().order_by("id")
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'email', 'tipo_usuario']
