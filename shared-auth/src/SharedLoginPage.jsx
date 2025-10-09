// src/LoginPage.jsx
import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Box, Heading, Text, VStack } from "@chakra-ui/react";
import { LoginButton } from "./LoginButton";

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogle = async () => {
    try {
      setIsLoading(true);
      const host = window.location.hostname; // subdominio → tenant
      const from = (location.state && location.state.from) || "/";
      const invite = new URLSearchParams(window.location.search).get("invite") || undefined; // ← invite si vino

      // Usar el oauthClient del paquete
      const { startGoogleLogin } = await import('./oauthClient');
      await startGoogleLogin({ host, returnTo: from, invite });
    } catch (e) {
      console.error("[OAuth] startGoogleLogin failed", e);
      setIsLoading(false); // Solo resetear si hay error
    }
  };

  return (
    <Box
      minH="100vh"
      // Fondo azul claro, sobrio
      bgGradient="linear(to-br, blue.50, blue.100)"
      position="relative"
      overflow="hidden"
      display="flex"
      alignItems="center"
      justifyContent="center"
      px={{ base: 4, sm: 6 }}
      py={{ base: 16, md: 24 }}
    >
      {/* Sutiles halos decorativos */}
      <Box
        position="absolute"
        top="-20%"
        right="-10%"
        w="60vw"
        h="60vw"
        bgGradient="radial(circle, rgba(59,130,246,0.18), rgba(59,130,246,0))"
        filter="blur(40px)"
        pointerEvents="none"
      />
      <Box
        position="absolute"
        bottom="-25%"
        left="-15%"
        w="70vw"
        h="70vw"
        bgGradient="radial(circle, rgba(37,99,235,0.12), rgba(37,99,235,0))"
        filter="blur(48px)"
        pointerEvents="none"
      />

      {/* Tarjeta centrada */}
      <Box
        w="100%"
        maxW="md"
        bg="white"
        borderRadius="xl"
        boxShadow="xl"
        px={{ base: 6, sm: 8 }}
        py={{ base: 8, sm: 10 }}
        position="relative"
        zIndex={1}
      >
        <VStack spacing={6} align="stretch" textAlign="center">
          <Heading size="lg" color="gray.800">
            ¡Bienvenido!
          </Heading>
          <Text color="gray.600" fontSize="sm">
            Accedé a tu cuenta para continuar.
          </Text>

          <LoginButton
            onClick={handleGoogle}
            isLoading={isLoading}
            loadingText="Conectando..."
            isDisabled={isLoading}
            width="full"
            size="lg"
          />

          <Text fontSize="xs" color="gray.500">
            Al continuar, aceptás nuestros Términos y la Política de Privacidad.
          </Text>
        </VStack>
      </Box>
    </Box>
  );
};

export default LoginPage;
