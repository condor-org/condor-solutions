// src/pages/auth/LoginPage.jsx
import React, { useContext, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { AuthContext } from "../../auth/AuthContext";
import { toast } from "react-toastify";
import { Box, Heading, Text, Divider, useColorModeValue } from "@chakra-ui/react";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import { startGoogleLogin } from "../../auth/oauthClient";

const LoginPage = () => {
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();

  const formBg = useColorModeValue("white", "gray.900");
  const textColor = useColorModeValue("gray.800", "white");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await login(email, password); // tu flujo actual
      toast.success("Inicio de sesión exitoso");
    } catch (err) {
      toast.error("Credenciales inválidas");
      setError("Credenciales inválidas");
    }
  };

  const handleGoogle = async () => {
    try {
      // host: necesario para que tu BE firme state con el host correcto
      const host = window.location.hostname; // ej: padel.cnd-ia.com
      // returnTo: si venías de una ruta protegida y te redirigieron al login
      const from = (location.state && location.state.from) || "/";
      await startGoogleLogin({ host, returnTo: from });
    } catch (e) {
      console.error("[OAuth] startGoogleLogin failed", e); // LOG sin PII
      toast.error("No pudimos iniciar el login con Google");
    }
  };

  return (
    <Box maxW="md" mx="auto" px={4} py={8}>
      <Heading size="md" textAlign="center" mb={6} color={textColor}>
        Iniciar Sesión
      </Heading>

      <Box as="form" onSubmit={handleSubmit} bg={formBg} p={6} rounded="md" shadow="md" color={textColor}>
        <Input
          label="Correo electrónico"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Input
          label="Contraseña"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <Button type="submit" width="full" mt={4}>
          Ingresar
        </Button>

        <Divider my={4} />

        <Button variant="outline" width="full" onClick={handleGoogle}>
          Continuar con Google
        </Button>

        {error && (
          <Text color="red.400" fontSize="sm" mt={3} textAlign="center">
            {error}
          </Text>
        )}
      </Box>
    </Box>
  );
};

export default LoginPage;
