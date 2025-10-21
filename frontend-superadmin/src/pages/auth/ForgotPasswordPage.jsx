// src/pages/auth/ForgotPasswordPage.jsx
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
  HStack,
  Button as ChakraButton
} from "@chakra-ui/react";
import { ViewIcon, ViewOffIcon } from "@chakra-ui/icons";
import Button from "../../components/ui/Button";
import { useAuth } from "../../auth/AuthContext";

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  const { sendVerificationCode, verifyCode } = useAuth();
  
  const [step, setStep] = useState(1); // 1: email, 2: código + nueva contraseña
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  
  // Datos del formulario
  const [email, setEmail] = useState("");
  const [codigo, setCodigo] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleSendCode = async (e) => {
    e.preventDefault();
    
    if (!email) {
      setError("Por favor ingresa tu email");
      return;
    }

    try {
      setIsLoading(true);
      setError("");
      
      await sendVerificationCode({
        email: email,
        intent: "reset_password"
      });
      
      setStep(2);
      setSuccess("Te enviamos un código de verificación a tu email");
    } catch (err) {
      setError(err.message || "Error al enviar el código de verificación");
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    
    if (!codigo || !newPassword || !confirmPassword) {
      setError("Por favor completa todos los campos");
      return;
    }
    
    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }
    
    if (newPassword.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres");
      return;
    }

    try {
      setIsLoading(true);
      setError("");
      
      await verifyCode({
        email: email,
        codigo: codigo,
        intent: "reset_password",
        password: newPassword
      });
      
      setSuccess("¡Contraseña actualizada! Redirigiendo al login...");
      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (err) {
      setError(err.message || "Error al actualizar la contraseña");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendCode = async () => {
    try {
      setIsLoading(true);
      setError("");
      
      await sendVerificationCode({
        email: email,
        intent: "reset_password"
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
            {step === 1 ? "Recuperar contraseña" : "Nueva contraseña"}
          </Heading>
          <Text color="gray.600" fontSize="sm">
            {step === 1 
              ? "Ingresá tu email para recibir un código de verificación" 
              : "Ingresá el código y tu nueva contraseña"
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
            <form onSubmit={handleSendCode}>
              <VStack spacing={4} align="stretch">
                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Email</FormLabel>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="tu@email.com"
                    size="lg"
                  />
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
            <form onSubmit={handleResetPassword}>
              <VStack spacing={4} align="stretch">
                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Código de verificación</FormLabel>
                  <Input
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value)}
                    placeholder="123456"
                    size="lg"
                    textAlign="center"
                    fontSize="xl"
                    letterSpacing="0.2em"
                    maxLength={6}
                  />
                  <Text fontSize="xs" color="gray.500" textAlign="center">
                    Ingresá el código de 6 dígitos que te enviamos a {email}
                  </Text>
                </FormControl>

                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="gray.700">Nueva contraseña</FormLabel>
                  <InputGroup size="lg">
                    <Input
                      type={showPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
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
                  <FormLabel fontSize="sm" color="gray.700">Confirmar nueva contraseña</FormLabel>
                  <InputGroup size="lg">
                    <Input
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Repetí tu nueva contraseña"
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
                  loadingText="Actualizando..."
                  isDisabled={isLoading}
                >
                  Actualizar contraseña
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
                    Cambiar email
                  </ChakraButton>
                </HStack>
              </VStack>
            </form>
          )}

          <Text fontSize="sm" color="gray.600">
            ¿Recordaste tu contraseña?{" "}
            <Link to="/login" style={{ color: "#3182ce", fontWeight: "500" }}>
              Iniciá sesión aquí
            </Link>
          </Text>

          <Text fontSize="xs" color="gray.500">
            Al continuar, aceptás nuestros Términos y la Política de Privacidad.
          </Text>
        </VStack>
      </Box>
    </Box>
  );
};

export default ForgotPasswordPage;
