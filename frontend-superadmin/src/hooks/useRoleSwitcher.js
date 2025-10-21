// src/hooks/useRoleSwitcher.js
/**
 * Hook para manejar el cambio de roles en el frontend.
 * Permite al usuario cambiar entre diferentes vistas según su rol.
 * Realiza llamadas al backend para cambiar rol y actualiza el estado local.
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth/AuthContext';
export const useRoleSwitcher = () => {
  const { user } = useAuth();
  const [selectedRole, setSelectedRole] = useState(null);
  
  // Debug: Log cuando selectedRole cambia
  useEffect(() => {
    console.log('🔄 [useRoleSwitcher] selectedRole cambió a:', selectedRole);
  }, [selectedRole]);
  const [availableRoles, setAvailableRoles] = useState([]);

  // Inicializar roles disponibles
  useEffect(() => {
    console.log('🔍 [useRoleSwitcher] user:', user);
    console.log('🔍 [useRoleSwitcher] cliente_actual:', user?.cliente_actual);
    console.log('🔍 [useRoleSwitcher] roles:', user?.cliente_actual?.roles);
    
    if (user?.cliente_actual?.roles) {
      const roles = user.cliente_actual.roles;
      console.log('✅ [useRoleSwitcher] Roles encontrados:', roles);
      setAvailableRoles(roles);
      
          // Establecer rol inicial
          if (roles.length > 0) {
            // Usar el rol actual del usuario como rol seleccionado
            const currentRole = user.cliente_actual.rol || roles[0];
            console.log('🎯 [useRoleSwitcher] Estableciendo rol inicial:', currentRole);
            setSelectedRole(currentRole);
        
        // Actualizar título inicial
        const roleLabel = {
          super_admin: 'Super Admin',
          admin_cliente: 'Admin',
          manager: 'Manager',
          coach: 'Coach',
          receptionist: 'Recepcionista',
          empleado_cliente: 'Empleado',
          usuario_final: 'Usuario',
        }[currentRole] || currentRole;
        
        document.title = `Padel App - ${roleLabel}`;
      }
    }
  }, [user]);

  // Obtener información del rol actual
  const getCurrentRoleInfo = useCallback(() => {
    if (!selectedRole || !user?.cliente_actual) return null;
    
    return {
      role: selectedRole,
      isAdmin: selectedRole === 'admin_cliente' || selectedRole === 'super_admin',
      isManager: selectedRole === 'manager',
      isCoach: selectedRole === 'coach',
      isReceptionist: selectedRole === 'receptionist',
      isEmployee: selectedRole === 'empleado_cliente',
      isUser: selectedRole === 'usuario_final',
      isSuperAdmin: selectedRole === 'super_admin',
    };
  }, [selectedRole, user]);

  // Cambiar rol seleccionado
  const changeRole = useCallback(async (newRole) => {
    if (availableRoles.includes(newRole)) {
      try {
        console.log('🔄 Cambiando rol a:', newRole);
        
        // Hacer llamada al backend para cambiar el rol
        const response = await fetch('/api/auth/cambiar-rol/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access')}`,
          },
          body: JSON.stringify({ rol: newRole }),
        });
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.ok) {
          console.log('✅ [useRoleSwitcher] Cambio de rol exitoso:', data);
          console.log('🔄 [useRoleSwitcher] Nuevo rol:', newRole);
          console.log('👤 [useRoleSwitcher] Usuario actualizado:', data.user);
          
          // Actualizar tokens y datos del usuario
          localStorage.setItem('access', data.access);
          localStorage.setItem('refresh', data.refresh);
          localStorage.setItem('user', JSON.stringify(data.user));
          
          console.log('💾 [useRoleSwitcher] Tokens actualizados en localStorage');
          
          // Actualizar header de autorización global
          if (window.axios) {
            window.axios.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;
          }
          
          // Actualizar estado local
          console.log('🔄 [useRoleSwitcher] Actualizando selectedRole a:', newRole);
          setSelectedRole(newRole);
          
          // Cambiar título de la app
          const roleLabel = {
            super_admin: 'Super Admin',
            admin_cliente: 'Admin',
            manager: 'Manager',
            coach: 'Coach',
            receptionist: 'Recepcionista',
            empleado_cliente: 'Empleado',
            usuario_final: 'Usuario',
          }[newRole] || newRole;
          
          document.title = `Padel App - ${roleLabel}`;
          
          // Disparar evento personalizado para que otros componentes reaccionen
          console.log('📡 [useRoleSwitcher] Disparando evento roleChanged');
          window.dispatchEvent(new CustomEvent('roleChanged', { 
            detail: { 
              newRole, 
              roleInfo: getCurrentRoleInfo(),
              user: data.user
            } 
          }));
          
          // Redirigir a la ruta correcta según el rol
          let redirectPath = '/';
          if (newRole === 'admin_cliente' || newRole === 'super_admin') {
            redirectPath = '/admin';
          } else if (newRole === 'usuario_final') {
            redirectPath = '/jugador';  // Dashboard principal para usuarios finales
          } else if (newRole === 'empleado_cliente') {
            redirectPath = '/profesores/turnos';
          }
          
          // Redirigir a la ruta correcta
          console.log('🚀 [useRoleSwitcher] Redirigiendo a:', redirectPath);
          window.location.href = redirectPath;
          
        } else {
          throw new Error(data.error || 'Error al cambiar rol');
        }
        
      } catch (error) {
        console.error('❌ Error al cambiar rol:', error);
        alert(`Error al cambiar rol: ${error.message}`);
      }
    }
  }, [availableRoles, getCurrentRoleInfo]);

  // Verificar si el usuario tiene múltiples roles
  const hasMultipleRoles = availableRoles.length > 1;

  return {
    selectedRole,
    availableRoles,
    hasMultipleRoles,
    changeRole,
    getCurrentRoleInfo,
  };
};

export default useRoleSwitcher;
