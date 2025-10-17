# apps/auth_core/permissions.py

from rest_framework import permissions


class EsSuperAdmin(permissions.BasePermission):
    """
    Permite acceso solo a SuperAdmins.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_usuario == 'super_admin'


class EsAdminCliente(permissions.BasePermission):
    """
    Permite acceso a usuarios admin_cliente y super_admin.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_usuario in ['admin_cliente', 'super_admin']


class EsAdminDelMismoCliente(permissions.BasePermission):
    """
    Permite acceso si el usuario es admin_cliente (limitado a su cliente)
    o super_admin (acceso total).
    Usa el rol actual del JWT en lugar del tipo_usuario del modelo.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        
        # Super admin siempre tiene acceso
        if user.is_super_admin:
            return True
        
        # Para otros usuarios, verificar el rol actual del JWT
        from .utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        return rol_actual in ['admin_cliente', 'super_admin']

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_super_admin:
            return True

        # Para admin_cliente, verificar que el objeto pertenezca a su cliente
        cliente_actual = getattr(request, 'cliente_actual', None)
        if not cliente_actual:
            return False

        # Si el objeto tiene cliente_id directo
        if hasattr(obj, 'cliente_id'):
            return obj.cliente_id == cliente_actual.id

        # Si el objeto tiene cliente como FK (caso usuarios)
        if hasattr(obj, 'cliente'):
            return getattr(obj.cliente, 'id', None) == cliente_actual.id

        # Por defecto, denegar
        return False


class EsAdminClienteORechaza(permissions.BasePermission):
    """
    Permite acceso solo a:
    - super_admin (control total)
    - admin_cliente pero solo usuarios de su mismo cliente
    """
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and (
            user.tipo_usuario in ['super_admin', 'admin_cliente']
        )