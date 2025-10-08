// shared-auth/AuthContext.js
// Contexto de autenticación compartido

import React, { createContext, useContext } from 'react';

const AuthContext = createContext({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  login: () => {},
  logout: () => {},
  refreshToken: () => {},
});

export default AuthContext;

// Hook para usar el contexto
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
