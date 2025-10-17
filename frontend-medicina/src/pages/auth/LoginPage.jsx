// src/pages/auth/LoginPage.jsx
import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Box, Heading, Text, VStack, Spinner } from "@chakra-ui/react";
import Button from "../../components/ui/Button";
import { startGoogleLogin } from "../../auth/oauthClient";

const GoogleIcon = (props) => (
  <Box as="span" display="inline-block" mr={2} {...props}>
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      {/* Amarillo */}
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3C33.9 32.6 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.7 1.1 7.8 2.9l5.7-5.7C33.7 6.1 29.1 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20c10 0 19.1-7.3 19.1-20 0-1.2-.1-2.3-.5-3.5z"
      />
      {/* Rojo */}
      <path
        fill="#FF3D00"
        d="M6.3 14.7l6.6 4.8C14.7 16.2 18.9 12 24 12c3 0 5.7 1.1 7.8 2.9l5.7-5.7C33.7 6.1 29.1 4 24 4 16.1 4 9.3 8.5 6.3 14.7z"
      />
      {/* Verde 1 */}
      <path
        fill="#4CAF50"
        d="M24 44c5.2 0 9.9-1.9 13.5-5.1l-6.2-5.1C29.3 36 26.8 37 24 37c-5.3 0-9.9-3.4-11.6-8.1l-6.6 5.1C9 39.4 15.9 44 24 44z"
      />
      {/* Verde 2 (antes era azul) */}
      <path
        fill="#34A853"
        d="M43.6 20.5H42V20H24v8h11.3c-1.4 4-5.3 7-11.3 7-5.3 0-9.9-3.4-11.6-8.1l-6.6 5.1C9 39.4 15.9 44 24 44c10 0 19.1-7.3 19.1-20 0-1.2-.1-2.3-.5-3.5z"
      />
    </svg>
  </Box>
);

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
          <Box>
            <Heading size="lg" color="gray.800">
              ¡Bienvenido a Canchas!
            </Heading>
            <Text color="green.600" fontSize="sm" fontWeight="medium" mt={1}>
              🏟️ Distrito Canchas - Puerto 8081
            </Text>
          </Box>
          <Text color="gray.600" fontSize="sm">
            Accedé a tu cuenta para continuar.
          </Text>

          <Button
            onClick={handleGoogle}
            width="full"
            size="lg"
            isLoading={isLoading}
            loadingText="Conectando..."
            isDisabled={isLoading}
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            {!isLoading && <GoogleIcon />}
            <span>{isLoading ? "Conectando..." : "Ingresar con Google"}</span>
          </Button>

          <Text fontSize="xs" color="gray.500">
            Al continuar, aceptás nuestros Términos y la Política de Privacidad.
          </Text>
        </VStack>
      </Box>
    </Box>
  );
};

export default LoginPage;
