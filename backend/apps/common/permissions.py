# apps/common/permissions.py

from rest_framework import permissions


class EsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        """Grant access only to authenticated super admin users.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.

        Returns:
            bool: ``True`` if the user is authenticated and is ``super_admin``.
        """
        return request.user.is_authenticated and request.user.tipo_usuario == 'super_admin'


class EsAdminDeSuCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        """Check if the user is an authenticated admin for their client.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.

        Returns:
            bool: ``True`` if the user is authenticated ``admin_cliente``.
        """
        user = request.user
        return user.is_authenticated and user.tipo_usuario == 'admin_cliente'

    def has_object_permission(self, request, view, obj):
        """Authorize only if the object's client matches the user's client.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.
            obj (Any): The object being accessed.

        Returns:
            bool: ``True`` if the object's ``cliente`` equals the user's ``cliente``.
        """
        cliente_obj = getattr(obj, 'cliente', None)
        return cliente_obj and cliente_obj == request.user.cliente


class EsPrestador(permissions.BasePermission):
    """
    Permite acceso a un prestador que accede a su propio perfil y datos.
    """
    def has_permission(self, request, view):
        """Allow access to authenticated "empleado_cliente" users.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.

        Returns:
            bool: ``True`` if user is authenticated and ``empleado_cliente``.
        """
        return request.user.is_authenticated and request.user.tipo_usuario == 'empleado_cliente'

    def has_object_permission(self, request, view, obj):
        """Grant access when the object belongs to the requesting user.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.
            obj (Any): The object being accessed.

        Returns:
            bool: ``True`` if the object has a ``user`` attribute equal to the request user.
        """
        return hasattr(obj, 'user') and obj.user == request.user


class EsDelMismoCliente(permissions.BasePermission):
    """
    Permite acceso si el objeto pertenece al mismo cliente que el usuario autenticado.
    """
    def has_object_permission(self, request, view, obj):
        """Authorize if the object belongs to the same client as the user.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.
            obj (Any): The object being accessed.

        Returns:
            bool: ``True`` if the object's client matches the user's client.
        """
        cliente_obj = getattr(obj, 'cliente', None)
        return request.user.is_authenticated and cliente_obj == request.user.cliente



class SoloLecturaUsuariosFinalesYEmpleados(permissions.BasePermission):
    """
    - Permite acceso GET a cualquier usuario autenticado (incluso usuario_final o prestador).
    - Solo permite escribir si el usuario es super_admin o admin_cliente.
    """

    def has_permission(self, request, view):
        """Allow read access to authenticated users and restrict writes.

        Args:
            request (Request): The current HTTP request.
            view (View): The DRF view attempting access.

        Returns:
            bool: ``True`` for authenticated reads or for writes by super/admin users.
        """
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Solo super_admin y admin_cliente pueden escribir
        return request.user.is_authenticated and (
            request.user.tipo_usuario in {"super_admin", "admin_cliente"}
        )
