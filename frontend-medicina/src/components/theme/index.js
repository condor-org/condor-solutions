// src/components/theme/index.js

import { extendTheme } from '@chakra-ui/react';
import { mode } from '@chakra-ui/theme-tools';

const colors = {
  brand: {
    primary: '#3182ce',
    secondary: '#2d3748',
    accent: '#38a169',
    danger: '#e53e3e',
  },
  background: {
    light: '#f7fafc',
    dark: '#1a202c',
  },
};

const components = {
  Button: {
    baseStyle: {
      fontWeight: 'semibold',
      borderRadius: 'md',
      transition: 'background-color 0.2s ease',
    },
    variants: {
      solid: (props) => ({
        bg: mode('brand.primary', 'brand.accent')(props),
        color: 'white',
        _hover: { bg: mode('blue.700', 'green.600')(props) },
      }),
      ghost: (props) => ({
        bg: 'transparent',
        color: mode('brand.primary', 'brand.accent')(props),
        _hover: { bg: mode('blue.50', 'green.900')(props) },
      }),
    },
  },
  Input: {
    baseStyle: {
      field: {
        borderRadius: 'md',
        bg: mode('white', 'gray.800'),
        color: mode('gray.800', 'white'),
        _placeholder: {
          color: mode('gray.400', 'gray.500'),
        },
      },
    },
  },
  Modal: {
    baseStyle: (props) => ({
      dialog: {
        bg: mode('white', 'gray.900')(props),
        color: mode('gray.800', 'white')(props),
      },
    }),
  },
};

const theme = extendTheme({
  colors,
  fonts: {
    body: 'Inter, sans-serif',
    heading: 'Inter, sans-serif',
  },
  breakpoints: {
    sm: '30em',
    md: '48em',
    lg: '62em',
    xl: '80em',
  },
  styles: {
    global: (props) => ({
      body: {
        bg: mode('background.light', 'background.dark')(props),
        color: mode('gray.800', 'white')(props),
      },
    }),
  },
  components,
});

export default theme;
