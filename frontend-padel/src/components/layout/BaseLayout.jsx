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
        {/* Indicador distintivo para identificar frontend de padel */}
        <div style={{
          position: 'fixed',
          top: '10px',
          right: '10px',
          background: '#F44336',
          color: 'white',
          padding: '5px 10px',
          borderRadius: '5px',
          fontSize: '12px',
          fontWeight: 'bold',
          zIndex: 9999,
          fontFamily: 'monospace'
        }}>
          🎾 PADEL
        </div>
        <AppRoutes />
      </AuthProvider>
    </Router>
  </ChakraProvider>
);

export default BaseLayout;
