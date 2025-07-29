# apps/auth_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class RegistroSerializer(LoggedModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
            "nombre",
            "apellido",
            "telefono",
            "tipo_usuario",
            "cliente",
        )
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")

        # 🚫 Forzar siempre a usuario_final y eliminar cliente
        validated_data["tipo_usuario"] = "usuario_final"
        validated_data.pop("cliente", None)

        if not validated_data.get("username"):
            base_username = validated_data["email"].split("@")[0]
            validated_data["username"] = base_username

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        logger.info(f"[USUARIO REGISTRADO] ID={user.id} Email={user.email}")
        return user


class UsuarioSerializer(LoggedModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "nombre",
            "apellido",
            "telefono",
            "is_active",
            "is_staff",
            "tipo_usuario",
            "cliente",
            "password",
        )
        read_only_fields = ["id", "username"]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_request = request.user

            # 🔒 Seguridad: si es admin_cliente, forzamos su propio cliente
            if user_request.tipo_usuario == 'admin_cliente':
                validated_data['cliente'] = user_request.cliente

        password = validated_data.pop("password", None)
        instance = User(**validated_data)
        if password:
            instance.set_password(password)
        else:
            instance.set_unusable_password()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["tipo_usuario"] = user.tipo_usuario
        token["email"] = user.email
        token["cliente_id"] = str(user.cliente_id) if user.cliente_id else None
        return token

    def validate(self, attrs):
        email = attrs.get("email") or attrs.get("username")
        logger.debug(f"[LOGIN ATTEMPT] Intento login con email={email}")

        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "telefono": self.user.telefono,
            "tipo_usuario": self.user.tipo_usuario,
            "cliente_id": self.user.cliente_id,
        }
        return data
