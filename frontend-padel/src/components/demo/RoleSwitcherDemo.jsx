// src/components/demo/RoleSwitcherDemo.jsx
import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';
import { useRoleSwitcher } from '../../hooks/useRoleSwitcher';
import RoleBasedContent from '../layout/RoleBasedContent';
import RoleIndicator from '../layout/RoleIndicator';

/**
 * Componente de demostración del sistema de roles
 * Muestra cómo funciona el selector de roles y el contenido basado en roles
 */
const RoleSwitcherDemo = () => {
  const { selectedRole, availableRoles, hasMultipleRoles, changeRole, getCurrentRoleInfo } = useRoleSwitcher();
  const roleInfo = getCurrentRoleInfo();
  
  const bg = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  if (!hasMultipleRoles) {
    return (
      <Box p={6} bg={bg} borderRadius="md" border="1px solid" borderColor={borderColor}>
        <Text fontSize="lg" fontWeight="bold" mb={4}>
          Sistema de Selector de Roles
        </Text>
        <Text color="gray.600">
          Este usuario no tiene múltiples roles. El selector no se mostrará en la navbar.
        </Text>
        <Text fontSize="sm" color="gray.500" mt={2}>
          Para probar el selector, el usuario debe tener más de un rol en el mismo cliente.
        </Text>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <Box p={6} bg={bg} borderRadius="md" border="1px solid" borderColor={borderColor}>
        <Text fontSize="lg" fontWeight="bold" mb={4}>
          🎭 Sistema de Selector de Roles
        </Text>
        
        <VStack spacing={4} align="stretch">
          <HStack justify="space-between">
            <Text fontWeight="medium">Rol actual:</Text>
            <Badge colorScheme="blue" variant="solid">
              {selectedRole}
            </Badge>
          </HStack>
          
          <HStack justify="space-between">
            <Text fontWeight="medium">Roles disponibles:</Text>
            <HStack spacing={2}>
              {availableRoles.map((role) => (
                <Badge
                  key={role}
                  colorScheme={role === selectedRole ? 'blue' : 'gray'}
                  variant={role === selectedRole ? 'solid' : 'outline'}
                >
                  {role}
                </Badge>
              ))}
            </HStack>
          </HStack>
          
          <Divider />
          
          <Text fontSize="sm" color="gray.600">
            💡 <strong>Tip:</strong> Usa el selector en la navbar para cambiar entre roles.
            Cada rol tiene una vista diferente con permisos específicos.
          </Text>
        </VStack>
      </Box>

      <RoleBasedContent>
        <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor={borderColor}>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            Contenido Principal
          </Text>
          <Text fontSize="sm" color="gray.600">
            Este contenido se muestra independientemente del rol seleccionado.
            Los elementos específicos por rol se muestran arriba.
          </Text>
        </Box>
      </RoleBasedContent>

      {/* Indicador de rol que reacciona a los cambios */}
      <RoleIndicator showDetails={true} />

      <Box p={4} bg="blue.50" borderRadius="md" border="1px solid" borderColor="blue.200">
        <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={2}>
          🔧 Información Técnica
        </Text>
        <VStack spacing={2} align="stretch" fontSize="xs" color="blue.600">
          <Text>• Hook: <code>useRoleSwitcher()</code></Text>
          <Text>• Componente: <code>RoleSwitcher</code></Text>
          <Text>• Ubicación: Navbar (solo si hasMultipleRoles = true)</Text>
          <Text>• Responsive: Mobile/Desktop</Text>
          <Text>• Accesibilidad: Navegación por teclado</Text>
        </VStack>
      </Box>
    </VStack>
  );
};

export default RoleSwitcherDemo;
