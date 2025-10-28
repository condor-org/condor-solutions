import React from 'react';
import { 
  VStack, HStack, Box, Text, Circle, 
  useColorModeValue 
} from '@chakra-ui/react';
import { FaArrowRight } from 'react-icons/fa';
import CategoriaBadge from './CategoriaBadge';

const TimelineItem = ({ item, isLast }) => {
  const lineColor = useColorModeValue('gray.300', 'gray.600');
  
  return (
    <HStack 
      align="start" 
      spacing={{ base: 3, md: 4 }}
      position="relative"
    >
      {/* Línea vertical */}
      {!isLast && (
        <Box
          position="absolute"
          left="11px"
          top="40px"
          bottom="-20px"
          width="2px"
          bg={lineColor}
        />
      )}
      
      {/* Círculo */}
      <Circle 
        size={{ base: "24px", md: "28px" }}
        bg="blue.500" 
        color="white"
        fontSize={{ base: "xs", md: "sm" }}
      >
        {item.categoria_nueva}
      </Circle>
      
      {/* Contenido */}
      <Box flex="1" pb={4}>
        <HStack spacing={2} mb={1}>
          <CategoriaBadge categoria={item.categoria_nueva} />
          {item.categoria_anterior && (
            <>
              <FaArrowRight size={12} color="gray" />
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                desde {item.categoria_anterior}
              </Text>
            </>
          )}
        </HStack>
        
        <Text fontSize={{ base: "sm", md: "md" }} color="gray.700">
          {item.motivo}
        </Text>
        
        <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500" mt={1}>
          {new Date(item.fecha_cambio).toLocaleString()}
        </Text>
        
        {item.medico && (
          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
            Por: {item.medico.nombre}
          </Text>
        )}
      </Box>
    </HStack>
  );
};

const PacienteTimeline = ({ historial }) => {
  return (
    <VStack
      align="stretch"
      spacing={0}
      px={{ base: 2, md: 4 }}
      py={{ base: 3, md: 4 }}
    >
      {historial.map((item, index) => (
        <TimelineItem 
          key={item.id} 
          item={item} 
          isLast={index === historial.length - 1}
        />
      ))}
    </VStack>
  );
};

export default PacienteTimeline;
