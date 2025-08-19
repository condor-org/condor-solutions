// src/pages/usuario/JugadorDashboard.jsx
import React, { useContext, useEffect, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import ReservarTurno from "./ReservarTurno";
import ReservarAbono from "./ReservarAbono"; // ← agregado
import { FaCalendarCheck, FaCreditCard, FaClock } from "react-icons/fa";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  useDisclosure,
  Box,
  Heading,
  Flex
} from "@chakra-ui/react";

import {
  useBodyBg,
  useCardColors,
  useModalColors
} from "../../components/theme/tokens";

import { axiosAuth } from "../../utils/axiosAuth";

const JugadorDashboard = () => {
  const { user, accessToken, logout } = useContext(AuthContext);
  const [mostrarReserva, setMostrarReserva] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  const [turnosReservados, setTurnosReservados] = useState(0);
  const [pagosRealizados, setPagosRealizados] = useState(0);
  const [proximoTurno, setProximoTurno] = useState("--/--");

  const bg = useBodyBg();
  const card = useCardColors();
  const modal = useModalColors();

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);

    api.get("turnos/").then(res => {
      const turnos = res.data.results || res.data || [];
      setTurnosReservados(turnos.length);
      const futuros = turnos
        .filter(t => t.fecha && new Date(t.fecha) >= new Date())
        .sort((a, b) => (a.fecha > b.fecha ? 1 : -1));
      if (futuros.length > 0) {
        setProximoTurno(
          `${futuros[0].fecha?.slice(5)} - ${futuros[0].hora?.slice(0, 5)}hs`
        );
      }
    });

    api.get("pagos/comprobantes/").then(res => {
      const comps = res.data.results || res.data || [];
      setPagosRealizados(comps.length);
    });
  }, [accessToken]);

  const openModal = (modo = null) => {
    setMostrarReserva(modo);
    onOpen();
  };

  const closeModal = () => {
    setMostrarReserva(null);
    onClose();
  };

  return (
    <Box minH="100vh" bg={bg} color={card.color}>
      <Box maxW="5xl" mx="auto" px={4} py={8}>
        <Heading as="h2" size="xl" mb={6} textAlign="center">
          Bienvenido, {user?.email}
        </Heading>

        <Flex justify="center" mb={8} gap={6} flexWrap="wrap">
          <Card title="Turnos reservados" value={turnosReservados} icon={FaCalendarCheck} />
          <Card title="Pagos realizados" value={pagosRealizados} icon={FaCreditCard} />
          <Card title="Próximo turno" value={proximoTurno} icon={FaClock} />
        </Flex>

        <Flex justify="center" mt={4} gap={4}>
          <Button onClick={() => { setMostrarReserva("reservar"); onOpen(); }} variant={mostrarReserva === "reservar" ? "secondary" : "primary"}>
            Reservar turno
          </Button>
          <Button onClick={() => { setMostrarReserva("misTurnos"); onOpen(); }} variant="secondary">
            Mis Reservas
          </Button>
          <Button onClick={() => { setMostrarReserva("abono"); onOpen(); }} variant="secondary">
            Reservar Abono
          </Button>
        </Flex>

        <Modal isOpen={isOpen} onClose={closeModal} size="6xl" isCentered>
          <ModalOverlay />
          <ModalContent bg={modal.bg} color={modal.color} maxW="6xl" p={0}>
            <ModalBody>
              {mostrarReserva === "abono" ? (
                <ReservarAbono onClose={closeModal} />
              ) : (
                <ReservarTurno
                  onClose={closeModal}
                  defaultMisTurnos={mostrarReserva === "misTurnos"}
                />
              )}
            </ModalBody>
          </ModalContent>
        </Modal>
      </Box>
    </Box>
  );
};

export default JugadorDashboard;
