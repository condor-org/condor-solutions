// src/components/ui/Input.jsx

import React from 'react';
import { Input as ChakraInput, Text, useColorModeValue } from '@chakra-ui/react';

const Input = ({ label, error, ...props }) => {
  const inputBg = useColorModeValue('white', 'gray.800');
  const inputColor = useColorModeValue('gray.800', 'white');

  return (
    <div style={{ marginBottom: '1rem' }}>
      {label && <Text fontSize="sm" mb={1}>{label}</Text>}
      <ChakraInput bg={inputBg} color={inputColor} {...props} />
      {error && (
        <Text color="red.400" fontSize="xs" mt={1}>
          {error}
        </Text>
      )}
    </div>
  );
};

export default Input;
