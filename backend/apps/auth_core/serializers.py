# apps/auth_core/serializers.py
from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.contrib.auth import get_user_model
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UsuarioSerializer(LoggedModelSerializer):
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
            "tipo_usuario",
            "cliente",
        )
        read_only_fields = ["id", "username"]

    # ------- helpers -------
    def _request_user(self):
        return getattr(self.context.get("request"), "user", None)

    def validate_email(self, v):
        v = (v or "").strip().lower()
        if not v:
            raise serializers.ValidationError("Email requerido")
        return v

    def validate(self, attrs):
        req = self._request_user()
        if not req:
            return attrs

        # normalizar email → username
        email = attrs.get("email") or getattr(self.instance, "email", None)
        if email:
            attrs["email"] = email.strip().lower()

        # tipo de usuario permitido
        new_tipo = attrs.get("tipo_usuario", getattr(self.instance, "tipo_usuario", "usuario_final"))
        if new_tipo == "super_admin" and getattr(req, "tipo_usuario", "") != "super_admin":
            raise serializers.ValidationError("No podés asignar super_admin.")

        # control de cliente:
        if getattr(req, "tipo_usuario", "") == "admin_cliente":
            # admin_cliente solo puede operar sobre su cliente
            attrs["cliente"] = req.cliente
            # y no puede mover usuarios a otro cliente
        else:
            # super_admin puede setear cliente; el modelo ya impide nulos salvo super_admin
            pass

        return attrs

    def create(self, validated_data):
        # username=email y password inutilizable (sin credenciales)
        if not validated_data.get("username"):
            validated_data["username"] = validated_data["email"]

        instance = User(**validated_data)
        if hasattr(instance, "set_unusable_password"):
            instance.set_unusable_password()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        # si cambian email, reflejar en username
        email = validated_data.get("email")
        if email:
            validated_data["username"] = email

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # nunca setear password aquí
        instance.save()
        return instance