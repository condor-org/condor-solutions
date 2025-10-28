import React from 'react';
import { Box, Flex, Spinner, useColorModeValue } from '@chakra-ui/react';
import ETHENavbar from './ETHENavbar';

const ETHELayout = ({ children, loading = false }) => {
  const bg = useColorModeValue('gray.50', 'gray.900');
  
  console.log('🏗️ ETHELayout: Componente montado');
  console.log('🏗️ ETHELayout: Loading:', loading);
  console.log('🏗️ ETHELayout: Children:', children);
  
  if (loading) {
    console.log('⏳ ETHELayout: Mostrando loading...');
    return (
      <Box minH="100vh" bg={bg}>
        <ETHENavbar />
        <Flex
          minH="calc(100vh - 60px)"
          align="center"
          justify="center"
        >
          <Spinner size="xl" />
        </Flex>
      </Box>
    );
  }
  
  console.log('✅ ETHELayout: Renderizando layout completo');
  return (
    <Box minH="100vh" bg={bg}>
      <ETHENavbar />
      <Box as="main" minH="calc(100vh - 60px)">
        {children}
      </Box>
    </Box>
  );
};

export default ETHELayout;
