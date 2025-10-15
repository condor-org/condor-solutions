# apps/auth_core/serializers.py
from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.contrib.auth import get_user_model
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UsuarioSerializer(LoggedModelSerializer):
    # Campo para múltiples roles (solo para escritura)
    roles = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="Lista de roles a asignar al usuario"
    )
    
    # Campo para leer los roles del usuario
    user_roles = serializers.SerializerMethodField(read_only=True)
    
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
            "is_super_admin",
            "roles",
            "user_roles",
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

        # Validar que no se pueda asignar is_super_admin
        if attrs.get("is_super_admin", False):
            raise serializers.ValidationError({"is_super_admin": "No se puede asignar is_super_admin a través de este endpoint"})

        # control de cliente:
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(req)
        cliente_actual = getattr(req, 'cliente_actual', None)
        
        if rol_actual == "admin_cliente" and cliente_actual:
            # admin_cliente solo puede operar sobre su cliente
            attrs["cliente"] = cliente_actual
            # y no puede mover usuarios a otro cliente
        else:
            # super_admin puede setear cliente; el modelo ya impide nulos salvo super_admin
            pass

        return attrs

    def create(self, validated_data):
        # Extraer roles si están presentes
        roles = validated_data.pop('roles', [])
        
        # username=email y password inutilizable (sin credenciales)
        if not validated_data.get("username"):
            validated_data["username"] = validated_data["email"]

        instance = User(**validated_data)
        if hasattr(instance, "set_unusable_password"):
            instance.set_unusable_password()
        instance.save()
        
        # Asignar roles si se proporcionaron
        if roles:
            from apps.auth_core.models import UserClient
            cliente = validated_data.get('cliente')
            
            if cliente:
                for rol in roles:
                    # Validar que el rol sea válido y no sea super_admin
                    if rol in ['usuario_final', 'admin_cliente', 'empleado_cliente']:
                        UserClient.objects.get_or_create(
                            usuario=instance,
                            cliente=cliente,
                            rol=rol,
                            defaults={'activo': True}
                        )
                        logger.info(f"[UsuarioSerializer] Asignado rol '{rol}' al usuario {instance.email} en cliente {cliente.id}")
                    elif rol == 'super_admin':
                        logger.warning(f"[UsuarioSerializer] Intento de asignar rol 'super_admin' al usuario {instance.email} - BLOQUEADO")
                        raise serializers.ValidationError({"roles": "No se puede asignar el rol 'super_admin' a través de este endpoint"})
            else:
                logger.warning(f"[UsuarioSerializer] No se pudo asignar roles porque no hay cliente especificado")
        
        return instance

    def update(self, instance, validated_data):
        # Extraer roles si están presentes
        roles = validated_data.pop('roles', None)
        
        # si cambian email, reflejar en username
        email = validated_data.get("email")
        if email:
            validated_data["username"] = email

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # nunca setear password aquí
        instance.save()
        
        # Actualizar roles si se proporcionaron
        if roles is not None:
            from apps.auth_core.models import UserClient
            cliente = validated_data.get('cliente') or instance.cliente
            
            if cliente:
                # Eliminar roles existentes para este cliente
                UserClient.objects.filter(usuario=instance, cliente=cliente).delete()
                
                # Agregar nuevos roles
                for rol in roles:
                    if rol in ['usuario_final', 'admin_cliente', 'empleado_cliente']:
                        UserClient.objects.create(
                            usuario=instance,
                            cliente=cliente,
                            rol=rol,
                            activo=True
                        )
                        logger.info(f"[UsuarioSerializer] Actualizado rol '{rol}' al usuario {instance.email} en cliente {cliente.id}")
                    elif rol == 'super_admin':
                        logger.warning(f"[UsuarioSerializer] Intento de asignar rol 'super_admin' al usuario {instance.email} - BLOQUEADO")
                        raise serializers.ValidationError({"roles": "No se puede asignar el rol 'super_admin' a través de este endpoint"})
            else:
                logger.warning(f"[UsuarioSerializer] No se pudo actualizar roles porque no hay cliente especificado")
        
        return instance
    
    def get_user_roles(self, obj):
        """
        Obtiene todos los roles del usuario en el cliente actual.
        """
        request = self.context.get('request')
        if not request:
            return []
        
        cliente_actual = getattr(request, 'cliente_actual', None)
        if not cliente_actual:
            return []
        
        if obj.is_super_admin:
            return ['super_admin']
        
        # Obtener todos los roles activos del usuario en el cliente actual
        from apps.auth_core.models import UserClient
        roles = UserClient.objects.filter(
            usuario=obj,
            cliente=cliente_actual,
            activo=True
        ).values_list('rol', flat=True)
        
        return list(roles)