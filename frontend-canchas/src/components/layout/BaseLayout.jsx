// src/templates/BaseLayout.jsx

import React from 'react';
import { ChakraProvider } from '@chakra-ui/react';
import theme from '../theme';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from '../../auth/AuthContext';
import AppRoutes from '../../router/AppRoutes';

const BaseLayout = () => (
  <ChakraProvider theme={theme}>
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  </ChakraProvider>
);

export default BaseLayout;
