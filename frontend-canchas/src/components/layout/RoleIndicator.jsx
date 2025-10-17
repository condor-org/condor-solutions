// src/components/layout/RoleIndicator.jsx
import React, { useState, useEffect } from 'react';
import {
  Box,
  Text,
  Badge,
  HStack,
  VStack,
  useColorModeValue,
  useBreakpointValue,
} from '@chakra-ui/react';
import { useRoleSwitcher } from '../../hooks/useRoleSwitcher';

const ROLE_ICONS = {
  super_admin: '👑',
  admin_cliente: '⚙️',
  manager: '📊',
  coach: '🏆',
  receptionist: '🏢',
  empleado_cliente: '👨‍💼',
  usuario_final: '👤',
};

const ROLE_COLORS = {
  super_admin: 'purple',
  admin_cliente: 'blue',
  manager: 'green',
  coach: 'orange',
  receptionist: 'teal',
  empleado_cliente: 'cyan',
  usuario_final: 'gray',
};

/**
 * Componente que muestra el rol actual y reacciona a los cambios
 * Se puede usar en cualquier parte de la app para mostrar el estado del rol
 */
const RoleIndicator = ({ showDetails = false }) => {
  const { selectedRole, getCurrentRoleInfo } = useRoleSwitcher();
  const [roleInfo, setRoleInfo] = useState(null);
  
  const bg = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.700', 'gray.200');
  const isMobile = useBreakpointValue({ base: true, md: false });

  // Reaccionar a cambios de rol
  useEffect(() => {
    const handleRoleChange = (event) => {
      const { newRole, roleInfo: newRoleInfo } = event.detail;
      console.log('🎭 RoleIndicator: Rol cambiado a', newRole);
      setRoleInfo(newRoleInfo);
    };

    window.addEventListener('roleChanged', handleRoleChange);
    
    // Establecer estado inicial
    if (selectedRole) {
      setRoleInfo(getCurrentRoleInfo());
    }

    return () => {
      window.removeEventListener('roleChanged', handleRoleChange);
    };
  }, [selectedRole, getCurrentRoleInfo]);

  if (!selectedRole || !roleInfo) {
    return null;
  }

  const roleIcon = ROLE_ICONS[selectedRole] || '👤';
  const roleColor = ROLE_COLORS[selectedRole] || 'gray';

  if (!showDetails) {
    // Vista compacta
    return (
      <HStack spacing={2} px={3} py={1} bg={bg} borderRadius="md" border="1px solid" borderColor={borderColor}>
        <Text fontSize="sm">{roleIcon}</Text>
        <Text fontSize="sm" color={textColor} fontWeight="medium">
          {selectedRole}
        </Text>
        <Badge colorScheme={roleColor} variant="outline" fontSize="xs">
          Activo
        </Badge>
      </HStack>
    );
  }

  // Vista detallada
  return (
    <Box p={4} bg={bg} borderRadius="lg" border="1px solid" borderColor={borderColor}>
      <VStack spacing={3} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="bold" color={textColor}>
            Estado del Rol
          </Text>
          <Badge colorScheme={roleColor} variant="solid" fontSize="sm">
            {roleIcon} {selectedRole}
          </Badge>
        </HStack>
        
        <VStack spacing={2} align="stretch">
          <HStack justify="space-between">
            <Text fontSize="sm" color="gray.600">Es Admin:</Text>
            <Badge colorScheme={roleInfo.isAdmin ? 'green' : 'gray'} variant="outline">
              {roleInfo.isAdmin ? 'Sí' : 'No'}
            </Badge>
          </HStack>
          
          <HStack justify="space-between">
            <Text fontSize="sm" color="gray.600">Es Manager:</Text>
            <Badge colorScheme={roleInfo.isManager ? 'green' : 'gray'} variant="outline">
              {roleInfo.isManager ? 'Sí' : 'No'}
            </Badge>
          </HStack>
          
          <HStack justify="space-between">
            <Text fontSize="sm" color="gray.600">Es Coach:</Text>
            <Badge colorScheme={roleInfo.isCoach ? 'green' : 'gray'} variant="outline">
              {roleInfo.isCoach ? 'Sí' : 'No'}
            </Badge>
          </HStack>
          
          <HStack justify="space-between">
            <Text fontSize="sm" color="gray.600">Es Usuario:</Text>
            <Badge colorScheme={roleInfo.isUser ? 'green' : 'gray'} variant="outline">
              {roleInfo.isUser ? 'Sí' : 'No'}
            </Badge>
          </HStack>
        </VStack>
        
        <Box p={2} bg={`${roleColor}.50`} borderRadius="md">
          <Text fontSize="xs" color={`${roleColor}.700`} textAlign="center">
            💡 Cambia el rol en la navbar para ver diferentes vistas
          </Text>
        </Box>
      </VStack>
    </Box>
  );
};

export default RoleIndicator;
