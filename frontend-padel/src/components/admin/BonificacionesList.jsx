// src/components/admin/BonificacionesList.jsx

import React, { useState, useEffect } from 'react';
import {
  VStack, Text, Flex, IconButton, Badge, Spinner, useColorModeValue,
  Box, HStack, Divider, useBreakpointValue
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import { useCardColors, useMutedText } from '../theme/tokens';
import { axiosAuth } from '../../utils/axiosAuth';
import { toast } from 'react-toastify';
import Button from '../ui/Button';

const BonificacionesList = ({ usuarioId, accessToken, logout, onRefresh }) => {
  const [bonificaciones, setBonificaciones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [eliminando, setEliminando] = useState(null);
  
  const card = useCardColors();
  const mutedText = useMutedText();
  const hoverBg = useColorModeValue("gray.50", "gray.600");
  
  const isMobile = useBreakpointValue({ base: true, md: false });
  const buttonSize = useBreakpointValue({ base: "sm", md: "md" });

  useEffect(() => {
    if (usuarioId && accessToken) {
      fetchBonificaciones();
    }
  }, [usuarioId, accessToken]);

  const fetchBonificaciones = async () => {
    setLoading(true);
    try {
      const response = await axiosAuth(accessToken, logout).get(
        `/turnos/bonificados/usuario/${usuarioId}/`
      );
      setBonificaciones(response.data || []);
    } catch (error) {
      console.error("Error cargando bonificaciones:", error);
      toast.error("Error cargando bonificaciones");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (bonificacionId, motivo) => {
    if (!window.confirm(`¿Eliminar esta bonificación?\nMotivo: ${motivo}`)) return;
    
    setEliminando(bonificacionId);
    try {
      await axiosAuth(accessToken, logout).delete(
        `/turnos/bonificaciones/${bonificacionId}/`,
        { motivo: "Eliminada por administrador" }
      );
      toast.success("Bonificación eliminada");
      fetchBonificaciones();
      if (onRefresh) onRefresh();
    } catch (error) {
      console.error("Error eliminando bonificación:", error);
      toast.error("Error eliminando bonificación");
    } finally {
      setEliminando(null);
    }
  };

  const formatFecha = (fecha) => {
    return new Date(fecha).toLocaleDateString('es-AR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getTipoLabel = (tipo) => {
    const labels = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };
    return labels[tipo] || tipo;
  };

  const getEstadoColor = (usado, validoHasta) => {
    if (usado) return "red";
    if (validoHasta && new Date(validoHasta) < new Date()) return "orange";
    return "green";
  };

  const getEstadoText = (usado, validoHasta) => {
    if (usado) return "Usado";
    if (validoHasta && new Date(validoHasta) < new Date()) return "Vencido";
    return "Activo";
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
          🎁 Bonificaciones Asignadas
        </Text>
        <Text fontSize="sm" color={mutedText}>
          {bonificaciones.length} bonificación{bonificaciones.length !== 1 ? 'es' : ''}
        </Text>
      </Flex>

      {bonificaciones.length === 0 ? (
        <Box
          p={6}
          bg={card.bg}
          borderRadius="md"
          borderWidth="1px"
          borderStyle="dashed"
          textAlign="center"
        >
          <Text color={mutedText}>No hay bonificaciones asignadas</Text>
        </Box>
      ) : (
        <VStack spacing={3} align="stretch">
          {bonificaciones.map((bono) => (
            <Box
              key={bono.id}
              p={4}
              bg={card.bg}
              borderRadius="md"
              borderWidth="1px"
              borderColor="gray.200"
              _hover={{ bg: hoverBg }}
              transition="background-color 0.2s ease"
            >
              <VStack align="stretch" spacing={3}>
                <Flex justify="space-between" align="start" wrap="wrap" gap={2}>
                  <VStack align="start" spacing={2} flex="1" minW={0}>
                    <HStack spacing={2} wrap="wrap" align="center">
                      <Text fontWeight="bold" fontSize="md">
                        {getTipoLabel(bono.tipo_turno)}
                      </Text>
                      <Badge
                        colorScheme={getEstadoColor(bono.usado, bono.valido_hasta)}
                        size="sm"
                      >
                        {getEstadoText(bono.usado, bono.valido_hasta)}
                      </Badge>
                    </HStack>
                    <Text fontSize="sm" color={mutedText}>
                      <Text as="span" fontWeight="semibold">Motivo:</Text> {bono.motivo}
                    </Text>
                    <Text fontSize="sm" color={mutedText}>
                      <Text as="span" fontWeight="semibold">Valor:</Text> <Text as="span" color="green.600" fontWeight="semibold">${bono.valor ? Number(bono.valor).toLocaleString('es-AR') : '0'}</Text>
                    </Text>
                  </VStack>
                  
                  <IconButton
                    icon={<DeleteIcon />}
                    size={buttonSize}
                    colorScheme="red"
                    variant="ghost"
                    onClick={() => handleDelete(bono.id, bono.motivo)}
                    isLoading={eliminando === bono.id}
                    isDisabled={bono.usado}
                    aria-label="Eliminar bonificación"
                    flexShrink={0}
                  />
                </Flex>

                <Divider />

                <HStack justify="space-between" wrap="wrap" gap={2}>
                  <VStack align="start" spacing={1}>
                    <Text fontSize="xs" color={mutedText}>
                      Creado: {formatFecha(bono.fecha_creacion)}
                    </Text>
                    {bono.valido_hasta && (
                      <Text fontSize="xs" color={mutedText}>
                        Válido hasta: {formatFecha(bono.valido_hasta)}
                      </Text>
                    )}
                  </VStack>
                  
                  {bono.valor && (
                    <Text fontSize="sm" fontWeight="medium" color="green.500">
                      ${Number(bono.valor).toLocaleString('es-AR')}
                    </Text>
                  )}
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      )}
    </VStack>
  );
};

export default BonificacionesList;
