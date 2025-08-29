// src/components/ui/Card.jsx
import React from "react";
import { Box, Text, useColorModeValue, Icon as ChakraIcon } from "@chakra-ui/react";

const Card = ({ title, value, icon: IconComp }) => {
  const bg = useColorModeValue('white', 'gray.800');
  const color = useColorModeValue('gray.800', 'white');
  const iconColor = useColorModeValue('blue.500', 'blue.400');

  return (
    <Box
      bg={bg}
      p={{ base: 4, md: 4 }}
      rounded="md"
      textAlign="center"
      boxShadow={{ base: 'md', md: '2xl' }}
      color={color}
      // ✅ móvil ocupa todo el ancho disponible; respeta límites
      w={{ base: '100%', sm: 'auto' }}
      maxW={{ base: '100%', sm: '300px' }}
      mx={{ base: 0, sm: 'auto' }}
      minW={{ base: 0, sm: '220px' }}
      // Permite truncados internos si el contenedor es chico
      minH={0}
    >
      {IconComp && (
        <Box mb={{ base: 2, md: 3 }} color={iconColor} display="inline-block">
          <ChakraIcon as={IconComp} boxSize={{ base: 7, md: 8 }} />
        </Box>
      )}
      <Text fontSize={{ base: 'md', md: 'lg' }} fontWeight="semibold" mb={{ base: 1, md: 1 }}>
        {title}
      </Text>
      <Text fontSize={{ base: 'xl', md: '2xl' }} fontWeight="bold">
        {value}
      </Text>
    </Box>
  );
};

export default Card;
