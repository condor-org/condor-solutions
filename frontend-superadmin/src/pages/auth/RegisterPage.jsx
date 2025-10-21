// src/pages/auth/RegisterPage.jsx
import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  Box, 
  Heading, 
  Text, 
  VStack, 
  Input, 
  InputGroup, 
  InputRightElement, 
  IconButton,
  Alert,
  AlertIcon,
  FormControl,
  FormLabel,
  FormErrorMessage,
  HStack,
  Button as ChakraButton
} from "@chakra-ui/react";
import { ViewIcon, ViewOffIcon } from "@chakra-ui/icons";
import Button from "../../components/ui/Button";
import { useAuth } from "../../auth/AuthContext";

const RegisterPage = () => {
  const navigate = useNavigate();
  const { sendVerificationCode, verifyCode } = useAuth();
  
  const [step, setStep] = useState(1); // 1: formulario, 2: verificación
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  
  // Datos del formulario
  const [formData, setFormData] = useState({
    nombre: "",
    apellido: "",
    email: "",
    telefono: "",
    password: "",
    confirmPassword: ""
  });
  
  // Datos de verificación
  const [verificationData, setVerificationData] = useState({
    codigo: ""
  });
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleSubmitForm = async (e) => {
    e.preventDefault();
    
    // Validaciones
    if (!formData.nombre || !formData.apellido || !formData.email || !formData.password) {
      setError("Por favor completa todos los campos obligatorios");
      return;
    }
    
    if (formData.password !== formData.confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }
    
    if (formData.password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres");
      return;
    }

    try {
      setIsLoading(true);
      setError("");
      
      await sendVerificationCode({
        email: formData.email,
        intent: "registro",
        nombre: formData.nombre,
        apellido: formData.apellido,
        telefono: formData.telefono
      });
      
      setStep(2);
      setSuccess("Te enviamos un código de verificación a tu email");
    } catch (err) {
      setError(err.message || "Error al enviar el código de verificación");
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    
    if (!verificationData.codigo) {
      setError("Por favor ingresa el código de verificación");
      return;
    }

    try {
      setIsLoading(true);
      setError("");
      
      await verifyCode({
        email: formData.email,
        codigo: verificationData.codigo,
        intent: "registro",
        password: formData.password
      });
      
      setSuccess("¡Registro exitoso! Redirigiendo...");
      setTimeout(() => {
        navigate("/");
      }, 2000);
    } catch (err) {
      setError(err.message || "Error al verificar el código");
      setIsLoading(false);
    }
  };

  const handleResendCode = async () => {
    try {
      setIsLoading(true);
      setError("");
      
      await sendVerificationCode({
        email: formData.email,
        intent: "registro",
        nombre: formData.nombre,
        apellido: formData.apellido,
        telefono: formData.telefono
      });
      
      setSuccess("Código reenviado correctamente");
    } catch (err) {
      setError(err.message || "Error al reenviar el código");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box
      minH="100vh"
      bgGradient="linear(to-br, blue.50, blue.100)"
      position="relative"
      overflow="hidden"
      display="flex"
      alignItems="center"
      justifyContent="center"
      px={{ base: 4, sm: 6 }}
      py={{ base: 16, md: 24 }}
    >
      {/* Sutiles halos decorativos */}
      <Box
        position="absolute"
        top="-20%"
        right="-10%"
        w="60vw"
        h="60vw"
        bgGradient="radial(circle, rgba(59,130,246,0.18), rgba(59,130,246,0))"
        filter="blur(40px)"
        pointerEvents="none"
      />
      <Box
        position="absolute"
        bottom="-25%"
        left="-15%"
        w="70vw"
        h="70vw"
        bgGradient="radial(circle, rgba(37,99,235,0.12), rgba(37,99,235,0))"
        filter="blur(48px)"
        pointerEvents="none"
      />

      {/* Tarjeta centrada */}
      <Box
        w="100%"
        maxW="md"
        bg="white"
        borderRadius="xl"
        boxShadow="xl"
        px={{ base: 6, sm: 8 }}
        py={{ base: 8, sm: 10 }}
        position="relative"
        zIndex={1}
      >
        <VStack spacing={6} align="stretch" textAlign="center">
          <Heading size="lg" color="gray.800">
            {step === 1 ? "Crear cuenta" : "Verifica tu email"}
          </Heading>
          <Text color="gray.600" fontSize="sm">
            {step === 1 
              ? "Completá tus datos para registrarte" 
              : "Ingresá el código que te enviamos a tu email"
            }
          </Text>

          {error && (
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              {error}
            </Alert>
          )}

          {success && (
            <Alert status="success" borderRadius="md">
              <AlertIcon />
              {success}
            </Alert>
          )}

          {step === 1 ? (
            <form onSubmit={handleSubmitForm}>
              <VStack spacing={4} align="stretch">
                <HStack spacing={4}>
                  <FormControl isRequired>
                    <FormLabel fontSize="sm" color="gray.700">Nombre</FormLabel>
                    <Input
                      value={formData.nombre}
                      onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                      placeholder="Tu nombre"
                      size="lg"
                    />
                  </FormControl>
                  <FormControl isRequired>
                    <FormLabel fontSize="sm" color="gray.700">Apellido</FormLabel>
                    <Input
                      value={formData.apellido}
                      onChange={(e) => setFormData({...formData, apellido: e.target.value})}
                      placeholder="Tu apellido"
                      size="lg"
                    />
                  </FormControl>
                </HStack>

                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Email</FormLabel>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    placeholder="tu@email.com"
                    size="lg"
                  />
                </FormControl>

                <FormControl>
                  <FormLabel fontSize="sm" color="gray.700">Teléfono (opcional)</FormLabel>
                  <Input
                    type="tel"
                    value={formData.telefono}
                    onChange={(e) => setFormData({...formData, telefono: e.target.value})}
                    placeholder="+54 9 11 1234-5678"
                    size="lg"
                  />
                </FormControl>

                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Contraseña</FormLabel>
                  <InputGroup size="lg">
                    <Input
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={(e) => setFormData({...formData, password: e.target.value})}
                      placeholder="Mínimo 8 caracteres"
                    />
                    <InputRightElement>
                      <IconButton
                        aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                        icon={showPassword ? <ViewOffIcon /> : <ViewIcon />}
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowPassword(!showPassword)}
                      />
                    </InputRightElement>
                  </InputGroup>
                </FormControl>

                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Confirmar contraseña</FormLabel>
                  <InputGroup size="lg">
                    <Input
                      type={showConfirmPassword ? "text" : "password"}
                      value={formData.confirmPassword}
                      onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                      placeholder="Repetí tu contraseña"
                    />
                    <InputRightElement>
                      <IconButton
                        aria-label={showConfirmPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                        icon={showConfirmPassword ? <ViewOffIcon /> : <ViewIcon />}
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      />
                    </InputRightElement>
                  </InputGroup>
                </FormControl>

                <Button
                  type="submit"
                  width="full"
                  size="lg"
                  isLoading={isLoading}
                  loadingText="Enviando código..."
                  isDisabled={isLoading}
                >
                  Enviar código de verificación
                </Button>
              </VStack>
            </form>
          ) : (
            <form onSubmit={handleVerifyCode}>
              <VStack spacing={4} align="stretch">
                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Código de verificación</FormLabel>
                  <Input
                    value={verificationData.codigo}
                    onChange={(e) => setVerificationData({...verificationData, codigo: e.target.value})}
                    placeholder="123456"
                    size="lg"
                    textAlign="center"
                    fontSize="xl"
                    letterSpacing="0.2em"
                    maxLength={6}
                  />
                  <Text fontSize="xs" color="gray.500" textAlign="center">
                    Ingresá el código de 6 dígitos que te enviamos a {formData.email}
                  </Text>
                </FormControl>

                <Button
                  type="submit"
                  width="full"
                  size="lg"
                  isLoading={isLoading}
                  loadingText="Verificando..."
                  isDisabled={isLoading}
                >
                  Verificar y crear cuenta
                </Button>

                <HStack justify="center" spacing={4}>
                  <ChakraButton
                    variant="link"
                    size="sm"
                    onClick={handleResendCode}
                    isLoading={isLoading}
                    isDisabled={isLoading}
                  >
                    Reenviar código
                  </ChakraButton>
                  <ChakraButton
                    variant="link"
                    size="sm"
                    onClick={() => setStep(1)}
                    isDisabled={isLoading}
                  >
                    Cambiar datos
                  </ChakraButton>
                </HStack>
              </VStack>
            </form>
          )}

          <Text fontSize="sm" color="gray.600">
            ¿Ya tenés cuenta?{" "}
            <Link to="/login" style={{ color: "#3182ce", fontWeight: "500" }}>
              Iniciá sesión aquí
            </Link>
          </Text>

          <Text fontSize="xs" color="gray.500">
            Al registrarte, aceptás nuestros Términos y la Política de Privacidad.
          </Text>
        </VStack>
      </Box>
    </Box>
  );
};

export default RegisterPage;
