import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, Card, CardBody, HStack, VStack,
  Text, Button, Input, Select, Badge, useToast, Spinner,
  Table, Thead, Tbody, Tr, Th, Td, SimpleGrid
} from '@chakra-ui/react';
import { FaSearch, FaUser, FaCalendar, FaStethoscope } from 'react-icons/fa';
import { CategoriaBadge } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

const ListaPacientesPage = () => {
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    busqueda: '',
    categoria: '',
    estado: ''
  });
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarPacientes();
  }, []);
  
  const cargarPacientes = async () => {
    setLoading(true);
    try {
      console.log('👥 ListaPacientesPage: Cargando todos los pacientes...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/pacientes/?admin_ministro=true
      const pacientesMock = [
        {
          id: 1,
          nombre: 'María',
          apellido: 'González',
          documento: '12345678',
          categoria_actual: 'C3',
          estado_actual: 'EN_TRATAMIENTO',
          fecha_ingreso: '2025-01-15T09:30:00Z',
          medico_actual: {
            nombre: 'Dr. Roberto',
            apellido: 'Martínez',
            especialidad: 'Hepatología'
          },
          user: {
            nombre: 'María',
            apellido: 'González',
            email: 'maria.gonzalez@email.com'
          },
          estadisticas: {
            total_consultas: 8,
            ultima_consulta: '2025-01-20T10:30:00Z'
          }
        },
        {
          id: 2,
          nombre: 'Carlos',
          apellido: 'Rodríguez',
          documento: '87654321',
          categoria_actual: 'C2',
          estado_actual: 'EN_TRATAMIENTO',
          fecha_ingreso: '2025-01-10T11:15:00Z',
          medico_actual: {
            nombre: 'Dr. Ana',
            apellido: 'López',
            especialidad: 'Medicina Interna'
          },
          user: {
            nombre: 'Carlos',
            apellido: 'Rodríguez',
            email: 'carlos.rodriguez@email.com'
          },
          estadisticas: {
            total_consultas: 5,
            ultima_consulta: '2025-01-19T14:15:00Z'
          }
        },
        {
          id: 3,
          nombre: 'Ana',
          apellido: 'Martínez',
          documento: '11223344',
          categoria_actual: 'C1',
          estado_actual: 'ALTA_MEDICA',
          fecha_ingreso: '2025-01-05T08:45:00Z',
          medico_actual: {
            nombre: 'Dr. Carlos',
            apellido: 'García',
            especialidad: 'Medicina General'
          },
          user: {
            nombre: 'Ana',
            apellido: 'Martínez',
            email: 'ana.martinez@email.com'
          },
          estadisticas: {
            total_consultas: 3,
            ultima_consulta: '2025-01-18T09:45:00Z'
          }
        },
        {
          id: 4,
          nombre: 'Luis',
          apellido: 'Fernández',
          documento: '55667788',
          categoria_actual: 'C3',
          estado_actual: 'FALLECIDO',
          fecha_ingreso: '2025-01-12T13:20:00Z',
          medico_actual: {
            nombre: 'Dr. Roberto',
            apellido: 'Martínez',
            especialidad: 'Hepatología'
          },
          user: {
            nombre: 'Luis',
            apellido: 'Fernández',
            email: 'luis.fernandez@email.com'
          },
          estadisticas: {
            total_consultas: 6,
            ultima_consulta: '2025-01-17T11:00:00Z'
          }
        }
      ];
      
      setPacientes(pacientesMock);
      console.log('✅ ListaPacientesPage: Pacientes cargados (mock):', pacientesMock);
      
    } catch (error) {
      console.error('❌ ListaPacientesPage: Error cargando pacientes:', error);
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
      
      const cumpleEstado = !filtros.estado || paciente.estado_actual === filtros.estado;
      
      return cumpleBusqueda && cumpleCategoria && cumpleEstado;
    });
  };
  
  const getEstadoColor = (estado) => {
    switch (estado) {
      case 'EN_TRATAMIENTO': return 'blue';
      case 'ALTA_MEDICA': return 'green';
      case 'FALLECIDO': return 'red';
      case 'ABANDONO': return 'orange';
      default: return 'gray';
    }
  };
  
  const getEstadoLabel = (estado) => {
    switch (estado) {
      case 'EN_TRATAMIENTO': return 'En Tratamiento';
      case 'ALTA_MEDICA': return 'Alta Médica';
      case 'FALLECIDO': return 'Fallecido';
      case 'ABANDONO': return 'Abandono';
      default: return estado;
    }
  };
  
  const pacientesFiltrados = filtrarPacientes();
  
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
        <Heading size={{ base: "lg", md: "xl" }}>Seguimiento de Todos los Pacientes</Heading>
        
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
                <option value="C1">C1 - Estable</option>
                <option value="C2">C2 - Moderado</option>
                <option value="C3">C3 - Avanzado</option>
              </Select>
              <Select
                placeholder="Filtrar por estado"
                value={filtros.estado}
                onChange={(e) => setFiltros(prev => ({ ...prev, estado: e.target.value }))}
              >
                <option value="">Todos los estados</option>
                <option value="EN_TRATAMIENTO">En Tratamiento</option>
                <option value="ALTA_MEDICA">Alta Médica</option>
                <option value="FALLECIDO">Fallecido</option>
                <option value="ABANDONO">Abandono</option>
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
                    <Th>Estado</Th>
                    <Th>Médico Actual</Th>
                    <Th>Última Consulta</Th>
                    <Th>Estadísticas</Th>
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
                        <Badge colorScheme={getEstadoColor(paciente.estado_actual)} fontSize="xs">
                          {getEstadoLabel(paciente.estado_actual)}
                        </Badge>
                      </Td>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontSize={{ base: "xs", md: "sm" }}>
                            {paciente.medico_actual.nombre} {paciente.medico_actual.apellido}
                          </Text>
                          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                            {paciente.medico_actual.especialidad}
                          </Text>
                        </VStack>
                      </Td>
                      <Td>
                        <Text fontSize={{ base: "xs", md: "sm" }}>
                          {new Date(paciente.estadisticas.ultima_consulta).toLocaleDateString()}
                        </Text>
                      </Td>
                      <Td>
                        <Text fontSize={{ base: "xs", md: "sm" }}>
                          {paciente.estadisticas.total_consultas} consultas
                        </Text>
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
                        <Badge colorScheme={getEstadoColor(paciente.estado_actual)} fontSize="xs">
                          {getEstadoLabel(paciente.estado_actual)}
                        </Badge>
                      </HStack>
                      
                      <VStack align="start" spacing={1} w="100%">
                        <Text fontSize="sm" color="gray.600">
                          <strong>Médico:</strong> {paciente.medico_actual.nombre} {paciente.medico_actual.apellido}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          <strong>Última consulta:</strong> {new Date(paciente.estadisticas.ultima_consulta).toLocaleDateString()}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          <strong>Consultas:</strong> {paciente.estadisticas.total_consultas}
                        </Text>
                      </VStack>
                      
                      <Button
                        size="sm"
                        colorScheme="blue"
                        variant="outline"
                        onClick={() => window.location.href = `/seguimiento-paciente/${paciente.id}`}
                        w="100%"
                      >
                        Ver Seguimiento Completo
                      </Button>
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
    </Box>
  );
};

export default ListaPacientesPage;
