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
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_usuario in ['admin_cliente', 'super_admin']

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tipo_usuario == 'super_admin':
            return True

        cliente_id_user = getattr(user, 'cliente_id', None)

        # Si el objeto tiene cliente_id directo
        if hasattr(obj, 'cliente_id'):
            return obj.cliente_id == cliente_id_user

        # Si el objeto tiene cliente como FK (caso usuarios)
        if hasattr(obj, 'cliente'):
            return getattr(obj.cliente, 'id', None) == cliente_id_user

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