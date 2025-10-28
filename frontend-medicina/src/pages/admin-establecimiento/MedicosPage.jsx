import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, Card, CardBody, 
  Text, HStack, VStack, Button, Input, Select,
  Table, Thead, Tbody, Tr, Th, Td, useToast, Spinner,
  Badge, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalBody, ModalFooter, ModalCloseButton, FormControl,
  FormLabel, Checkbox, CheckboxGroup, useDisclosure
} from '@chakra-ui/react';
import { FaUserMd, FaPlus, FaEdit, FaTrash, FaCalendar } from 'react-icons/fa';
import { CategoriaBadge, ProductividadMedicoCard } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';

const MedicoCard = ({ medico, onEdit, onDelete, onCancelarTurnos }) => (
  <Card>
    <CardBody>
      <Stack spacing={3}>
        <HStack justify="space-between">
          <HStack>
            <FaUserMd color="#4299E1" size={20} />
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold" fontSize={{ base: "sm", md: "md" }}>
                {medico.user.nombre} {medico.user.apellido}
              </Text>
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
                Mat. {medico.matricula}
              </Text>
            </VStack>
          </HStack>
          <Badge colorScheme={medico.activo ? "green" : "red"} fontSize="xs">
            {medico.activo ? "Activo" : "Inactivo"}
          </Badge>
        </HStack>
        
        <HStack spacing={1} flexWrap="wrap">
          {medico.categorias.map(cat => (
            <CategoriaBadge key={cat} categoria={cat} size="sm" />
          ))}
        </HStack>
        
        <HStack justify="space-between">
          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
            {medico.especialidad_medica}
          </Text>
          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.600">
            {medico.disponibilidades?.length || 0} disponibilidades
          </Text>
        </HStack>
        
        <HStack spacing={2}>
          <Button size="sm" onClick={() => onEdit(medico)}>
            <FaEdit />
          </Button>
          <Button size="sm" onClick={() => onCancelarTurnos(medico)}>
            <FaCalendar />
          </Button>
          <Button size="sm" colorScheme="red" onClick={() => onDelete(medico)}>
            <FaTrash />
          </Button>
        </HStack>
      </Stack>
    </CardBody>
  </Card>
);

