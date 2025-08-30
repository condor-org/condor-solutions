import React, { useEffect, useState, useContext, useRef } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import AppButton from "../../components/ui/Button";
import {
  Box, Button, Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  ModalCloseButton, Input, Text, useDisclosure, useToast, Select,
  VStack, HStack, Divider, IconButton, Badge, useBreakpointValue,
  AlertDialog, AlertDialogOverlay, AlertDialogContent, AlertDialogHeader,
  AlertDialogBody, AlertDialogFooter
} from "@chakra-ui/react";

import { useModalColors, useMutedText, useCardColors, useInputColors } from "../../components/theme/tokens";
import { CloseIcon } from "@chakra-ui/icons";

import TurnoSelector from "../../components/forms/TurnoSelector.jsx";
import TurnoCalendar from "../../components/calendar/TurnoCalendar.jsx";
import ReservaPagoModal from "../../components/modals/ReservaPagoModal.jsx";


const isoHoy = new Date().toISOString().slice(0, 10);
const hhmm = (iso) => (iso?.split("T")[1]?.slice(0,5) || "");
// === Fechas en horario local (evita el corrimiento por UTC) ===
const toLocalDate = (isoYmd) => {
  if (!isoYmd) return null;
  const [y, m, d] = isoYmd.split("-").map(Number);
  return new Date(y, m - 1, d); // local time, sin shift
};

const weekdayLabel = (isoYmd) =>
  toLocalDate(isoYmd)?.toLocaleDateString("es-AR", { weekday: "long" }) || "";

