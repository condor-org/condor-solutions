import React from 'react';
import { Box, VStack, HStack, Text, Badge, Button } from '@chakra-ui/react';
import { FaHospital, FaMapMarkerAlt } from 'react-icons/fa';
import CategoriaBadge from './CategoriaBadge';

const CentroCard = ({ centro, onSelect, selected }) => {
  return (
    <Box
      p={{ base: 3, md: 4 }}
      borderWidth="2px"
      borderRadius={{ base: "md", md: "lg" }}
      borderColor={selected ? "blue.500" : "gray.200"}
      bg={selected ? "blue.50" : "white"}
      cursor="pointer"
      onClick={onSelect}
      _hover={{ 
        shadow: "md", 
        borderColor: "blue.300" 
      }}
      transition="all 0.2s"
    >
      <VStack align="stretch" spacing={3}>
        <HStack>
          <FaHospital color={selected ? "#4299E1" : "#718096"} />
          <Text 
            fontWeight="bold" 
            fontSize={{ base: "sm", md: "md" }}
            color={selected ? "blue.700" : "gray.800"}
          >
            {centro.nombre_centro}
          </Text>
        </HStack>
        
        <HStack spacing={1} flexWrap="wrap">
          {centro.categorias.map(cat => (
            <CategoriaBadge key={cat} categoria={cat} size="sm" />
          ))}
        </HStack>
        
        <HStack fontSize={{ base: "xs", md: "sm" }} color="gray.600">
          <FaMapMarkerAlt />
          <Text>{centro.establecimiento_nombre}</Text>
        </HStack>
        
        {selected && (
          <Badge colorScheme="blue" fontSize="xs">
            Seleccionado
          </Badge>
        )}
      </VStack>
    </Box>
  );
};

export default CentroCard;
