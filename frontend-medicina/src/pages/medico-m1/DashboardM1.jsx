import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, Stat, StatLabel, StatNumber, HStack, VStack,
  Button, useToast, Spinner, Badge
} from '@chakra-ui/react';
import { FaUserPlus, FaCalendar, FaStethoscope, FaArrowUp } from 'react-icons/fa';
import { useAuth } from '../../auth/AuthContext';
import { getDashboardStats, getPacientes } from '../../api/etheApi';
import { CategoriaBadge } from '../../components/ethe';

const SummaryCard = ({ icon: Icon, title, value, color = "blue" }) => (
  <Card>
    <CardBody>
      <Stat>
        <HStack>
          <Icon color={`${color}.500`} size={24} />
          <VStack align="start" spacing={0}>
            <StatLabel fontSize={{ base: "sm", md: "md" }}>{title}</StatLabel>
            <StatNumber fontSize={{ base: "2xl", md: "3xl" }}>{value}</StatNumber>
          </VStack>
        </HStack>
      </Stat>
    </CardBody>
  </Card>
);

const DashboardM1 = () => {
  const [stats, setStats] = useState({
    pacientesHoy: 0,
    pacientesMes: 0,
    testsPocus: 0,
    derivacionesC2: 0
  });
  const [loading, setLoading] = useState(true);
  const [recentPatients, setRecentPatients] = useState([]);
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarEstadisticas();
    cargarPacientesRecientes();
  }, []);
  
  const cargarEstadisticas = async () => {
    try {
      console.log('📊 DashboardM1: Cargando estadísticas...');
      
      // Llamada a la API real
      const data = await getDashboardStats('medico_m1');
      
      setStats(data);
      console.log('✅ DashboardM1: Estadísticas cargadas:', data);

    } catch (error) {
      console.error('❌ DashboardM1: Error cargando estadísticas:', error);
      toast({
        title: "Error",
        description: error.response?.data?.error || error.response?.data?.detail || "Error cargando estadísticas",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      
      // Mantener valores por defecto en caso de error
      setStats({
        pacientesHoy: 0,
        pacientesMes: 0,
        testsPocus: 0,
        derivacionesC2: 0
      });
    } finally {
      setLoading(false);
    }
  };
  
  const cargarPacientesRecientes = async () => {
    try {
      console.log('👥 DashboardM1: Cargando pacientes recientes...');
      
      // Llamada a la API real - obtener pacientes ingresados por este médico
      const data = await getPacientes({ 
        medico_id: user?.id,
        limit: 5
      });
      
      // Los datos pueden venir en formato paginado o array directo
      const pacientes = data.results || data;
      setRecentPatients(pacientes);
      console.log('✅ DashboardM1: Pacientes recientes cargados:', pacientes);

    } catch (error) {
      console.error('❌ DashboardM1: Error cargando pacientes recientes:', error);
      // No mostrar toast para errores secundarios
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
        {/* Encabezado */}
        <Box>
          <Heading size={{ base: "md", md: "lg" }}>
            Dashboard Médico M1
          </Heading>
          <Text color="gray.600" fontSize={{ base: "sm", md: "md" }}>
            Bienvenido, Dr. {user?.nombre} {user?.apellido}. Aquí tienes un resumen de tu actividad.
          </Text>
        </Box>

        {/* Botón principal - Ingresar Nuevo Paciente */}
        <Card bg="blue.50" borderColor="blue.200" borderWidth="2px">
          <CardBody>
            <VStack spacing={4}>
              <FaUserPlus size={48} color="#3182ce" />
              <VStack spacing={2}>
                <Heading size={{ base: "md", md: "lg" }} color="blue.700">
                  Ingresar Nuevo Paciente
                </Heading>
                <Text fontSize={{ base: "sm", md: "md" }} color="gray.600" textAlign="center" maxW="400px">
                  Realizar chequeo inicial con POCUS y FIB4, y registrar paciente en el sistema
                </Text>
              </VStack>
              <Button
                colorScheme="blue"
                size={{ base: "md", md: "lg" }}
                onClick={() => window.location.href = '/medico-m1/ingresar-paciente'}
                px={{ base: 6, md: 8 }}
                py={{ base: 5, md: 6 }}
                fontSize={{ base: "md", md: "lg" }}
                fontWeight="bold"
              >
                🏥 Ingresar Paciente
              </Button>
            </VStack>
          </CardBody>
        </Card>

        {/* Tarjetas de estadísticas */}
        <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} spacing={4}>
          <SummaryCard
            icon={FaCalendar}
            title="Pacientes Hoy"
            value={stats.pacientesHoy}
            color="blue"
          />
          <SummaryCard
            icon={FaUserPlus}
            title="Pacientes Este Mes"
            value={stats.pacientesMes}
            color="green"
          />
          <SummaryCard
            icon={FaStethoscope}
            title="Tests POCUS (Mes)"
            value={stats.testsPocus}
            color="purple"
          />
          <SummaryCard
            icon={FaArrowUp}
            title="Derivaciones a C2 (Mes)"
            value={stats.derivacionesC2}
            color="orange"
          />
        </SimpleGrid>

        {/* Pacientes recientes */}
        <Card>
          <CardBody>
            <Heading size={{ base: "sm", md: "md" }} mb={4}>
              Pacientes Ingresados Recientemente
            </Heading>
            <Stack spacing={3}>
              {recentPatients.length > 0 ? (
                recentPatients.map(patient => (
                  <HStack 
                    key={patient.id} 
                    justify="space-between" 
                    p={3} 
                    bg="gray.50" 
                    borderRadius="md"
                    flexWrap="wrap"
                    gap={2}
                  >
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                        {patient.user?.nombre || patient.nombre} {patient.user?.apellido || patient.apellido}
                      </Text>
                      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                        Doc: {patient.documento}
                      </Text>
                      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
                        Ingresado: {new Date(patient.fecha_ingreso).toLocaleDateString()}
                      </Text>
                    </VStack>
                    <CategoriaBadge categoria={patient.categoria_actual} />
                  </HStack>
                ))
              ) : (
                <Text color="gray.500" fontSize={{ base: "sm", md: "md" }}>
                  No hay pacientes recientes para mostrar.
                </Text>
              )}
            </Stack>
            <Button
              mt={4}
              variant="link"
              colorScheme="blue"
              onClick={() => window.location.href = '/medico-m1/pacientes'}
              fontSize={{ base: "sm", md: "md" }}
            >
              Ver todos mis pacientes
            </Button>
          </CardBody>
        </Card>
      </Stack>
    </Box>
  );
};

export default DashboardM1;
