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
    
    # Campo para el cliente actual del usuario
    cliente_actual = serializers.SerializerMethodField(read_only=True)
    
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
            "cliente_actual",
        )
        read_only_fields = ["id", "username"]

    # ------- helpers -------
    def _request_user(self):
        return getattr(self.context.get("request"), "user", None)

    def validate_email(self, v):
        v = (v or "").strip().lower()
        if not v:
            raise serializers.ValidationError("Email requerido")
        
        # Verificar si el email ya existe (solo para creación, no para actualización)
        if not self.instance and User.objects.filter(email=v).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email")
        
        return v

    def validate(self, attrs):
        # Obtener request real desde el contexto del serializer
        ctx_request = self.context.get("request")
        if not ctx_request:
            # Sin request en contexto, no aplicar reglas de rol/cliente aquí
            return attrs

        # normalizar email → username
        email = attrs.get("email") or getattr(self.instance, "email", None)
        if email:
            attrs["email"] = email.strip().lower()

        # tipo de usuario permitido
        new_tipo = attrs.get("tipo_usuario", getattr(self.instance, "tipo_usuario", "usuario_final"))
        if new_tipo == "super_admin" and getattr(ctx_request.user, "tipo_usuario", "") != "super_admin":
            raise serializers.ValidationError("No podés asignar super_admin.")

        # Validar que no se pueda asignar is_super_admin
        if attrs.get("is_super_admin", False):
            raise serializers.ValidationError({"is_super_admin": "No se puede asignar is_super_admin a través de este endpoint"})

        # control de cliente según rol y tenant
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(ctx_request)
        cliente_actual = getattr(ctx_request, 'cliente_actual', None)

        # Crear usuario vía API SIEMPRE requiere tenant resuelto: asignar cliente_actual
        if cliente_actual is not None:
            attrs["cliente"] = cliente_actual
        else:
            raise serializers.ValidationError({"cliente": "cliente_actual no resuelto para este host"})

        return attrs

    def create(self, validated_data):
        # Extraer roles si están presentes
        roles = validated_data.pop('roles', [])
        email = validated_data.get('email')
        
        # Verificar si el usuario ya existe por email
        try:
            instance = User.objects.get(email=email)
            logger.info(f"[UsuarioSerializer] Usuario existente encontrado: {email}, actualizando roles")
            
            # Si el usuario existe, solo actualizar roles (no crear duplicado)
            if roles:
                from apps.auth_core.models import UserClient
                cliente = validated_data.get('cliente')
                
                if cliente:
                    # Eliminar roles existentes para este cliente
                    UserClient.objects.filter(usuario=instance, cliente=cliente).delete()
                    logger.info(f"[UsuarioSerializer] Roles existentes eliminados para {instance.email} en cliente {cliente.id}")
                    
                    # Asignar nuevos roles
                    for rol in roles:
                        # Validar que el rol sea válido y no sea super_admin
                        if rol in ['usuario_final', 'admin_cliente', 'empleado_cliente']:
                            UserClient.objects.create(
                                usuario=instance,
                                cliente=cliente,
                                rol=rol,
                                activo=True
                            )
                            logger.info(f"[UsuarioSerializer] Asignado rol '{rol}' al usuario {instance.email} en cliente {cliente.id}")
                        elif rol == 'super_admin':
                            logger.warning(f"[UsuarioSerializer] Intento de asignar rol 'super_admin' al usuario {instance.email} - BLOQUEADO")
                            raise serializers.ValidationError({"roles": "No se puede asignar el rol 'super_admin' a través de este endpoint"})
                else:
                    logger.warning(f"[UsuarioSerializer] No se pudo asignar roles porque no hay cliente especificado")
            
            return instance
            
        except User.DoesNotExist:
            # Crear nuevo usuario solo si no existe
            if not validated_data.get("username"):
                validated_data["username"] = validated_data["email"]

            instance = User(**validated_data)
            if hasattr(instance, "set_unusable_password"):
                instance.set_unusable_password()
            try:
                instance.save()
            except ValueError as e:
                # Transformar a error de validación (evita 500)
                raise serializers.ValidationError({"cliente": str(e)})
            logger.info(f"[UsuarioSerializer] Nuevo usuario creado: {email}")
            
            # Asignar roles si se proporcionaron
            if roles:
                from apps.auth_core.models import UserClient
                cliente = validated_data.get('cliente')
                
                if cliente:
                    # Asignar nuevos roles
                    for rol in roles:
                        # Validar que el rol sea válido y no sea super_admin
                        if rol in ['usuario_final', 'admin_cliente', 'empleado_cliente']:
                            UserClient.objects.create(
                                usuario=instance,
                                cliente=cliente,
                                rol=rol,
                                activo=True
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
    
    def get_cliente_actual(self, obj):
        """
        Obtiene el cliente actual del usuario con su rol.
        """
        cliente_actual = obj.cliente_actual
        if not cliente_actual:
            return None
        
        return {
            'id': cliente_actual.cliente.id,
            'nombre': cliente_actual.cliente.nombre,
            'rol': cliente_actual.rol,
            'activo': cliente_actual.activo
        }