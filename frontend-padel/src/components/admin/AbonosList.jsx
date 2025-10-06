// src/components/admin/AbonosList.jsx

import React, { useState, useEffect } from 'react';
import {
  VStack, Text, Flex, Badge, Spinner, useColorModeValue,
  Box, HStack, Divider, useBreakpointValue, Collapse, IconButton
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import { useCardColors, useMutedText } from '../theme/tokens';
import { axiosAuth } from '../../utils/axiosAuth';
import { toast } from 'react-toastify';

const AbonosList = ({ usuarioId, accessToken, logout, onRenovar, onCancelar }) => {
  const [abonos, setAbonos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedAbonos, setExpandedAbonos] = useState(new Set());
  
  const card = useCardColors();
  const mutedText = useMutedText();
  const hoverBg = useColorModeValue("gray.50", "gray.600");
  
  const isMobile = useBreakpointValue({ base: true, md: false });
  const buttonSize = useBreakpointValue({ base: "sm", md: "md" });

  useEffect(() => {
    if (usuarioId && accessToken) {
      fetchAbonos();
    }
  }, [usuarioId, accessToken]);

  const fetchAbonos = async () => {
    setLoading(true);
    try {
      const response = await axiosAuth(accessToken, logout).get(
        `/padel/abonos/mios/?usuario_id=${usuarioId}`
      );
      setAbonos(response.data || []);
    } catch (error) {
      console.error("Error cargando abonos:", error);
      toast.error("Error cargando abonos");
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (abonoId) => {
    const newExpanded = new Set(expandedAbonos);
    if (newExpanded.has(abonoId)) {
      newExpanded.delete(abonoId);
    } else {
      newExpanded.add(abonoId);
    }
    setExpandedAbonos(newExpanded);
  };

  const formatFecha = (fecha) => {
    return new Date(fecha).toLocaleDateString('es-AR', {
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

  const getEstadoColor = (renovado, estadoVigencia) => {
    if (renovado) return "green";
    if (estadoVigencia === "vencido") return "red";
    return "blue";
  };

  const getEstadoText = (renovado, estadoVigencia) => {
    if (renovado) return "Renovado";
    if (estadoVigencia === "vencido") return "Vencido";
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
          📅 Abonos Mensuales
        </Text>
        <Text fontSize="sm" color={mutedText}>
          {abonos.length} abono{abonos.length !== 1 ? 's' : ''}
        </Text>
      </Flex>

      {abonos.length === 0 ? (
        <Box
          p={6}
          bg={card.bg}
          borderRadius="md"
          borderWidth="1px"
          borderStyle="dashed"
          textAlign="center"
        >
          <Text color={mutedText}>No hay abonos activos</Text>
        </Box>
      ) : (
        <VStack spacing={3} align="stretch">
          {abonos.map((abono) => (
            <Box
              key={abono.id}
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
                  <VStack align="start" spacing={1} flex="1" minW={0}>
                    <HStack spacing={2} wrap="wrap">
                    <Text fontWeight="bold" fontSize="md">
                      {abono.sede_nombre || "Sede no disponible"}
                    </Text>
                      <Badge
                        colorScheme={getEstadoColor(abono.renovado, abono.estado_vigencia)}
                        size="sm"
                      >
                        {getEstadoText(abono.renovado, abono.estado_vigencia)}
                      </Badge>
                    </HStack>
                    <Text fontSize="sm" color={mutedText}>
                      Prestador: {abono.prestador_nombre || "No asignado"}
                    </Text>
                    <Text fontSize="sm" color={mutedText}>
                      Tipo: {abono.tipo_clase_codigo || "Personalizado"} - ${abono.tipo_clase_precio ? Number(abono.tipo_clase_precio).toLocaleString('es-AR') : "Configuración personalizada"}
                    </Text>
                  </VStack>
                  
                  <IconButton
                    icon={expandedAbonos.has(abono.id) ? <ChevronUpIcon /> : <ChevronDownIcon />}
                    size={buttonSize}
                    variant="ghost"
                    onClick={() => toggleExpanded(abono.id)}
                    aria-label={expandedAbonos.has(abono.id) ? "Contraer" : "Expandir"}
                    flexShrink={0}
                  />
                </Flex>

                <Collapse in={expandedAbonos.has(abono.id)}>
                  <Box>
                    <Divider mb={3} />
                    
                    <Text fontWeight="medium" mb={2} color={card.color}>
                      Turnos Reservados:
                    </Text>
                    
                    {abono.turnos_reservados?.length > 0 ? (
                      <VStack spacing={2} align="stretch">
                        {abono.turnos_reservados.map((turno) => (
                          <Box
                            key={turno.id}
                            p={2}
                            bg={hoverBg}
                            borderRadius="sm"
                            borderWidth="1px"
                            borderColor="gray.100"
                          >
                            <HStack justify="space-between" wrap="wrap" gap={1}>
                              <Text fontSize="sm" fontWeight="medium">
                                {formatFecha(turno.fecha)} - {formatHora(turno.hora)}
                              </Text>
                              <Badge
                                colorScheme={turno.estado === "reservado" ? "green" : "gray"}
                                size="xs"
                              >
                                {turno.estado}
                              </Badge>
                            </HStack>
                          </Box>
                        ))}
                      </VStack>
                    ) : (
                      <Text fontSize="sm" color={mutedText}>
                        No hay turnos reservados
                      </Text>
                    )}

                    {abono.ventana_renovacion && (
                      <Box mt={3} p={2} bg="blue.50" borderRadius="sm" borderWidth="1px" borderColor="blue.200">
                        <Text fontSize="xs" color="blue.700" fontWeight="medium">
                          ⏰ En ventana de renovación
                        </Text>
                      </Box>
                    )}
                  </Box>
                </Collapse>
              </VStack>
            </Box>
          ))}
        </VStack>
      )}
    </VStack>
  );
};

export default AbonosList;
