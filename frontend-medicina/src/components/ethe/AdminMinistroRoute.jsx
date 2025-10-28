import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Box, Text, Spinner, VStack } from '@chakra-ui/react';

const AdminMinistroRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <Box minH="100vh" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Spinner size="xl" />
          <Text>Verificando permisos...</Text>
        </VStack>
      </Box>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  // Verificar si el usuario es admin ministro
  const rol = user?.cliente_actual?.rol;
  const esAdminMinistro = rol === 'admin_ministro_salud' || rol === 'admin_ministro';
  
  if (!esAdminMinistro) {
    return (
      <Box minH="100vh" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Text fontSize="xl" fontWeight="bold" color="red.500">
            Acceso Denegado
          </Text>
          <Text color="gray.600">
            Solo el Ministro de Salud puede acceder a esta funcionalidad.
          </Text>
        </VStack>
      </Box>
    );
  }
  
  return children;
};

export default AdminMinistroRoute;
