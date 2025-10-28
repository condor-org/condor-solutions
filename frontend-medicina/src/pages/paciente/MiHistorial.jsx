import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, HStack, VStack, Button, Select, Input,
  Table, Thead, Tbody, Tr, Th, Td, useToast, Spinner,
  Badge, Alert, AlertIcon, Divider
} from '@chakra-ui/react';
import { FaStethoscope, FaUserMd, FaCalendar, FaChartLine } from 'react-icons/fa';
import { CategoriaBadge, TestResultCard, PacienteTimeline } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

const HistorialCard = ({ item, tipo }) => (
  <Card>
    <CardBody>
      <Stack spacing={3}>
        <HStack justify="space-between">
          <HStack>
            <FaStethoscope color="#4299E1" size={16} />
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                {tipo === 'test' ? item.tipo_test : 'Cambio de Categoría'}
              </Text>
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                {new Date(tipo === 'test' ? item.fecha_realizacion : item.fecha_cambio).toLocaleDateString('es-ES')}
              </Text>
            </VStack>
          </HStack>
          <Badge colorScheme={tipo === 'test' ? 'blue' : 'purple'}>
            {tipo === 'test' ? item.resultado : item.categoria_nueva}
          </Badge>
        </HStack>
        
        {tipo === 'test' && (
          <VStack align="start" spacing={1}>
            <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
              Médico: {item.medico?.user.nombre} {item.medico?.user.apellido}
            </Text>
            {item.valor_numerico && (
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                Valor: {item.valor_numerico}
              </Text>
            )}
            {item.observaciones && (
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.700" fontStyle="italic">
                {item.observaciones}
              </Text>
            )}
          </VStack>
        )}
        
        {tipo === 'categoria' && (
          <VStack align="start" spacing={1}>
            <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
              {item.categoria_anterior ? `De ${item.categoria_anterior} a ${item.categoria_nueva}` : `Categoría inicial: ${item.categoria_nueva}`}
            </Text>
            <Text fontSize={{ base: "xs", md: "sm" }} color="gray.700">
              {item.motivo}
            </Text>
            {item.medico && (
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                Por: {item.medico.nombre}
              </Text>
            )}
          </VStack>
        )}
      </Stack>
    </CardBody>
  </Card>
);

