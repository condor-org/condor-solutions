import React, { useState, useEffect } from 'react';
import { 
  Box, Stack, Heading, SimpleGrid, FormControl, FormLabel, 
  Input, Select, Textarea, Button, Alert, AlertIcon, 
  Text, useToast, Spinner, VStack, HStack
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { CategoriaBadge, CentroCard } from '../../components/ethe';
import { useAuth } from '../../auth/AuthContext';
import { API_ENDPOINTS } from '../../config/api';

const IngresarPaciente = () => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    // Datos personales
    documento: '',
    nombre: '',
    apellido: '',
    email: '',
    telefono: '',
    fecha_nacimiento: '',
    obra_social: '',
    
    // Domicilio
    domicilio_calle: '',
    domicilio_ciudad: '',
    domicilio_provincia: '',
    domicilio_codigo_postal: '',
    
    // Tests
    resultado_pocus: 'HG', // Default: Hígado Graso
    resultado_fib4: '',
  });
  
  const [centrosC2, setCentrosC2] = useState([]);
  const [selectedCentro, setSelectedCentro] = useState(null);
  const [turnosDisponibles, setTurnosDisponibles] = useState([]);
  const [selectedTurno, setSelectedTurno] = useState(null);
  
  const toast = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Cargar centros C2 cuando FIB4 = R
  useEffect(() => {
    if (formData.resultado_fib4 === 'R') {
      cargarCentrosC2();
    }
  }, [formData.resultado_fib4]);
  
  // Cargar turnos cuando se selecciona centro
  useEffect(() => {
    if (selectedCentro) {
      cargarTurnosDisponibles();
    }
  }, [selectedCentro]);
  
  const cargarCentrosC2 = async () => {
    try {
      const response = await fetch(`${API_ENDPOINTS.CENTROS}?categorias=C2`, {
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setCentrosC2(data);
    } catch (error) {
      console.error('Error cargando centros C2:', error);
      toast({
        title: "Error",
        description: "Error cargando centros C2",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };
  
  const cargarTurnosDisponibles = async () => {
    try {
      const response = await fetch(`${API_ENDPOINTS.TURNOS_DISPONIBLES}?centro=${selectedCentro.id}&medico_cat=M2`, {
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setTurnosDisponibles(data);
    } catch (error) {
      console.error('Error cargando turnos:', error);
      toast({
        title: "Error",
        description: "Error cargando turnos disponibles",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleIngresar = async () => {
    setLoading(true);
    
    try {
      // 1. Ingresar paciente
      const response = await fetch(API_ENDPOINTS.PACIENTE_INGRESAR, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error || 'Error ingresando paciente');
      }
      
      // 2. Si C2 y hay turno seleccionado, reservar turno
      if (result.categoria === 'C2' && selectedTurno) {
        const turnoResponse = await fetch(API_ENDPOINTS.TURNOS_RESERVAR, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${user.token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            paciente_id: result.paciente.id,
            turno_id: selectedTurno.id
          })
        });
        
        if (!turnoResponse.ok) {
          throw new Error('Error reservando turno');
        }
      }
      
      toast({
        title: "Paciente ingresado exitosamente",
        description: `Categoría asignada: ${result.categoria}`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      
      navigate('/medico-m1/pacientes');
      
    } catch (error) {
      toast({
        title: "Error",
        description: error.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleCancelar = () => {
    navigate('/medico-m1/dashboard');
  };
  
  return (
    <Box flex="1" p={{ base: 4, md: 6 }}>
      <Stack spacing={{ base: 4, md: 6 }}>
        <Heading size={{ base: "lg", md: "xl" }}>Ingresar Paciente</Heading>
        
        {/* Datos Personales */}
        <Box>
          <Heading size={{ base: "md", md: "lg" }} mb={4}>Datos Personales</Heading>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={{ base: 3, md: 4 }}>
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Documento</FormLabel>
              <Input
                name="documento"
                value={formData.documento}
                onChange={handleInputChange}
                placeholder="DNI/CUIL"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Nombre</FormLabel>
              <Input
                name="nombre"
                value={formData.nombre}
                onChange={handleInputChange}
                placeholder="Nombre"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Apellido</FormLabel>
              <Input
                name="apellido"
                value={formData.apellido}
                onChange={handleInputChange}
                placeholder="Apellido"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Email</FormLabel>
              <Input
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="email@ejemplo.com"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Teléfono</FormLabel>
              <Input
                name="telefono"
                value={formData.telefono}
                onChange={handleInputChange}
                placeholder="123456789"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Fecha Nacimiento</FormLabel>
              <Input
                name="fecha_nacimiento"
                type="date"
                value={formData.fecha_nacimiento}
                onChange={handleInputChange}
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Obra Social</FormLabel>
              <Input
                name="obra_social"
                value={formData.obra_social}
                onChange={handleInputChange}
                placeholder="OSDE, Swiss Medical, etc."
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
          </SimpleGrid>
        </Box>
        
        {/* Domicilio */}
        <Box>
          <Heading size={{ base: "md", md: "lg" }} mb={4}>Domicilio</Heading>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={{ base: 3, md: 4 }}>
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Calle</FormLabel>
              <Input
                name="domicilio_calle"
                value={formData.domicilio_calle}
                onChange={handleInputChange}
                placeholder="Av. Corrientes 1234"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Ciudad</FormLabel>
              <Input
                name="domicilio_ciudad"
                value={formData.domicilio_ciudad}
                onChange={handleInputChange}
                placeholder="Buenos Aires"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Provincia</FormLabel>
              <Input
                name="domicilio_provincia"
                value={formData.domicilio_provincia}
                onChange={handleInputChange}
                placeholder="CABA"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
            
            <FormControl>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>Código Postal</FormLabel>
              <Input
                name="domicilio_codigo_postal"
                value={formData.domicilio_codigo_postal}
                onChange={handleInputChange}
                placeholder="1000"
                size={{ base: "sm", md: "md" }}
              />
            </FormControl>
          </SimpleGrid>
        </Box>
        
        {/* Resultados de Tests */}
        <Box>
          <Heading size={{ base: "md", md: "lg" }} mb={4}>Resultados de Tests</Heading>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={{ base: 3, md: 4 }}>
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>POCUS</FormLabel>
              <Select
                name="resultado_pocus"
                value={formData.resultado_pocus}
                onChange={handleInputChange}
                size={{ base: "sm", md: "md" }}
              >
                <option value="NORMAL">Normal</option>
                <option value="HG">Hígado Graso (HG)</option>
              </Select>
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500" mt={1}>
                Por defecto: Hígado Graso
              </Text>
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel fontSize={{ base: "sm", md: "md" }}>FIB4</FormLabel>
              <Select
                name="resultado_fib4"
                value={formData.resultado_fib4}
                onChange={handleInputChange}
                size={{ base: "sm", md: "md" }}
                placeholder="Seleccione..."
              >
                <option value="NR">No Riesgo (NR)</option>
                <option value="R">Riesgo (R)</option>
              </Select>
            </FormControl>
          </SimpleGrid>
        </Box>
        
        {/* Si POCUS = Normal, mostrar mensaje */}
        {formData.resultado_pocus === 'NORMAL' && (
          <Alert status="info" borderRadius={{ base: "md", md: "lg" }}>
            <AlertIcon />
            <Box fontSize={{ base: "sm", md: "md" }}>
              <Text fontWeight="bold">Paciente no requiere ingreso</Text>
              <Text>POCUS Normal - No ingresa al sistema</Text>
            </Box>
          </Alert>
        )}
        
        {/* Si FIB4 = R, mostrar centros C2 */}
        {formData.resultado_pocus === 'HG' && formData.resultado_fib4 === 'R' && centrosC2.length > 0 && (
          <Box>
            <Heading size={{ base: "md", md: "lg" }} mb={4}>Asignar Centro C2</Heading>
            <Alert status="info" borderRadius={{ base: "md", md: "lg" }} mb={4}>
              <AlertIcon />
              <Box fontSize={{ base: "sm", md: "md" }}>
                <Text fontWeight="bold">Paciente requiere atención C2</Text>
                <Text>Seleccione centro y turno para continuar</Text>
              </Box>
            </Alert>
            
            {/* Grid responsive de centros */}
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={{ base: 3, md: 4 }} mb={6}>
              {centrosC2.map(centro => (
                <CentroCard
                  key={centro.id}
                  centro={centro}
                  onSelect={() => setSelectedCentro(centro)}
                  selected={selectedCentro?.id === centro.id}
                />
              ))}
            </SimpleGrid>
            
            {/* Calendario de turnos */}
            {selectedCentro && turnosDisponibles.length > 0 && (
              <Box>
                <Heading size={{ base: "sm", md: "md" }} mb={3}>Turnos Disponibles</Heading>
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={{ base: 2, md: 3 }}>
                  {turnosDisponibles.map(turno => (
                    <Button
                      key={turno.id}
                      variant={selectedTurno?.id === turno.id ? "solid" : "outline"}
                      colorScheme={selectedTurno?.id === turno.id ? "blue" : "gray"}
                      onClick={() => setSelectedTurno(turno)}
                      size={{ base: "sm", md: "md" }}
                      p={{ base: 2, md: 3 }}
                    >
                      {new Date(turno.fecha).toLocaleDateString()} - {turno.hora}
                    </Button>
                  ))}
                </SimpleGrid>
              </Box>
            )}
          </Box>
        )}
        
        {/* Botones responsive */}
        <Stack direction={{ base: "column", md: "row" }} spacing={{ base: 3, md: 4 }}>
          <Button 
            onClick={handleIngresar} 
            isLoading={loading}
            loadingText="Ingresando..."
            colorScheme="blue"
            size={{ base: "md", md: "lg" }}
            flex={{ base: 1, md: "none" }}
            isDisabled={formData.resultado_pocus === 'NORMAL'}
          >
            Ingresar Paciente
          </Button>
          <Button 
            variant="outline" 
            onClick={handleCancelar}
            size={{ base: "md", md: "lg" }}
            flex={{ base: 1, md: "none" }}
          >
            Cancelar
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
};

export default IngresarPaciente;
