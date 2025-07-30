import React, { useEffect, useState } from "react";
import { Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Spinner, Text } from "@chakra-ui/react";
import { axiosAuth } from "../../utils/axiosAuth";
import { useAuth } from "../../auth/AuthContext";
import { useBodyBg, useCardColors } from "../../components/theme/tokens";

const TurnosReservados = () => {
  const { user, accessToken } = useAuth();
  const [turnos, setTurnos] = useState([]);
  const [loading, setLoading] = useState(true);

  const bg = useBodyBg();
  const card = useCardColors();

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);
    api.get("turnos/")
      .then(res => {
        const data = res.data.results || res.data || [];
        const reservados = data.filter(t => t.estado === "reservado");
        setTurnos(reservados);
      })
      .catch(() => setTurnos([]))
      .finally(() => setLoading(false));
  }, [accessToken]);

  return (
    <Box maxW="4xl" mx="auto" px={4} py={8} bg={bg} color={card.color}>
      <Heading size="md" mb={6} textAlign="center">Turnos Reservados</Heading>
      {loading ? (
        <Spinner mx="auto" display="block" />
      ) : turnos.length === 0 ? (
        <Text textAlign="center">No hay turnos reservados.</Text>
      ) : (
        <Table variant="simple" colorScheme="blue">
          <Thead bg={card.bg}>
            <Tr>
              <Th>Fecha</Th>
              <Th>Hora</Th>
              <Th>Sede</Th>
              <Th>Usuario</Th>
            </Tr>
          </Thead>
          <Tbody>
            {turnos.map(t => (
              <Tr key={t.id} _hover={{ bg: card.bg }}>
                <Td>{t.fecha}</Td>
                <Td>{t.hora}</Td>
                <Td>{t.lugar}</Td>
                <Td>{t.usuario}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </Box>
  );
};

export default TurnosReservados;
