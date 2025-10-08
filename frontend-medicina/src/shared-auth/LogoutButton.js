// shared-auth/LogoutButton.js
// Componente de botón de logout

import React from 'react';
import { Button } from '@chakra-ui/react';
import useAuth from './useAuth';

const LogoutButton = ({ children = 'Cerrar Sesión', ...props }) => {
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <Button onClick={handleLogout} {...props}>
      {children}
    </Button>
  );
};

export default LogoutButton;
