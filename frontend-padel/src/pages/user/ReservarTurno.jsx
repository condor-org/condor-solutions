import React, { useEffect, useState, useContext } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import {
  Box, Button, Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  ModalCloseButton, Input, Text, useDisclosure, useToast, Select
} from "@chakra-ui/react";

import {
  useCardColors,
  useInputColors
} from "../../components/theme/tokens";

import TurnoSelector from "../../components/forms/TurnoSelector";
import TurnoCalendar from "../../components/calendar/TurnoCalendar";
import ReservaPagoModal from "../../components/modals/ReservaPagoModal";

const ReservarTurno = () => {
  const { accessToken } = useContext(AuthContext);
  const toast = useToast();
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [turnos, setTurnos] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [archivo, setArchivo] = useState(null);
  const [configPago, setConfigPago] = useState({});
  const [loading, setLoading] = useState(false);
  const [turnoSeleccionado, setTurnoSeleccionado] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [tiposClase, setTiposClase] = useState([]);
  const [tipoClaseId, setTipoClaseId] = useState("");


  const card = useCardColors();
  const input = useInputColors();

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);
    api.get("turnos/sedes/")
      .then(res => setSedes(res.data.results || res.data || []))
      .catch(() => setSedes([]));
    if (sedeId) {
      api.get(`padel/sedes/${sedeId}/`)
        .then(res => {
          const conf = res.data.configuracion_padel || {};
          setConfigPago({
            alias: conf.alias || "",
            cbu_cvu: conf.cbu_cvu || "",
            tiempo_maximo_minutos: conf.tiempo_maximo_minutos || 15
          });
        })
        .catch(() => setConfigPago({}));
    }
      
  }, [accessToken]);

  // 🔹 Cargar tipos de clase
  useEffect(() => {
    if (!sedeId || !accessToken) return;
    const api = axiosAuth(accessToken);
    api.get(`padel/tipos-clase/?sede_id=${sedeId}`)
      .then(res => setTiposClase(res.data.results || res.data || []))
      .catch(() => setTiposClase([]));
  }, [sedeId, accessToken]);

  // 🔹 Cargar profesores
  useEffect(() => {
    if (!sedeId || !accessToken) {
      setProfesores([]);
      return;
    }
    const api = axiosAuth(accessToken);
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => setProfesores(res.data.results || res.data || []))
      .catch(() => setProfesores([]));
  }, [sedeId, accessToken]);

  useEffect(() => {
    if (!sedeId || !profesorId || !accessToken) {
      setTurnos([]);
      return;
    }
    const api = axiosAuth(accessToken);
    api.get(`turnos/disponibles/?prestador_id=${profesorId}&lugar_id=${sedeId}`)
      .then(res => {
        const turnosData = res.data.results || res.data || [];
        const eventos = turnosData.map(t => {
          const [h, m] = t.hora.split(":");
          const hFin = ("0" + (parseInt(h) + 1)).slice(-2);
          const isRes = t.estado === "reservado";
          const color = isRes ? "#e74c3c" : "#27ae60";
          const title = isRes ? "🔴 Reservado" : "🟢 Disponible";
          return {
            id: t.id,
            title,
            start: `${t.fecha}T${t.hora}`,
            end: `${t.fecha}T${hFin}:${m}`,
            backgroundColor: color,
            borderColor: color,
            textColor: "#fff",
            extendedProps: t,
          };
        });
        setTurnos(eventos);
      })
      .catch(() => setTurnos([]));

  }, [sedeId, profesorId, accessToken]);

  const handleEventClick = (info) => {
    const isReservado = info.event.extendedProps.estado === "reservado";
  
    if (isReservado) {
      toast({
        title: "Turno ya reservado",
        description: "Este turno no puede seleccionarse.",
        status: "warning",
        duration: 2000
      });
      return;
    }
  
    if (!tipoClaseId) {
      toast({
        title: "Seleccioná un tipo de clase",
        description: "Debés elegir un tipo de clase antes de reservar.",
        status: "warning",
        duration: 4000
      });
      return;
    }
  
    setTurnoSeleccionado(info.event);
    setArchivo(null);
    onOpen();
  };
  
  

  const handleReserva = async () => {
    if (!turnoSeleccionado || !archivo || !tipoClaseId) {
      toast({
        title: "Faltan datos.",
        description: "Seleccioná un turno, tipo de clase y subí el comprobante.",
        status: "warning", duration: 10000
      });
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("turno_id", turnoSeleccionado.id);
      formData.append("tipo_clase_id", tipoClaseId);
      formData.append("archivo", archivo);
  
      const api = axiosAuth(accessToken);
      await api.post("turnos/reservar/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast({ title: "Reserva enviada", description: "Será validada por el administrador.", status: "success", duration: 3500 });
      onClose();
      setArchivo(null);
      setTurnoSeleccionado(null);
      const profId = profesorId;
      setProfesorId(""); setTimeout(() => setProfesorId(profId), 50);
    } catch (e) {
      let msg = e?.response?.data?.error || e?.response?.data?.detail || "Error al enviar la reserva";
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
      console.error("[handleReserva][Error]", e);
    } finally {
      setLoading(false);
    }
  };
  
  const renderEventContent = (eventInfo) => {
    const bg = eventInfo.event.backgroundColor;
    const isReservado = eventInfo.event.extendedProps.estado === "reservado";
    return (
      <Box
        w="100%" h="100%" bg={bg} color="white" borderRadius="md"
        boxShadow="md" fontWeight="bold" p={1} gap={1}
        display="flex" flexDirection="column" alignItems="center" justifyContent="center"
        cursor="pointer" onClick={(e) => {
          e.stopPropagation();
          if (isReservado) {
            toast({
              title: "Turno ya reservado",
              description: "Este turno no puede seleccionarse.",
              status: "warning", duration: 2000,
            });
          } else {
            handleEventClick(eventInfo);
          }
        }}
        _hover={{ opacity: 0.88, boxShadow: `${bg}22 0 2px 8px` }}
        style={{ height: "90%", margin: "2px 0" }}
      >
        <Box fontSize="sm" ml="0.01em" mb={-1}>
          {eventInfo.timeText.split("-")[0]?.trim()}
        </Box>
        <Box fontSize="sm" fontWeight="semibold" mt={-1}>
          {eventInfo.event.title}
        </Box>
      </Box>
    );
  };

  return (
    <Box
      w="100%" maxW="1000px" mx="auto" mt={8} p={6}
      bg={card.bg} color={card.color}
      rounded="xl" boxShadow="2xl"
    >
      <Text fontSize="2xl" fontWeight="bold" mb={4} textAlign="center">
        Reserva de Turnos
      </Text>

      <TurnoSelector
        sedes={sedes}
        profesores={profesores}
        tiposClase={tiposClase}
        sedeId={sedeId}
        profesorId={profesorId}
        tipoClaseId={tipoClaseId}
        onSedeChange={(id) => {
          setSedeId(id);
          setProfesorId("");
          setTipoClaseId("");
          setTiposClase([]);
          setTurnos([]);
          setConfigPago({});
        }}
        onProfesorChange={setProfesorId}
        onTipoClaseChange={setTipoClaseId}
        disabled={false}
      />


      <Box
        bg={card.bg}
        rounded="md"
        p={6}
        boxShadow="lg"
        overflow="hidden"
        minH="500px"
        mt={4}
      >
        <TurnoCalendar
          events={turnos}
          onEventClick={handleEventClick}
          height={500}
          slotMinTime="07:00:00"
          slotMaxTime="23:00:00"
        />
      </Box>

      <ReservaPagoModal
        isOpen={isOpen}
        onClose={onClose}
        turno={turnoSeleccionado}
        configPago={configPago}
        tipoClase={tiposClase.find(tc => String(tc.id) === String(tipoClaseId))} // 🔹 Agregar esto
        archivo={archivo}
        onArchivoChange={(file) => setArchivo(file)}
        onRemoveArchivo={() => setArchivo(null)}
        onConfirmar={handleReserva}
        loading={loading}
        tiempoRestante={configPago?.tiempo_maximo_minutos ? configPago.tiempo_maximo_minutos * 60 : undefined}
      />

    </Box>
  );
};

export default ReservarTurno;
