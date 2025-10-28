import React, { useState, useEffect } from 'react';
import {
  Box, Stack, Heading, SimpleGrid, Card, CardBody,
  Text, HStack, VStack, Table, Thead, Tbody, Tr, Th, Td,
  useToast, Spinner, Badge, Button, Modal, ModalOverlay,
  ModalContent, ModalHeader, ModalBody, ModalCloseButton,
  FormControl, FormLabel, Input, Textarea, Select,
  useDisclosure, Alert, AlertIcon, IconButton
} from '@chakra-ui/react';
import { FaPlus, FaEdit, FaUserPlus, FaHospital, FaPhone, FaEnvelope, FaMapMarkerAlt } from 'react-icons/fa';
import { useAuth } from '../../auth/AuthContext';

const EstablecimientosPage = () => {
  const [establecimientos, setEstablecimientos] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creando, setCreando] = useState(false);
  const [asignando, setAsignando] = useState(false);
  
  const { isOpen: isCreateOpen, onOpen: onCreateOpen, onClose: onCreateClose } = useDisclosure();
  const { isOpen: isAssignOpen, onOpen: onAssignOpen, onClose: onAssignClose } = useDisclosure();
  
  const [formData, setFormData] = useState({
    nombre: '',
    direccion: '',
    telefono: '',
    email: ''
  });
  
  const [assignData, setAssignData] = useState({
    establecimiento_id: null,
    admin_id: null
  });
  
  const toast = useToast();
  const { user } = useAuth();
  
  useEffect(() => {
    cargarEstablecimientos();
    cargarAdmins();
  }, []);
  
  const cargarEstablecimientos = async () => {
    try {
      setLoading(true);
      console.log('🏥 EstablecimientosPage: Cargando establecimientos...');
      
      // TODO: Implementar llamada real a la API
      // const response = await fetch('/api/ethe/ministro/establecimientos/', {
      //   headers: { 'Authorization': `Bearer ${user.token}` }
      // });
      // const data = await response.json();
      
      // Datos mock por ahora
      const establecimientosMock = [
        {
          id: 1,
          nombre: "Hospital Central ETHE",
          direccion: "Av. Corrientes 1234, CABA",
          telefono: "011-4567-8900",
          email: "info@hospital-ethe.com",
          activo: true,
          admin_establecimiento: {
            id: 32,
            nombre: "Admin Establecimiento",
            email: "admin.establecimiento@ethe.com"
          },
          medicos_count: 0,
          pacientes_count: 0
        },
        {
          id: 2,
          nombre: "Hospital Regional ETHE Norte",
          direccion: "Av. Libertador 2500, CABA",
          telefono: "011-4567-8901",
          email: "info@hospital-norte-ethe.com",
          activo: true,
          admin_establecimiento: {
            id: 36,
            nombre: "María Rodríguez",
            email: "maria.rodriguez@ethe.com"
          },
          medicos_count: 0,
          pacientes_count: 0
        }
      ];
      
      setEstablecimientos(establecimientosMock);
      console.log('✅ EstablecimientosPage: Establecimientos cargados:', establecimientosMock);
      
    } catch (error) {
      console.error('❌ EstablecimientosPage: Error cargando establecimientos:', error);
      toast({
        title: "Error",
        description: "Error cargando establecimientos",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const cargarAdmins = async () => {
    try {
      // TODO: Implementar llamada real a la API para obtener admins disponibles
      const adminsMock = [
        { id: 1, nombre: "Admin 1", email: "admin1@ethe.com" },
        { id: 2, nombre: "Admin 2", email: "admin2@ethe.com" }
      ];
      setAdmins(adminsMock);
    } catch (error) {
      console.error('Error cargando admins:', error);
    }
  };
  
  const handleCrearEstablecimiento = async () => {
    try {
      setCreando(true);
      
      // TODO: Implementar llamada real a la API
      // const response = await fetch('/api/ethe/ministro/establecimientos/', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${user.token}`
      //   },
      //   body: JSON.stringify(formData)
      // });
      
      console.log('Creando establecimiento:', formData);
      
      toast({
        title: "Éxito",
        description: "Establecimiento creado correctamente",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      onCreateClose();
      setFormData({ nombre: '', direccion: '', telefono: '', email: '' });
      cargarEstablecimientos();
      
    } catch (error) {
      console.error('Error creando establecimiento:', error);
      toast({
        title: "Error",
        description: "Error creando establecimiento",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setCreando(false);
    }
  };
  
  const handleAsignarAdmin = async () => {
    try {
      setAsignando(true);
      
      // TODO: Implementar llamada real a la API
      // const response = await fetch(`/api/ethe/ministro/asignar-admin-establecimiento/${assignData.establecimiento_id}/`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${user.token}`
      //   },
      //   body: JSON.stringify({ admin_id: assignData.admin_id })
      // });
      
      console.log('Asignando admin:', assignData);
      
      toast({
        title: "Éxito",
        description: "Admin asignado correctamente",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      onAssignClose();
      setAssignData({ establecimiento_id: null, admin_id: null });
      cargarEstablecimientos();
      
    } catch (error) {
      console.error('Error asignando admin:', error);
      toast({
        title: "Error",
        description: "Error asignando admin",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setAsignando(false);
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
          <Heading size={{ base: "lg", md: "xl" }}>Gestión de Establecimientos</Heading>
          <Button
            colorScheme="blue"
            leftIcon={<FaPlus />}
            onClick={onCreateOpen}
          >
            Nuevo Establecimiento
          </Button>
        </HStack>
        
        {/* Lista de establecimientos */}
        <Card>
          <CardBody>
            <Table variant="simple" size={{ base: "sm", md: "md" }}>
              <Thead>
                <Tr>
                  <Th>Establecimiento</Th>
                  <Th>Contacto</Th>
                  <Th>Admin Asignado</Th>
                  <Th>Estado</Th>
                  <Th>Acciones</Th>
                </Tr>
              </Thead>
              <Tbody>
                {establecimientos.map(est => (
                  <Tr key={est.id}>
                    <Td>
                      <VStack align="start" spacing={1}>
                        <Text fontWeight="bold">{est.nombre}</Text>
                        <HStack spacing={2} fontSize="sm" color="gray.600">
                          <FaMapMarkerAlt />
                          <Text>{est.direccion}</Text>
                        </HStack>
                      </VStack>
                    </Td>
                    <Td>
                      <VStack align="start" spacing={1} fontSize="sm">
                        <HStack spacing={2}>
                          <FaPhone />
                          <Text>{est.telefono}</Text>
                        </HStack>
                        <HStack spacing={2}>
                          <FaEnvelope />
                          <Text>{est.email}</Text>
                        </HStack>
                      </VStack>
                    </Td>
                    <Td>
                      {est.admin_establecimiento ? (
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">{est.admin_establecimiento.nombre}</Text>
                          <Text fontSize="sm" color="gray.600">{est.admin_establecimiento.email}</Text>
                        </VStack>
                      ) : (
                        <Text color="gray.500" fontSize="sm">Sin asignar</Text>
                      )}
                    </Td>
                    <Td>
                      <Badge colorScheme={est.activo ? "green" : "red"}>
                        {est.activo ? "Activo" : "Inactivo"}
                      </Badge>
                    </Td>
                    <Td>
                      <HStack spacing={2}>
                        <IconButton
                          icon={<FaEdit />}
                          size="sm"
                          variant="ghost"
                          colorScheme="blue"
                          aria-label="Editar"
                        />
                        <IconButton
                          icon={<FaUserPlus />}
                          size="sm"
                          variant="ghost"
                          colorScheme="green"
                          aria-label="Asignar Admin"
                          onClick={() => {
                            setAssignData({ ...assignData, establecimiento_id: est.id });
                            onAssignOpen();
                          }}
                        />
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
        
        {/* Modal Crear Establecimiento */}
        <Modal isOpen={isCreateOpen} onClose={onCreateClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Crear Nuevo Establecimiento</ModalHeader>
            <ModalCloseButton />
            <ModalBody pb={6}>
              <Stack spacing={4}>
                <FormControl isRequired>
                  <FormLabel>Nombre</FormLabel>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Nombre del establecimiento"
                  />
                </FormControl>
                
                <FormControl>
                  <FormLabel>Dirección</FormLabel>
                  <Textarea
                    value={formData.direccion}
                    onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                    placeholder="Dirección completa"
                  />
                </FormControl>
                
                <FormControl>
                  <FormLabel>Teléfono</FormLabel>
                  <Input
                    value={formData.telefono}
                    onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                    placeholder="Teléfono de contacto"
                  />
                </FormControl>
                
                <FormControl>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="Email de contacto"
                  />
                </FormControl>
                
                <HStack justify="flex-end" spacing={3}>
                  <Button onClick={onCreateClose}>Cancelar</Button>
                  <Button
                    colorScheme="blue"
                    onClick={handleCrearEstablecimiento}
                    isLoading={creando}
                    loadingText="Creando..."
                  >
                    Crear
                  </Button>
                </HStack>
              </Stack>
            </ModalBody>
          </ModalContent>
        </Modal>
        
        {/* Modal Asignar Admin */}
        <Modal isOpen={isAssignOpen} onClose={onAssignClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Asignar Administrador</ModalHeader>
            <ModalCloseButton />
            <ModalBody pb={6}>
              <Stack spacing={4}>
                <FormControl isRequired>
                  <FormLabel>Administrador</FormLabel>
                  <Select
                    value={assignData.admin_id || ''}
                    onChange={(e) => setAssignData({ ...assignData, admin_id: parseInt(e.target.value) })}
                    placeholder="Seleccionar administrador"
                  >
                    {admins.map(admin => (
                      <option key={admin.id} value={admin.id}>
                        {admin.nombre} ({admin.email})
                      </option>
                    ))}
                  </Select>
                </FormControl>
                
                <Alert status="info">
                  <AlertIcon />
                  <Text fontSize="sm">
                    Se asignará el administrador seleccionado al establecimiento.
                  </Text>
                </Alert>
                
                <HStack justify="flex-end" spacing={3}>
                  <Button onClick={onAssignClose}>Cancelar</Button>
                  <Button
                    colorScheme="green"
                    onClick={handleAsignarAdmin}
                    isLoading={asignando}
                    loadingText="Asignando..."
                  >
                    Asignar
                  </Button>
                </HStack>
              </Stack>
            </ModalBody>
          </ModalContent>
        </Modal>
      </Stack>
    </Box>
  );
};

export default EstablecimientosPage;