# apps/auth_core/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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

        # Si querés forzar tipo_usuario solo durante registro:
        validated_data["tipo_usuario"] = "jugador"

        if not validated_data.get("username"):
            base_username = validated_data["email"].split("@")[0]
            validated_data["username"] = base_username

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "nombre",       # Campos propios
            "apellido",     # Campos propios
            "telefono",
            "is_active",
            "is_staff",
            "tipo_usuario",
        )
        read_only_fields = ["id", "username"]

    def update(self, instance, validated_data):
        # Permite actualizar todos los campos indicados:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
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
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "telefono": self.user.telefono,
            "tipo_usuario": self.user.tipo_usuario,
        }
        return data
