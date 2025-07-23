// src/pages/auth/RegistroPage.jsx

import React, { useState } from "react";
import { Box, Heading, Text, useColorModeValue } from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import axios from "axios";


const RegistroPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [telefono, setTelefono] = useState("");
  const [error, setError] = useState("");

  const navigate = useNavigate();
  const formBg = useColorModeValue("white", "gray.900");
  const textColor = useColorModeValue("gray.800", "white");
  const errorColor = useColorModeValue("red.500", "red.400");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
  
    if (password.length < 8) {
      toast.error("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
  
    try {
      const api = axios.create({
        baseURL: `${process.env.REACT_APP_API_BASE_URL}/api/`,
        headers: { "Content-Type": "application/json" },
      });
  
      const res = await api.post("auth/registro/", {
        email,
        password,
        nombre,
        apellido,
        telefono,
        tipo_usuario: "jugador",
      });
  
      toast.success("Registro exitoso");
      navigate("/login");
    } catch (err) {
      const data = err.response?.data;
      const errorMessage =
        typeof data === "string"
          ? data
          : Object.values(data).flat().join(" | ") || "Error en el registro";
  
      toast.error(errorMessage);
      setError(errorMessage);
    }
  };
  

  return (
    <Box maxW="md" mx="auto" px={4} py={8}>
      <Heading size="md" textAlign="center" mb={6} color={textColor}>
        Registro
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
          label="Nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          required
        />

        <Input
          label="Apellido"
          value={apellido}
          onChange={(e) => setApellido(e.target.value)}
          required
        />

        <Input
          label="Teléfono"
          value={telefono}
          onChange={(e) => setTelefono(e.target.value)}
          required
        />

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
          Registrarse
        </Button>

        {error && (
          <Text color={errorColor} fontSize="sm" mt={3} textAlign="center">
            {error}
          </Text>
        )}
      </Box>
    </Box>
  );
};

export default RegistroPage;
