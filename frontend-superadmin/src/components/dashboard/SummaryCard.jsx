// src/components/dashboard/SummaryCard.jsx

import React from 'react';
import { Box, Text, useColorModeValue, Icon } from '@chakra-ui/react';

const SummaryCard = ({
  title,
  value,
  icon,
  bg,
  color,
  iconColor,
  maxW = '300px',
  minW = '220px',
}) => {
  const defaultBg = useColorModeValue('white', 'gray.800');
  const defaultColor = useColorModeValue('gray.800', 'white');
  const defaultIconColor = useColorModeValue('blue.500', 'blue.400');

  return (
    <Box
      bg={bg || defaultBg}
      // padding y sombras adaptadas
      p={{ base: 4, md: 6 }}
      rounded="md"
      textAlign="center"
      boxShadow={{ base: 'md', md: '2xl' }}
      color={color || defaultColor}
      // ancho fluido en mobile, límites a partir de sm
      w={{ base: '100%', sm: 'auto' }}
      maxW={{ base: '100%', sm: maxW }}
      minW={{ base: '0', sm: minW }}
      mx={{ base: 0, sm: 'auto' }}
    >
      {icon && (
        <Box mb={{ base: 2, md: 3 }} color={iconColor || defaultIconColor} display="inline-block">
          <Icon as={icon} boxSize={{ base: 6, md: 8 }} />
        </Box>
      )}
      <Text fontSize={{ base: 'sm', md: 'lg' }} fontWeight="semibold" mb={{ base: 1, md: 1 }}>
        {title}
      </Text>
      <Text fontSize={{ base: 'xl', md: '3xl' }} fontWeight="bold">
        {value}
      </Text>
    </Box>
  );
};

export default SummaryCard;
