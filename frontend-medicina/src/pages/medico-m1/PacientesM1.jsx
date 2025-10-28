import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, HStack, VStack, Button, Select, Input,
  Table, Thead, Tbody, Tr, Th, Td, useToast, Spinner
} from '@chakra-ui/react';
import { CategoriaBadge, ModalDerivacion } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { getInfoDerivacion } from '../../utils/derivacion';

const PacientesM1 = () => {
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroCategoria, setFiltroCategoria] = useState('');
  const [filtroFecha, setFiltroFecha] = useState('');
  const [modalDerivacion, setModalDerivacion] = useState({
    isOpen: false,
    paciente: null
  });
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarPacientes();
  }, [filtroCategoria, filtroFecha]);
  
  const cargarPacientes = async () => {
    setLoading(true);
    try {
      console.log('👥 PacientesM1: Cargando pacientes...');
      
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamadas reales a:
      // - /api/ethe/pacientes/?medico_ingreso=${user.id}
      // - /api/ethe/pacientes/${paciente.id}/estadisticas-asistencia/
      
      // Simular lista de pacientes para M1 con estadísticas
      const pacientesMock = [
        {
          id: 1,
          nombre: 'María',
          apellido: 'González',
          documento: '12345678',
          categoria_actual: 'C1',
          fecha_ingreso: '2025-10-20T09:30:00Z',
          user: {
            nombre: 'María',
            apellido: 'González',
            email: 'maria.gonzalez@email.com'
          },
          estadisticas_asistencia: {
            total_turnos: 2,
            asistidos: 2,
            no_asistidos: 0,
            pendientes: 0,
            tasa_asistencia: 100.0
          }
        },
        {
          id: 2,
          nombre: 'Juan',
          apellido: 'Pérez',
          documento: '87654321',
          categoria_actual: 'C1',
          fecha_ingreso: '2025-10-19T14:15:00Z',
          ultimo_test: {
            tipo: 'POCUS',
            resultado: 'ALTO',
            fecha: '2025-10-20T10:00:00Z'
          },
          user: {
            nombre: 'Juan',
            apellido: 'Pérez',
            email: 'juan.perez@email.com'
          },
          estadisticas_asistencia: {
            total_turnos: 3,
            asistidos: 2,
            no_asistidos: 1,
            pendientes: 0,
            tasa_asistencia: 66.7
          }
        },
        {
          id: 3,
          nombre: 'Ana',
          apellido: 'López',
          documento: '11223344',
          categoria_actual: 'C1',
          fecha_ingreso: '2025-10-18T11:00:00Z',
          user: {
            nombre: 'Ana',
            apellido: 'López',
            email: 'ana.lopez@email.com'
          },
          estadisticas_asistencia: {
            total_turnos: 1,
            asistidos: 1,
            no_asistidos: 0,
            pendientes: 0,
            tasa_asistencia: 100.0
          }
        },
        {
          id: 4,
          nombre: 'Carlos',
          apellido: 'Martínez',
          documento: '55667788',
          categoria_actual: 'C1',
          fecha_ingreso: '2025-10-17T16:45:00Z',
          ultimo_test: {
            tipo: 'FIB4',
            resultado: 'ALTO',
            fecha: '2025-10-18T09:00:00Z'
          },
          user: {
            nombre: 'Carlos',
            apellido: 'Martínez',
            email: 'carlos.martinez@email.com'
          },
          estadisticas_asistencia: {
            total_turnos: 4,
            asistidos: 3,
            no_asistidos: 1,
            pendientes: 0,
            tasa_asistencia: 75.0
          }
        }
      ];
      
      // Aplicar filtros si existen
      let pacientesFiltrados = pacientesMock;
      
      if (filtroCategoria) {
        pacientesFiltrados = pacientesFiltrados.filter(p => p.categoria_actual === filtroCategoria);
      }
      
      if (filtroFecha) {
        const fechaFiltro = new Date(filtroFecha).toISOString().split('T')[0];
        pacientesFiltrados = pacientesFiltrados.filter(p => 
          p.fecha_ingreso.startsWith(fechaFiltro)
        );
      }
      
      setPacientes(pacientesFiltrados);
      console.log('✅ PacientesM1: Pacientes cargados (mock):', pacientesFiltrados);
      
    } catch (error) {
      console.error('❌ PacientesM1: Error cargando pacientes:', error);
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
  
  const verDetalle = (paciente) => {
    // TODO: Implementar modal o navegación a detalle
    console.log('Ver detalle del paciente:', paciente);
  };

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
  
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
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
        <HStack justify="space-between" align="center">
          <Heading size={{ base: "lg", md: "xl" }}>Mis Pacientes</Heading>
          <Button 
            colorScheme="green" 
            onClick={() => window.location.href = '/medico-m1/ingresar-paciente'}
            size={{ base: "sm", md: "md" }}
          >
            Ingresar Paciente
          </Button>
        </HStack>
        
        {/* Filtros responsive */}
        <Stack direction={{ base: "column", md: "row" }} spacing={{ base: 3, md: 4 }}>
          <Select
            placeholder="Todas las categorías"
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          >
            <option value="C1">C1 - Estable</option>
            <option value="C2">C2 - Intermedio</option>
          </Select>
          
          <Input
            type="date"
            placeholder="Fecha de ingreso"
            value={filtroFecha}
            onChange={(e) => setFiltroFecha(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          />
        </Stack>
        
        {/* Tabla responsive (Desktop) */}
        <Box display={{ base: "none", md: "block" }}>
          <Table variant="simple" size={{ base: "sm", md: "md" }}>
            <Thead>
              <Tr>
                <Th>Paciente</Th>
                <Th>Documento</Th>
                <Th>Categoría</Th>
                <Th>Fecha Ingreso</Th>
                <Th>Asistencia</Th>
                <Th>Acciones</Th>
              </Tr>
            </Thead>
            <Tbody>
              {pacientes.map(paciente => (
                <Tr key={paciente.id}>
                  <Td>
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                        {paciente.user.nombre} {paciente.user.apellido}
                      </Text>
                      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                        {paciente.user.email}
                      </Text>
                    </VStack>
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>{paciente.documento}</Td>
                  <Td>
                    <CategoriaBadge categoria={paciente.categoria_actual} />
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {formatDate(paciente.creado_en)}
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {paciente.estadisticas_asistencia?.tasa_asistencia || 0}%
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      <Button 
                        size="sm" 
                        onClick={() => window.location.href = `/seguimiento-paciente/${paciente.id}`}
                        colorScheme="blue"
                        variant="outline"
                      >
                        Ver Seguimiento
                      </Button>
                      {getInfoDerivacion(paciente, 'C1').puedeDerivar && (
                        <Button 
                          size="sm" 
                          onClick={() => handleDerivar(paciente)}
                          colorScheme={getInfoDerivacion(paciente, 'C1').colorBoton}
                        >
                          {getInfoDerivacion(paciente, 'C1').textoBoton}
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
        <Stack display={{ base: "block", md: "none" }} spacing={3}>
          {pacientes.map(paciente => (
            <Card key={paciente.id}>
              <CardBody>
                <Stack spacing={3}>
                  <HStack justify="space-between">
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                        {paciente.user.nombre} {paciente.user.apellido}
                      </Text>
                      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                        {paciente.user.email}
                      </Text>
                    </VStack>
                    <CategoriaBadge categoria={paciente.categoria_actual} />
                  </HStack>
                  
                  <HStack justify="space-between">
                    <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                      Doc: {paciente.documento}
                    </Text>
                    <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                      {formatDate(paciente.creado_en)}
                    </Text>
                  </HStack>
                  
                  <HStack justify="space-between">
                    <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                      Asistencia: {paciente.estadisticas_asistencia?.tasa_asistencia || 0}%
                    </Text>
                    <HStack spacing={2}>
                      <Button 
                        size="sm" 
                        onClick={() => verDetalle(paciente)}
                        colorScheme="blue"
                        variant="outline"
                      >
                        Ver Detalle
                      </Button>
                      {getInfoDerivacion(paciente, 'C1').puedeDerivar && (
                        <Button 
                          size="sm" 
                          onClick={() => handleDerivar(paciente)}
                          colorScheme={getInfoDerivacion(paciente, 'C1').colorBoton}
                        >
                          {getInfoDerivacion(paciente, 'C1').textoBoton}
                        </Button>
                      )}
                    </HStack>
                  </HStack>
                </Stack>
              </CardBody>
            </Card>
          ))}
        </Stack>
        
        {pacientes.length === 0 && (
          <Card>
            <CardBody>
              <Text textAlign="center" color="gray.500">
                No hay pacientes que coincidan con los filtros
              </Text>
            </CardBody>
          </Card>
        )}
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

export default PacientesM1;
