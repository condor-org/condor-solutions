import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, Card, CardBody, HStack, VStack, 
  Text, Button, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalBody, ModalFooter, ModalCloseButton, Select, Input,
  Textarea, Alert, AlertIcon, useToast, Spinner, useDisclosure
} from '@chakra-ui/react';
import { AsistenciaBadge } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

const AgendaM3 = () => {
  const [turnosHoy, setTurnosHoy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTurno, setSelectedTurno] = useState(null);
  const [marcandoAsistencia, setMarcandoAsistencia] = useState(false);
  
  // Modal TRATAMIENTO
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [tratamientoData, setTratamientoData] = useState({
    tipo_tratamiento: '',
    medicamento: '',
    dosis: '',
    frecuencia: '',
    duracion: '',
    observaciones: ''
  });
  const [registrandoTratamiento, setRegistrandoTratamiento] = useState(false);
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarTurnosHoy();
  }, []);
  
  const cargarTurnosHoy = async () => {
    setLoading(true);
    try {
      console.log('📅 AgendaM3: Cargando turnos del día...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/turnos/?medico=${user.id}&fecha=${hoy}
      const turnosMock = [
        {
          id: 1,
          fecha: '2025-01-22',
          hora: '09:00',
          duracion: 45,
          estado: 'CONFIRMADO',
          asistio: null,
          observaciones: '',
          usuario: {
            id: 1,
            nombre: 'María',
            apellido: 'González',
            email: 'maria.gonzalez@email.com',
            telefono: '+54 11 1234-5678'
          },
          paciente: {
            id: 1,
            documento: '12345678',
            categoria_actual: 'C3'
          },
          centro: {
            id: 1,
            nombre: 'Centro de Atención C3',
            direccion: 'Av. Corrientes 1234'
          }
        },
        {
          id: 2,
          fecha: '2025-01-22',
          hora: '11:00',
          duracion: 45,
          estado: 'CONFIRMADO',
          asistio: null,
          observaciones: '',
          usuario: {
            id: 2,
            nombre: 'Carlos',
            apellido: 'Rodríguez',
            email: 'carlos.rodriguez@email.com',
            telefono: '+54 11 2345-6789'
          },
          paciente: {
            id: 2,
            documento: '87654321',
            categoria_actual: 'C3'
          },
          centro: {
            id: 1,
            nombre: 'Centro de Atención C3',
            direccion: 'Av. Corrientes 1234'
          }
        },
        {
          id: 3,
          fecha: '2025-01-22',
          hora: '15:00',
          duracion: 45,
          estado: 'CONFIRMADO',
          asistio: null,
          observaciones: '',
          usuario: {
            id: 3,
            nombre: 'Ana',
            apellido: 'Martínez',
            email: 'ana.martinez@email.com',
            telefono: '+54 11 3456-7890'
          },
          paciente: {
            id: 3,
            documento: '11223344',
            categoria_actual: 'C3'
          },
          centro: {
            id: 1,
            nombre: 'Centro de Atención C3',
            direccion: 'Av. Corrientes 1234'
          }
        }
      ];
      
      setTurnosHoy(turnosMock);
      console.log('✅ AgendaM3: Turnos cargados (mock):', turnosMock);
      
    } catch (error) {
      console.error('❌ AgendaM3: Error cargando turnos:', error);
      toast({
        title: "Error",
        description: "Error cargando turnos del día",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const marcarAsistencia = async (turnoId, asistio) => {
    setMarcandoAsistencia(true);
    try {
      console.log('✅ AgendaM3: Marcando asistencia (mock)...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/turnos/${turnoId}/marcar-asistencia/
      
      // Simular delay de API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      toast({
        title: "Asistencia marcada",
        description: asistio ? "Paciente marcado como asistió" : "Paciente marcado como no asistió",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      // Actualizar el estado local
      setTurnosHoy(prev => prev.map(turno => 
        turno.id === turnoId 
          ? { ...turno, asistio: asistio, estado: 'COMPLETADO' }
          : turno
      ));
      
      console.log('✅ AgendaM3: Asistencia marcada (mock)');
      
    } catch (error) {
      console.error('❌ AgendaM3: Error marcando asistencia:', error);
      toast({
        title: "Error",
        description: "Error marcando asistencia",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setMarcandoAsistencia(false);
    }
  };
  
  const openTratamientoModal = (turno) => {
    setSelectedTurno(turno);
    setTratamientoData({
      tipo_tratamiento: '',
      medicamento: '',
      dosis: '',
      frecuencia: '',
      duracion: '',
      observaciones: ''
    });
    onOpen();
  };
  
  const handleRegistrarTratamiento = async () => {
    if (!tratamientoData.tipo_tratamiento) {
      toast({
        title: "Error",
        description: "Debe seleccionar un tipo de tratamiento",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setRegistrandoTratamiento(true);
    try {
      console.log('💊 AgendaM3: Registrando tratamiento (mock)...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/tratamientos/ (POST)
      
      // Simular delay de API
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      toast({
        title: "Tratamiento registrado",
        description: `Tratamiento: ${tratamientoData.tipo_tratamiento}`,
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      console.log('✅ AgendaM3: Tratamiento registrado (mock)');
      onClose();
      cargarTurnosHoy();
      
    } catch (error) {
      console.error('❌ AgendaM3: Error registrando tratamiento:', error);
      toast({
        title: "Error",
        description: "Error registrando tratamiento",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setRegistrandoTratamiento(false);
    }
  };
  
  if (loading) {
    return (
      <Box flex="1" p={{ base: 4, md: 6 }} display="flex" justifyContent="center" alignItems="center">
        <Spinner size="xl" />
      </Box>
    );
  }
  
  return (
    <Box flex="1" p={{ base: 4, md: 6 }}>
      <Stack spacing={6}>
        <Box>
          <Heading size="lg" mb={2}>
            Mi Agenda - Médico M3
          </Heading>
          <Text color="gray.600">
            Gestión de turnos y tratamientos para pacientes C3
          </Text>
        </Box>
        
        <Box>
          <Heading size="md" mb={4}>
            Turnos de hoy ({turnosHoy.length})
          </Heading>
          
          <Stack spacing={4}>
            {turnosHoy.map((turno) => (
              <Card key={turno.id} borderWidth="1px" borderColor="gray.200">
                <CardBody>
                  <Stack spacing={4}>
                    <HStack justify="space-between" flexWrap="wrap">
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="bold" fontSize={{ base: "md", md: "lg" }}>
                          {turno.usuario.nombre} {turno.usuario.apellido}
                        </Text>
                        <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                          {turno.hora} - {turno.centro?.nombre || 'Centro de Atención'}
                        </Text>
                        <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                          Doc: {turno.paciente?.documento || 'N/A'} | Categoría: {turno.paciente?.categoria_actual || 'C3'}
                        </Text>
                      </VStack>
                      <AsistenciaBadge asistio={turno.asistio} />
                    </HStack>
                    
                    {/* Acciones responsive */}
                    <Stack direction={{ base: "column", sm: "row" }} spacing={2}>
                      {turno.asistio === null && (
                        <>
                          <Button
                            onClick={() => marcarAsistencia(turno.id, true)}
                            isLoading={marcandoAsistencia}
                            loadingText="Marcando..."
                            colorScheme="green"
                            size={{ base: "sm", md: "md" }}
                            flex={{ base: 1, sm: "none" }}
                          >
                            Asistió
                          </Button>
                          <Button
                            onClick={() => marcarAsistencia(turno.id, false)}
                            isLoading={marcandoAsistencia}
                            loadingText="Marcando..."
                            colorScheme="red"
                            variant="outline"
                            size={{ base: "sm", md: "md" }}
                            flex={{ base: 1, sm: "none" }}
                          >
                            No asistió
                          </Button>
                        </>
                      )}
                      
                      {turno.asistio === true && (
                        <Button
                          onClick={() => openTratamientoModal(turno)}
                          colorScheme="blue"
                          size={{ base: "sm", md: "md" }}
                          flex={{ base: 1, sm: "none" }}
                        >
                          Registrar Tratamiento
                        </Button>
                      )}
                    </Stack>
                  </Stack>
                </CardBody>
              </Card>
            ))}
          </Stack>
          
          {turnosHoy.length === 0 && (
            <Card>
              <CardBody textAlign="center" py={8}>
                <Text fontSize="lg" color="gray.500">
                  No hay turnos programados para hoy
                </Text>
              </CardBody>
            </Card>
          )}
        </Box>
      </Stack>
      
      {/* Modal TRATAMIENTO */}
      <Modal isOpen={isOpen} onClose={onClose} size={{ base: "full", md: "xl" }}>
        <ModalOverlay />
        <ModalContent m={{ base: 0, md: 4 }}>
          <ModalHeader fontSize={{ base: "lg", md: "xl" }}>
            Registrar Tratamiento
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Stack spacing={4}>
              <Text fontSize={{ base: "sm", md: "md" }}>
                Paciente: {selectedTurno?.usuario.nombre} {selectedTurno?.usuario.apellido}
              </Text>
              
              <Select
                placeholder="Seleccione tipo de tratamiento..."
                value={tratamientoData.tipo_tratamiento}
                onChange={(e) => setTratamientoData(prev => ({ ...prev, tipo_tratamiento: e.target.value }))}
                size={{ base: "sm", md: "md" }}
              >
                <option value="ANTIVIRAL">Antiviral</option>
                <option value="INMUNOSUPRESOR">Inmunosupresor</option>
                <option value="CORTICOIDE">Corticoide</option>
                <option value="OTRO">Otro</option>
              </Select>
              
              <Input
                placeholder="Medicamento"
                value={tratamientoData.medicamento}
                onChange={(e) => setTratamientoData(prev => ({ ...prev, medicamento: e.target.value }))}
                size={{ base: "sm", md: "md" }}
              />
              
              <HStack spacing={2}>
                <Input
                  placeholder="Dosis"
                  value={tratamientoData.dosis}
                  onChange={(e) => setTratamientoData(prev => ({ ...prev, dosis: e.target.value }))}
                  size={{ base: "sm", md: "md" }}
                />
                <Input
                  placeholder="Frecuencia"
                  value={tratamientoData.frecuencia}
                  onChange={(e) => setTratamientoData(prev => ({ ...prev, frecuencia: e.target.value }))}
                  size={{ base: "sm", md: "md" }}
                />
                <Input
                  placeholder="Duración"
                  value={tratamientoData.duracion}
                  onChange={(e) => setTratamientoData(prev => ({ ...prev, duracion: e.target.value }))}
                  size={{ base: "sm", md: "md" }}
                />
              </HStack>
              
              <Textarea
                placeholder="Observaciones del tratamiento..."
                rows={3}
                value={tratamientoData.observaciones}
                onChange={(e) => setTratamientoData(prev => ({ ...prev, observaciones: e.target.value }))}
                size={{ base: "sm", md: "md" }}
              />
            </Stack>
          </ModalBody>
          <ModalFooter>
            <Stack direction={{ base: "column", sm: "row" }} spacing={2} w="100%">
              <Button
                onClick={handleRegistrarTratamiento}
                isLoading={registrandoTratamiento}
                loadingText="Registrando..."
                colorScheme="blue"
                flex={{ base: 1, sm: "none" }}
              >
                Registrar
              </Button>
              <Button
                variant="outline"
                onClick={onClose}
                flex={{ base: 1, sm: "none" }}
              >
                Cancelar
              </Button>
            </Stack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default AgendaM3;
