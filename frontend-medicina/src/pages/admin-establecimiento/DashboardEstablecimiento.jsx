import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, Stat, StatLabel, StatNumber, HStack, VStack,
  Table, Thead, Tbody, Tr, Th, Td, useToast, Spinner,
  Badge, Button, Alert, AlertIcon
} from '@chakra-ui/react';
import { FaUserMd, FaCalendar, FaUsers, FaChartLine, FaExclamationTriangle } from 'react-icons/fa';
import { CategoriaBadge, ProductividadMedicoCard } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

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

const DashboardEstablecimiento = () => {
  const [stats, setStats] = useState({
    medicos_activos: 0,
    turnos_hoy: 0,
    pacientes_activos: 0,
    tasa_asistencia: 0
  });
  const [medicos, setMedicos] = useState([]);
  const [turnosHoy, setTurnosHoy] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarEstadisticas();
    cargarMedicos();
    cargarTurnosHoy();
  }, []);
  
  const cargarEstadisticas = async () => {
    try {
      console.log('📊 DashboardEstablecimiento: Cargando estadísticas...');
      
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/dashboard/estadisticas-generales/
      
      // Simular estadísticas generales del establecimiento
      const estadisticasMock = {
        total_pacientes: 156,
        pacientes_activos: 142,
        pacientes_c1: 89,
        pacientes_c2: 38,
        pacientes_c3: 15,
        total_medicos: 8,
        medicos_activos: 7,
        turnos_hoy: 12,
        turnos_mes: 234,
        tasa_asistencia: 87.5
      };
      
      setStats(estadisticasMock);
      console.log('✅ DashboardEstablecimiento: Estadísticas cargadas (mock):', estadisticasMock);
      
    } catch (error) {
      console.error('❌ DashboardEstablecimiento: Error cargando estadísticas:', error);
      toast({
        title: "Error",
        description: "Error cargando estadísticas",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const cargarMedicos = async () => {
    try {
      console.log('👨‍⚕️ DashboardEstablecimiento: Cargando médicos...');
      
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/medicos/?con_estadisticas=true
      
      // Simular lista de médicos con estadísticas
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
            pacientes_ingresados: 45,
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
            fibroscan_realizados: 38,
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
            consultas_realizadas: 67
          }
        }
      ];
      
      setMedicos(medicosMock);
      console.log('✅ DashboardEstablecimiento: Médicos cargados (mock):', medicosMock);
      
    } catch (error) {
      console.error('❌ DashboardEstablecimiento: Error cargando médicos:', error);
    }
  };
  
  const cargarTurnosHoy = async () => {
    try {
      console.log('📅 DashboardEstablecimiento: Cargando turnos del día...');
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/turnos/?fecha=${hoy}
      const turnosMock = [
        {
          id: 1,
          fecha: '2025-01-22',
          hora: '09:00',
          medico: { nombre: 'Dr. Carlos', apellido: 'García' },
          paciente: { nombre: 'María', apellido: 'González', documento: '12345678' },
          asistio: null,
          estado: 'CONFIRMADO'
        },
        {
          id: 2,
          fecha: '2025-01-22',
          hora: '10:30',
          medico: { nombre: 'Dra. Ana', apellido: 'López' },
          paciente: { nombre: 'Carlos', apellido: 'Rodríguez', documento: '87654321' },
          asistio: true,
          estado: 'COMPLETADO'
        },
        {
          id: 3,
          fecha: '2025-01-22',
          hora: '14:00',
          medico: { nombre: 'Dr. Roberto', apellido: 'Martínez' },
          paciente: { nombre: 'Ana', apellido: 'Martínez', documento: '11223344' },
          asistio: null,
          estado: 'CONFIRMADO'
        },
        {
          id: 4,
          fecha: '2025-01-22',
          hora: '15:30',
          medico: { nombre: 'Dr. Carlos', apellido: 'García' },
          paciente: { nombre: 'Luis', apellido: 'Fernández', documento: '55667788' },
          asistio: false,
          estado: 'COMPLETADO'
        }
      ];
      
      setTurnosHoy(turnosMock);
      console.log('✅ DashboardEstablecimiento: Turnos cargados (mock):', turnosMock);
      
    } catch (error) {
      console.error('❌ DashboardEstablecimiento: Error cargando turnos:', error);
    }
  };
  
  const cancelarTurnosMasivo = async (medicoId, fecha, motivo) => {
    try {
      const response = await fetch('/api/turnos/cancelar-masivo/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          medico_id: medicoId,
          fecha: fecha,
          motivo: motivo
        })
      });
      
      if (response.ok) {
        toast({
          title: "Turnos cancelados",
          description: "Se cancelaron los turnos exitosamente",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        
        cargarTurnosHoy();
      } else {
        throw new Error('Error cancelando turnos');
      }
      
    } catch (error) {
      console.error('Error cancelando turnos:', error);
      toast({
        title: "Error",
        description: "Error cancelando turnos",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
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
        <Heading size={{ base: "lg", md: "xl" }}>Dashboard Establecimiento</Heading>
        
        {/* Métricas principales */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={{ base: 4, md: 6 }}>
          <SummaryCard
            icon={FaUserMd}
            title="Médicos Activos"
            value={stats.medicos_activos}
            color="blue"
          />
          <SummaryCard
            icon={FaCalendar}
            title="Turnos Hoy"
            value={stats.turnos_hoy}
            color="green"
          />
          <SummaryCard
            icon={FaUsers}
            title="Pacientes Activos"
            value={stats.pacientes_activos}
            color="purple"
          />
          <SummaryCard
            icon={FaChartLine}
            title="Tasa Asistencia"
            value={`${stats.tasa_asistencia}%`}
            color="orange"
          />
        </SimpleGrid>
        
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
                    <Th>Estado</Th>
                    <Th>Acciones</Th>
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
                        <Badge colorScheme={medico.activo ? "green" : "red"}>
                          {medico.activo ? "Activo" : "Inactivo"}
                        </Badge>
                      </Td>
                      <Td>
                        <Button size="sm" colorScheme="red">
                          Cancelar Turnos
                        </Button>
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
        
        {/* Turnos de hoy */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Turnos de Hoy</Heading>
            
            {turnosHoy.length > 0 ? (
              <Stack spacing={3}>
                {turnosHoy.slice(0, 5).map(turno => (
                  <HStack key={turno.id} justify="space-between" p={3} bg="gray.50" borderRadius="md">
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                        {turno.paciente.nombre} {turno.paciente.apellido}
                      </Text>
                      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                        {turno.hora} - Dr. {turno.medico.nombre} {turno.medico.apellido}
                      </Text>
                    </VStack>
                    <Badge colorScheme={turno.asistio === true ? "green" : turno.asistio === false ? "red" : "blue"}>
                      {turno.asistio === true ? "Asistió" : turno.asistio === false ? "No Asistió" : "Pendiente"}
                    </Badge>
                  </HStack>
                ))}
                
                {turnosHoy.length > 5 && (
                  <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500" textAlign="center">
                    Y {turnosHoy.length - 5} turnos más...
                  </Text>
                )}
              </Stack>
            ) : (
              <Text textAlign="center" color="gray.500">
                No hay turnos programados para hoy
              </Text>
            )}
          </CardBody>
        </Card>
        
        {/* Alertas */}
        <Stack spacing={3}>
          {stats.tasa_asistencia < 70 && (
            <Alert status="warning" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Tasa de asistencia baja</Text>
                <Text>Tasa actual: {stats.tasa_asistencia}% - Revisar protocolos de seguimiento</Text>
              </Box>
            </Alert>
          )}
          
          {turnosHoy.filter(t => t.asistio === null).length > 0 && (
            <Alert status="info" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">
                  {turnosHoy.filter(t => t.asistio === null).length} turnos pendientes de marcar
                </Text>
                <Text>Revisar agenda de médicos</Text>
              </Box>
            </Alert>
          )}
        </Stack>
      </Stack>
    </Box>
  );
};

export default DashboardEstablecimiento;
