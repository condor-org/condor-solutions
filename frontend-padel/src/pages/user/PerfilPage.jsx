import React from "react";
import { Box, Heading, Text, useColorModeValue } from "@chakra-ui/react";

const PerfilPage = () => {
  const bg = useColorModeValue("gray.100", "gray.900");
  const textColor = useColorModeValue("gray.800", "white");

  return (
    <Box maxW="2xl" mx="auto" px={4} py={8} bg={bg} color={textColor}>
      <Heading size="md" textAlign="center" mb={6}>
        Perfil de Usuario
      </Heading>
      <Text textAlign="center" opacity={0.7}>
        Próximamente más funcionalidades.
      </Text>
    </Box>
  );
};

export default PerfilPage;
