import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, Card, CardBody, HStack, VStack,
  Text, Button, Input, Select, Badge, useToast, Spinner,
  Table, Thead, Tbody, Tr, Th, Td, SimpleGrid
} from '@chakra-ui/react';
import { FaSearch, FaUser, FaCalendar, FaFlask } from 'react-icons/fa';
import { CategoriaBadge, ModalDerivacion } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { getInfoDerivacion } from '../../utils/derivacion';

const PacientesM2 = () => {
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    busqueda: '',
    categoria: '',
    fibroscan_pendiente: ''
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
      console.log('👥 PacientesM2: Cargando pacientes...');
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
          categoria_actual: 'C2',
          fecha_ingreso: '2025-01-15T09:30:00Z',
          ultima_consulta: '2025-01-20T10:30:00Z',
          fibroscan_realizado: true,
          fibroscan_fecha: '2025-01-18T14:00:00Z',
          fibroscan_resultado: 'BAJO',
          derivado_c3: false,
          user: {
            nombre: 'María',
            apellido: 'González',
            email: 'maria.gonzalez@email.com'
          },
          estadisticas: {
            total_consultas: 3,
            fibroscan_realizados: 1,
            ultima_derivacion: null
          }
        },
        {
          id: 2,
          nombre: 'Carlos',
          apellido: 'Rodríguez',
          documento: '87654321',
          categoria_actual: 'C2',
          fecha_ingreso: '2025-01-10T11:15:00Z',
          ultima_consulta: '2025-01-19T14:15:00Z',
          fibroscan_realizado: true,
          fibroscan_fecha: '2025-01-18T10:00:00Z',
          fibroscan_resultado: 'ALTO',
          derivado_c3: false,
          user: {
            nombre: 'Carlos',
            apellido: 'Rodríguez',
            email: 'carlos.rodriguez@email.com'
          },
          estadisticas: {
            total_consultas: 2,
            fibroscan_realizados: 1,
            ultima_derivacion: null
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
          fibroscan_realizado: true,
          fibroscan_fecha: '2025-01-15T16:30:00Z',
          fibroscan_resultado: 'ALTO',
          derivado_c3: true,
          fecha_derivacion: '2025-01-15T16:30:00Z',
          user: {
            nombre: 'Ana',
            apellido: 'Martínez',
            email: 'ana.martinez@email.com'
          },
          estadisticas: {
            total_consultas: 4,
            fibroscan_realizados: 1,
            ultima_derivacion: '2025-01-15T16:30:00Z'
          }
        },
        {
          id: 4,
          nombre: 'Luis',
          apellido: 'Fernández',
          documento: '55667788',
          categoria_actual: 'C2',
          fecha_ingreso: '2025-01-12T13:20:00Z',
          ultima_consulta: '2025-01-17T11:00:00Z',
          fibroscan_realizado: false,
          fibroscan_fecha: null,
          fibroscan_resultado: null,
          derivado_c3: false,
          user: {
            nombre: 'Luis',
            apellido: 'Fernández',
            email: 'luis.fernandez@email.com'
          },
          estadisticas: {
            total_consultas: 1,
            fibroscan_realizados: 0,
            ultima_derivacion: null
          }
        }
      ];
      
      setPacientes(pacientesMock);
      console.log('✅ PacientesM2: Pacientes cargados (mock):', pacientesMock);
      
    } catch (error) {
      console.error('❌ PacientesM2: Error cargando pacientes:', error);
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
      
      const cumpleCategoria = !filtros.categoria || paciente.categoria_actual === filtros.categoria;
      
      const cumpleFibroscan = !filtros.fibroscan_pendiente || 
        (filtros.fibroscan_pendiente === 'pendiente' && !paciente.fibroscan_realizado) ||
        (filtros.fibroscan_pendiente === 'realizado' && paciente.fibroscan_realizado);
      
      return cumpleBusqueda && cumpleCategoria && cumpleFibroscan;
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
        <Heading size={{ base: "lg", md: "xl" }}>Mis Pacientes (Médico M2)</Heading>
        
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
                placeholder="Filtrar por categoría"
                value={filtros.categoria}
                onChange={(e) => setFiltros(prev => ({ ...prev, categoria: e.target.value }))}
              >
                <option value="">Todas las categorías</option>
                <option value="C2">C2</option>
                <option value="C3">C3</option>
              </Select>
              <Select
                placeholder="Filtrar por FIBROSCAN"
                value={filtros.fibroscan_pendiente}
                onChange={(e) => setFiltros(prev => ({ ...prev, fibroscan_pendiente: e.target.value }))}
              >
                <option value="">Todos</option>
                <option value="pendiente">FIBROSCAN Pendiente</option>
                <option value="realizado">FIBROSCAN Realizado</option>
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
                    <Th>Categoría</Th>
                    <Th>FIBROSCAN</Th>
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
                        <CategoriaBadge categoria={paciente.categoria_actual} size="sm" />
                      </Td>
                      <Td>
                        {paciente.fibroscan_realizado ? (
                          <VStack align="start" spacing={0}>
                            <Badge colorScheme="green" fontSize="xs">Realizado</Badge>
                            <Text fontSize="xs" color="gray.500">
                              {new Date(paciente.fibroscan_fecha).toLocaleDateString()}
                            </Text>
                            <Badge 
                              colorScheme={paciente.fibroscan_resultado === 'ALTO' ? 'red' : 'green'} 
                              fontSize="xs"
                            >
                              {paciente.fibroscan_resultado}
                            </Badge>
                          </VStack>
                        ) : (
                          <Badge colorScheme="yellow" fontSize="xs">Pendiente</Badge>
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
                          <Text fontSize="xs">{paciente.estadisticas.fibroscan_realizados} FIBROSCAN</Text>
                        </VStack>
                      </Td>
                      <Td>
                        {paciente.derivado_c3 ? (
                          <Badge colorScheme="red" fontSize="xs">Derivado a C3</Badge>
                        ) : (
                          <Badge colorScheme="blue" fontSize="xs">En Seguimiento</Badge>
                        )}
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <Button
                            size="sm"
                            colorScheme="blue"
                            variant="outline"
                            onClick={() => window.location.href = `/seguimiento-paciente/${paciente.id}`}
                          >
                            Ver Seguimiento
                          </Button>
                          {getInfoDerivacion(paciente, 'C2').puedeDerivar && (
                            <Button
                              size="sm"
                              colorScheme={getInfoDerivacion(paciente, 'C2').colorBoton}
                              onClick={() => handleDerivar(paciente)}
                            >
                              {getInfoDerivacion(paciente, 'C2').textoBoton}
                            </Button>
                          )}
                        </HStack>
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
                        {paciente.fibroscan_realizado ? (
                          <>
                            <Badge colorScheme="green" fontSize="xs">FIBROSCAN Realizado</Badge>
                            <Badge 
                              colorScheme={paciente.fibroscan_resultado === 'ALTO' ? 'red' : 'green'} 
                              fontSize="xs"
                            >
                              {paciente.fibroscan_resultado}
                            </Badge>
                          </>
                        ) : (
                          <Badge colorScheme="yellow" fontSize="xs">FIBROSCAN Pendiente</Badge>
                        )}
                        
                        {paciente.derivado_c3 && (
                          <Badge colorScheme="red" fontSize="xs">Derivado a C3</Badge>
                        )}
                      </HStack>
                      
                      <HStack justify="space-between" w="100%" fontSize="sm" color="gray.600">
                        <Text>{paciente.estadisticas.total_consultas} consultas</Text>
                        <Text>{paciente.estadisticas.fibroscan_realizados} FIBROSCAN</Text>
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

export default PacientesM2;
