// shared-auth/LoginButton.js
// Componente de botón de login

import React from 'react';
import { Button } from '@chakra-ui/react';
import oauthClient from './oauthClient';

const LoginButton = ({ children = 'Iniciar Sesión', ...props }) => {
  const handleLogin = () => {
    oauthClient.initiateLogin();
  };

  return (
    <Button onClick={handleLogin} {...props}>
      {children}
    </Button>
  );
};

export default LoginButton;
