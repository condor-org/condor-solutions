// src/components/layout/RoleBasedContent.jsx
import React from 'react';
import { Box, Text, Badge, VStack, HStack } from '@chakra-ui/react';
import { useRoleSwitcher } from '../../hooks/useRoleSwitcher';

/**
 * Componente de ejemplo que muestra contenido diferente según el rol seleccionado
 * Este es un ejemplo de cómo usar el hook useRoleSwitcher en otros componentes
 */
const RoleBasedContent = ({ children }) => {
  const { selectedRole, getCurrentRoleInfo } = useRoleSwitcher();
  const roleInfo = getCurrentRoleInfo();

  if (!roleInfo) {
    return <Box>No hay información de rol disponible</Box>;
  }

  return (
    <VStack spacing={4} align="stretch">
      {/* Indicador de rol actual */}
      <Box p={3} bg="blue.50" borderRadius="md" border="1px solid" borderColor="blue.200">
        <HStack justify="space-between">
          <Text fontSize="sm" fontWeight="medium">
            Vista actual:
          </Text>
          <Badge colorScheme="blue" variant="solid">
            {selectedRole}
          </Badge>
        </HStack>
      </Box>

      {/* Contenido específico por rol */}
      {roleInfo.isSuperAdmin && (
        <Box p={3} bg="purple.50" borderRadius="md">
          <Text fontSize="sm" color="purple.700">
            🔧 Vista de Super Admin - Acceso total al sistema
          </Text>
        </Box>
      )}

      {roleInfo.isAdmin && (
        <Box p={3} bg="blue.50" borderRadius="md">
          <Text fontSize="sm" color="blue.700">
            👑 Vista de Admin - Gestión del cliente
          </Text>
        </Box>
      )}

      {roleInfo.isManager && (
        <Box p={3} bg="green.50" borderRadius="md">
          <Text fontSize="sm" color="green.700">
            📊 Vista de Manager - Gestión de equipos
          </Text>
        </Box>
      )}

      {roleInfo.isCoach && (
        <Box p={3} bg="orange.50" borderRadius="md">
          <Text fontSize="sm" color="orange.700">
            🏆 Vista de Coach - Gestión de entrenamientos
          </Text>
        </Box>
      )}

      {roleInfo.isReceptionist && (
        <Box p={3} bg="teal.50" borderRadius="md">
          <Text fontSize="sm" color="teal.700">
            🏢 Vista de Recepcionista - Atención al cliente
          </Text>
        </Box>
      )}

      {roleInfo.isEmployee && (
        <Box p={3} bg="cyan.50" borderRadius="md">
          <Text fontSize="sm" color="cyan.700">
            👨‍💼 Vista de Empleado - Funciones operativas
          </Text>
        </Box>
      )}

      {roleInfo.isUser && (
        <Box p={3} bg="gray.50" borderRadius="md">
          <Text fontSize="sm" color="gray.700">
            👤 Vista de Usuario - Acceso básico
          </Text>
        </Box>
      )}

      {/* Contenido principal */}
      <Box>
        {children}
      </Box>
    </VStack>
  );
};

export default RoleBasedContent;
