import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Text,
  Badge,
  Card,
  CardBody,
  SimpleGrid,
  Select,
  Input,
  useToast,
  Spinner,
  Divider,
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Radio,
  RadioGroup,
  Stack
} from '@chakra-ui/react';
import { FaCalendar, FaClock, FaUser, FaMapMarkerAlt } from 'react-icons/fa';
import { getCentrosSuperiores, reservarTurnoDerivacion } from '../../api/etheApi';

const ModalDerivacion = ({ isOpen, onClose, paciente, onSuccess }) => {
  const [centros, setCentros] = useState([]);
  const [centroSeleccionado, setCentroSeleccionado] = useState(null);
  const [turnos, setTurnos] = useState([]);
  const [turnoSeleccionado, setTurnoSeleccionado] = useState('');
  const [motivo, setMotivo] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingTurnos, setLoadingTurnos] = useState(false);
  const [filtroFecha, setFiltroFecha] = useState('');
  const [filtroFranja, setFiltroFranja] = useState('dia'); // dia, semana, mes
  
  const toast = useToast();

  useEffect(() => {
    if (isOpen) {
      cargarCentros();
    }
  }, [isOpen]);

  useEffect(() => {
    if (centroSeleccionado) {
      cargarTurnos();
    }
  }, [centroSeleccionado, filtroFecha, filtroFranja]);

  const cargarCentros = async () => {
    setLoading(true);
    try {
      const data = await getCentrosSuperiores();
      setCentros(data.centros_superiores || []);
      console.log('✅ Centros cargados:', data);
    } catch (error) {
      console.error('❌ Error cargando centros:', error);
      toast({
        title: "Error",
        description: "Error cargando centros superiores",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const cargarTurnos = async () => {
    if (!centroSeleccionado) return;
    
    console.log('🔍 Centro seleccionado:', centroSeleccionado);
    console.log('🔍 Médicos del centro:', centroSeleccionado.medicos);
    
    setLoadingTurnos(true);
    try {
      // Filtrar turnos del centro seleccionado y agregar información del médico
      const turnosCentro = centroSeleccionado.medicos.flatMap(medico => 
        (medico.turnos || []).map(turno => ({
          ...turno,
          medico_nombre: medico.nombre,
          especialidad: medico.especialidad,
          matricula: medico.matricula
        }))
      );
      
      console.log('🔍 Turnos del centro:', turnosCentro);
      
      // Aplicar filtros
      let turnosFiltrados = turnosCentro;
      
      if (filtroFecha) {
        turnosFiltrados = turnosFiltrados.filter(turno => 
          turno.fecha === filtroFecha
        );
      }
      
      setTurnos(turnosFiltrados);
      console.log('✅ Turnos cargados:', turnosFiltrados);
    } catch (error) {
      console.error('❌ Error cargando turnos:', error);
      toast({
        title: "Error",
        description: "Error cargando turnos disponibles",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoadingTurnos(false);
    }
  };

  const handleReservar = async () => {
    if (!turnoSeleccionado || !motivo.trim()) {
      toast({
        title: "Campos requeridos",
        description: "Selecciona un turno y especifica el motivo de derivación",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setLoading(true);
    try {
      const data = await reservarTurnoDerivacion({
        turno_id: turnoSeleccionado,
        paciente_id: paciente.id,
        motivo_derivacion: motivo
      });
      
      toast({
        title: "Turno reservado",
        description: "El turno de derivación ha sido reservado exitosamente",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      onSuccess && onSuccess(data);
      onClose();
    } catch (error) {
      console.error('❌ Error reservando turno:', error);
      toast({
        title: "Error",
        description: "Error reservando turno de derivación",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setCentroSeleccionado(null);
    setTurnos([]);
    setTurnoSeleccionado('');
    setMotivo('');
    setFiltroFecha('');
    setFiltroFranja('dia');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatTime = (timeString) => {
    return new Date(`2000-01-01T${timeString}`).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="6xl">
      <ModalOverlay />
      <ModalContent maxH="90vh">
        <ModalHeader>
          <Heading size="lg">Derivar Paciente</Heading>
          <Text color="gray.600" fontSize="sm">
            {paciente?.user?.nombre} {paciente?.user?.apellido} - {paciente?.categoria_actual}
          </Text>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody overflowY="auto">
          <VStack spacing={6} align="stretch">
            {/* Paso 1: Seleccionar Centro */}
            <Box>
              <Heading size="md" mb={4}>1. Seleccionar Centro de Atención Superior</Heading>
              
              {loading ? (
                <Box textAlign="center" py={8}>
                  <Spinner size="lg" />
                  <Text mt={2}>Cargando centros...</Text>
                </Box>
              ) : (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  {centros.map(centro => (
                    <Card 
                      key={centro.id}
                      cursor="pointer"
                      borderWidth={centroSeleccionado?.id === centro.id ? 2 : 1}
                      borderColor={centroSeleccionado?.id === centro.id ? "blue.500" : "gray.200"}
                      onClick={() => setCentroSeleccionado(centro)}
                      _hover={{ borderColor: "blue.300" }}
                    >
                      <CardBody>
                        <VStack align="start" spacing={2}>
                          <HStack>
                            <FaMapMarkerAlt color="blue" />
                            <Text fontWeight="bold">{centro.nombre}</Text>
                          </HStack>
                          <Text fontSize="sm" color="gray.600">{centro.direccion}</Text>
                          <HStack spacing={2}>
                            <Badge colorScheme="blue">{centro.categoria}</Badge>
                            <Text fontSize="sm">{centro.medicos?.length || 0} médicos</Text>
                          </HStack>
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </SimpleGrid>
              )}
            </Box>

            {/* Paso 2: Seleccionar Turno */}
            {centroSeleccionado && (
              <Box>
                <Heading size="md" mb={4}>2. Seleccionar Turno</Heading>
                
                {/* Filtros de turnos */}
                <HStack spacing={4} mb={4}>
                  <Select
                    placeholder="Franja de tiempo"
                    value={filtroFranja}
                    onChange={(e) => setFiltroFranja(e.target.value)}
                    w="200px"
                  >
                    <option value="dia">Día</option>
                    <option value="semana">Semana</option>
                    <option value="mes">Mes</option>
                  </Select>
                  
                  <Input
                    type="date"
                    value={filtroFecha}
                    onChange={(e) => setFiltroFecha(e.target.value)}
                    w="200px"
                  />
                </HStack>

                {loadingTurnos ? (
                  <Box textAlign="center" py={8}>
                    <Spinner size="lg" />
                    <Text mt={2}>Cargando turnos...</Text>
                  </Box>
                ) : (
                  <Box>
                    <Text mb={4} fontWeight="medium">
                      Turnos disponibles en {centroSeleccionado.nombre}
                    </Text>
                    
                    {turnos.length === 0 ? (
                      <Text color="gray.500" textAlign="center" py={8}>
                        No hay turnos disponibles con los filtros aplicados
                      </Text>
                    ) : (
                      <RadioGroup value={turnoSeleccionado} onChange={setTurnoSeleccionado}>
                        <Stack spacing={2}>
                          {turnos.map(turno => (
                            <Card key={turno.id} borderWidth={1}>
                              <CardBody>
                                <Radio value={turno.id.toString()}>
                                  <HStack spacing={4}>
                                    <VStack align="start" spacing={1}>
                                      <HStack>
                                        <FaCalendar color="blue" />
                                        <Text fontWeight="medium">{formatDate(turno.fecha)}</Text>
                                      </HStack>
                                      <HStack>
                                        <FaClock color="green" />
                                        <Text>{formatTime(turno.hora)}</Text>
                                      </HStack>
                                    </VStack>
                                    
                                    <Divider orientation="vertical" />
                                    
                                    <VStack align="start" spacing={1}>
                                      <HStack>
                                        <FaUser color="purple" />
                                        <Text fontWeight="medium">{turno.medico_nombre}</Text>
                                      </HStack>
                                      <Text fontSize="sm" color="gray.600">{turno.especialidad}</Text>
                                    </VStack>
                                  </HStack>
                                </Radio>
                              </CardBody>
                            </Card>
                          ))}
                        </Stack>
                      </RadioGroup>
                    )}
                  </Box>
                )}
              </Box>
            )}

            {/* Paso 3: Motivo de derivación */}
            {turnoSeleccionado && (
              <Box>
                <Heading size="md" mb={4}>3. Motivo de Derivación</Heading>
                <Input
                  placeholder="Especifica el motivo de la derivación..."
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </Box>
            )}
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={handleClose}>
            Cancelar
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleReservar}
            isLoading={loading}
            isDisabled={!turnoSeleccionado || !motivo.trim()}
          >
            Reservar Turno
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ModalDerivacion;
