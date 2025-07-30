// src/components/modals/ReservaInfoModal.jsx

import React from "react";
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

  const fecha = new Date(turno?.start);

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="lg" motionPreset="slideInBottom">
      <ModalOverlay />
      <ModalContent bg={modalBg} color={modalText} px={6} py={4} borderRadius="2xl">
        <ModalHeader fontWeight="bold" fontSize="lg" color="red.400">
          Información de la Reserva
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
                  {fecha.toLocaleDateString("es-AR", {
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
                  {fecha.toLocaleTimeString("es-AR", {
                    hour: "2-digit",
                    minute: "2-digit"
                  })}
                </Text>
              </Flex>
              <Flex align="center" gap={3} mt={2}>
                <Icon as={FaUser} boxSize={5} />
                <Text>
                  <b>Reservado por:</b>{" "}
                  {turno.extendedProps?.usuario || "-"}
                </Text>
              </Flex>
            </Box>
          )}

          <Text fontSize="sm" color="gray.500">
            Si este turno necesita ser cancelado o modificado, por favor contactate con el administrador.
          </Text>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ReservaInfoModal;
