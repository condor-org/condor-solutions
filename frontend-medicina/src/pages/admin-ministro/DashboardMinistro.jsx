import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, Stat, StatLabel, StatNumber, HStack, VStack,
  Table, Thead, Tbody, Tr, Th, Td, useToast, Spinner,
  Badge, Progress, Alert, AlertIcon, Button
} from '@chakra-ui/react';
import { FaUsers, FaHospital, FaClinicMedical, FaChartLine, FaUserMd, FaUser, FaPlus, FaCog } from 'react-icons/fa';
import { CategoriaBadge, ProductividadMedicoCard } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { getDashboardStats, getMedicos } from '../../api/etheApi';

const SummaryCard = ({ icon: Icon, title, value, color = "blue", subtitle }) => (
  <Card>
    <CardBody>
      <Stat>
        <HStack>
          <Icon color={`${color}.500`} size={24} />
          <VStack align="start" spacing={0}>
            <StatLabel fontSize={{ base: "sm", md: "md" }}>{title}</StatLabel>
            <StatNumber fontSize={{ base: "2xl", md: "3xl" }}>{value}</StatNumber>
            {subtitle && (
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                {subtitle}
              </Text>
            )}
          </VStack>
        </HStack>
      </Stat>
    </CardBody>
  </Card>
);

