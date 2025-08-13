// src/components/modals/ReservaPagoModal.jsx

import React, { useEffect } from "react";
import {
  Box,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Text,
  Button,
  Icon,
  Input,
  useColorModeValue,
  Flex,
  Switch,
  FormControl,
  FormLabel
} from "@chakra-ui/react";
import { FaCalendarAlt, FaClock, FaTrash } from "react-icons/fa";
import CountdownClock from "../ui/CountdownClock";

const ReservaPagoModal = ({
  alias, 
  cbuCvu,
  isOpen,
  onClose,
  turno,
  configPago,
  tipoClase,
  archivo,
  onArchivoChange,
  onRemoveArchivo,
  onConfirmar,
  loading,
  tiempoRestante,
  bonificaciones = [],
  usarBonificado,
  setUsarBonificado
}) => {
  const modalBg = useColorModeValue("white", "gray.900");
  const modalText = useColorModeValue("gray.800", "white");
  const resumenBg = useColorModeValue("green.50", "green.900");
  const resumenBorder = useColorModeValue("green.400", "green.500");
  const resumenText = useColorModeValue("green.800", "green.200");
  const dropzoneBg = useColorModeValue("gray.100", "#232b34");
  const dropzoneHover = useColorModeValue("gray.200", "#243039");
  const dropzoneBorder = useColorModeValue("green.500", "#27ae60");

  const tieneBonos = bonificaciones.length > 0;
  useEffect(() => {
    if (!tieneBonos && usarBonificado) {
      setUsarBonificado(false);
    }
  }, [tieneBonos, usarBonificado, setUsarBonificado]);
  

  const segundos = Number(tiempoRestante || configPago?.tiempo_maximo_minutos * 60 || 180);


  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="lg" motionPreset="slideInBottom">
      <ModalOverlay />
      <ModalContent bg={modalBg} color={modalText} px={6} py={4} borderRadius="2xl">
        <ModalHeader fontWeight="bold" fontSize="lg" color="blue.300">
          Confirmar reserva
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {turno && (
            <Box
              mb={5}
              border="2px solid"
              borderColor={resumenBorder}
              bg={resumenBg}
              color={resumenText}
              borderRadius="md"
              px={4}
              py={3}
            >
              <Flex align="center" gap={3}>
                <Icon as={FaCalendarAlt} boxSize={5} />
                <Text>
                  <b>Día:</b>{" "}
                  {turno.start.toLocaleDateString("es-AR", {
                    weekday: "long",
                    day: "numeric",
                    month: "long"
                  })}
                </Text>
              </Flex>
              <Flex align="center" gap={3} mt={2}>
                <Icon as={FaClock} boxSize={5} />
                <Text>
                  <b>Hora:</b>{" "}
                  {turno.start.toLocaleTimeString("es-AR", {
                    hour: "2-digit",
                    minute: "2-digit"
                  })}
                </Text>
              </Flex>
            </Box>
          )}

          {tipoClase && (
            <Box mb={6}>
              <Text><b>Tipo de clase:</b> {tipoClase.nombre}</Text>
              <Text><b>Monto:</b> ${tipoClase.precio}</Text>
              <Text><b>Alias:</b> {alias}</Text>
              <Text><b>CBU/CVU:</b> {cbuCvu}</Text>
            </Box>
          )}

          <CountdownClock
            segundosTotales={segundos}
            size="md"
            showLabel={true}
            colorScheme="green"
            onFinalizar={() => {
              onClose();
              alert("⏱ El tiempo para confirmar la reserva ha finalizado.");
            }}
          />

          {tieneBonos && (
            <Box
              mt={6}
              mb={4}
              p={4}
              borderRadius="md"
              bg={`${resumenBg}88`}
              border="1px solid"
              borderColor={resumenBorder}
            >
              <Text fontWeight="medium" mb={2}>
                Tenés {bonificaciones.length} turno{bonificaciones.length > 1 ? "s" : ""} bonificado{bonificaciones.length > 1 ? "s" : ""}.
              </Text>
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="usarBonificado" mb="0">
                  ¿Querés usar uno para esta reserva?
                </FormLabel>
                <Switch
                  id="usarBonificado"
                  isChecked={usarBonificado}
                  onChange={(e) => setUsarBonificado(e.target.checked)}
                  colorScheme="teal"
                />
              </FormControl>
            </Box>
          )}

          {!usarBonificado && (
            <Box
              as="label"
              htmlFor="archivo"
              border="2px dashed"
              borderColor={dropzoneBorder}
              bg={dropzoneBg}
              px={4}
              py={4}
              minH="60px"
              rounded="lg"
              w="100%"
              cursor="pointer"
              display="flex"
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              _hover={{ borderColor: "green.400", bg: dropzoneHover }}
              mt={4}
              mb={3}
            >
              <Input
                id="archivo"
                type="file"
                display="none"
                onChange={e => onArchivoChange(e.target.files[0])}
              />
              <Text color="gray.500" fontSize="sm" fontWeight="medium">
                {archivo ? `📄 ${archivo.name}` : "📎 Subí el comprobante de pago"}
              </Text>
            </Box>
          )}

          {!usarBonificado && archivo && (
            <Button
              size="sm"
              leftIcon={<FaTrash />}
              colorScheme="red"
              variant="ghost"
              onClick={onRemoveArchivo}
              mb={2}
            >
              Quitar archivo
            </Button>
          )}

          <Text fontSize="sm" color="gray.500" mt={6}>
            <b>📋 Política de reserva:</b> Toda reserva debe incluir comprobante de pago.
            Las cancelaciones sólo se permiten con <b>mínimo 24 horas de anticipación</b>.
            Si no se confirma el pago antes del fin del contador, el turno será liberado automáticamente.
          </Text>
          
        </ModalBody>

        <ModalFooter>
          <Button colorScheme="blue" mr={3} isLoading={loading} onClick={onConfirmar}>
            Confirmar reserva
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ReservaPagoModal;
