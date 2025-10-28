import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, Card, CardBody, HStack, VStack, 
  Text, Button, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalBody, ModalFooter, ModalCloseButton, Select, Input,
  Textarea, Alert, AlertIcon, useToast, Spinner, useDisclosure
} from '@chakra-ui/react';
import { AsistenciaBadge } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { API_ENDPOINTS, getApiUrl } from '../../config/api';

const AgendaM2 = () => {
  const [turnosHoy, setTurnosHoy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTurno, setSelectedTurno] = useState(null);
  const [marcandoAsistencia, setMarcandoAsistencia] = useState(false);
  
  // Modal FIBROSCAN
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [fibroscanData, setFibroscanData] = useState({
    resultado: '',
    valor_numerico: '',
    observaciones: ''
  });
  const [registrandoFibroscan, setRegistrandoFibroscan] = useState(false);
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarTurnosHoy();
  }, []);
  
  const cargarTurnosHoy = async () => {
    setLoading(true);
    try {
      console.log('📅 AgendaM2: Cargando turnos del día...');
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
          duracion: 30,
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
            categoria_actual: 'C2'
          },
          centro: {
            id: 1,
            nombre: 'Centro de Atención C2',
            direccion: 'Av. Corrientes 1234'
          }
        },
        {
          id: 2,
          fecha: '2025-01-22',
          hora: '10:30',
          duracion: 30,
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
            categoria_actual: 'C2'
          },
          centro: {
            id: 1,
            nombre: 'Centro de Atención C2',
            direccion: 'Av. Corrientes 1234'
          }
        },
        {
          id: 3,
          fecha: '2025-01-22',
          hora: '14:00',
          duracion: 30,
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
            categoria_actual: 'C2'
          },
          centro: {
            id: 1,
            nombre: 'Centro de Atención C2',
            direccion: 'Av. Corrientes 1234'
          }
        }
      ];
      
      setTurnosHoy(turnosMock);
      console.log('✅ AgendaM2: Turnos cargados (mock):', turnosMock);
      
    } catch (error) {
      console.error('❌ AgendaM2: Error cargando turnos:', error);
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
      console.log('✅ AgendaM2: Marcando asistencia (mock)...');
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
      
      console.log('✅ AgendaM2: Asistencia marcada (mock)');
      
    } catch (error) {
      console.error('❌ AgendaM2: Error marcando asistencia:', error);
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
  
  const openFibroscanModal = (turno) => {
    setSelectedTurno(turno);
    setFibroscanData({
      resultado: '',
      valor_numerico: '',
      observaciones: ''
    });
    onOpen();
  };
  
  const handleRegistrarFibroscan = async () => {
    if (!fibroscanData.resultado) {
      toast({
        title: "Error",
        description: "Debe seleccionar un resultado",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setRegistrandoFibroscan(true);
    try {
      console.log('🔬 AgendaM2: Registrando FIBROSCAN (mock)...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/tests/ (POST)
      
      // Simular delay de API
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      toast({
        title: "FIBROSCAN registrado",
        description: `Resultado: ${fibroscanData.resultado}`,
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      // Si resultado = ALTO, mostrar alerta
      if (fibroscanData.resultado === 'ALTO') {
        toast({
          title: "Paciente pasa a C3",
          description: "Debe asignar turno con médico M3",
          status: "warning",
          duration: 5000,
          isClosable: true,
        });
      }
      
      console.log('✅ AgendaM2: FIBROSCAN registrado (mock)');
      onClose();
      cargarTurnosHoy();
      
    } catch (error) {
      console.error('❌ AgendaM2: Error registrando FIBROSCAN:', error);
      toast({
        title: "Error",
        description: "Error registrando FIBROSCAN",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setRegistrandoFibroscan(false);
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
      <Stack spacing={{ base: 4, md: 6 }}>
        <Heading size={{ base: "lg", md: "xl" }}>Mi Agenda</Heading>
        
        {/* Turnos del día */}
        <Box>
          <Heading size={{ base: "md", md: "lg" }} mb={4}>
            Turnos de Hoy ({turnosHoy.length})
          </Heading>
          
          <Stack spacing={{ base: 3, md: 4 }}>
            {turnosHoy.map(turno => (
              <Card key={turno.id}>
                <CardBody>
                  <Stack spacing={3}>
                    <HStack justify="space-between" flexWrap="wrap">
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="bold" fontSize={{ base: "md", md: "lg" }}>
                          {turno.usuario.nombre} {turno.usuario.apellido}
                        </Text>
                        <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                          {turno.hora} - {turno.centro?.nombre || 'Centro de Atención'}
                        </Text>
                        <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                          Doc: {turno.paciente?.documento || 'N/A'}
                        </Text>
                      </VStack>
                      <AsistenciaBadge asistio={turno.asistio} />
                    </HStack>
                    
                    {/* Acciones responsive */}
                    <Stack direction={{ base: "column", sm: "row" }} spacing={2}>
                      {turno.asistio === null && (
                        <>
                          <Button
                            size={{ base: "sm", md: "md" }}
                            colorScheme="green"
                            onClick={() => marcarAsistencia(turno.id, true)}
                            isLoading={marcandoAsistencia}
                            flex={{ base: 1, sm: "none" }}
                          >
                            Asistió
                          </Button>
                          <Button
                            size={{ base: "sm", md: "md" }}
                            colorScheme="red"
                            onClick={() => marcarAsistencia(turno.id, false)}
                            isLoading={marcandoAsistencia}
                            flex={{ base: 1, sm: "none" }}
                          >
                            No Asistió
                          </Button>
                        </>
                      )}
                      
                      {turno.asistio === true && (
                        <Button
                          size={{ base: "sm", md: "md" }}
                          colorScheme="blue"
                          onClick={() => openFibroscanModal(turno)}
                          flex={{ base: 1, sm: "none" }}
                        >
                          Registrar FIBROSCAN
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
              <CardBody>
                <Text textAlign="center" color="gray.500">
                  No hay turnos programados para hoy
                </Text>
              </CardBody>
            </Card>
          )}
        </Box>
      </Stack>
      
      {/* Modal FIBROSCAN */}
      <Modal isOpen={isOpen} onClose={onClose} size={{ base: "full", md: "xl" }}>
        <ModalOverlay />
        <ModalContent m={{ base: 0, md: 4 }}>
          <ModalHeader fontSize={{ base: "lg", md: "xl" }}>
            Registrar FIBROSCAN
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Stack spacing={4}>
              <Text fontSize={{ base: "sm", md: "md" }}>
                Paciente: {selectedTurno?.usuario.nombre} {selectedTurno?.usuario.apellido}
              </Text>
              
              <Select
                placeholder="Seleccione resultado..."
                value={fibroscanData.resultado}
                onChange={(e) => setFibroscanData(prev => ({ ...prev, resultado: e.target.value }))}
                size={{ base: "sm", md: "md" }}
              >
                <option value="BAJO">Bajo</option>
                <option value="INTERMEDIO">Intermedio</option>
                <option value="ALTO">Alto</option>
              </Select>
              
              <Input
                placeholder="Valor numérico (opcional)"
                type="number"
                step="0.1"
                value={fibroscanData.valor_numerico}
                onChange={(e) => setFibroscanData(prev => ({ ...prev, valor_numerico: e.target.value }))}
                size={{ base: "sm", md: "md" }}
              />
              
              <Textarea
                placeholder="Observaciones..."
                rows={3}
                value={fibroscanData.observaciones}
                onChange={(e) => setFibroscanData(prev => ({ ...prev, observaciones: e.target.value }))}
                size={{ base: "sm", md: "md" }}
              />
              
              {fibroscanData.resultado === "ALTO" && (
                <Alert status="warning" borderRadius="md">
                  <AlertIcon />
                  <Box fontSize={{ base: "sm", md: "md" }}>
                    <Text fontWeight="bold">Paciente pasa a C3</Text>
                    <Text>Deberá asignar turno con médico M3</Text>
                  </Box>
                </Alert>
              )}
            </Stack>
          </ModalBody>
          <ModalFooter>
            <Stack direction={{ base: "column", sm: "row" }} spacing={2} w="100%">
              <Button
                onClick={handleRegistrarFibroscan}
                isLoading={registrandoFibroscan}
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

export default AgendaM2;
