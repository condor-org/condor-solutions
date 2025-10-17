import React, { useContext, useEffect, useState } from "react";
import {
  Box,
  Text,
  useDisclosure,
  useToast,
  Select
} from "@chakra-ui/react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import TurnoCalendar from "../../components/calendar/TurnoCalendar";
import ReservaInfoModal from "../../components/modals/ReservaInfoModal";
import { useCardColors, useBodyBg } from "../../components/theme/tokens";

const TurnosReservados = () => {
  const card = useCardColors();
  const bg = useBodyBg();

  const { accessToken, user } = useContext(AuthContext);
  const [turnos, setTurnos] = useState([]);
  const [sedes, setSedes] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [eventoSeleccionado, setEventoSeleccionado] = useState(null);
  const [profesorId, setProfesorId] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  console.log("[TurnosReservados] Usuario logueado:", user);

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);

    const obtenerPrestadorYDisponibilidades = async () => {
      try {
        const prestadorRes = await api.get("/turnos/prestador/mio/");
        const prestador = prestadorRes.data;
        console.log("[useEffect][prestador] Prestador:", prestador);

        if (!prestador?.id) {
          console.warn("[useEffect][prestador] Prestador no encontrado.");
          return;
        }

        setProfesorId(prestador.id);

        const dispRes = await api.get(
          `/turnos/disponibilidades/?prestador_id=${prestador.id}&expand=lugar`
        );
        console.log("[useEffect][sedes] Response:", dispRes.data);

        const lugaresUnicos = Array.from(
          new Map(
            (dispRes.data.results || dispRes.data || []).map((d) => [
              d.lugar,
              { id: d.lugar, nombre: d.lugar_nombre },
            ])
          ).values()
        );

        console.log("[useEffect][sedes] Sedes únicas extraídas:", lugaresUnicos);
        setSedes(lugaresUnicos);
      } catch (error) {
        console.error("[useEffect][prestador/disponibilidades][ERROR]", error);
        toast({
          title: "Error al obtener datos del profesor",
          status: "error",
          duration: 5000,
        });
      }
    };

    obtenerPrestadorYDisponibilidades();
  }, [accessToken, toast]);

  useEffect(() => {
    if (!accessToken || !sedeId || !profesorId) {
      console.warn("[useEffect][turnos] Faltan datos: accessToken, sedeId o profesorId");
      return;
    }

    const api = axiosAuth(accessToken);
    const url = `/turnos/disponibles/?lugar_id=${sedeId}&prestador_id=${profesorId}`;
    console.log("[useEffect][turnos] Fetching turnos desde:", url);

    api
      .get(url)
      .then((res) => {
        const datos = res.data.results || res.data || [];
        console.log("[useEffect][turnos] Turnos recibidos:", datos);

        const eventos = datos.map((t) => {
          const [h, m] = t.hora.split(":");
          const hFin = ("0" + (parseInt(h) + 1)).slice(-2);
          const color = t.estado === "reservado" ? "#e74c3c" : "#27ae60";
          const title = t.estado === "reservado" ? "🔴 Reservado" : "🟢 Disponible";
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
      .catch((err) => {
        console.error("[useEffect][turnos][ERROR]", err);
        setTurnos([]);
        toast({
          title: "Error al cargar turnos",
          description: "Verificá tu conexión o volvé a intentar.",
          status: "error",
          duration: 5000,
        });
      });
  }, [accessToken, sedeId, profesorId, toast]);

  const handleEventClick = (info) => {
    const isReservado = info.event.extendedProps.estado === "reservado";
    if (!isReservado) return;
    setEventoSeleccionado(info.event);
    onOpen();
  };

  return (
    <Box w="100%" minH="100vh" bg={bg} py={8}>
      <Box
        maxW="1000px"
        mx="auto"
        p={6}
        bg={card.bg}
        color={card.color}
        rounded="xl"
        boxShadow="2xl"
      >
        <Text fontSize="2xl" fontWeight="bold" mb={6} textAlign="center">
          Turnos Reservados
        </Text>

        <Box mb={4}>
          <Select
            placeholder="Seleccionar sede"
            value={sedeId}
            onChange={(e) => setSedeId(e.target.value)}
            maxW="300px"
            mx="auto"
            bg={card.bg}
          >
            {sedes.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre}
              </option>
            ))}
          </Select>
        </Box>

        {sedes.length === 0 ? (
          <Text textAlign="center" mt={6} fontSize="lg" color="red.500">
            No tenés sedes disponibles asociadas.
          </Text>
        ) : sedeId && turnos.length === 0 ? (
          <Text textAlign="center" mt={6} fontSize="lg" color="red.500">
            No hay turnos disponibles para esta sede.
          </Text>
        ) : sedeId ? (
          <Box
            bg={card.bgSecondary}
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
        ) : null}

        <ReservaInfoModal
          isOpen={isOpen}
          onClose={onClose}
          turno={eventoSeleccionado}
        />
      </Box>
    </Box>
  );
};

export default TurnosReservados;
