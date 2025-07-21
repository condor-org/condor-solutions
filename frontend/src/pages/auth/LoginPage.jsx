// src/pages/auth/LoginPage.jsx

import React, { useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../../auth/AuthContext";
import { toast } from "react-toastify";
import { Box, Heading, Text, useColorModeValue } from "@chakra-ui/react";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";

const LoginPage = () => {
  const { login, user } = useContext(AuthContext);
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      await login(email, password);
      toast.success("Inicio de sesión exitoso");
      // Redirección gestionada por useEffect
    } catch {
      toast.error("Credenciales inválidas");
      setError("Credenciales inválidas");
    }
  };

  useEffect(() => {
    if (user?.tipo_usuario) {
      const destino = user.tipo_usuario === "admin" ? "/admin" : "/jugador";
      navigate(destino);
    }
  }, [user, navigate]);

  const formBg = useColorModeValue("white", "gray.900");
  const textColor = useColorModeValue("gray.800", "white");

  return (
    <Box maxW="md" mx="auto" px={4} py={8}>
      <Heading size="md" textAlign="center" mb={6} color={textColor}>
        Iniciar Sesión
      </Heading>

      <Box
        as="form"
        onSubmit={handleSubmit}
        bg={formBg}
        p={6}
        rounded="md"
        shadow="md"
        color={textColor}
      >
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

        <Button
          variant="outline"
          width="full"
          mt={2}
          onClick={() => navigate("/registro")}
        >
          Registrarse
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
