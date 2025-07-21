// src/components/ui/Card.jsx

import React from "react";
import { Box, Text, useColorModeValue } from "@chakra-ui/react";

const Card = ({ title, value, icon: Icon }) => {
  const bg = useColorModeValue('white', 'gray.800');
  const color = useColorModeValue('gray.800', 'white');
  const iconColor = useColorModeValue('blue.500', 'blue.400');

  return (
    <Box
      bg={bg}
      p={4}
      rounded="md"
      textAlign="center"
      boxShadow="2xl"
      color={color}
      maxW="300px"
      mx="auto"
      minW="220px"
    >
      {Icon && (
        <Box mb={3} color={iconColor} display="inline-block">
          <Icon size={32} />
        </Box>
      )}
      <Text fontSize="lg" fontWeight="semibold" mb={1}>
        {title}
      </Text>
      <Text fontSize="2xl" fontWeight="bold">
        {value}
      </Text>
    </Box>
  );
};

export default Card;
