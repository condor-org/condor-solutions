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
      p={{ base: 4, md: 6 }}
      rounded="md"
      textAlign="center"
      boxShadow="2xl"
      color={color || defaultColor}
      maxW={maxW}
      minW={minW}
      mx="auto"
    >
      {icon && (
        <Box mb={3} color={iconColor || defaultIconColor} display="inline-block">
          <Icon as={icon} boxSize={8} />
        </Box>
      )}
      <Text fontSize={{ base: 'md', md: 'lg' }} fontWeight="semibold" mb={1}>
        {title}
      </Text>
      <Text fontSize={{ base: '2xl', md: '3xl' }} fontWeight="bold">
        {value}
      </Text>
    </Box>
  );
};

export default SummaryCard;