const MedicosPage = () => {
  const [medicos, setMedicos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroActivo, setFiltroActivo] = useState('');
  const [filtroCategoria, setFiltroCategoria] = useState('');
  const [busqueda, setBusqueda] = useState('');
  
  // Modal para crear/editar
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [modalData, setModalData] = useState({
    id: null,
    nombre: '',
    apellido: '',
    email: '',
    password: '',
    matricula: '',
    especialidad_medica: '',
    categorias: []
  });
  const [guardando, setGuardando] = useState(false);
  
  // Modal para cancelar turnos
  const { isOpen: isOpenCancelar, onOpen: onOpenCancelar, onClose: onCloseCancelar } = useDisclosure();
  const [medicoSeleccionado, setMedicoSeleccionado] = useState(null);
  const [fechaCancelacion, setFechaCancelacion] = useState('');
  const [motivoCancelacion, setMotivoCancelacion] = useState('');
  const [cancelando, setCancelando] = useState(false);
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarMedicos();
  }, [filtroActivo, filtroCategoria, busqueda]);
  
  const cargarMedicos = async () => {
    setLoading(true);
    try {
      console.log('👨‍⚕️ MedicosPage: Cargando médicos...');
      
      // ========================================
      // DATOS MOCK - TEMPORAL HASTA IMPLEMENTAR APIs
      // ========================================
      // TODO: Reemplazar con llamada real a:
      // - /api/ethe/medicos/?con_estadisticas=true
      
      // Simular lista completa de médicos del establecimiento
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
        },
        {
          id: 5,
          user: {
            nombre: 'Dr. Roberto',
            apellido: 'Silva',
            email: 'roberto.silva@ethe.com'
          },
          categorias: ['M2', 'M3'],
          matricula: 'MP33333',
          especialidad_medica: 'Gastroenterología',
          activo: false,
          estadisticas: {
            pacientes_ingresados: 0,
            fibroscan_realizados: 0,
            consultas_realizadas: 0
          }
        }
      ];
      
      // Aplicar filtros si existen
      let medicosFiltrados = medicosMock;
      
      if (filtroActivo) {
        const activo = filtroActivo === 'true';
        medicosFiltrados = medicosFiltrados.filter(m => m.activo === activo);
      }
      
      if (filtroCategoria) {
        medicosFiltrados = medicosFiltrados.filter(m => 
          m.categorias.includes(filtroCategoria)
        );
      }
      
      if (busqueda) {
        const busquedaLower = busqueda.toLowerCase();
        medicosFiltrados = medicosFiltrados.filter(m => 
          m.user.nombre.toLowerCase().includes(busquedaLower) ||
          m.user.apellido.toLowerCase().includes(busquedaLower) ||
          m.user.email.toLowerCase().includes(busquedaLower) ||
          m.matricula.toLowerCase().includes(busquedaLower)
        );
      }
      
      setMedicos(medicosFiltrados);
      console.log('✅ MedicosPage: Médicos cargados (mock):', medicosFiltrados);
      
    } catch (error) {
      console.error('❌ MedicosPage: Error cargando médicos:', error);
      toast({
        title: "Error",
        description: "Error cargando médicos",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleCrear = () => {
    setModalData({
      id: null,
      nombre: '',
      apellido: '',
      email: '',
      password: '',
      matricula: '',
      especialidad_medica: '',
      categorias: []
    });
    onOpen();
  };
  
  const handleEditar = (medico) => {
    setModalData({
      id: medico.id,
      nombre: medico.user.nombre,
      apellido: medico.user.apellido,
      email: medico.user.email,
      password: '',
      matricula: medico.matricula,
      especialidad_medica: medico.especialidad_medica,
      categorias: medico.categorias
    });
    onOpen();
  };
  
  const handleGuardar = async () => {
    if (!modalData.categorias.length) {
      toast({
        title: "Error",
        description: "Debe seleccionar al menos una categoría",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setGuardando(true);
    try {
      const url = modalData.id 
        ? `/api/ethe/medicos/${modalData.id}/`
        : '/api/ethe/medicos/';
      
      const method = modalData.id ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(modalData)
      });
      
      if (response.ok) {
        toast({
          title: "Éxito",
          description: modalData.id ? "Médico actualizado" : "Médico creado",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        
        onClose();
        cargarMedicos();
      } else {
        throw new Error('Error guardando médico');
      }
      
    } catch (error) {
      console.error('Error guardando médico:', error);
      toast({
        title: "Error",
        description: "Error guardando médico",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setGuardando(false);
    }
  };
  
  const handleCancelarTurnos = (medico) => {
    setMedicoSeleccionado(medico);
    setFechaCancelacion('');
    setMotivoCancelacion('');
    onOpenCancelar();
  };
  
  const handleConfirmarCancelacion = async () => {
    if (!fechaCancelacion || !motivoCancelacion) {
      toast({
        title: "Error",
        description: "Debe completar fecha y motivo",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setCancelando(true);
    try {
      const response = await fetch('/api/turnos/cancelar-masivo/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          medico_id: medicoSeleccionado.id,
          fecha: fechaCancelacion,
          motivo: motivoCancelacion
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
        
        onCloseCancelar();
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
    } finally {
      setCancelando(false);
    }
  };
  
  const handleEliminar = async (medico) => {
    if (window.confirm(`¿Está seguro de eliminar ${medico.user.nombre} ${medico.user.apellido}?`)) {
      try {
        const response = await fetch(`/api/ethe/medicos/${medico.id}/`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${user.token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          toast({
            title: "Éxito",
            description: "Médico eliminado",
            status: "success",
            duration: 3000,
            isClosable: true,
          });
          
          cargarMedicos();
        } else {
          throw new Error('Error eliminando médico');
        }
        
      } catch (error) {
        console.error('Error eliminando médico:', error);
        toast({
          title: "Error",
          description: "Error eliminando médico",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
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
        <HStack justify="space-between">
          <Heading size={{ base: "lg", md: "xl" }}>Médicos</Heading>
          <Button 
            leftIcon={<FaPlus />} 
            onClick={handleCrear}
            size={{ base: "sm", md: "md" }}
          >
            Nuevo Médico
          </Button>
        </HStack>
        
        {/* Filtros responsive */}
        <Stack direction={{ base: "column", md: "row" }} spacing={{ base: 3, md: 4 }}>
          <Input
            placeholder="Buscar médicos..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            w={{ base: "100%", md: "300px" }}
            size={{ base: "sm", md: "md" }}
          />
          
          <Select
            placeholder="Todas las categorías"
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          >
            <option value="M1">M1</option>
            <option value="M2">M2</option>
            <option value="M3">M3</option>
          </Select>
          
          <Select
            placeholder="Todos los estados"
            value={filtroActivo}
            onChange={(e) => setFiltroActivo(e.target.value)}
            w={{ base: "100%", md: "200px" }}
            size={{ base: "sm", md: "md" }}
          >
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </Select>
        </Stack>
        
        {/* Tabla responsive (Desktop) */}
        <Box display={{ base: "none", md: "block" }} overflowX="auto">
          <Table variant="simple" size={{ base: "sm", md: "md" }}>
            <Thead>
              <Tr>
                <Th>Médico</Th>
                <Th>Categorías</Th>
                <Th>Matrícula</Th>
                <Th>Especialidad</Th>
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
                        {medico.user.email}
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
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {medico.matricula}
                  </Td>
                  <Td fontSize={{ base: "sm", md: "md" }}>
                    {medico.especialidad_medica}
                  </Td>
                  <Td>
                    <Badge colorScheme={medico.activo ? "green" : "red"}>
                      {medico.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      <Button size="sm" onClick={() => handleEditar(medico)}>
                        <FaEdit />
                      </Button>
                      <Button size="sm" onClick={() => handleCancelarTurnos(medico)}>
                        <FaCalendar />
                      </Button>
                      <Button size="sm" colorScheme="red" onClick={() => handleEliminar(medico)}>
                        <FaTrash />
                      </Button>
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
        
        {/* Cards responsive (Mobile) */}
        <SimpleGrid display={{ base: "grid", md: "none" }} columns={1} spacing={3}>
          {medicos.map(medico => (
            <MedicoCard
              key={medico.id}
              medico={medico}
              onEdit={handleEditar}
              onDelete={handleEliminar}
              onCancelarTurnos={handleCancelarTurnos}
            />
          ))}
        </SimpleGrid>
        
        {medicos.length === 0 && (
          <Card>
            <CardBody>
              <Text textAlign="center" color="gray.500">
                No hay médicos que coincidan con los filtros
              </Text>
            </CardBody>
          </Card>
        )}
      </Stack>
      
      {/* Modal crear/editar médico */}
      <Modal isOpen={isOpen} onClose={onClose} size={{ base: "full", md: "xl" }}>
        <ModalOverlay />
        <ModalContent m={{ base: 0, md: 4 }}>
          <ModalHeader fontSize={{ base: "lg", md: "xl" }}>
            {modalData.id ? 'Editar Médico' : 'Nuevo Médico'}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Stack spacing={4}>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl isRequired>
                  <FormLabel fontSize={{ base: "sm", md: "md" }}>Nombre</FormLabel>
                  <Input
                    value={modalData.nombre}
                    onChange={(e) => setModalData(prev => ({ ...prev, nombre: e.target.value }))}
                    placeholder="Carlos"
                    size={{ base: "sm", md: "md" }}
                  />
                </FormControl>
                
                <FormControl isRequired>
                  <FormLabel fontSize={{ base: "sm", md: "md" }}>Apellido</FormLabel>
                  <Input
                    value={modalData.apellido}
                    onChange={(e) => setModalData(prev => ({ ...prev, apellido: e.target.value }))}
                    placeholder="García"
                    size={{ base: "sm", md: "md" }}
                  />
                </FormControl>
              </SimpleGrid>
              
              <FormControl isRequired>
                <FormLabel fontSize={{ base: "sm", md: "md" }}>Email</FormLabel>
                <Input
                  type="email"
                  value={modalData.email}
                  onChange={(e) => setModalData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="dr.garcia@hospital.com"
                  size={{ base: "sm", md: "md" }}
                />
              </FormControl>
              
              {!modalData.id && (
                <FormControl isRequired>
                  <FormLabel fontSize={{ base: "sm", md: "md" }}>Contraseña</FormLabel>
                  <Input
                    type="password"
                    value={modalData.password}
                    onChange={(e) => setModalData(prev => ({ ...prev, password: e.target.value }))}
                    placeholder="Contraseña temporal"
                    size={{ base: "sm", md: "md" }}
                  />
                </FormControl>
              )}
              
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl isRequired>
                  <FormLabel fontSize={{ base: "sm", md: "md" }}>Matrícula</FormLabel>
                  <Input
                    value={modalData.matricula}
                    onChange={(e) => setModalData(prev => ({ ...prev, matricula: e.target.value }))}
                    placeholder="12345"
                    size={{ base: "sm", md: "md" }}
                  />
                </FormControl>
                
                <FormControl>
                  <FormLabel fontSize={{ base: "sm", md: "md" }}>Especialidad</FormLabel>
                  <Input
                    value={modalData.especialidad_medica}
                    onChange={(e) => setModalData(prev => ({ ...prev, especialidad_medica: e.target.value }))}
                    placeholder="Hepatología"
                    size={{ base: "sm", md: "md" }}
                  />
                </FormControl>
              </SimpleGrid>
              
              <FormControl isRequired>
                <FormLabel fontSize={{ base: "sm", md: "md" }}>Categorías</FormLabel>
                <CheckboxGroup
                  value={modalData.categorias}
                  onChange={(value) => setModalData(prev => ({ ...prev, categorias: value }))}
                >
                  <Stack direction={{ base: "column", md: "row" }} spacing={3}>
                    <Checkbox value="M1">M1</Checkbox>
                    <Checkbox value="M2">M2</Checkbox>
                    <Checkbox value="M3">M3</Checkbox>
                  </Stack>
                </CheckboxGroup>
              </FormControl>
            </Stack>
          </ModalBody>
          <ModalFooter>
            <Stack direction={{ base: "column", sm: "row" }} spacing={2} w="100%">
              <Button
                onClick={handleGuardar}
                isLoading={guardando}
                loadingText="Guardando..."
                colorScheme="blue"
                flex={{ base: 1, sm: "none" }}
              >
                Guardar
              </Button>
              <Button
                variant="outline"
                onClick={onClose}
                flex={{ base: 1, sm: "none" }}
              >
                Cancelar
              </Button>
            </Stack>
          </ModalFooter>
        </ModalContent>
      </Modal>
      
      {/* Modal cancelar turnos */}
      <Modal isOpen={isOpenCancelar} onClose={onCloseCancelar} size={{ base: "full", md: "md" }}>
        <ModalOverlay />
        <ModalContent m={{ base: 0, md: 4 }}>
          <ModalHeader fontSize={{ base: "lg", md: "xl" }}>
            Cancelar Turnos Masivamente
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Stack spacing={4}>
              <Text fontSize={{ base: "sm", md: "md" }}>
                Médico: {medicoSeleccionado?.user.nombre} {medicoSeleccionado?.user.apellido}
              </Text>
              
              <FormControl isRequired>
                <FormLabel fontSize={{ base: "sm", md: "md" }}>Fecha</FormLabel>
                <Input
                  type="date"
                  value={fechaCancelacion}
                  onChange={(e) => setFechaCancelacion(e.target.value)}
                  size={{ base: "sm", md: "md" }}
                />
              </FormControl>
              
              <FormControl isRequired>
                <FormLabel fontSize={{ base: "sm", md: "md" }}>Motivo</FormLabel>
                <Input
                  value={motivoCancelacion}
                  onChange={(e) => setMotivoCancelacion(e.target.value)}
                  placeholder="Feriado, licencia médica, etc."
                  size={{ base: "sm", md: "md" }}
                />
              </FormControl>
            </Stack>
          </ModalBody>
          <ModalFooter>
            <Stack direction={{ base: "column", sm: "row" }} spacing={2} w="100%">
              <Button
                onClick={handleConfirmarCancelacion}
                isLoading={cancelando}
                loadingText="Cancelando..."
                colorScheme="red"
                flex={{ base: 1, sm: "none" }}
              >
                Cancelar Turnos
              </Button>
              <Button
                variant="outline"
                onClick={onCloseCancelar}
                flex={{ base: 1, sm: "none" }}
              >
                Cancelar
              </Button>
            </Stack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default MedicosPage;
