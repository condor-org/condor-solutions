// src/components/ui/Input.jsx
import React from 'react';
import { Input as ChakraInput, Text, useColorModeValue, FormControl, FormLabel } from '@chakra-ui/react';

const Input = ({ label, error, size = { base: 'md', md: 'md' }, ...props }) => {
  const inputBg = useColorModeValue('white', 'gray.800');
  const inputColor = useColorModeValue('gray.800', 'white');

  return (
    <FormControl mb={4} w="100%" minW={0}>
      {label && (
        <FormLabel m={0} mb={1}>
          <Text fontSize={{ base: 'sm', md: 'sm' }} noOfLines={2} wordBreak="break-word">
            {label}
          </Text>
        </FormLabel>
      )}
      <ChakraInput
        bg={inputBg}
        color={inputColor}
        size={size}
        w="100%"
        minW={0}
        {...props}
      />
      {error && (
        <Text color="red.400" fontSize={{ base: 'xs', md: 'xs' }} mt={1} wordBreak="break-word">
          {error}
        </Text>
      )}
    </FormControl>
  );
};

export default Input;