const longDayLabel = (isoYmd) =>
  toLocalDate(isoYmd)?.toLocaleDateString("es-AR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  }) || "";


// Helper genérico para traer todas las páginas de un endpoint DRF
async function fetchAllPages(api, url, { params = {}, maxPages = 50, pageSize = 100, logTag = "fetchAllPages" } = {}) {
  const items = [];
  let nextUrl = url;
  let page = 0;
  let currentParams = { ...params, limit: params.limit ?? pageSize, offset: params.offset ?? 0 };

  try {
    let res = await api.get(nextUrl, { params: currentParams });
    let data = res.data;

    if (!("results" in data) && !("next" in data)) {
      console.debug(`[${logTag}] Respuesta no paginada. Normalizando.`, { url: nextUrl });
      const arr = Array.isArray(data) ? data : (data?.results || []);
      return arr;
    }

    while (true) {
      page += 1;
      const results = data?.results ?? [];
      items.push(...results);

      console.debug(`[${logTag}] Página ${page} | acumulados=${items.length} | next=${data?.next ?? "null"}`);

      if (!data?.next) break;
      if (results.length === 0) {
        console.warn(`[${logTag}] Corte por results.length === 0 en página ${page}.`);
        break;
      }
      if (page >= maxPages) {
        console.error(`[${logTag}] Corte por maxPages=${maxPages}.`, { url });
        break;
      }

      const isAbsolute = typeof data.next === "string" && /^https?:\/\//i.test(data.next);
      if (isAbsolute) {
        res = await api.get(data.next);
      } else {
        const nextOffset = (currentParams.offset ?? 0) + (currentParams.limit ?? pageSize);
        currentParams = { ...currentParams, offset: nextOffset };
        res = await api.get(nextUrl, { params: currentParams });
      }
      data = res.data;
    }
  } catch (err) {
    console.error(`[${logTag}] Error al paginar`, { url, params, err });
  }
  return items;
}


const ReservarTurno = ({ onClose, defaultMisTurnos = false }) => {
  const { accessToken } = useContext(AuthContext);
  const misTurnosModalSize = useBreakpointValue({ base: "full", md: "lg" });
  const toast = useToast();
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [turnos, setTurnos] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [archivo, setArchivo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [turnoSeleccionado, setTurnoSeleccionado] = useState(null);
  const pagoDisc = useDisclosure();
  const [tiposClase, setTiposClase] = useState([]);
  const [tipoClaseId, setTipoClaseId] = useState("");
  const [bonificaciones, setBonificaciones] = useState([]);
  const [usarBonificado, setUsarBonificado] = useState(false);
  const [reservas, setReservas] = useState([]);
  const [loadingReservas, setLoadingReservas] = useState(false);
  const [cancelandoId, setCancelandoId] = useState(null);
  const misTurnosDisc = useDisclosure();
  const [misTurnos, setMisTurnos] = useState([]);
  const [loadingMisTurnos, setLoadingMisTurnos] = useState(false);
  const modal = useModalColors();
  const muted = useMutedText();
  const [configPago, setConfigPago] = useState({});
  const card = useCardColors();
  const input = useInputColors();
  // Confirmación de cancelación (reemplaza window.confirm)
  const [confirmCancel, setConfirmCancel] = useState({ open: false, turno: null });
  const cancelDialogRef = useRef();


  const tipoClaseSeleccionada = tiposClase.find(tc => String(tc.id) === String(tipoClaseId));


  const codigoSel = tipoClaseSeleccionada?.codigo;
  const tipoTurnoSeleccionado =
    codigoSel === "x2" ? "x2" :
    codigoSel === "x3" ? "x3" :
    codigoSel === "x4" ? "x4" : "x1";
  

  // ¿hay bono del mismo tipo?
  const tieneBonoDeEsteTipo = bonificaciones.length > 0;


    // 👇 en el componente ReservarTurno...
  const isMobile = useBreakpointValue({ base: true, md: false });

  // Día seleccionado (sólo mobile)
  const [selectedDay, setSelectedDay] = useState(isoHoy);

  // Fechas disponibles (derivadas de turnos)
  const availableDays = React.useMemo(() => {
    const s = new Set(
      (turnos || []).map(e => (e.start || "").slice(0,10)).filter(Boolean)
    );
    return Array.from(s).sort(); // yyyy-mm-dd
  }, [turnos]);

  // Inicializar/corregir selectedDay cuando cambian los turnos
  useEffect(() => {
    if (!availableDays.length) {
      setSelectedDay(isoHoy);
      return;
    }
    const firstFuture = availableDays.find(d => d >= isoHoy) || availableDays[0];
    if (!availableDays.includes(selectedDay)) {
      setSelectedDay(firstFuture);
    }
  }, [availableDays]); // eslint-disable-line react-hooks/exhaustive-deps

  // Slots del día seleccionado (sólo mobile)
  const slotsOfDay = React.useMemo(() => {
    if (!selectedDay) return [];
    return (turnos || [])
      .filter(e => (e.start || "").slice(0,10) === selectedDay)
      .slice()
      .sort((a,b) => (a.start < b.start ? -1 : 1));
  }, [turnos, selectedDay]);

  // Click en item (simula FullCalendar eventClick)
  const handleMobileSlotClick = (slot) => {
    const info = {
      event: {
        id: slot.id,
        title: slot.title,
        extendedProps: slot.extendedProps, // acá vive estado, etc.
      },
      timeText: `${hhmm(slot.start)} - ${hhmm(slot.end)}`,
    };
    handleEventClick(info);
  };

  // si cambia el tipo y ya no hay bono, apago el toggle
  useEffect(() => {
    if (usarBonificado && !tieneBonoDeEsteTipo) setUsarBonificado(false);
  }, [usarBonificado, tieneBonoDeEsteTipo]);


  useEffect(() => {
    if (defaultMisTurnos) {
      cargarMisTurnos();
    }
  }, [defaultMisTurnos]);

  // Cargar sedes (solo depende del token)
  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);
    api.get("turnos/sedes/")
      .then(res => setSedes(res.data.results || res.data || []))
      .catch(() => setSedes([]));
  }, [accessToken]);
  

  // 🔹 Cargar configuración de pago (alias y CBU/CVU)
  useEffect(() => {
    if (!sedeId) return;
    const sede = sedes.find(s => String(s.id) === String(sedeId));
    if (!sede) {
      setConfigPago({});
      return;
    }
    setConfigPago({
      alias: sede.alias || "",
      cbu_cvu: sede.cbu_cvu || ""
    });
  }, [sedeId, sedes]);

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

  // cargar Bonificaciones cuando el modal de pago está abierto
  useEffect(() => {
    if (!pagoDisc.isOpen || !accessToken || !tipoClaseId) {
      setBonificaciones([]); // coherencia visual si cambió el tipo o cerraste el modal
      return;
    }

    const api = axiosAuth(accessToken);
    api.get("turnos/bonificados/mios/", { params: { tipo_clase_id: tipoClaseId } })
      .then(res => setBonificaciones(Array.isArray(res.data) ? res.data : (res.data?.bonificaciones || [])))
      .catch((err) => {
        console.warn("[bonos.fetch] error", err);
        setBonificaciones([]);
      });
  }, [pagoDisc.isOpen, accessToken, tipoClaseId]); 
    

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
    pagoDisc.onOpen();
  };
  
  const handleCancelarTurno = async (turno) => {
     
    setCancelandoId(turno.id);
    try {
      const api = axiosAuth(accessToken);
      const resp = await api.post("turnos/cancelar/", { turno_id: turno.id });
      const bono = !!resp.data?.bonificacion_creada;
  
      toast({
        title: "Turno cancelado",
        description: bono
          ? "Se generó una bonificación para usar en el futuro."
          : "No se generó bonificación (el turno usaba una bonificación).",
        status: "success",
        duration: 5000,
      });
  
      // refresco lista de reservas
      await cargarMisTurnos();
  
      // refresco calendario (por si era del mismo profe/sede)
      const profId = profesorId;
      setProfesorId("");
      setTimeout(() => setProfesorId(profId), 50);
  
    } catch (e) {
      const msg = e?.response?.data?.error || e?.response?.data?.detail || "No se pudo cancelar el turno";
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
    } finally {
      setCancelandoId(null);
    }
  };
  
  const cargarMisTurnos = async () => {
    if (!accessToken) return;
    setLoadingMisTurnos(true);
    const api = axiosAuth(accessToken);
  
    try {
      // Traer TODAS las páginas de mis turnos (próximos + reservados)
      const turnos = await fetchAllPages(api, "turnos/", {
        params: { estado: "reservado", upcoming: 1 },
        pageSize: 100,
        logTag: "mis-reservas"
      });
  
      setMisTurnos(Array.isArray(turnos) ? turnos : []);
      console.debug("[mis-reservas] total turnos:", turnos.length);
    } catch (e) {
      console.error("[mis-reservas] error", e);
      toast({ title: "Error", description: "No se pudieron cargar tus turnos.", status: "error" });
      setMisTurnos([]);
    } finally {
      setLoadingMisTurnos(false);
    }
  };
  
  
  
  const abrirMisTurnos = () => {
    misTurnosDisc.onOpen();
    cargarMisTurnos();
  };
  const abrirConfirmacionCancelacion = (turno) => {
    setConfirmCancel({ open: true, turno });
  };
  
  const cerrarConfirmacionCancelacion = () => {
    setConfirmCancel({ open: false, turno: null });
  };
  
  const confirmarCancelacion = async () => {
    const t = confirmCancel.turno;
    if (!t) return;
    await handleCancelarTurno(t);   // reutiliza el handler existente
    cerrarConfirmacionCancelacion();
  };
  
  
  const handleReserva = async () => {
  if (!turnoSeleccionado || !tipoClaseId) {
    toast({
      title: "Faltan datos.",
      description: "Seleccioná un turno y un tipo de clase.",
      status: "warning",
      duration: 6000,
    });
    return;
  }

  // Si quiere usar Turno Bonificado, verificar match por tipo
  if (usarBonificado) {
    if (!tipoTurnoSeleccionado || !tieneBonoDeEsteTipo) {
      toast({
        title: "No podés usar Turno Bonificado",
        description: "No tenés un bono del mismo tipo de clase seleccionada.",
        status: "warning",
        duration: 6000,
      });
      return;
    }
  } else {
    if (!archivo) {
      toast({
        title: "Falta comprobante",
        description: "Subí el comprobante o activá 'Usar Turno Bonificado'.",
        status: "warning",
        duration: 6000,
      });
      return;
    }
  }

  setLoading(true);

    try {
      const formData = new FormData();
      formData.append("turno_id", turnoSeleccionado.id);
      formData.append("tipo_clase_id", tipoClaseId);

      if (usarBonificado) {
        formData.append("usar_bonificado", "true");
      } else {
        formData.append("archivo", archivo);
      }

      const api = axiosAuth(accessToken);
      await api.post("turnos/reservar/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast({
        title: "Reserva enviada",
        description: "Será validada por el administrador.",
        status: "success",
        duration: 3500,
      });

      pagoDisc.onClose();
      onClose?.(); // cierra el modal grande del dashboard si vino por ahí
      setArchivo(null);
      setTurnoSeleccionado(null);
      setUsarBonificado(false);

      // 🔄 Refrescar bonificaciones
      try {
        const res = await api.get("turnos/bonificados/mios/", { params: { tipo_clase_id: tipoClaseId } });
        const nuevasBonos = Array.isArray(res.data) ? res.data : (res.data?.bonificaciones || []);
        setBonificaciones(nuevasBonos);
      
        if (usarBonificado && nuevasBonos.length === 0) {
          toast({
            title: "Sin más bonificaciones",
            description: "Ya no te quedan turnos bonificados disponibles.",
            status: "info",
            duration: 5000,
          });
        }
      } catch (e) {
        console.warn("⚠️ Error al refrescar bonificaciones:", e);
        setBonificaciones([]);
      }

      // 🔁 Refrescar turnos
      const profId = profesorId;
      setProfesorId("");
      setTimeout(() => setProfesorId(profId), 50);
    } catch (e) {
      let msg =
        e?.response?.data?.error ||
        e?.response?.data?.detail ||
        "Error al enviar la reserva";
      toast({
        title: "Error",
        description: msg,
        status: "error",
        duration: 5000,
      });
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
    <Box w="100%" maxW="1000px" mx="auto" mt={8} p={6} bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl">
      {defaultMisTurnos ? (
        <>  
          {loadingMisTurnos ? (
            <Text color={muted}>Cargando...</Text>
          ) : misTurnos.length === 0 ? (
            <Text color={muted}>No tenés reservas.</Text>
          ) : (
            <VStack align="stretch" spacing={3}>
              {misTurnos.map((t) => (
                <Box key={t.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
                  <HStack justify="space-between" align="start">
                    <Box>
                      <Text fontWeight="semibold">{t.lugar_nombre || t.lugar || "Sede"}</Text>
                      <Text fontSize="sm" color={muted}>{t.fecha} · {t.hora?.slice(0,5)}</Text>
                      <Text fontSize="sm" color={muted}> Profesor: {t.prestador_nombre || "N/D"}</Text>
                      <HStack mt={2} spacing={2}>
                        <Badge colorScheme="green">reservado</Badge>
                        {t.prestador_nombre && <Badge variant="outline">{t.prestador_nombre}</Badge>}
                      </HStack>
                    </Box>
                    <Button
                      size="sm"
                      variant="danger"            // o tu variant custom
                      isLoading={cancelandoId === t.id}
                      onClick={() => abrirConfirmacionCancelacion(t)}
                    >
                      Cancelar
                    </Button>
                  </HStack>
                </Box>
              ))}
            </VStack>
          )}
        </>
      ) : (
        <>
          <HStack justify="space-between" mb={4}>
            <Text fontSize="2xl" fontWeight="bold">Reserva de Turnos</Text>
          </HStack>
  
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
            // 👇 nuevas props para el Día en mobile
            day={selectedDay}
            onDayChange={setSelectedDay}
            minDay={isoHoy}
            maxDay={availableDays.length ? availableDays[availableDays.length - 1] : undefined}
          />


                
          {isMobile ? (
            <VStack align="stretch" spacing={4}>
              <Divider my={2} />

              <Text fontWeight="semibold" mt={1}>
                Turnos disponibles
              </Text>

              {!slotsOfDay.length ? (
                <Box
                  border="1px dashed"
                  borderColor={input.border}
                  rounded="md"
                  p={4}
                  textAlign="center"
                  opacity={0.8}
                >
                  No hay turnos para el {longDayLabel(selectedDay)}
                </Box>
              ) : (
                <VStack align="stretch" spacing={3}>
                  {slotsOfDay.map((slot, idx) => {
                    const isReservado = slot?.extendedProps?.estado === "reservado";
                    const scheme = isReservado ? "red" : "green";
                    const tipoNombre =
                      slot?.extendedProps?.tipo_clase?.nombre ||
                      slot?.extendedProps?.tipo_clase_nombre ||
                      slot?.title?.replace(/^(🔴|🟢)\s*/, "") ||
                      "Turno";

                    return (
                      <Box
                        key={slot.id ?? `${slot.start}-${idx}`}
                        p={3}
                        bg={card.bg}
                        rounded="md"
                        borderWidth="1px"
                        borderColor={input.border}
                        _hover={{ boxShadow: "lg", cursor: isReservado ? "not-allowed" : "pointer", opacity: 0.95 }}
                        onClick={() => !isReservado && handleMobileSlotClick(slot)}
                      >
                        <HStack justify="space-between" align="center">
                          <Box>
                            <Text fontWeight="semibold">
                              {weekdayLabel(selectedDay)} · {hhmm(slot.start)} hs
                            </Text>
                            <HStack mt={1} spacing={2}>
                              <Badge variant="outline">{tipoNombre}</Badge>
                              <Badge colorScheme={scheme}>{isReservado ? "Reservado" : "Disponible"}</Badge>
                            </HStack>
                          </Box>

                          {/* botón azul como en Reservar Abono */}
                          <AppButton
                            variant={isReservado ? "ghost" : "primary"}
                            size="sm"
                            isDisabled={isReservado}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (!isReservado) handleMobileSlotClick(slot);
                            }}
                          >
                            {isReservado ? "Ocupado" : "Seleccionar"}
                          </AppButton>
                        </HStack>
                      </Box>
                    );
                  })}
                </VStack>
              )}
            </VStack>
          ) : (
            <TurnoCalendar
              events={turnos}
              onEventClick={handleEventClick}
              height={500}
              slotMinTime="07:00:00"
              slotMaxTime="23:00:00"
            />
          )}



        

  
          <ReservaPagoModal
            isOpen={pagoDisc.isOpen}
            onClose={pagoDisc.onClose}
            turno={turnoSeleccionado}
            tipoClase={tiposClase.find(tc => String(tc.id) === String(tipoClaseId))}
            archivo={archivo}
            onArchivoChange={setArchivo}
            onRemoveArchivo={() => setArchivo(null)}
            onConfirmar={handleReserva}
            loading={loading}
            tiempoRestante={configPago?.tiempo_maximo_minutos ? configPago.tiempo_maximo_minutos * 60 : undefined}
            bonificaciones={bonificaciones}
            usarBonificado={usarBonificado}
            setUsarBonificado={setUsarBonificado}
            alias={configPago.alias}
            cbuCvu={configPago.cbu_cvu}
          />
  
          {/* Modal interno de Mis turnos solo para el modo reservar */}
          <Modal isOpen={misTurnosDisc.isOpen} onClose={misTurnosDisc.onClose} isCentered size={misTurnosModalSize}>
            <ModalOverlay />
            <ModalContent bg={modal.bg} color={modal.color}>
              <ModalHeader>Mis turnos</ModalHeader>
              <ModalBody>
                {loadingMisTurnos ? (
                  <Text color={muted}>Cargando...</Text>
                ) : misTurnos.length === 0 ? (
                  <Text color={muted}>No tenés reservas.</Text>
                ) : (
                  <VStack align="stretch" spacing={3}>
                    {misTurnos.map((t) => (
                      <Box key={t.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
                        <HStack justify="space-between" align="start">
                          <Box>
                            <Text fontWeight="semibold">{t.lugar_nombre || t.lugar || "Sede"}</Text>
                            <Text fontSize="sm" color={muted}>{t.fecha} · {t.hora?.slice(0,5)}</Text>
                          </Box>
                          <Button
                            size="sm"
                            variant="danger"
                            isLoading={cancelandoId === t.id}
                            onClick={() => abrirConfirmacionCancelacion(t)}
                          >
                            Cancelar
                          </Button>
                        </HStack>
                      </Box>
                    ))}
                  </VStack>
                )}
              </ModalBody>
              <ModalFooter>
                <Button variant="ghost" onClick={misTurnosDisc.onClose}>Cerrar</Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
        </>
      )}
      {/* Confirmación de cancelación */}
      <AlertDialog
        isOpen={confirmCancel.open}
        leastDestructiveRef={cancelDialogRef}
        onClose={cerrarConfirmacionCancelacion}
        isCentered
      >
        <AlertDialogOverlay>
          <AlertDialogContent bg={modal.bg} color={modal.color}>
            <AlertDialogHeader fontWeight="bold">
              Confirmar cancelación
            </AlertDialogHeader>

            <AlertDialogBody>
              {(() => {
                const t = confirmCancel.turno;
                const fechaLegible = t
                  ? new Date(`${t.fecha}T${t.hora}`).toLocaleString("es-AR", {
                      weekday: "long",
                      day: "numeric",
                      month: "long",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "";
                return (
                  <>
                    ¿Querés cancelar el turno del <b>{fechaLegible}</b>?
                    <br />
                    <br />
                    <Badge colorScheme="yellow" variant="subtle">Importante</Badge>{" "}
                    Si este turno fue reservado usando una <b>bonificación</b>, <b>no se emitirá una nueva bonificación</b> al cancelarlo.
                  </>
                );
              })()}
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button
                ref={cancelDialogRef}
                variant="secondary"
                onClick={cerrarConfirmacionCancelacion}
              >
                Volver
              </Button>
              <Button
                ml={3}
                variant="danger"
                onClick={confirmarCancelacion}
                isLoading={!!(confirmCancel.turno && cancelandoId === confirmCancel.turno.id)}
              >
                Cancelar turno
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

    </Box>
  );
  
};

export default ReservarTurno;