const MiHistorial = () => {
  const [paciente, setPaciente] = useState(null);
  const [tests, setTests] = useState([]);
  const [historialCategorias, setHistorialCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroTipo, setFiltroTipo] = useState('');
  const [filtroFecha, setFiltroFecha] = useState('');
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarDatos();
  }, [filtroTipo, filtroFecha]);
  
  const cargarDatos = async () => {
    setLoading(true);
    try {
      console.log('📡 MiHistorial: Cargando datos...');
      
      // Usar datos mock del paciente
      const dataPaciente = {
        id: 1,
        nombre: user.nombre || 'Dr. Carlos',
        apellido: user.apellido || 'García',
        documento: '12345678',
        categoria_actual: 'C1',
        fecha_nacimiento: '1985-05-15',
        user: {
          nombre: user.nombre || 'Dr. Carlos',
          apellido: user.apellido || 'García',
          email: user.email || 'paciente@ethe.com'
        }
      };
      setPaciente(dataPaciente);
      console.log('✅ MiHistorial: Datos del paciente cargados');
      
      // Usar tests mock
      const dataTests = [
        {
          id: 1,
          tipo_test: 'POCUS',
          resultado: 'HG',
          valor_numerico: null,
          fecha_realizacion: '2025-10-20T10:00:00Z',
          medico: {
            user: {
              nombre: 'Dr. Carlos',
              apellido: 'García'
            }
          },
          observaciones: 'Hígado graso detectado'
        },
        {
          id: 2,
          tipo_test: 'FIB4',
          resultado: 'NR',
          valor_numerico: 1.2,
          fecha_realizacion: '2025-10-20T10:30:00Z',
          medico: {
            user: {
              nombre: 'Dr. Carlos',
              apellido: 'García'
            }
          },
          observaciones: 'Riesgo bajo'
        }
      ];
      setTests(dataTests);
      console.log('✅ MiHistorial: Tests cargados');
      
      // Usar historial de categorías mock
      const dataHistorial = [
        {
          id: 1,
          categoria_anterior: null,
          categoria_nueva: 'C1',
          motivo: 'Ingreso inicial - POCUS HG, FIB4 NR',
          fecha_cambio: '2025-10-20T10:30:00Z',
          medico: {
            user: {
              nombre: 'Dr. Carlos',
              apellido: 'García'
            }
          }
        }
      ];
      setHistorialCategorias(dataHistorial);
      console.log('✅ MiHistorial: Historial de categorías cargado');
      
    } catch (error) {
      console.error('❌ MiHistorial: Error cargando datos:', error);
      toast({
        title: "Error",
        description: "Error cargando datos del historial",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
      console.log('✅ MiHistorial: Carga completada');
    }
  };
  
  const getTestColor = (tipo, resultado) => {
    if (tipo === 'POCUS') {
      return resultado === 'HG' ? 'yellow' : 'green';
    }
    if (tipo === 'FIB4') {
      return resultado === 'R' ? 'red' : 'green';
    }
    if (tipo === 'FIBROSCAN') {
      switch (resultado) {
        case 'ALTO': return 'red';
        case 'INTERMEDIO': return 'yellow';
        case 'BAJO': return 'green';
        default: return 'gray';
      }
    }
    return 'blue';
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
        <Heading size={{ base: "lg", md: "xl" }}>Mi Historial Médico</Heading>
        
        {/* Información del paciente */}
        {paciente && (
          <Card>
            <CardBody>
              <HStack justify="space-between" mb={4}>
                <VStack align="start" spacing={1}>
                  <Text fontWeight="bold" fontSize={{ base: "lg", md: "xl" }}>
                    {paciente.user.nombre} {paciente.user.apellido}
                  </Text>
                  <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                    Doc: {paciente.documento}
                  </Text>
                  <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                    Ingresado el {new Date(paciente.creado_en).toLocaleDateString('es-ES')}
                  </Text>
                </VStack>
                <CategoriaBadge categoria={paciente.categoria_actual} />
              </HStack>
            </CardBody>
          </Card>
        )}
        
        {/* Filtros responsive */}
        <Stack direction={{ base: "column", md: "row" }} spacing={{ base: 3, md: 4 }}>
          <Select
            placeholder="Todos los tests"
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          >
            <option value="POCUS">POCUS</option>
            <option value="FIB4">FIB4</option>
            <option value="FIBROSCAN">FIBROSCAN</option>
          </Select>
          
          <Input
            type="date"
            placeholder="Fecha"
            value={filtroFecha}
            onChange={(e) => setFiltroFecha(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          />
        </Stack>
        
        {/* Timeline de categorías */}
        {historialCategorias.length > 0 && (
          <Card>
            <CardBody>
              <Heading size={{ base: "md", md: "lg" }} mb={4}>Evolución de Categorías</Heading>
              <PacienteTimeline historial={historialCategorias} />
            </CardBody>
          </Card>
        )}
        
        {/* Tests realizados */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Tests Realizados</Heading>
            
            {tests.length > 0 ? (
              <>
                {/* Tabla responsive (Desktop) */}
                <Box display={{ base: "none", md: "block" }} overflowX="auto">
                  <Table variant="simple" size={{ base: "sm", md: "md" }}>
                    <Thead>
                      <Tr>
                        <Th>Fecha</Th>
                        <Th>Tipo</Th>
                        <Th>Resultado</Th>
                        <Th>Médico</Th>
                        <Th>Valor</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {tests.map(test => (
                        <Tr key={test.id}>
                          <Td fontSize={{ base: "sm", md: "md" }}>
                            {new Date(test.fecha_realizacion).toLocaleDateString('es-ES')}
                          </Td>
                          <Td fontSize={{ base: "sm", md: "md" }}>
                            {test.tipo_test}
                          </Td>
                          <Td>
                            <Badge colorScheme={getTestColor(test.tipo_test, test.resultado)}>
                              {test.resultado}
                            </Badge>
                          </Td>
                          <Td fontSize={{ base: "sm", md: "md" }}>
                            {test.medico?.user.nombre} {test.medico?.user.apellido}
                          </Td>
                          <Td fontSize={{ base: "sm", md: "md" }}>
                            {test.valor_numerico || 'N/A'}
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
                
                {/* Cards responsive (Mobile) */}
                <Stack display={{ base: "block", md: "none" }} spacing={3}>
                  {tests.map(test => (
                    <HistorialCard key={test.id} item={test} tipo="test" />
                  ))}
                </Stack>
              </>
            ) : (
              <Text textAlign="center" color="gray.500">
                No hay tests registrados
              </Text>
            )}
          </CardBody>
        </Card>
        
        {/* Resumen de tests */}
        {tests.length > 0 && (
          <Card>
            <CardBody>
              <Heading size={{ base: "md", md: "lg" }} mb={4}>Resumen de Tests</Heading>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={{ base: 3, md: 4 }}>
                {['POCUS', 'FIB4', 'FIBROSCAN'].map(tipo => {
                  const testsTipo = tests.filter(t => t.tipo_test === tipo);
                  const ultimoTest = testsTipo[testsTipo.length - 1];
                  
                  return (
                    <VStack key={tipo} spacing={2}>
                      <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                        {tipo}
                      </Text>
                      <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold">
                        {testsTipo.length}
                      </Text>
                      {ultimoTest && (
                        <Badge colorScheme={getTestColor(tipo, ultimoTest.resultado)}>
                          Último: {ultimoTest.resultado}
                        </Badge>
                      )}
                    </VStack>
                  );
                })}
              </SimpleGrid>
            </CardBody>
          </Card>
        )}
        
        {/* Alertas importantes */}
        <Stack spacing={3}>
          {paciente?.categoria_actual === 'C3' && (
            <Alert status="error" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Paciente C3 - Alto Riesgo</Text>
                <Text>Requiere seguimiento médico especializado. Mantenga sus citas programadas.</Text>
              </Box>
            </Alert>
          )}
          
          {tests.filter(t => t.tipo_test === 'FIBROSCAN' && t.resultado === 'ALTO').length > 0 && (
            <Alert status="warning" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">FIBROSCAN Alto</Text>
                <Text>Su último FIBROSCAN mostró resultados altos. Es importante el seguimiento médico.</Text>
              </Box>
            </Alert>
          )}
        </Stack>
      </Stack>
    </Box>
  );
};

export default MiHistorial;
