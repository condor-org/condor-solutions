// src/components/ui/Button.jsx

import React from 'react';
import { Button as ChakraButton } from '@chakra-ui/react';

const Button = ({ variant = 'primary', children, ...props }) => {
  const variants = {
    primary: {
      bg: 'blue.600',
      color: 'white',
      _hover: { bg: 'blue.700' },
      _active: { bg: 'blue.800' },
      _focus: { boxShadow: 'outline' },
    },
    secondary: {
      bg: 'gray.600',
      color: 'white',
      _hover: { bg: 'gray.700' },
      _active: { bg: 'gray.800' },
      _focus: { boxShadow: 'outline' },
    },
    danger: {
      bg: 'red.600',
      color: 'white',
      _hover: { bg: 'red.700' },
      _active: { bg: 'red.800' },
      _focus: { boxShadow: 'outline' },
    },
  };

  return (
    <ChakraButton
      {...props}
      {...variants[variant]}
      fontWeight="semibold"
      rounded="md"
      transition="background-color 0.2s ease"
    >
      {children}
    </ChakraButton>
  );
};

export default Button;
