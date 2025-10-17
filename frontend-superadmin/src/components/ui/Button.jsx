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
      // ✅ ajustes suaves para mobile; no cambia el layout en desktop
      px={{ base: 3, md: 4 }}
      h={{ base: 9, md: 10 }}
      fontWeight="semibold"
      rounded="md"
      transition="background-color 0.2s ease"
      // Evita que se achique y deforme texto en contenedores tight
      flexShrink={0}
      // Permite truncado en padres con minW=0
      minW={0}
    >
      {children}
    </ChakraButton>
  );
};

export default Button;
