import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Spinner, Box, Flex } from '@chakra-ui/react';

const ETHERedirect = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  console.log('🔄 ETHERedirect: Componente montado');
  console.log('👤 ETHERedirect: User:', user);
  
  useEffect(() => {
    console.log('🔄 ETHERedirect: useEffect ejecutado');
    console.log('👤 ETHERedirect: User en useEffect:', user);
    console.log('👤 ETHERedirect: User completo:', JSON.stringify(user, null, 2));
    
    if (!user) {
      console.log('❌ ETHERedirect: No hay usuario, redirigiendo a login');
      navigate('/login');
      return;
    }
    
    // Obtener rol del usuario usando la misma estructura que frontend-padel
    const rol = user.cliente_actual?.rol || 'paciente';
    console.log('🎭 ETHERedirect: Rol detectado:', rol);
    console.log('🎭 ETHERedirect: user.cliente_actual:', user.cliente_actual);
    console.log('🎭 ETHERedirect: user.cliente_actual.rol:', user.cliente_actual?.rol);
    
    // Redirigir según el rol del usuario
    switch (rol) {
      case 'medico_m1':
        console.log('🔄 ETHERedirect: Redirigiendo a /medico-m1/dashboard');
        navigate('/medico-m1/dashboard');
        break;
      case 'medico_m2':
        console.log('🔄 ETHERedirect: Redirigiendo a /medico-m2/dashboard');
        navigate('/medico-m2/dashboard');
        break;
      case 'medico_m3':
        console.log('🔄 ETHERedirect: Redirigiendo a /medico-m3/dashboard');
        navigate('/medico-m3/dashboard');
        break;
      case 'admin_ministro_salud':
      case 'admin_ministro':
        console.log('🔄 ETHERedirect: Redirigiendo a /admin-ministro/dashboard');
        navigate('/admin-ministro/dashboard');
        break;
      case 'admin_establecimiento':
        console.log('🔄 ETHERedirect: Redirigiendo a /admin-establecimiento/dashboard');
        navigate('/admin-establecimiento/dashboard');
        break;
      case 'paciente':
        console.log('🔄 ETHERedirect: Redirigiendo a /paciente/dashboard');
        navigate('/paciente/dashboard');
        break;
      default:
        console.warn('⚠️ ETHERedirect: Rol no reconocido:', rol);
        console.log('🔄 ETHERedirect: Redirigiendo a /paciente/dashboard por defecto');
        navigate('/paciente/dashboard');
    }
  }, [user, navigate]);
  
  return (
    <Box minH="100vh" display="flex" alignItems="center" justifyContent="center">
      <Flex direction="column" align="center" spacing={4}>
        <Spinner size="xl" />
        <Box mt={4}>Redirigiendo...</Box>
      </Flex>
    </Box>
  );
};

export default ETHERedirect;