const DashboardMinistro = () => {
  const [stats, setStats] = useState({
    total_pacientes: 0,
    pacientes_por_categoria: { C1: 0, C2: 0, C3: 0 },
    tests_realizados_mes: { POCUS: 0, FIB4: 0, FIBROSCAN: 0 },
    centros_activos: 0,
    medicos_activos: 0,
    seguimientos_pendientes: 0,
    tasa_asistencia: 0
  });
  const [medicos, setMedicos] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarEstadisticasGenerales();
    cargarMedicos();
  }, []);
  
  const cargarEstadisticasGenerales = async () => {
    try {
      console.log('📊 DashboardMinistro: Cargando estadísticas generales...');
      
      // Llamada a la API real
      const data = await getDashboardStats('admin_ministro');
      
      setStats(data);
      console.log('✅ DashboardMinistro: Estadísticas generales cargadas:', data);
      
    } catch (error) {
      console.error('❌ DashboardMinistro: Error cargando estadísticas:', error);
      toast({
        title: "Error",
        description: error.response?.data?.error || error.response?.data?.detail || "Error cargando estadísticas generales",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      
      // Mantener valores por defecto
      setStats({
        total_establecimientos: 0,
        establecimientos_activos: 0,
        total_pacientes: 0,
        pacientes_activos: 0,
        pacientes_c1: 0,
        pacientes_c2: 0,
        pacientes_c3: 0,
        pacientes_por_categoria: { C1: 0, C2: 0, C3: 0 },
        total_medicos: 0,
        medicos_activos: 0,
        turnos_mes: 0,
        tasa_asistencia_general: 0,
        nuevos_ingresos_mes: 0,
        derivaciones_c2_mes: 0,
        derivaciones_c3_mes: 0,
        tests_realizados_mes: { POCUS: 0, FIB4: 0, FIBROSCAN: 0 }
      });
    } finally {
      setLoading(false);
    }
  };
  
  const cargarMedicos = async () => {
    try {
      console.log('👨‍⚕️ DashboardMinistro: Cargando médicos...');
      
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/medicos/?con_estadisticas=true
      
      // Simular lista de médicos con estadísticas (nivel nacional)
      const medicosMock = [
        {
          id: 1,
          user: {
            nombre: 'Dr. Carlos',
            apellido: 'García',
            email: 'carlos.garcia@ethe.com'
          },
          categorias: ['M1'],
          matricula: 'MP12345',
          especialidad_medica: 'Medicina General',
          activo: true,
          estadisticas: {
            pacientes_ingresados: 145,
            fibroscan_realizados: 0,
            consultas_realizadas: 0
          }
        },
        {
          id: 2,
          user: {
            nombre: 'Dra. Ana',
            apellido: 'López',
            email: 'ana.lopez@ethe.com'
          },
          categorias: ['M2'],
          matricula: 'MP67890',
          especialidad_medica: 'Gastroenterología',
          activo: true,
          estadisticas: {
            pacientes_ingresados: 0,
            fibroscan_realizados: 238,
            consultas_realizadas: 0
          }
        },
        {
          id: 3,
          user: {
            nombre: 'Dr. Miguel',
            apellido: 'Rodríguez',
            email: 'miguel.rodriguez@ethe.com'
          },
          categorias: ['M3'],
          matricula: 'MP11111',
          especialidad_medica: 'Hepatología',
          activo: true,
          estadisticas: {
            pacientes_ingresados: 0,
            fibroscan_realizados: 0,
            consultas_realizadas: 167
          }
        },
        {
          id: 4,
          user: {
            nombre: 'Dra. Laura',
            apellido: 'Fernández',
            email: 'laura.fernandez@ethe.com'
          },
          categorias: ['M1', 'M2'],
          matricula: 'MP22222',
          especialidad_medica: 'Medicina Interna',
          activo: true,
          estadisticas: {
            pacientes_ingresados: 89,
            fibroscan_realizados: 156,
            consultas_realizadas: 0
          }
        }
      ];
      
      setMedicos(medicosMock);
      console.log('✅ DashboardMinistro: Médicos cargados (mock):', medicosMock);
      
    } catch (error) {
      console.error('❌ DashboardMinistro: Error cargando médicos:', error);
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
        <Heading size={{ base: "lg", md: "xl" }}>Dashboard Ministro de Salud</Heading>
        
        {/* Métricas principales */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={{ base: 4, md: 6 }}>
          <SummaryCard
            icon={FaUsers}
            title="Total Pacientes"
            value={stats.total_pacientes}
            color="blue"
          />
          <SummaryCard
            icon={FaHospital}
            title="Establecimientos"
            value={stats.centros_activos}
            color="green"
          />
          <SummaryCard
            icon={FaClinicMedical}
            title="Centros Activos"
            value={stats.centros_activos}
            color="purple"
          />
          <SummaryCard
            icon={FaChartLine}
            title="Tasa Asistencia"
            value={`${stats.tasa_asistencia}%`}
            color="orange"
          />
        </SimpleGrid>
        
        {/* Distribución por categorías */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Distribución por Categorías</Heading>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={{ base: 3, md: 4 }}>
              <VStack>
                <CategoriaBadge categoria="C1" />
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold" color="green.500">
                  {stats.pacientes_por_categoria.C1}
                </Text>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                  Estable
                </Text>
              </VStack>
              <VStack>
                <CategoriaBadge categoria="C2" />
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold" color="yellow.500">
                  {stats.pacientes_por_categoria.C2}
                </Text>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                  Intermedio
                </Text>
              </VStack>
              <VStack>
                <CategoriaBadge categoria="C3" />
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold" color="red.500">
                  {stats.pacientes_por_categoria.C3}
                </Text>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                  Alto Riesgo
                </Text>
              </VStack>
            </SimpleGrid>
          </CardBody>
        </Card>
        
        {/* Tests realizados */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Tests Realizados (Mes)</Heading>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={{ base: 3, md: 4 }}>
              <VStack>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">POCUS</Text>
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold" color="blue.500">
                  {stats.tests_realizados_mes.POCUS}
                </Text>
              </VStack>
              <VStack>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">FIB4</Text>
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold" color="green.500">
                  {stats.tests_realizados_mes.FIB4}
                </Text>
              </VStack>
              <VStack>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">FIBROSCAN</Text>
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight="bold" color="purple.500">
                  {stats.tests_realizados_mes.FIBROSCAN}
                </Text>
              </VStack>
            </SimpleGrid>
          </CardBody>
        </Card>
        
        {/* Productividad por médico */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Productividad por Médico</Heading>
            
            {/* Tabla responsive (Desktop) */}
            <Box display={{ base: "none", md: "block" }} overflowX="auto">
              <Table variant="simple" size={{ base: "sm", md: "md" }}>
                <Thead>
                  <Tr>
                    <Th>Médico</Th>
                    <Th>Categoría</Th>
                    <Th>Productividad</Th>
                    <Th>Estadísticas</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {medicos.map(medico => (
                    <Tr key={medico.id}>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                            {medico.user.nombre} {medico.user.apellido}
                          </Text>
                          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                            Mat. {medico.matricula}
                          </Text>
                        </VStack>
                      </Td>
                      <Td>
                        <HStack spacing={1}>
                          {medico.categorias.map(cat => (
                            <CategoriaBadge key={cat} categoria={cat} size="sm" />
                          ))}
                        </HStack>
                      </Td>
                      <Td>
                        {medico.estadisticas?.pacientes_ingresados && (
                          <Text fontSize={{ base: "sm", md: "md" }}>
                            {medico.estadisticas.pacientes_ingresados} ingresos
                          </Text>
                        )}
                        {medico.estadisticas?.fibroscan_realizados && (
                          <Text fontSize={{ base: "sm", md: "md" }}>
                            {medico.estadisticas.fibroscan_realizados} FIBROSCAN
                          </Text>
                        )}
                        {medico.estadisticas?.consultas_realizadas && (
                          <Text fontSize={{ base: "sm", md: "md" }}>
                            {medico.estadisticas.consultas_realizadas} consultas
                          </Text>
                        )}
                      </Td>
                      <Td>
                        <Badge colorScheme="green" fontSize="xs">
                          Activo
                        </Badge>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
            
            {/* Cards responsive (Mobile) */}
            <SimpleGrid display={{ base: "grid", md: "none" }} columns={1} spacing={3}>
              {medicos.map(medico => (
                <ProductividadMedicoCard key={medico.id} medico={medico} />
              ))}
            </SimpleGrid>
          </CardBody>
        </Card>
        
        {/* Alertas y seguimientos pendientes */}
        {stats.seguimientos_pendientes > 0 && (
          <Alert status="warning" borderRadius={{ base: "md", md: "lg" }}>
            <AlertIcon />
            <Box fontSize={{ base: "sm", md: "md" }}>
              <Text fontWeight="bold">
                {stats.seguimientos_pendientes} seguimientos pendientes
              </Text>
              <Text>Revisar protocolos de seguimiento</Text>
            </Box>
          </Alert>
        )}
        
        {/* Sección de seguimiento de pacientes */}
        <Card>
          <CardBody>
            <VStack spacing={4}>
              <HStack justify="space-between" w="100%">
                <Heading size={{ base: "md", md: "lg" }}>Seguimiento de Pacientes</Heading>
                <Button
                  colorScheme="blue"
                  onClick={() => window.location.href = '/admin-ministro/seguimiento-pacientes'}
                  leftIcon={<FaUser />}
                >
                  Ver Todos los Pacientes
                </Button>
              </HStack>
              <Text color="gray.600" textAlign="center">
                Acceso completo al historial médico y evolución de todos los pacientes del sistema
              </Text>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="100%">
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                    {stats.total_pacientes}
                  </Text>
                  <Text fontSize="sm" color="gray.600">Total Pacientes</Text>
                </VStack>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold" color="green.500">
                    {stats.pacientes_activos}
                  </Text>
                  <Text fontSize="sm" color="gray.600">Pacientes Activos</Text>
                </VStack>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold" color="orange.500">
                    {stats.derivaciones_c2_mes + stats.derivaciones_c3_mes}
                  </Text>
                  <Text fontSize="sm" color="gray.600">Derivaciones Este Mes</Text>
                </VStack>
              </SimpleGrid>
            </VStack>
          </CardBody>
        </Card>

        {/* Sección de gestión de establecimientos */}
        <Card>
          <CardBody>
            <VStack spacing={4}>
              <HStack justify="space-between" w="100%">
                <Heading size={{ base: "md", md: "lg" }}>Gestión de Establecimientos</Heading>
                <HStack spacing={2}>
                  <Button
                    colorScheme="green"
                    onClick={() => window.location.href = '/admin-ministro/establecimientos'}
                    leftIcon={<FaCog />}
                    size={{ base: "sm", md: "md" }}
                  >
                    Gestionar
                  </Button>
                  <Button
                    colorScheme="blue"
                    onClick={() => window.location.href = '/admin-ministro/crear-establecimiento'}
                    leftIcon={<FaPlus />}
                    size={{ base: "sm", md: "md" }}
                  >
                    Nuevo Establecimiento
                  </Button>
                </HStack>
              </HStack>
              <Text color="gray.600" textAlign="center">
                Administrar establecimientos de salud y asignar administradores
              </Text>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="100%">
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                    {stats.total_establecimientos || 0}
                  </Text>
                  <Text fontSize="sm" color="gray.600">Total Establecimientos</Text>
                </VStack>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold" color="green.500">
                    {stats.establecimientos_activos || 0}
                  </Text>
                  <Text fontSize="sm" color="gray.600">Establecimientos Activos</Text>
                </VStack>
                <VStack>
                  <Text fontSize="2xl" fontWeight="bold" color="purple.500">
                    {stats.total_medicos || 0}
                  </Text>
                  <Text fontSize="sm" color="gray.600">Médicos en Sistema</Text>
                </VStack>
              </SimpleGrid>
            </VStack>
          </CardBody>
        </Card>
      </Stack>
    </Box>
  );
};

export default DashboardMinistro;
