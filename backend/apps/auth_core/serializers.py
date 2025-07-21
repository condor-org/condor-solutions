# apps/auth_core/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    username = serializers.CharField(required=False, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_blank=True)
    nombre = serializers.CharField(required=True)
    apellido = serializers.CharField(required=True)

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
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data["tipo_usuario"] = "jugador"

        if not validated_data.get("username"):
            base_username = validated_data["email"].split("@")[0]
            validated_data["username"] = base_username

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        logger.info(f"[USUARIO REGISTRADO] ID={user.id} Email={user.email}")

        return user


class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password]  # 🔒 Validación agregada
    )

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
            "password",
        )
        read_only_fields = ["id", "username"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = User(**validated_data)
        if password:
            instance.set_password(password)
        else:
            instance.set_unusable_password()
        instance.save()

        logger.info(f"[USUARIO CREADO ADMIN] ID={instance.id} Email={instance.email}")

        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()

        logger.info(f"[USUARIO ACTUALIZADO] ID={instance.id} Email={instance.email}")

        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["tipo_usuario"] = user.tipo_usuario
        token["email"] = user.email
        return token

    def validate(self, attrs):
        email = attrs.get("email") or attrs.get("username")
        logger.debug(f"[LOGIN ATTEMPT] Intento login con email={email}")

        try:
            data = super().validate(attrs)
            logger.info(f"[LOGIN SUCCESS] Usuario ID={self.user.id} email={self.user.email}")

        except Exception as e:
            logger.warning(f"[LOGIN FAILED] Email={email} — Exception en super().validate(): {str(e)}", exc_info=True)
            raise e

        logger.debug(f"[TOKEN PAYLOAD] {data}")

        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "telefono": self.user.telefono,
            "tipo_usuario": self.user.tipo_usuario,
        }
        return data
