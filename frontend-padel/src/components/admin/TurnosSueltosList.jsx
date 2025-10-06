// src/components/admin/TurnosSueltosList.jsx

import React, { useState, useEffect } from 'react';
import {
  VStack, Text, Flex, Badge, Spinner, useColorModeValue,
  Box, HStack, useBreakpointValue, IconButton
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import { useCardColors, useMutedText } from '../theme/tokens';
import { axiosAuth } from '../../utils/axiosAuth';
import { toast } from 'react-toastify';

const TurnosSueltosList = ({ usuarioId, accessToken, logout, onCancelar }) => {
  const [turnos, setTurnos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cancelando, setCancelando] = useState(null);
  
  const card = useCardColors();
  const mutedText = useMutedText();
  const hoverBg = useColorModeValue("gray.50", "gray.600");
  
  const isMobile = useBreakpointValue({ base: true, md: false });
  const buttonSize = useBreakpointValue({ base: "sm", md: "md" });

  useEffect(() => {
    if (usuarioId && accessToken) {
      fetchTurnos();
    }
  }, [usuarioId, accessToken]);

  const fetchTurnos = async () => {
    setLoading(true);
    try {
      const response = await axiosAuth(accessToken, logout).get(
        `/turnos/usuario/${usuarioId}/?upcoming=true&solo_sueltos=true`
      );
      setTurnos(response.data || []);
    } catch (error) {
      console.error("Error cargando turnos:", error);
      toast.error("Error cargando turnos");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelar = async (turnoId) => {
    if (!window.confirm("¿Cancelar este turno?")) return;
    
    setCancelando(turnoId);
    try {
      await axiosAuth(accessToken, logout).post(
        `/turnos/cancelar/`,
        { turno_id: turnoId }
      );
      toast.success("Turno cancelado");
      fetchTurnos();
      if (onCancelar) onCancelar();
    } catch (error) {
      console.error("Error cancelando turno:", error);
      toast.error("Error cancelando turno");
    } finally {
      setCancelando(null);
    }
  };

  const formatFecha = (fecha) => {
    return new Date(fecha).toLocaleDateString('es-AR', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatHora = (hora) => {
    return new Date(`2000-01-01T${hora}`).toLocaleTimeString('es-AR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTipoLabel = (tipo) => {
    const labels = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };
    return labels[tipo] || tipo;
  };

  const getEstadoColor = (estado) => {
    switch (estado) {
      case "reservado": return "green";
      case "disponible": return "blue";
      case "cancelado": return "red";
      default: return "gray";
    }
  };

  const isTurnoCancelable = (turno) => {
    // Verificar si el turno es cancelable (más de 6 horas de anticipación)
    const ahora = new Date();
    const fechaTurno = new Date(`${turno.fecha}T${turno.hora}`);
    const diffHoras = (fechaTurno - ahora) / (1000 * 60 * 60);
    return diffHoras >= 6 && turno.estado === "reservado";
  };

  if (loading) {
    return (
      <Flex justify="center" py={8}>
        <Spinner size="lg" color="blue.500" />
      </Flex>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      <Flex align="center" justify="space-between">
        <Text fontWeight="bold" fontSize="lg" color={card.color}>
          🏓 Clases Sueltas
        </Text>
        <Text fontSize="sm" color={mutedText}>
          {turnos.length} turno{turnos.length !== 1 ? 's' : ''}
        </Text>
      </Flex>

      {turnos.length === 0 ? (
        <Box
          p={6}
          bg={card.bg}
          borderRadius="md"
          borderWidth="1px"
          borderStyle="dashed"
          textAlign="center"
        >
          <Text color={mutedText}>No hay clases sueltas reservadas</Text>
        </Box>
      ) : (
        <VStack spacing={3} align="stretch">
          {turnos.map((turno) => (
            <Box
              key={turno.id}
              p={4}
              bg={card.bg}
              borderRadius="md"
              borderWidth="1px"
              borderColor="gray.200"
              _hover={{ bg: hoverBg }}
              transition="background-color 0.2s ease"
            >
              <Flex justify="space-between" align="start" wrap="wrap" gap={2}>
                <VStack align="start" spacing={2} flex="1" minW={0}>
                  <HStack spacing={2} wrap="wrap">
                    <Text fontWeight="bold" fontSize="md">
                      {formatFecha(turno.fecha)} - {formatHora(turno.hora)}
                    </Text>
                    <Badge
                      colorScheme={getEstadoColor(turno.estado)}
                      size="sm"
                    >
                      {turno.estado}
                    </Badge>
                  </HStack>
                  
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" color={mutedText}>
                      📍 {turno.lugar?.nombre || "Sede no disponible"}
                    </Text>
                    <Text fontSize="sm" color={mutedText}>
                      🎾 {getTipoLabel(turno.tipo_turno)}
                    </Text>
                    {turno.prestador_nombre && (
                      <Text fontSize="sm" color={mutedText}>
                        👨‍🏫 {turno.prestador_nombre}
                      </Text>
                    )}
                  </VStack>

                  {!isTurnoCancelable(turno) && turno.estado === "reservado" && (
                    <Box
                      p={2}
                      bg="orange.50"
                      borderRadius="sm"
                      borderWidth="1px"
                      borderColor="orange.200"
                    >
                      <Text fontSize="xs" color="orange.700">
                        ⚠️ No cancelable (menos de 6 horas de anticipación)
                      </Text>
                    </Box>
                  )}
                </VStack>
                
                {isTurnoCancelable(turno) && (
                  <IconButton
                    icon={<DeleteIcon />}
                    size={buttonSize}
                    colorScheme="red"
                    variant="ghost"
                    onClick={() => handleCancelar(turno.id)}
                    isLoading={cancelando === turno.id}
                    aria-label="Cancelar turno"
                    flexShrink={0}
                  />
                )}
              </Flex>
            </Box>
          ))}
        </VStack>
      )}
    </VStack>
  );
};

export default TurnosSueltosList;
