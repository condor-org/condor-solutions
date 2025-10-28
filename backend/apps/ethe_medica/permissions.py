# apps/ethe_medica/permissions.py

from rest_framework.permissions import BasePermission
from apps.auth_core.utils import get_rol_actual_del_jwt


class EsMedicoC1(BasePermission):
    """Permiso para médicos C1"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar si tiene relación con Medico
        if not hasattr(request.user, "medico_ethe"):
            return False
        
        return request.user.medico_ethe.tiene_categoria("C1")


class EsMedicoC2(BasePermission):
    """Permiso para médicos C2"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, "medico_ethe"):
            return False
        
        return request.user.medico_ethe.tiene_categoria("C2")


class EsMedicoC3(BasePermission):
    """Permiso para médicos C3"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, "medico_ethe"):
            return False
        
        return request.user.medico_ethe.tiene_categoria("C3")


class EsMedicoCualquiera(BasePermission):
    """Permiso para cualquier médico (M1, M2 o M3)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, "medico_ethe"):
            return False
        
        medico = request.user.medico_ethe
        return medico.tiene_categoria("C1") or medico.tiene_categoria("C2") or medico.tiene_categoria("C3")


class EsPaciente(BasePermission):
    """Permiso para pacientes"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, "paciente_ethe")


class EsAdminEstablecimiento(BasePermission):
    """Permiso para admin de establecimiento"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual == "admin_establecimiento"


class EsAdminMinistroSalud(BasePermission):
    """Permiso para admin ministro de salud"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual == "admin_ministro_salud"


class EsAdminETHE(BasePermission):
    """Permiso para cualquier admin ETHE (establecimiento o ministro)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual in ["admin_establecimiento", "admin_ministro_salud"]


class PuedeVerPacientes(BasePermission):
    """Permiso para ver pacientes (médicos, admins, pacientes propios)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin puede ver todo
        if request.user.is_super_admin:
            return True
        
        # Admins ETHE pueden ver pacientes de su cliente
        rol_actual = get_rol_actual_del_jwt(request)
        if rol_actual in ["admin_establecimiento", "admin_ministro_salud"]:
            return True
        
        # Médicos pueden ver pacientes
        if hasattr(request.user, "medico_ethe"):
            return True
        
        # Pacientes pueden ver solo sus propios datos
        if hasattr(request.user, "paciente_ethe"):
            return True
        
        return False


class PuedeCrearPacientes(BasePermission):
    """Permiso para crear pacientes (solo médicos C1)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Solo médicos C1 pueden crear pacientes
        if hasattr(request.user, "medico_ethe"):
            return request.user.medico_ethe.tiene_categoria("C1")
        
        return False


class PuedeRegistrarTests(BasePermission):
    """Permiso para registrar tests (médicos según tipo de test)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, "medico_ethe"):
            return False
        
        medico = request.user.medico_ethe
        
        # C1 puede registrar POCUS y FIB4
        if request.method == "POST" and "tipo_test" in request.data:
            tipo_test = request.data.get("tipo_test")
            
            if tipo_test == "POCUS" and medico.tiene_categoria("C1"):
                return True
            elif tipo_test == "FIB4" and medico.tiene_categoria("C1"):
                return True
            elif tipo_test == "FIBROSCAN" and medico.tiene_categoria("C2"):
                return True
        
        # Para otros métodos, permitir si es médico
        return medico.tiene_categoria("C1") or medico.tiene_categoria("C2") or medico.tiene_categoria("C3")


class PuedeGestionarCentros(BasePermission):
    """Permiso para gestionar centros (admin ministro)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin puede gestionar todo
        if request.user.is_super_admin:
            return True
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual == "admin_ministro_salud"


class PuedeGestionarMedicos(BasePermission):
    """Permiso para gestionar médicos (admin establecimiento)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin puede gestionar todo
        if request.user.is_super_admin:
            return True
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual == "admin_establecimiento"


class PuedeVerEstadisticas(BasePermission):
    """Permiso para ver estadísticas (admins)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin puede ver todo
        if request.user.is_super_admin:
            return True
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual in ["admin_establecimiento", "admin_ministro_salud"]


class PuedeGestionarAsignaciones(BasePermission):
    """Permiso para gestionar asignaciones de centros (admin ministro)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin puede gestionar todo
        if request.user.is_super_admin:
            return True
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual == "admin_ministro_salud"


class PuedeGestionarProtocolos(BasePermission):
    """Permiso para gestionar protocolos (admin ministro)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin puede gestionar todo
        if request.user.is_super_admin:
            return True
        
        rol_actual = get_rol_actual_del_jwt(request)
        return rol_actual == "admin_ministro_salud"
