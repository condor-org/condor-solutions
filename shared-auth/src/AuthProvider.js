// shared-auth/AuthProvider.js
// Proveedor de autenticación compartido

import React, { useState, useEffect, useCallback } from 'react';
import AuthContext from './AuthContext';
import authService from './authService';

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Verificar autenticación al cargar
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (authService.isAuthenticated()) {
          const userInfo = authService.getUserInfo();
          setUser(userInfo);
          setIsAuthenticated(true);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        authService.clearTokens();
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Función de login
  const login = useCallback((accessToken, refreshToken) => {
    try {
      authService.setTokens(accessToken, refreshToken);
      const userInfo = authService.getUserInfo();
      setUser(userInfo);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }, []);

  // Función de logout
  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  // Función para refrescar token
  const refreshToken = useCallback(async () => {
    try {
      const newToken = await authService.refreshToken();
      const userInfo = authService.getUserInfo();
      setUser(userInfo);
      setIsAuthenticated(true);
      return newToken;
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      throw error;
    }
  }, [logout]);

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
