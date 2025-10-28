import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, Card, CardBody, HStack, VStack,
  Text, Button, Input, Select, Badge, useToast, Spinner,
  Table, Thead, Tbody, Tr, Th, Td, SimpleGrid
} from '@chakra-ui/react';
import { FaSearch, FaUser, FaCalendar, FaPills } from 'react-icons/fa';
import { CategoriaBadge, ModalDerivacion } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { getInfoDerivacion } from '../../utils/derivacion';

const PacientesM3 = () => {
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    busqueda: '',
    estado_tratamiento: '',
    tipo_tratamiento: ''
  });
  const [modalDerivacion, setModalDerivacion] = useState({
    isOpen: false,
    paciente: null
  });
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarPacientes();
  }, []);
  
  const cargarPacientes = async () => {
    setLoading(true);
    try {
      console.log('👥 PacientesM3: Cargando pacientes...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/pacientes/?medico=${user.id}
      const pacientesMock = [
        {
          id: 1,
          nombre: 'María',
          apellido: 'González',
          documento: '12345678',
          categoria_actual: 'C3',
          fecha_ingreso: '2025-01-15T09:30:00Z',
          ultima_consulta: '2025-01-20T10:30:00Z',
          tratamiento_activo: true,
          tipo_tratamiento: 'ANTIVIRAL',
          medicamento: 'Sofosbuvir',
          dosis: '400mg',
          frecuencia: '1x día',
          duracion: '12 semanas',
          fecha_inicio_tratamiento: '2025-01-15T09:30:00Z',
          alta_medica: false,
          user: {
            nombre: 'María',
            apellido: 'González',
            email: 'maria.gonzalez@email.com'
          },
          estadisticas: {
            total_consultas: 4,
            tratamientos_prescritos: 1,
            ultima_evolucion: '2025-01-20T10:30:00Z'
          }
        },
        {
          id: 2,
          nombre: 'Carlos',
          apellido: 'Rodríguez',
          documento: '87654321',
          categoria_actual: 'C3',
          fecha_ingreso: '2025-01-10T11:15:00Z',
          ultima_consulta: '2025-01-19T14:15:00Z',
          tratamiento_activo: true,
          tipo_tratamiento: 'INMUNOSUPRESOR',
          medicamento: 'Tacrolimus',
          dosis: '2mg',
          frecuencia: '2x día',
          duracion: '6 meses',
          fecha_inicio_tratamiento: '2025-01-10T11:15:00Z',
          alta_medica: false,
          user: {
            nombre: 'Carlos',
            apellido: 'Rodríguez',
            email: 'carlos.rodriguez@email.com'
          },
          estadisticas: {
            total_consultas: 3,
            tratamientos_prescritos: 1,
            ultima_evolucion: '2025-01-19T14:15:00Z'
          }
        },
        {
          id: 3,
          nombre: 'Ana',
          apellido: 'Martínez',
          documento: '11223344',
          categoria_actual: 'C3',
          fecha_ingreso: '2025-01-05T08:45:00Z',
          ultima_consulta: '2025-01-18T09:45:00Z',
          tratamiento_activo: false,
          tipo_tratamiento: null,
          medicamento: null,
          dosis: null,
          frecuencia: null,
          duracion: null,
          fecha_inicio_tratamiento: null,
          alta_medica: true,
          fecha_alta: '2025-01-18T09:45:00Z',
          user: {
            nombre: 'Ana',
            apellido: 'Martínez',
            email: 'ana.martinez@email.com'
          },
          estadisticas: {
            total_consultas: 5,
            tratamientos_prescritos: 1,
            ultima_evolucion: '2025-01-18T09:45:00Z'
          }
        },
        {
          id: 4,
          nombre: 'Luis',
          apellido: 'Fernández',
          documento: '55667788',
          categoria_actual: 'C3',
          fecha_ingreso: '2025-01-12T13:20:00Z',
          ultima_consulta: '2025-01-17T11:00:00Z',
          tratamiento_activo: true,
          tipo_tratamiento: 'CORTICOIDE',
          medicamento: 'Prednisolona',
          dosis: '20mg',
          frecuencia: '1x día',
          duracion: '4 semanas',
          fecha_inicio_tratamiento: '2025-01-12T13:20:00Z',
          alta_medica: false,
          user: {
            nombre: 'Luis',
            apellido: 'Fernández',
            email: 'luis.fernandez@email.com'
          },
          estadisticas: {
            total_consultas: 2,
            tratamientos_prescritos: 1,
            ultima_evolucion: '2025-01-17T11:00:00Z'
          }
        }
      ];
      
      setPacientes(pacientesMock);
      console.log('✅ PacientesM3: Pacientes cargados (mock):', pacientesMock);
      
    } catch (error) {
      console.error('❌ PacientesM3: Error cargando pacientes:', error);
      toast({
        title: "Error",
        description: "Error cargando pacientes",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const filtrarPacientes = () => {
    return pacientes.filter(paciente => {
      const cumpleBusqueda = !filtros.busqueda || 
        `${paciente.user.nombre} ${paciente.user.apellido}`.toLowerCase().includes(filtros.busqueda.toLowerCase()) ||
        paciente.documento.includes(filtros.busqueda);
      
      const cumpleEstado = !filtros.estado_tratamiento || 
        (filtros.estado_tratamiento === 'activo' && paciente.tratamiento_activo) ||
        (filtros.estado_tratamiento === 'alta' && paciente.alta_medica) ||
        (filtros.estado_tratamiento === 'sin_tratamiento' && !paciente.tratamiento_activo && !paciente.alta_medica);
      
      const cumpleTipo = !filtros.tipo_tratamiento || paciente.tipo_tratamiento === filtros.tipo_tratamiento;
      
      return cumpleBusqueda && cumpleEstado && cumpleTipo;
    });
  };
  
  const pacientesFiltrados = filtrarPacientes();

  const handleDerivar = (paciente) => {
    setModalDerivacion({
      isOpen: true,
      paciente: paciente
    });
  };

  const handleCloseModal = () => {
    setModalDerivacion({
      isOpen: false,
      paciente: null
    });
  };

  const handleDerivacionSuccess = (data) => {
    toast({
      title: "Derivación exitosa",
      description: "El paciente ha sido derivado exitosamente",
      status: "success",
      duration: 3000,
      isClosable: true,
    });
    
    // Recargar pacientes para reflejar cambios
    cargarPacientes();
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
        <Heading size={{ base: "lg", md: "xl" }}>Mis Pacientes (Médico M3)</Heading>
        
        {/* Filtros */}
        <Card>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
              <Input
                placeholder="Buscar por nombre o documento..."
                value={filtros.busqueda}
                onChange={(e) => setFiltros(prev => ({ ...prev, busqueda: e.target.value }))}
                leftIcon={<FaSearch />}
              />
              <Select
                placeholder="Filtrar por estado"
                value={filtros.estado_tratamiento}
                onChange={(e) => setFiltros(prev => ({ ...prev, estado_tratamiento: e.target.value }))}
              >
                <option value="">Todos los estados</option>
                <option value="activo">En Tratamiento Activo</option>
                <option value="alta">Alta Médica</option>
                <option value="sin_tratamiento">Sin Tratamiento</option>
              </Select>
              <Select
                placeholder="Filtrar por tipo de tratamiento"
                value={filtros.tipo_tratamiento}
                onChange={(e) => setFiltros(prev => ({ ...prev, tipo_tratamiento: e.target.value }))}
              >
                <option value="">Todos los tipos</option>
                <option value="ANTIVIRAL">Antiviral</option>
                <option value="INMUNOSUPRESOR">Inmunosupresor</option>
                <option value="CORTICOIDE">Corticoide</option>
                <option value="OTRO">Otro</option>
              </Select>
            </SimpleGrid>
          </CardBody>
        </Card>
        
        {/* Lista de pacientes */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>
              Pacientes ({pacientesFiltrados.length})
            </Heading>
            
            {/* Tabla responsive (Desktop) */}
            <Box display={{ base: "none", md: "block" }} overflowX="auto">
              <Table variant="simple" size={{ base: "sm", md: "md" }}>
                <Thead>
                  <Tr>
                    <Th>Paciente</Th>
                    <Th>Tratamiento</Th>
                    <Th>Medicamento</Th>
                    <Th>Última Consulta</Th>
                    <Th>Estadísticas</Th>
                    <Th>Estado</Th>
                    <Th>Acciones</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {pacientesFiltrados.map(paciente => (
                    <Tr key={paciente.id}>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                            {paciente.user.nombre} {paciente.user.apellido}
                          </Text>
                          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                            Doc: {paciente.documento}
                          </Text>
                        </VStack>
                      </Td>
                      <Td>
                        {paciente.tratamiento_activo ? (
                          <VStack align="start" spacing={0}>
                            <Badge colorScheme="blue" fontSize="xs">{paciente.tipo_tratamiento}</Badge>
                            <Text fontSize="xs" color="gray.500">
                              {paciente.dosis} - {paciente.frecuencia}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                              {paciente.duracion}
                            </Text>
                          </VStack>
                        ) : paciente.alta_medica ? (
                          <Badge colorScheme="green" fontSize="xs">Alta Médica</Badge>
                        ) : (
                          <Badge colorScheme="gray" fontSize="xs">Sin Tratamiento</Badge>
                        )}
                      </Td>
                      <Td>
                        {paciente.medicamento ? (
                          <Text fontSize={{ base: "xs", md: "sm" }} fontWeight="medium">
                            {paciente.medicamento}
                          </Text>
                        ) : (
                          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                            N/A
                          </Text>
                        )}
                      </Td>
                      <Td>
                        <Text fontSize={{ base: "xs", md: "sm" }}>
                          {new Date(paciente.ultima_consulta).toLocaleDateString()}
                        </Text>
                      </Td>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontSize="xs">{paciente.estadisticas.total_consultas} consultas</Text>
                          <Text fontSize="xs">{paciente.estadisticas.tratamientos_prescritos} tratamientos</Text>
                        </VStack>
                      </Td>
                      <Td>
                        {paciente.alta_medica ? (
                          <Badge colorScheme="green" fontSize="xs">Alta Médica</Badge>
                        ) : paciente.tratamiento_activo ? (
                          <Badge colorScheme="blue" fontSize="xs">En Tratamiento</Badge>
                        ) : (
                          <Badge colorScheme="gray" fontSize="xs">Sin Tratamiento</Badge>
                        )}
                      </Td>
                      <Td>
                        <Button
                          size="sm"
                          colorScheme="blue"
                          variant="outline"
                          onClick={() => window.location.href = `/seguimiento-paciente/${paciente.id}`}
                        >
                          Ver Seguimiento
                        </Button>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
            
            {/* Cards responsive (Mobile) */}
            <SimpleGrid display={{ base: "grid", md: "none" }} columns={1} spacing={3}>
              {pacientesFiltrados.map(paciente => (
                <Card key={paciente.id} borderWidth="1px" borderRadius="lg">
                  <CardBody>
                    <VStack align="start" spacing={3}>
                      <HStack justify="space-between" w="100%">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold" fontSize="md">
                            {paciente.user.nombre} {paciente.user.apellido}
                          </Text>
                          <Text fontSize="sm" color="gray.600">
                            Doc: {paciente.documento}
                          </Text>
                        </VStack>
                        <CategoriaBadge categoria={paciente.categoria_actual} size="sm" />
                      </HStack>
                      
                      <HStack spacing={2} flexWrap="wrap">
                        {paciente.tratamiento_activo ? (
                          <>
                            <Badge colorScheme="blue" fontSize="xs">{paciente.tipo_tratamiento}</Badge>
                            <Badge colorScheme="purple" fontSize="xs">{paciente.medicamento}</Badge>
                          </>
                        ) : paciente.alta_medica ? (
                          <Badge colorScheme="green" fontSize="xs">Alta Médica</Badge>
                        ) : (
                          <Badge colorScheme="gray" fontSize="xs">Sin Tratamiento</Badge>
                        )}
                      </HStack>
                      
                      {paciente.tratamiento_activo && (
                        <VStack align="start" spacing={1} w="100%">
                          <Text fontSize="sm" color="gray.600">
                            <strong>Dosis:</strong> {paciente.dosis} - {paciente.frecuencia}
                          </Text>
                          <Text fontSize="sm" color="gray.600">
                            <strong>Duración:</strong> {paciente.duracion}
                          </Text>
                        </VStack>
                      )}
                      
                      <HStack justify="space-between" w="100%" fontSize="sm" color="gray.600">
                        <Text>{paciente.estadisticas.total_consultas} consultas</Text>
                        <Text>{paciente.estadisticas.tratamientos_prescritos} tratamientos</Text>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>
              ))}
            </SimpleGrid>
            
            {pacientesFiltrados.length === 0 && (
              <Text textAlign="center" color="gray.500" py={8}>
                No se encontraron pacientes con los filtros aplicados
              </Text>
            )}
          </CardBody>
        </Card>
      </Stack>
      
      {/* Modal de Derivación */}
      <ModalDerivacion
        isOpen={modalDerivacion.isOpen}
        onClose={handleCloseModal}
        paciente={modalDerivacion.paciente}
        onSuccess={handleDerivacionSuccess}
      />
    </Box>
  );
};

export default PacientesM3;
