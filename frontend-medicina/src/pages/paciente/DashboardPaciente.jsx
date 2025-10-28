import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, Stat, StatLabel, StatNumber, HStack, VStack,
  useToast, Spinner, Alert, AlertIcon, Button
} from '@chakra-ui/react';
import { FaUser, FaCalendar, FaStethoscope, FaChartLine, FaExclamationTriangle } from 'react-icons/fa';
import { CategoriaBadge, AsistenciaBadge } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

const SummaryCard = ({ icon: Icon, title, value, color = "blue", subtitle, onClick }) => (
  <Card cursor={onClick ? "pointer" : "default"} onClick={onClick} _hover={onClick ? { shadow: "md" } : {}}>
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

const DashboardPaciente = () => {
  console.log('🏥 DashboardPaciente: Componente montado');
  
  const [paciente, setPaciente] = useState(null);
  const [stats, setStats] = useState({
    total_turnos: 0,
    asistidos: 0,
    no_asistidos: 0,
    pendientes: 0,
    tasa_asistencia: 0
  });
  const [proximoTurno, setProximoTurno] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const toast = useToast();
  const { user } = useAuth();
  
  console.log('👤 DashboardPaciente: User:', user);
  
  useEffect(() => {
    cargarDatosPaciente();
  }, []);
  
  const cargarDatosPaciente = async () => {
    try {
      console.log('📡 DashboardPaciente: Cargando datos del paciente...');
      
      // Usar datos mock por ahora
      const dataPaciente = {
        id: 1,
        nombre: user.nombre || 'Juan',
        apellido: user.apellido || 'Pérez',
        documento: '12345678',
        categoria_actual: 'C1',
        fecha_nacimiento: '1985-05-15',
        domicilio_calle: 'Av. Corrientes 1000',
        domicilio_ciudad: 'Buenos Aires',
        domicilio_provincia: 'CABA',
        obra_social: 'OSDE',
        creado_en: '2025-10-20T10:00:00Z',
        user: {
          nombre: user.nombre || 'Juan',
          apellido: user.apellido || 'Pérez',
          email: user.email || 'paciente@ethe.com'
        }
      };
      
      setPaciente(dataPaciente);
      console.log('✅ DashboardPaciente: Datos del paciente cargados:', dataPaciente);
      
      // Usar estadísticas mock
      const dataStats = {
        total_turnos: 3,
        asistidos: 2,
        no_asistidos: 1,
        pendientes: 0,
        tasa_asistencia: 66.67
      };
      
      setStats(dataStats);
      console.log('✅ DashboardPaciente: Estadísticas cargadas:', dataStats);
      
      // Usar próximo turno mock
      const dataTurno = {
        id: 1,
        fecha: '2025-10-25',
        hora: '10:00',
        lugar: {
          nombre: 'Centro C2 - Gastroenterología',
          direccion: 'Av. Corrientes 1234'
        },
        recurso: {
          nombre: 'Dr. Ana López',
          especialidad: 'Gastroenterología'
        },
        asistio: null
      };
      
      setProximoTurno(dataTurno);
      console.log('✅ DashboardPaciente: Próximo turno cargado:', dataTurno);
      
    } catch (error) {
      console.error('❌ DashboardPaciente: Error cargando datos:', error);
      toast({
        title: "Error",
        description: "Error cargando datos del paciente",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };
  
  const formatTime = (timeString) => {
    return new Date(`2000-01-01T${timeString}`).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  console.log('🔄 DashboardPaciente: Renderizando...');
  console.log('📊 DashboardPaciente: Loading:', loading);
  console.log('❌ DashboardPaciente: Error:', error);
  console.log('👤 DashboardPaciente: Paciente:', paciente);
  console.log('📈 DashboardPaciente: Stats:', stats);
  console.log('📅 DashboardPaciente: Próximo turno:', proximoTurno);

  if (loading) {
    console.log('⏳ DashboardPaciente: Mostrando loading...');
    return (
      <Box flex="1" p={{ base: 4, md: 6 }} display="flex" justifyContent="center" alignItems="center">
        <Spinner size="xl" />
      </Box>
    );
  }
  
  console.log('✅ DashboardPaciente: Renderizando contenido principal');
  console.log('👤 DashboardPaciente: Paciente.user:', paciente?.user);
  console.log('👤 DashboardPaciente: Paciente.user.nombre:', paciente?.user?.nombre);

  return (
    <Box flex="1" p={{ base: 4, md: 6 }}>
      <Stack spacing={{ base: 4, md: 6 }}>
        <Heading size={{ base: "lg", md: "xl" }}>Mi Panel de Paciente</Heading>
        
        {/* Información personal */}
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
                    {paciente.user.email}
                  </Text>
                </VStack>
                <CategoriaBadge categoria={paciente.categoria_actual} />
              </HStack>
              
              <Text fontSize={{ base: "sm", md: "md" }} color="gray.700">
                Ingresado el {formatDate(paciente.creado_en)}
              </Text>
            </CardBody>
          </Card>
        )}
        
        {/* Métricas principales */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={{ base: 4, md: 6 }}>
          <SummaryCard
            icon={FaCalendar}
            title="Total Turnos"
            value={stats.total_turnos}
            color="blue"
            onClick={() => window.location.href = '/paciente/mis-turnos'}
          />
          <SummaryCard
            icon={FaStethoscope}
            title="Asistidos"
            value={stats.asistidos}
            color="green"
            subtitle={`${stats.tasa_asistencia}% de asistencia`}
          />
          <SummaryCard
            icon={FaChartLine}
            title="Pendientes"
            value={stats.pendientes}
            color="orange"
            onClick={() => window.location.href = '/paciente/mis-turnos'}
          />
          <SummaryCard
            icon={FaUser}
            title="Categoría"
            value={paciente?.categoria_actual || 'N/A'}
            color="purple"
            onClick={() => window.location.href = '/paciente/mi-historial'}
          />
        </SimpleGrid>
        
        {/* Próximo turno */}
        {proximoTurno && (
          <Card>
            <CardBody>
              <Heading size={{ base: "md", md: "lg" }} mb={4}>Próximo Turno</Heading>
              <HStack justify="space-between" flexWrap="wrap">
                <VStack align="start" spacing={1}>
                  <Text fontWeight="bold" fontSize={{ base: "md", md: "lg" }}>
                    {formatDate(proximoTurno.fecha)}
                  </Text>
                  <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                    {formatTime(proximoTurno.hora)} - {proximoTurno.lugar?.nombre || 'Centro no especificado'}
                  </Text>
                  <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                    Dr. {proximoTurno.recurso?.nombre || 'Médico no especificado'}
                  </Text>
                </VStack>
                <VStack align="end" spacing={1}>
                  <AsistenciaBadge asistio={proximoTurno.asistio} />
                  <Button 
                    size={{ base: "sm", md: "md" }}
                    colorScheme="blue"
                    onClick={() => window.location.href = '/paciente/mis-turnos'}
                  >
                    Ver Detalles
                  </Button>
                </VStack>
              </HStack>
            </CardBody>
          </Card>
        )}
        
        {/* Alertas importantes */}
        <Stack spacing={3}>
          {stats.tasa_asistencia < 70 && stats.total_turnos > 0 && (
            <Alert status="warning" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Tasa de asistencia baja</Text>
                <Text>Su tasa de asistencia es del {stats.tasa_asistencia}%. Es importante asistir a las citas programadas.</Text>
              </Box>
            </Alert>
          )}
          
          {paciente?.categoria_actual === 'C2' && stats.pendientes === 0 && (
            <Alert status="info" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Paciente C2 sin turnos</Text>
                <Text>Como paciente C2, debe tener turnos programados. Contacte a su médico si no tiene citas.</Text>
              </Box>
            </Alert>
          )}
          
          {paciente?.categoria_actual === 'C3' && stats.pendientes === 0 && (
            <Alert status="error" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Paciente C3 sin turnos</Text>
                <Text>Como paciente C3, debe tener turnos programados urgentemente. Contacte a su médico inmediatamente.</Text>
              </Box>
            </Alert>
          )}
        </Stack>
        
        {/* Acciones rápidas */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Acciones Rápidas</Heading>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              <Button 
                colorScheme="blue" 
                size={{ base: "md", md: "lg" }}
                onClick={() => window.location.href = '/paciente/mis-turnos'}
              >
                Ver Mis Turnos
              </Button>
              <Button 
                colorScheme="purple" 
                size={{ base: "md", md: "lg" }}
                onClick={() => window.location.href = '/paciente/mi-historial'}
              >
                Ver Mi Historial
              </Button>
            </SimpleGrid>
          </CardBody>
        </Card>
      </Stack>
    </Box>
  );
};

export default DashboardPaciente;
