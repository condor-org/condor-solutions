import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, Card, CardBody, HStack, VStack,
  Text, Badge, Button, useToast, Spinner, Divider,
  SimpleGrid, Alert, AlertIcon, useDisclosure, Modal, ModalOverlay,
  ModalContent, ModalHeader, ModalBody, ModalCloseButton,
  Table, Thead, Tbody, Tr, Th, Td, Tag, TagLabel
} from '@chakra-ui/react';
import { 
  FaUser, FaCalendar, FaStethoscope, FaFlask, FaPills, 
  FaHeart, FaExclamationTriangle, FaCheckCircle, FaTimesCircle,
  FaArrowRight, FaHospital, FaUserMd, FaFileMedical
} from 'react-icons/fa';
import { CategoriaBadge } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { useParams } from 'react-router-dom';

const EventoTimeline = ({ icon: Icon, color, title, fecha, descripcion, detalles, categoria }) => (
  <Card borderLeft={`4px solid`} borderLeftColor={`${color}.500`} mb={4}>
    <CardBody>
      <HStack spacing={3}>
        <Box bg={`${color}.500`} color="white" p={2} borderRadius="md">
          <Icon />
        </Box>
        <VStack align="start" spacing={2} flex={1}>
          <HStack justify="space-between" w="100%">
            <Text fontWeight="bold" fontSize="md">{title}</Text>
            <Text fontSize="sm" color="gray.500">
              {new Date(fecha).toLocaleDateString()}
            </Text>
          </HStack>
          <Text fontSize="sm" color="gray.600">{descripcion}</Text>
          {categoria && <CategoriaBadge categoria={categoria} size="sm" />}
          {detalles && (
            <Box w="100%" p={2} bg="gray.50" borderRadius="md">
              <Text fontSize="xs" color="gray.700">{detalles}</Text>
            </Box>
          )}
        </VStack>
      </HStack>
    </CardBody>
  </Card>
);

