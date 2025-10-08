import React from "react";
import { Box, Heading, Text, Button, useColorModeValue } from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";

const NotFoundPage = () => {
  const navigate = useNavigate();
  const bg = useColorModeValue("gray.100", "gray.900");
  const textColor = useColorModeValue("gray.800", "white");

  return (
    <Box minH="100vh" bg={bg} color={textColor} display="flex" flexDirection="column" alignItems="center" justifyContent="center" px={4}>
      <Heading size="2xl" mb={4}>404</Heading>
      <Text fontSize="lg" mb={6}>Página no encontrada</Text>
      <Button colorScheme="blue" onClick={() => navigate("/")}>
        Volver al inicio
      </Button>
    </Box>
  );
};

export default NotFoundPage;
