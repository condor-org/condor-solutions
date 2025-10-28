import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, HStack, VStack, Button, Select, Input,
  Table, Thead, Tbody, Tr, Th, Td, useToast, Spinner,
  Badge, Alert, AlertIcon
} from '@chakra-ui/react';
import { FaCalendar, FaMapMarkerAlt, FaUserMd, FaClock } from 'react-icons/fa';
import { AsistenciaBadge } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

const TurnoCard = ({ turno }) => (
  <Card>
    <CardBody>
      <Stack spacing={3}>
        <HStack justify="space-between">
          <VStack align="start" spacing={0}>
            <Text fontWeight="bold" fontSize={{ base: "md", md: "lg" }}>
              {new Date(turno.fecha).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </Text>
            <HStack>
              <FaClock size={14} color="#718096" />
              <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
                {new Date(`2000-01-01T${turno.hora}`).toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </Text>
            </HStack>
          </VStack>
          <AsistenciaBadge asistio={turno.asistio} />
        </HStack>
        
        <HStack>
          <FaUserMd color="#4299E1" size={16} />
          <Text fontSize={{ base: "sm", md: "md" }}>
            Dr. {turno.recurso.nombre}
          </Text>
        </HStack>
        
        <HStack>
          <FaMapMarkerAlt color="#718096" size={16} />
          <Text fontSize={{ base: "sm", md: "md" }} color="gray.600">
            {turno.lugar.nombre}
          </Text>
        </HStack>
        
        {turno.observaciones_asistencia && (
          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600" fontStyle="italic">
            {turno.observaciones_asistencia}
          </Text>
        )}
      </Stack>
    </CardBody>
  </Card>
);

const MisTurnos = () => {
  const [turnos, setTurnos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroFecha, setFiltroFecha] = useState('');
  const [filtroMedico, setFiltroMedico] = useState('');
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarTurnos();
  }, [filtroEstado, filtroFecha, filtroMedico]);
  
  const cargarTurnos = async () => {
    setLoading(true);
    try {
      let url = '/api/turnos/mis-turnos/';
      const params = new URLSearchParams();
      
      if (filtroEstado) {
        params.append('estado', filtroEstado);
      }
      
      if (filtroFecha) {
        params.append('fecha', filtroFecha);
      }
      
      if (filtroMedico) {
        params.append('medico', filtroMedico);
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      setTurnos(data);
      
    } catch (error) {
      console.error('Error cargando turnos:', error);
      toast({
        title: "Error",
        description: "Error cargando turnos",
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
      case 'reservado': return 'blue';
      case 'confirmado': return 'green';
      case 'cancelado': return 'red';
      case 'completado': return 'purple';
      default: return 'gray';
    }
  };
  
  const getEstadoLabel = (estado) => {
    switch (estado) {
      case 'reservado': return 'Reservado';
      case 'confirmado': return 'Confirmado';
      case 'cancelado': return 'Cancelado';
      case 'completado': return 'Completado';
      default: return estado;
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
        <Heading size={{ base: "lg", md: "xl" }}>Mis Turnos</Heading>
        
        {/* Filtros responsive */}
        <Stack direction={{ base: "column", md: "row" }} spacing={{ base: 3, md: 4 }}>
          <Select
            placeholder="Todos los estados"
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          >
            <option value="reservado">Reservado</option>
            <option value="confirmado">Confirmado</option>
            <option value="cancelado">Cancelado</option>
            <option value="completado">Completado</option>
          </Select>
          
          <Input
            type="date"
            placeholder="Fecha"
            value={filtroFecha}
            onChange={(e) => setFiltroFecha(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          />
          
          <Input
            placeholder="Buscar médico..."
            value={filtroMedico}
            onChange={(e) => setFiltroMedico(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          />
        </Stack>
        
        {/* Tabla responsive (Desktop) */}
        <Box display={{ base: "none", md: "block" }} overflowX="auto">
          <Table variant="simple" size={{ base: "sm", md: "md" }}>
            <Thead>
              <Tr>
                <Th>Fecha</Th>
                <Th>Hora</Th>
                <Th>Médico</Th>
                <Th>Centro</Th>
                <Th>Estado</Th>
                <Th>Asistencia</Th>
              </Tr>
            </Thead>
            <Tbody>
              {turnos.map(turno => (
                <Tr key={turno.id}>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {new Date(turno.fecha).toLocaleDateString('es-ES')}
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {new Date(`2000-01-01T${turno.hora}`).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    Dr. {turno.recurso.nombre}
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {turno.lugar.nombre}
                  </Td>
                  <Td>
                    <Badge colorScheme={getEstadoColor(turno.estado)}>
                      {getEstadoLabel(turno.estado)}
                    </Badge>
                  </Td>
                  <Td>
                    <AsistenciaBadge asistio={turno.asistio} />
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
        
        {/* Cards responsive (Mobile) */}
        <Stack display={{ base: "block", md: "none" }} spacing={3}>
          {turnos.map(turno => (
            <TurnoCard key={turno.id} turno={turno} />
          ))}
        </Stack>
        
        {turnos.length === 0 && (
          <Card>
            <CardBody>
              <VStack spacing={4}>
                <FaCalendar size={48} color="#718096" />
                <Text textAlign="center" color="gray.500" fontSize={{ base: "md", md: "lg" }}>
                  No hay turnos que coincidan con los filtros
                </Text>
                <Text textAlign="center" color="gray.400" fontSize={{ base: "sm", md: "md" }}>
                  Si esperaba ver turnos, contacte a su médico
                </Text>
              </VStack>
            </CardBody>
          </Card>
        )}
        
        {/* Alertas importantes */}
        <Stack spacing={3}>
          {turnos.filter(t => t.estado === 'reservado' && new Date(t.fecha) <= new Date()).length > 0 && (
            <Alert status="warning" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Turnos próximos</Text>
                <Text>Tiene turnos programados para hoy o fechas pasadas. Verifique su asistencia.</Text>
              </Box>
            </Alert>
          )}
          
          {turnos.filter(t => t.asistio === false).length > 0 && (
            <Alert status="info" borderRadius={{ base: "md", md: "lg" }}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Turnos no asistidos</Text>
                <Text>Recuerde que es importante asistir a todas las citas programadas para su seguimiento médico.</Text>
              </Box>
            </Alert>
          )}
        </Stack>
      </Stack>
    </Box>
  );
};

export default MisTurnos;
