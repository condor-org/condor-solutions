import React from 'react';
import { Box, HStack, VStack, Text, Stat, StatLabel, StatNumber } from '@chakra-ui/react';
import { FaUserMd } from 'react-icons/fa';
import CategoriaBadge from './CategoriaBadge';

const ProductividadMedicoCard = ({ medico }) => {
  const getProductividadLabel = () => {
    if (medico.categorias.includes('M1')) return 'Pacientes Ingresados';
    if (medico.categorias.includes('M2')) return 'FIBROSCAN Realizados';
    if (medico.categorias.includes('M3')) return 'Consultas Realizadas';
    return 'Productividad';
  };
  
  const getProductividadValue = () => {
    const stats = medico.estadisticas || {};
    return stats.pacientes_ingresados || 
           stats.fibroscan_realizados || 
           stats.consultas_realizadas || 
           0;
  };
  
  return (
    <Box
      p={{ base: 3, md: 4 }}
      borderWidth="1px"
      borderRadius={{ base: "md", md: "lg" }}
      bg="white"
      shadow="sm"
    >
      <VStack align="stretch" spacing={3}>
        <HStack justify="space-between">
          <HStack>
            <FaUserMd color="#4299E1" size={20} />
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                {medico.user.nombre} {medico.user.apellido}
              </Text>
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                Mat. {medico.matricula}
              </Text>
            </VStack>
          </HStack>
          
          <HStack spacing={1}>
            {medico.categorias.map(cat => (
              <CategoriaBadge key={cat} categoria={cat} size="sm" />
            ))}
          </HStack>
        </HStack>
        
        <Stat>
          <StatLabel fontSize={{ base: "xs", md: "sm" }}>
            {getProductividadLabel()}
          </StatLabel>
          <StatNumber fontSize={{ base: "2xl", md: "3xl" }}>
            {getProductividadValue()}
          </StatNumber>
        </Stat>
      </VStack>
    </Box>
  );
};

export default ProductividadMedicoCard;
