// src/components/modals/ReservaInfoModal.jsx

import React, { useMemo } from "react";
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
  useColorModeValue,
  Flex
} from "@chakra-ui/react";
import { FaCalendarAlt, FaClock, FaUser } from "react-icons/fa";

const ReservaInfoModal = ({ isOpen, onClose, turno }) => {
  const modalBg = useColorModeValue("white", "gray.900");
  const modalText = useColorModeValue("gray.800", "white");
  const resumenBg = useColorModeValue("red.50", "red.900");
  const resumenBorder = useColorModeValue("red.400", "red.500");
  const resumenText = useColorModeValue("red.800", "red.200");

  // Normaliza fecha para evitar errores si llega string
  const fecha = useMemo(() => {
    if (!turno?.start) return null;
    try {
      return turno.start instanceof Date ? turno.start : new Date(turno.start);
    } catch {
      return null;
    }
  }, [turno?.start]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      isCentered
      // ✅ modal más contenido en móvil, igual que antes en desktop
      size={{ base: "xs", sm: "sm", md: "lg" }}
      motionPreset="slideInBottom"
    >
      <ModalOverlay />
      <ModalContent
        bg={modalBg}
        color={modalText}
        px={{ base: 4, md: 6 }}
        py={{ base: 3, md: 4 }}
        borderRadius="2xl"
      >
        <ModalHeader
          fontWeight="bold"
          fontSize={{ base: "md", md: "lg" }}
          color="red.400"
        >
          Información de la Reserva
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {turno && fecha && (
            <Box
              mb={{ base: 4, md: 5 }}
              border="2px solid"
              borderColor={resumenBorder}
              bg={resumenBg}
              color={resumenText}
              borderRadius="md"
              px={{ base: 3, md: 4 }}
              py={{ base: 2, md: 3 }}
              // ✅ evita desbordes de línea en móvil
              wordBreak="break-word"
            >
              <Flex align="center" gap={{ base: 2, md: 3 }} wrap="wrap">
                <Icon as={FaCalendarAlt} boxSize={{ base: 4, md: 5 }} />
                <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                  <b>Día:</b>{" "}
                  {fecha.toLocaleDateString("es-AR", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })}
                </Text>
              </Flex>
              <Flex align="center" gap={{ base: 2, md: 3 }} mt={2} wrap="wrap">
                <Icon as={FaClock} boxSize={{ base: 4, md: 5 }} />
                <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                  <b>Hora:</b>{" "}
                  {fecha.toLocaleTimeString("es-AR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </Text>
              </Flex>
              <Flex align="center" gap={{ base: 2, md: 3 }} mt={2} wrap="wrap">
                <Icon as={FaUser} boxSize={{ base: 4, md: 5 }} />
                <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                  <b>Reservado por:</b>{" "}
                  {turno.extendedProps?.usuario || "-"}
                </Text>
              </Flex>
            </Box>
          )}

          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
            Si este turno necesita ser cancelado o modificado, por favor contactate con el administrador.
          </Text>
        </ModalBody>

        <ModalFooter>
          <Button
            variant="ghost"
            onClick={onClose}
            size={{ base: "sm", md: "md" }}
          >
            Cerrar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ReservaInfoModal;
