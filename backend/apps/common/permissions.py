# apps/common/permissions.py

from rest_framework import permissions


class EsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class EsAdminDeSuCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        from apps.auth_core.utils import get_rol_actual_del_jwt
        user = request.user
        rol_actual = get_rol_actual_del_jwt(request)
        return user.is_authenticated and (rol_actual == 'admin_cliente' or user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        from apps.auth_core.utils import get_rol_actual_del_jwt
        user = request.user
        rol_actual = get_rol_actual_del_jwt(request)
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        if user.is_super_admin:
            return True
            
        if rol_actual == 'admin_cliente' and cliente_actual:
            cliente_obj = getattr(obj, 'cliente', None)
            return cliente_obj and cliente_obj.id == cliente_actual.id
        
        return False


class EsPrestador(permissions.BasePermission):
    """
    Permite acceso a un prestador que accede a su propio perfil y datos.
    """
    def has_permission(self, request, view):
        from apps.auth_core.utils import get_rol_actual_del_jwt
        user = request.user
        rol_actual = get_rol_actual_del_jwt(request)
        return user.is_authenticated and rol_actual == 'empleado_cliente'

    def has_object_permission(self, request, view, obj):
        return hasattr(obj, 'user') and obj.user == request.user


class EsDelMismoCliente(permissions.BasePermission):
    """
    Permite acceso si el objeto pertenece al mismo cliente que el usuario autenticado.
    """
    def has_object_permission(self, request, view, obj):
        from apps.auth_core.utils import get_rol_actual_del_jwt
        user = request.user
        rol_actual = get_rol_actual_del_jwt(request)
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        if not user.is_authenticated:
            return False
            
        if user.is_super_admin:
            return True
            
        if rol_actual == 'admin_cliente' and cliente_actual:
            cliente_obj = getattr(obj, 'cliente', None)
            return cliente_obj and cliente_obj.id == cliente_actual.id
            
        return False



class SoloLecturaUsuariosFinalesYEmpleados(permissions.BasePermission):
    """
    - Permite acceso GET a cualquier usuario autenticado (incluso usuario_final o prestador).
    - Solo permite escribir si el usuario es super_admin o admin_cliente.
    """

    def has_permission(self, request, view):
        from apps.auth_core.utils import get_rol_actual_del_jwt
        user = request.user
        
        if not user.is_authenticated:
            return False
            
        if request.method in permissions.SAFE_METHODS:
            return True

        # Solo super_admin y admin_cliente pueden escribir
        rol_actual = get_rol_actual_del_jwt(request)
        return user.is_super_admin or rol_actual == 'admin_cliente'