const SeguimientoPaciente = () => {
  const [paciente, setPaciente] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [eventoSeleccionado, setEventoSeleccionado] = useState(null);
  const [accesoDenegado, setAccesoDenegado] = useState(false);
  
  const toast = useToast();
  const { user } = useAuth();
  const { pacienteId } = useParams();
  
  useEffect(() => {
    if (pacienteId) {
      cargarSeguimientoPaciente();
    }
  }, [pacienteId]);
  
  const cargarSeguimientoPaciente = async () => {
    setLoading(true);
    setAccesoDenegado(false);
    
    try {
      console.log('👤 SeguimientoPaciente: Cargando seguimiento del paciente...');
      
      // Validar acceso al paciente
      const rol = user?.cliente_actual?.rol;
      const esAdminMinistro = rol === 'admin_ministro_salud' || rol === 'admin_ministro';
      
      if (!esAdminMinistro) {
        // Para médicos, validar que el paciente esté en su lista
        // TODO: Implementar validación real con API
        // const tieneAcceso = await validarAccesoPaciente(pacienteId, user.id);
        // if (!tieneAcceso) {
        //   setAccesoDenegado(true);
        //   return;
        // }
      }
      
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamadas reales a:
      // - /api/ethe/pacientes/${pacienteId}/
      // - /api/ethe/pacientes/${pacienteId}/historial-completo/
      
      // Datos del paciente
      const pacienteMock = {
        id: parseInt(pacienteId),
        nombre: 'María',
        apellido: 'González',
        documento: '12345678',
        fecha_nacimiento: '1985-03-15',
        edad: 39,
        sexo: 'F',
        telefono: '+54 11 1234-5678',
        email: 'maria.gonzalez@email.com',
        direccion: 'Av. Corrientes 1234, CABA',
        estado_actual: 'EN_TRATAMIENTO', // EN_TRATAMIENTO, ALTA_MEDICA, FALLECIDO, ABANDONO
        categoria_actual: 'C3',
        fecha_ingreso: '2025-01-15T09:30:00Z',
        medico_ingreso: {
          nombre: 'Dr. Carlos',
          apellido: 'García',
          especialidad: 'Medicina General'
        },
        medico_actual: {
          nombre: 'Dr. Roberto',
          apellido: 'Martínez',
          especialidad: 'Hepatología'
        },
        user: {
          nombre: 'María',
          apellido: 'González',
          email: 'maria.gonzalez@email.com'
        }
      };
      
      // Historial completo del paciente
      const historialMock = [
        {
          id: 1,
          tipo: 'INGRESO',
          fecha: '2025-01-15T09:30:00Z',
          descripcion: 'Ingreso al sistema ETHE',
          detalles: 'Paciente derivada por médico general. FIB4 inicial: 2.8',
          categoria: 'C1',
          medico: 'Dr. Carlos García',
          centro: 'Hospital Central',
          datos_adicionales: {
            fib4_inicial: 2.8,
            pocus_inicial: 'NORMAL',
            motivo_derivacion: 'Elevación de transaminasas'
          }
        },
        {
          id: 2,
          tipo: 'CONSULTA',
          fecha: '2025-01-20T10:00:00Z',
          descripcion: 'Primera consulta de seguimiento',
          detalles: 'Evolución favorable. POCUS normal.',
          categoria: 'C1',
          medico: 'Dr. Carlos García',
          centro: 'Hospital Central',
          datos_adicionales: {
            pocus: 'NORMAL',
            observaciones: 'Paciente asintomática'
          }
        },
        {
          id: 3,
          tipo: 'FIBROSCAN',
          fecha: '2025-01-25T14:30:00Z',
          descripcion: 'Realización de FIBROSCAN',
          detalles: 'Resultado: ALTO (F3-F4). Paciente pasa a C2.',
          categoria: 'C2',
          medico: 'Dr. Carlos García',
          centro: 'Hospital Central',
          datos_adicionales: {
            resultado: 'ALTO',
            valor: '12.5 kPa',
            observaciones: 'Fibrosis significativa detectada'
          }
        },
        {
          id: 4,
          tipo: 'DERIVACION',
          fecha: '2025-01-25T14:30:00Z',
          descripcion: 'Derivación a médico M2',
          detalles: 'Derivada por resultado FIBROSCAN alto.',
          categoria: 'C2',
          medico: 'Dr. Carlos García',
          centro: 'Hospital Central',
          medico_destino: 'Dr. Ana López'
        },
        {
          id: 5,
          tipo: 'CONSULTA',
          fecha: '2025-02-01T11:00:00Z',
          descripcion: 'Primera consulta con médico M2',
          detalles: 'Evaluación inicial. Plan de seguimiento establecido.',
          categoria: 'C2',
          medico: 'Dr. Ana López',
          centro: 'Centro de Atención C2',
          datos_adicionales: {
            plan_seguimiento: 'Control cada 3 meses',
            medicacion: 'Ninguna'
          }
        },
        {
          id: 6,
          tipo: 'FIBROSCAN',
          fecha: '2025-04-15T16:00:00Z',
          descripcion: 'FIBROSCAN de seguimiento',
          detalles: 'Resultado: MUY ALTO. Paciente pasa a C3.',
          categoria: 'C3',
          medico: 'Dr. Ana López',
          centro: 'Centro de Atención C2',
          datos_adicionales: {
            resultado: 'MUY ALTO',
            valor: '18.2 kPa',
            observaciones: 'Progresión de fibrosis'
          }
        },
        {
          id: 7,
          tipo: 'DERIVACION',
          fecha: '2025-04-15T16:00:00Z',
          descripcion: 'Derivación a médico M3',
          detalles: 'Derivada por FIBROSCAN muy alto.',
          categoria: 'C3',
          medico: 'Dr. Ana López',
          centro: 'Centro de Atención C2',
          medico_destino: 'Dr. Roberto Martínez'
        },
        {
          id: 8,
          tipo: 'CONSULTA',
          fecha: '2025-04-22T09:00:00Z',
          descripcion: 'Primera consulta con médico M3',
          detalles: 'Evaluación especializada. Inicio de tratamiento.',
          categoria: 'C3',
          medico: 'Dr. Roberto Martínez',
          centro: 'Centro de Atención C3',
          datos_adicionales: {
            plan_tratamiento: 'Antiviral + Inmunosupresor',
            medicacion: 'Sofosbuvir + Tacrolimus'
          }
        },
        {
          id: 9,
          tipo: 'TRATAMIENTO',
          fecha: '2025-04-22T09:00:00Z',
          descripcion: 'Inicio de tratamiento especializado',
          detalles: 'Prescripción de Sofosbuvir 400mg/día + Tacrolimus 2mg/12hs.',
          categoria: 'C3',
          medico: 'Dr. Roberto Martínez',
          centro: 'Centro de Atención C3',
          datos_adicionales: {
            medicamento: 'Sofosbuvir + Tacrolimus',
            dosis: '400mg/día + 2mg/12hs',
            duracion: '12 semanas',
            observaciones: 'Tolerancia inicial buena'
          }
        },
        {
          id: 10,
          tipo: 'CONSULTA',
          fecha: '2025-05-20T10:30:00Z',
          descripcion: 'Control de tratamiento',
          detalles: 'Evolución favorable. Sin efectos adversos.',
          categoria: 'C3',
          medico: 'Dr. Roberto Martínez',
          centro: 'Centro de Atención C3',
          datos_adicionales: {
            tolerancia: 'Excelente',
            efectos_adversos: 'Ninguno',
            adherencia: '100%'
          }
        }
      ];
      
      setPaciente(pacienteMock);
      setHistorial(historialMock);
      console.log('✅ SeguimientoPaciente: Datos cargados (mock):', { paciente: pacienteMock, historial: historialMock });
      
    } catch (error) {
      console.error('❌ SeguimientoPaciente: Error cargando datos:', error);
      toast({
        title: "Error",
        description: "Error cargando seguimiento del paciente",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
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
  
  const getEstadoIcon = (estado) => {
    switch (estado) {
      case 'EN_TRATAMIENTO': return FaStethoscope;
      case 'ALTA_MEDICA': return FaCheckCircle;
      case 'FALLECIDO': return FaTimesCircle;
      case 'ABANDONO': return FaExclamationTriangle;
      default: return FaUser;
    }
  };
  
  const getTipoIcon = (tipo) => {
    switch (tipo) {
      case 'INGRESO': return FaUser;
      case 'CONSULTA': return FaStethoscope;
      case 'FIBROSCAN': return FaFlask;
      case 'TRATAMIENTO': return FaPills;
      case 'DERIVACION': return FaArrowRight;
      case 'ALTA': return FaCheckCircle;
      case 'FALLECIMIENTO': return FaTimesCircle;
      default: return FaFileMedical;
    }
  };
  
  const getTipoColor = (tipo) => {
    switch (tipo) {
      case 'INGRESO': return 'green';
      case 'CONSULTA': return 'blue';
      case 'FIBROSCAN': return 'purple';
      case 'TRATAMIENTO': return 'orange';
      case 'DERIVACION': return 'yellow';
      case 'ALTA': return 'green';
      case 'FALLECIMIENTO': return 'red';
      default: return 'gray';
    }
  };
  
  const abrirDetalles = (evento) => {
    setEventoSeleccionado(evento);
    setModalAbierto(true);
  };
  
  if (loading) {
    return (
      <Box flex="1" p={{ base: 4, md: 6 }} display="flex" justifyContent="center" alignItems="center">
        <Spinner size="xl" />
      </Box>
    );
  }
  
  if (accesoDenegado) {
    return (
      <Box flex="1" p={{ base: 4, md: 6 }} display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Text fontSize="xl" fontWeight="bold" color="red.500">
            Acceso Denegado
          </Text>
          <Text color="gray.600" textAlign="center">
            No tienes permisos para ver el seguimiento de este paciente.
          </Text>
          <Button
            colorScheme="blue"
            onClick={() => window.history.back()}
          >
            Volver
          </Button>
        </VStack>
      </Box>
    );
  }
  
  if (!paciente) {
    return (
      <Box flex="1" p={{ base: 4, md: 6 }}>
        <Text>Paciente no encontrado</Text>
      </Box>
    );
  }
  
  const EstadoIcon = getEstadoIcon(paciente.estado_actual);
  
  return (
    <Box flex="1" p={{ base: 4, md: 6 }}>
      <Stack spacing={{ base: 4, md: 6 }}>
        {/* Header del paciente */}
        <Card>
          <CardBody>
            <HStack justify="space-between" flexWrap="wrap" spacing={4}>
              <VStack align="start" spacing={2}>
                <Heading size={{ base: "lg", md: "xl" }}>
                  {paciente.user.nombre} {paciente.user.apellido}
                </Heading>
                <HStack spacing={4} flexWrap="wrap">
                  <Text fontSize="sm" color="gray.600">
                    Doc: {paciente.documento}
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    Edad: {paciente.edad} años
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    {paciente.sexo === 'F' ? 'Femenino' : 'Masculino'}
                  </Text>
                </HStack>
              </VStack>
              <VStack align="end" spacing={2}>
                <HStack>
                  <EstadoIcon color={`${getEstadoColor(paciente.estado_actual)}.500`} />
                  <Badge colorScheme={getEstadoColor(paciente.estado_actual)} size="lg">
                    {paciente.estado_actual.replace('_', ' ')}
                  </Badge>
                </HStack>
                <CategoriaBadge categoria={paciente.categoria_actual} />
              </VStack>
            </HStack>
          </CardBody>
        </Card>
        
        {/* Información actual */}
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
          <Card>
            <CardBody>
              <Heading size="md" mb={3}>Información de Contacto</Heading>
              <VStack align="start" spacing={2}>
                <Text><strong>Teléfono:</strong> {paciente.telefono}</Text>
                <Text><strong>Email:</strong> {paciente.email}</Text>
                <Text><strong>Dirección:</strong> {paciente.direccion}</Text>
              </VStack>
            </CardBody>
          </Card>
          
          <Card>
            <CardBody>
              <Heading size="md" mb={3}>Información Médica</Heading>
              <VStack align="start" spacing={2}>
                <Text><strong>Médico Actual:</strong> {paciente.medico_actual.nombre} {paciente.medico_actual.apellido}</Text>
                <Text><strong>Especialidad:</strong> {paciente.medico_actual.especialidad}</Text>
                <Text><strong>Fecha Ingreso:</strong> {new Date(paciente.fecha_ingreso).toLocaleDateString()}</Text>
                <Text><strong>Médico Ingreso:</strong> {paciente.medico_ingreso.nombre} {paciente.medico_ingreso.apellido}</Text>
              </VStack>
            </CardBody>
          </Card>
        </SimpleGrid>
        
        {/* Alertas especiales */}
        {paciente.estado_actual === 'FALLECIDO' && (
          <Alert status="error" borderRadius={{ base: "md", md: "lg" }}>
            <AlertIcon />
            <Box>
              <Text fontWeight="bold">Paciente Fallecido</Text>
              <Text>Este paciente ha fallecido. El historial se mantiene para fines estadísticos y de investigación.</Text>
            </Box>
          </Alert>
        )}
        
        {paciente.estado_actual === 'ABANDONO' && (
          <Alert status="warning" borderRadius={{ base: "md", md: "lg" }}>
            <AlertIcon />
            <Box>
              <Text fontWeight="bold">Paciente en Abandono</Text>
              <Text>Este paciente ha abandonado el tratamiento. Se recomienda seguimiento especial.</Text>
            </Box>
          </Alert>
        )}
        
        {/* Timeline del historial */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>
              Historial Completo del Paciente
            </Heading>
            
            <Stack spacing={0}>
              {historial.map((evento, index) => {
                const TipoIcon = getTipoIcon(evento.tipo);
                return (
                  <EventoTimeline
                    key={evento.id}
                    icon={TipoIcon}
                    color={getTipoColor(evento.tipo)}
                    title={`${evento.tipo} - ${evento.descripcion}`}
                    fecha={evento.fecha}
                    descripcion={evento.detalles}
                    categoria={evento.categoria}
                    detalles={`Médico: ${evento.medico} | Centro: ${evento.centro}`}
                  />
                );
              })}
            </Stack>
          </CardBody>
        </Card>
        
        {/* Resumen estadístico */}
        <Card>
          <CardBody>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Resumen Estadístico</Heading>
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
              <VStack>
                <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                  {historial.filter(e => e.tipo === 'CONSULTA').length}
                </Text>
                <Text fontSize="sm" color="gray.600">Consultas</Text>
              </VStack>
              <VStack>
                <Text fontSize="2xl" fontWeight="bold" color="purple.500">
                  {historial.filter(e => e.tipo === 'FIBROSCAN').length}
                </Text>
                <Text fontSize="sm" color="gray.600">FIBROSCAN</Text>
              </VStack>
              <VStack>
                <Text fontSize="2xl" fontWeight="bold" color="orange.500">
                  {historial.filter(e => e.tipo === 'TRATAMIENTO').length}
                </Text>
                <Text fontSize="sm" color="gray.600">Tratamientos</Text>
              </VStack>
              <VStack>
                <Text fontSize="2xl" fontWeight="bold" color="yellow.500">
                  {historial.filter(e => e.tipo === 'DERIVACION').length}
                </Text>
                <Text fontSize="sm" color="gray.600">Derivaciones</Text>
              </VStack>
            </SimpleGrid>
          </CardBody>
        </Card>
      </Stack>
    </Box>
  );
};

export default SeguimientoPaciente;
