# apps/common/permissions.py

from rest_framework import permissions


class EsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_usuario == 'super_admin'


class EsAdminDeSuCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.tipo_usuario == 'admin_cliente'

    def has_object_permission(self, request, view, obj):
        cliente_obj = getattr(obj, 'cliente', None)
        return cliente_obj and cliente_obj == request.user.cliente


class EsPrestador(permissions.BasePermission):
    """
    Permite acceso a un prestador que accede a su propio perfil y datos.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_usuario == 'empleado_cliente'

    def has_object_permission(self, request, view, obj):
        return hasattr(obj, 'user') and obj.user == request.user


class EsDelMismoCliente(permissions.BasePermission):
    """
    Permite acceso si el objeto pertenece al mismo cliente que el usuario autenticado.
    """
    def has_object_permission(self, request, view, obj):
        cliente_obj = getattr(obj, 'cliente', None)
        return request.user.is_authenticated and cliente_obj == request.user.cliente



class SoloLecturaUsuariosFinalesYEmpleados(permissions.BasePermission):
    """
    - Permite acceso GET a cualquier usuario autenticado (incluso usuario_final o prestador).
    - Solo permite escribir si el usuario es super_admin o admin_cliente.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Solo super_admin y admin_cliente pueden escribir
        return request.user.is_authenticated and (
            request.user.tipo_usuario in {"super_admin", "admin_cliente"}
        )
