import React, { useState, useEffect } from 'react';
import {
  Box, Stack, Heading, Card, CardBody, Text, SimpleGrid,
  VStack, HStack, Button, useToast, Spinner, Badge
} from '@chakra-ui/react';
import { FaUserMd, FaStethoscope, FaChartLine, FaCalendarAlt } from 'react-icons/fa';
import { useAuth } from '../../auth/AuthContext';
import { CategoriaBadge } from '../../components/ethe';
import { useNavigate } from 'react-router-dom';
import { getDashboardStats, getPacientes } from '../../api/etheApi';

const DashboardM2 = () => {
  const [stats, setStats] = useState({
    pacientesC2Hoy: 0,
    fibroscanRealizadosMes: 0,
    derivacionesC3Mes: 0,
    pacientesC2Activos: 0
  });
  const [recentPatients, setRecentPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const toast = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    cargarEstadisticas();
    cargarPacientesRecientes();
  }, []);

  const cargarEstadisticas = async () => {
    try {
      console.log('📊 DashboardM2: Cargando estadísticas...');
      
      // Llamada a la API real
      const data = await getDashboardStats('medico_m2');
      
      setStats(data);
      console.log('✅ DashboardM2: Estadísticas cargadas:', data);
    } catch (error) {
      console.error('❌ DashboardM2: Error cargando estadísticas:', error);
      toast({
        title: "Error",
        description: error.response?.data?.error || error.response?.data?.detail || "Error cargando estadísticas",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      
      // Mantener valores por defecto
      setStats({
        pacientesC2Hoy: 0,
        fibroscanRealizadosMes: 0,
        derivacionesC3Mes: 0,
        pacientesC2Activos: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const cargarPacientesRecientes = async () => {
    try {
      console.log('👥 DashboardM2: Cargando pacientes recientes...');
      
      // Llamada a la API real - obtener pacientes C2
      const data = await getPacientes({ 
        categoria: 'C2',
        limit: 5
      });
      
      const pacientes = data.results || data;
      setRecentPatients(pacientes);
      console.log('✅ DashboardM2: Pacientes recientes cargados:', pacientes);
    } catch (error) {
      console.error('❌ DashboardM2: Error cargando pacientes recientes:', error);
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
          <Heading size={{ base: "md", md: "lg" }}>
            Dashboard Médico M2
          </Heading>
          <Text color="gray.600" fontSize={{ base: "sm", md: "md" }}>
            Bienvenido, Dr. {user?.nombre} {user?.apellido}. Aquí tienes un resumen de tu actividad.
          </Text>
        </Box>

        {/* Tarjetas de estadísticas */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
          <Card>
            <CardBody>
              <VStack>
                <FaUserMd size={32} color="#3182ce" />
                <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                  Pacientes C2 Hoy
                </Text>
                <Heading size={{ base: "md", md: "lg" }}>{stats.pacientesC2Hoy}</Heading>
              </VStack>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <VStack>
                <FaStethoscope size={32} color="#38a169" />
                <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                  FIBROSCAN Realizados (Mes)
                </Text>
                <Heading size={{ base: "md", md: "lg" }}>{stats.fibroscanRealizadosMes}</Heading>
              </VStack>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <VStack>
                <FaChartLine size={32} color="#dd6b20" />
                <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                  Derivaciones a C3 (Mes)
                </Text>
                <Heading size={{ base: "md", md: "lg" }}>{stats.derivacionesC3Mes}</Heading>
              </VStack>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <VStack>
                <FaCalendarAlt size={32} color="#805ad5" />
                <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                  Pacientes C2 Activos
                </Text>
                <Heading size={{ base: "md", md: "lg" }}>{stats.pacientesC2Activos}</Heading>
              </VStack>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Sección de acciones principales */}
        <Box>
          <Card bg="blue.50" borderColor="blue.200" borderWidth="2px">
            <CardBody>
              <VStack spacing={4}>
                <FaCalendarAlt size={48} color="#3182ce" />
                <VStack spacing={2}>
                  <Heading size={{ base: "md", md: "lg" }} color="blue.700">
                    Gestionar Agenda
                  </Heading>
                  <Text fontSize={{ base: "sm", md: "md" }} color="gray.600" textAlign="center" maxW="400px">
                    Revisa tus turnos del día y registra los resultados de FIBROSCAN.
                  </Text>
                </VStack>
                <Button
                  colorScheme="blue"
                  size={{ base: "md", md: "lg" }}
                  onClick={() => navigate('/medico-m2/agenda')}
                  px={{ base: 6, md: 8 }}
                  py={{ base: 5, md: 6 }}
                  fontSize={{ base: "md", md: "lg" }}
                  fontWeight="bold"
                >
                  📅 Ir a mi Agenda
                </Button>
              </VStack>
            </CardBody>
          </Card>
        </Box>

        {/* Pacientes recientes */}
        <Card>
          <CardBody>
            <Heading size={{ base: "sm", md: "md" }} mb={4}>
              Pacientes C2 Recientes
            </Heading>
            <Stack spacing={3}>
              {recentPatients.length > 0 ? (
                recentPatients.map(patient => (
                  <HStack key={patient.id} justify="space-between" p={3} bg="gray.50" borderRadius="md">
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                        {patient.user?.nombre || patient.nombre} {patient.user?.apellido || patient.apellido}
                      </Text>
                      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                        Doc: {patient.documento}
                      </Text>
                    </VStack>
                    <HStack>
                      <CategoriaBadge categoria={patient.categoria_actual} />
                      {patient.fibroscan_pendiente && (
                        <Badge colorScheme="orange" fontSize={{ base: "xs", md: "sm" }}>
                          FIBROSCAN Pendiente
                        </Badge>
                      )}
                    </HStack>
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
              onClick={() => navigate('/medico-m2/pacientes')}
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

export default DashboardM2;
