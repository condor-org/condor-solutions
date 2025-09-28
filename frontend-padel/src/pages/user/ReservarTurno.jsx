// src/pages/usuario/ReservarTurno.jsx
import React, { useEffect, useState, useContext, useRef } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import AppButton from "../../components/ui/Button";
import {
  Box, Button, Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  ModalCloseButton, Input, Text, useDisclosure, useToast,
  VStack, HStack, Divider, Badge, useBreakpointValue,
  AlertDialog, AlertDialogOverlay, AlertDialogContent, AlertDialogHeader,
  AlertDialogBody, AlertDialogFooter, Skeleton, Stack,
} from "@chakra-ui/react";

import { useModalColors, useMutedText, useCardColors, useInputColors } from "../../components/theme/tokens";
import TurnoSelector from "../../components/forms/TurnoSelector.jsx";
import TurnoCalendar from "../../components/calendar/TurnoCalendar.jsx";
import ReservaPagoModal from "../../components/modals/ReservaPagoModal.jsx";

const isoHoy = new Date().toISOString().slice(0, 10);
const hhmm = (iso) => (iso?.split("T")[1]?.slice(0,5) || "");
const toLocalDate = (isoYmd) => {
  if (!isoYmd) return null;
  const [y, m, d] = isoYmd.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const weekdayLabel = (isoYmd) =>
  toLocalDate(isoYmd)?.toLocaleDateString("es-AR", { weekday: "long" }) || "";
const longDayLabel = (isoYmd) =>
  toLocalDate(isoYmd)?.toLocaleDateString("es-AR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  }) || "";

// Helper: paginado DRF
async function fetchAllPages(api, url, { params = {}, maxPages = 50, pageSize = 100, logTag = "fetchAllPages" } = {}) {
  const items = [];
  let nextUrl = url;
  let page = 0;
  let currentParams = { ...params, limit: params.limit ?? pageSize, offset: params.offset ?? 0 };

  try {
    let res = await api.get(nextUrl, { params: currentParams });
    let data = res.data;

    if (!("results" in data) && !("next" in data)) {
      const arr = Array.isArray(data) ? data : (data?.results || []);
      return arr;
    }

    while (true) {
      page += 1;
      const results = data?.results ?? [];
      items.push(...results);

      if (!data?.next || results.length === 0 || page >= maxPages) break;

      const isAbsolute = typeof data.next === "string" && /^https?:\/\//i.test(data.next);
      if (isAbsolute) res = await api.get(data.next);
      else {
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

function firstApiErrorMessage(data) {
  if (!data) return null;
  if (typeof data === "string") return data;

  // DRF: {"field": ["msg1", "msg2"]} o {"detail": "msg"}
  if (data.detail) return Array.isArray(data.detail) ? data.detail[0] : data.detail;

  // Tomar el primer campo con mensaje
  const keys = Object.keys(data);
  for (const k of keys) {
    const v = data[k];
    if (typeof v === "string" && v) return v;
    if (Array.isArray(v) && v.length) return String(v[0]);
  }

  return null;
}

const ReservarTurno = ({ onClose }) => {
  const { accessToken } = useContext(AuthContext);
  const toast = useToast();

  // Filtros / catálogo
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [tiposClase, setTiposClase] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [tipoClaseId, setTipoClaseId] = useState("");
  const [diasDisponibles, setDiasDisponibles] = useState([]);

  // Disponibilidad para el calendario / lista mobile
  const [turnos, setTurnos] = useState([]);

  // Reserva
  const [archivo, setArchivo] = useState(null);
  const [loading, setLoading] = useState(false);
  const pagoDisc = useDisclosure();
  const [turnoSeleccionado, setTurnoSeleccionado] = useState(null);

  // Bonos
  const [bonificaciones, setBonificaciones] = useState([]);

  // Mis próximas reservas (SIEMPRE arriba)
  const [misTurnos, setMisTurnos] = useState([]);
  const [loadingMisTurnos, setLoadingMisTurnos] = useState(false);
  const [cancelandoId, setCancelandoId] = useState(null);

  // UI helpers
  const modal = useModalColors();
  const muted = useMutedText();
  const card = useCardColors();
  const input = useInputColors();
  const isMobile = useBreakpointValue({ base: true, md: false });
  const [configPago, setConfigPago] = useState({});

  // Día seleccionado (mobile)
  const [selectedDay, setSelectedDay] = useState(isoHoy);
  const availableDays = React.useMemo(() => {
    const s = new Set((turnos || []).map(e => (e.start || "").slice(0,10)).filter(Boolean));
    return Array.from(s).sort();
  }, [turnos]);
  useEffect(() => {
    if (!availableDays.length) { setSelectedDay(isoHoy); return; }
    const firstFuture = availableDays.find(d => d >= isoHoy) || availableDays[0];
    if (!availableDays.includes(selectedDay)) setSelectedDay(firstFuture);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableDays]);

  const slotsOfDay = React.useMemo(() => {
    if (!selectedDay) return [];
    return (turnos || [])
      .filter(e => (e.start || "").slice(0,10) === selectedDay)
      .slice()
      .sort((a,b) => (a.start < b.start ? -1 : 1));
  }, [turnos, selectedDay]);

  // ==== Cargas base ====
  const cargarMisTurnos = async () => {
    if (!accessToken) return;
    setLoadingMisTurnos(true);
    const api = axiosAuth(accessToken);
    try {
      const turnos = await fetchAllPages(api, "turnos/", {
        params: { estado: "reservado", upcoming: 1 },
        pageSize: 100,
        logTag: "mis-reservas",
      });
      setMisTurnos(Array.isArray(turnos) ? turnos : []);
    } catch (e) {
      console.error("[mis-reservas] error", e);
      toast({ title: "Error", description: "No se pudieron cargar tus turnos.", status: "error" });
      setMisTurnos([]);
    } finally {
      setLoadingMisTurnos(false);
    }
  };
  useEffect(() => { cargarMisTurnos(); }, [accessToken]); // al montar

  // Sedes
  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);
    api.get("turnos/sedes/")
      .then(res => setSedes(res.data.results || res.data || []))
      .catch(() => setSedes([]));
  }, [accessToken]);

  // Config de pago (alias/CBU por sede)
  useEffect(() => {
    if (!sedeId) return;
    const sede = sedes.find(s => String(s.id) === String(sedeId));
    if (!sede) { setConfigPago({}); return; }
    setConfigPago({ alias: sede.alias || "", cbu_cvu: sede.cbu_cvu || "" });
  }, [sedeId, sedes]);

  // Tipos de clase
  useEffect(() => {
    if (!sedeId || !accessToken) return;
    const api = axiosAuth(accessToken);
    api.get(`padel/tipos-clase/?sede_id=${sedeId}`)
      .then(res => setTiposClase(res.data.results || res.data || []))
      .catch(() => setTiposClase([]));
  }, [sedeId, accessToken]);

  // Profesores por sede
  const [profesoresLoading, setProfesoresLoading] = useState(false);
  useEffect(() => {
    if (!sedeId || !accessToken) { setProfesores([]); return; }
    setProfesoresLoading(true);
    const api = axiosAuth(accessToken);
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => setProfesores(res.data.results || res.data || []))
      .catch(() => setProfesores([]))
      .finally(() => setProfesoresLoading(false));
  }, [sedeId, accessToken]);

  // Filtrar días disponibles basado en disponibilidades del profesor
  useEffect(() => {
    if (!profesorId || !sedeId) {
      setDiasDisponibles([]);
      setSelectedDay(isoHoy); // Limpiar selección de día
      return;
    }

    const profesor = profesores.find(p => String(p.id) === String(profesorId));
    if (!profesor?.disponibilidades) {
      setDiasDisponibles([]);
      setSelectedDay(isoHoy);
      return;
    }

    // Filtrar disponibilidades para la sede actual
    const disponibilidadesSede = profesor.disponibilidades.filter(
      disp => String(disp.sede_id) === String(sedeId)
    );

    // Extraer días de la semana únicos
    const diasUnicos = [...new Set(disponibilidadesSede.map(disp => disp.dia_semana))];
    setDiasDisponibles(diasUnicos);
    setSelectedDay(isoHoy); // Limpiar selección de día
  }, [profesorId, sedeId, profesores]);

  // Turnos disponibles
  useEffect(() => {
    if (!sedeId || !profesorId || !accessToken) { setTurnos([]); return; }
    const api = axiosAuth(accessToken);
    api.get(`turnos/disponibles/?prestador_id=${profesorId}&lugar_id=${sedeId}`)
      .then(res => {
        const turnosData = res.data.results || res.data || [];
        const eventos = turnosData.map(t => {
          const [h, m] = t.hora.split(":");
          const hFin = ("0" + (parseInt(h, 10) + 1)).slice(-2);
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

  // Bonificaciones (cuando abre modal y hay tipo clase)
  useEffect(() => {
    if (!pagoDisc.isOpen || !accessToken || !tipoClaseId) { setBonificaciones([]); return; }
    const api = axiosAuth(accessToken);
    api.get("turnos/bonificados/mios/", { params: { tipo_clase_id: tipoClaseId } })
      .then(res => setBonificaciones(Array.isArray(res.data) ? res.data : (res.data?.bonificaciones || [])))
      .catch(() => setBonificaciones([]));
  }, [pagoDisc.isOpen, accessToken, tipoClaseId]);

  // === Interacciones ===
  const handleEventClick = (info) => {
    const isReservado = info.event.extendedProps.estado === "reservado";
    if (isReservado) {
      toast({ title: "Turno ya reservado", description: "Este turno no puede seleccionarse.", status: "warning", duration: 2000 });
      return;
    }
    if (!tipoClaseId) {
      toast({ title: "Seleccioná un tipo de clase", description: "Debés elegir un tipo de clase antes de reservar.", status: "warning", duration: 4000 });
      return;
    }
    setTurnoSeleccionado(info.event);
    setArchivo(null);
    pagoDisc.onOpen();
  };

  const handleMobileSlotClick = (slot) => {
    const info = {
      event: { id: slot.id, title: slot.title, extendedProps: slot.extendedProps },
      timeText: `${hhmm(slot.start)} - ${hhmm(slot.end)}`,
    };
    handleEventClick(info);
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

      await cargarMisTurnos();
      const profId = profesorId;
      setProfesorId("");
      setTimeout(() => setProfesorId(profId), 50);
    } catch (e) {
      const data = e?.response?.data;
      let msg =
        firstApiErrorMessage(data) ||
        e?.response?.data?.error ||
        e?.response?.data?.detail ||
        "No se pudo cancelar el turno";

      // Caso especial: política de cancelación (400 con 'hasta ... horas' o similar)
      const isPolicy = /cancelar.*hasta/i.test(String(msg));
      if (isPolicy) {
        toast({
          title: "No se puede cancelar este turno",
          description: msg,          // ej: “Solo se puede cancelar hasta 12 h antes (hasta 16/09 14:00).”
          status: "warning",
          duration: 6000,
        });
      } else {
        toast({
          title: "Error",
          description: String(msg),
          status: "error",
          duration: 6000,
        });
      }
    }  finally {
      setCancelandoId(null);
    }
  };

  // Confirm dialog para cancelar
  const [confirmCancel, setConfirmCancel] = useState({ open: false, turno: null });
  const cancelDialogRef = useRef();
  const abrirConfirmacionCancelacion = (turno) => setConfirmCancel({ open: true, turno });
  const cerrarConfirmacionCancelacion = () => setConfirmCancel({ open: false, turno: null });
  const confirmarCancelacion = async () => {
    const t = confirmCancel.turno;
    if (!t) return;
    await handleCancelarTurno(t);
    cerrarConfirmacionCancelacion();
  };

  // <- ACTUALIZADO: ya no validamos comprobante acá; el backend decide.
  const handleReserva = async (bonificacionId) => {
    if (!turnoSeleccionado || !tipoClaseId) {
      toast({ title: "Faltan datos.", description: "Seleccioná un turno y un tipo de clase.", status: "warning", duration: 6000 });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("turno_id", turnoSeleccionado.id);
      formData.append("tipo_clase_id", tipoClaseId);
      if (bonificacionId) formData.append("bonificacion_id", String(bonificacionId));
      if (archivo) formData.append("archivo", archivo);

      const api = axiosAuth(accessToken);
      await api.post("turnos/reservar/", formData, { headers: { "Content-Type": "multipart/form-data" } });

      toast({ title: "Reserva enviada", description: "Será validada por el administrador.", status: "success", duration: 3500 });

      pagoDisc.onClose();
      onClose?.();
      setArchivo(null);
      setTurnoSeleccionado(null);

      // refrescar bonos
      try {
        const res = await api.get("turnos/bonificados/mios/", { params: { tipo_clase_id: tipoClaseId } });
        setBonificaciones(Array.isArray(res.data) ? res.data : (res.data?.bonificaciones || []));
      } catch { setBonificaciones([]); }

      // refrescar lista “Mis reservas”
      await cargarMisTurnos();

      // refrescar calendario
      const profId = profesorId;
      setProfesorId("");
      setTimeout(() => setProfesorId(profId), 50);
    } catch (e) {
      const msg =
        e?.response?.data?.archivo ||
        e?.response?.data?.bonificacion_id ||
        e?.response?.data?.error ||
        e?.response?.data?.detail ||
        "Error al enviar la reserva";
      toast({ title: "Error", description: String(msg), status: "error", duration: 5000 });
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
        cursor="pointer"
        onClick={(e) => {
          e.stopPropagation();
          if (isReservado) {
            toast({ title: "Turno ya reservado", description: "Este turno no puede seleccionarse.", status: "warning", duration: 2000 });
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
      {/* === Mis reservas (arriba) === */}
      <Box mb={6}>
        <Text fontWeight="semibold" mb={2}>Mis clases sueltas</Text>
        {loadingMisTurnos ? (
          <Stack>
            <Skeleton height="70px" rounded="md" />
            <Skeleton height="70px" rounded="md" />
          </Stack>
        ) : !misTurnos.length ? (
          <Text color={muted}>No tenés reservas próximas.</Text>
        ) : (
          <VStack align="stretch" spacing={3}>
            {misTurnos.map((t) => (
              <Box key={t.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
                <HStack justify="space-between" align="start">
                  <Box>
                    <Text fontWeight="semibold">{t.lugar_nombre || t.lugar || "Sede"}</Text>
                    <Text fontSize="sm" color={muted}>{t.fecha} · {t.hora?.slice(0,5)}</Text>
                    {t.prestador_nombre && (
                      <Text fontSize="sm" color={muted}>Profesor: {t.prestador_nombre}</Text>
                    )}
                    <HStack mt={2} spacing={2}>
                      <Badge colorScheme="green">reservado</Badge>
                      {t.prestador_nombre && <Badge variant="outline">{t.prestador_nombre}</Badge>}
                    </HStack>
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
      </Box>

      <Divider my={4} />

      {/* === Selector + disponibilidad === */}
      <HStack justify="space-between" mb={4}>
        <Text fontSize="2xl" fontWeight="bold"> Reservar clases sueltas</Text>
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
        day={selectedDay}
        onDayChange={setSelectedDay}
        minDay={isoHoy}
        maxDay={availableDays.length ? availableDays[availableDays.length - 1] : undefined}
        diasDisponibles={diasDisponibles}
      />

      {isMobile ? (
        <VStack align="stretch" spacing={4}>
          <Divider my={2} />
          <Text fontWeight="semibold" mt={1}>Turnos disponibles</Text>
          {!slotsOfDay.length ? (
            <Box border="1px dashed" borderColor={input.border} rounded="md" p={4} textAlign="center" opacity={0.8}>
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
                    overflow="hidden"
                  >
                    <HStack justify="space-between" align="center" gap={3}>
                      <Box flex="1" minW={0}>
                        <Text fontWeight="semibold" noOfLines={1}>
                          {weekdayLabel(selectedDay)} · {hhmm(slot.start)} hs
                        </Text>
                        <HStack mt={1} spacing={2}>
                          <Badge variant="outline" noOfLines={1}>{tipoNombre}</Badge>
                          <Badge colorScheme={scheme}>{isReservado ? "Reservado" : "Disponible"}</Badge>
                        </HStack>
                      </Box>
                      <AppButton
                        variant={isReservado ? "ghost" : "primary"}
                        size="sm"
                        flexShrink={0}
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
          renderEventContent={renderEventContent}
          diasDisponibles={diasDisponibles}
          profesorId={profesorId}
        />
      )}

      {/* Modal de pago */}
      <ReservaPagoModal
        isOpen={pagoDisc.isOpen}
        onClose={pagoDisc.onClose}
        turno={turnoSeleccionado}
        tipoClase={tiposClase.find(tc => String(tc.id) === String(tipoClaseId))}
        archivo={archivo}
        onArchivoChange={setArchivo}
        onRemoveArchivo={() => setArchivo(null)}
        onConfirmar={handleReserva}               // recibe bonificacionId
        loading={loading}
        tiempoRestante={configPago?.tiempo_maximo_minutos ? configPago.tiempo_maximo_minutos * 60 : undefined}
        bonificaciones={bonificaciones}
        alias={configPago.alias}
        cbuCvu={configPago.cbu_cvu}
      />

      {/* Confirmación de cancelación */}
      <AlertDialog isOpen={confirmCancel.open} leastDestructiveRef={cancelDialogRef} onClose={cerrarConfirmacionCancelacion} isCentered>
        <AlertDialogOverlay>
          <AlertDialogContent bg={modal.bg} color={modal.color}>
            <AlertDialogHeader fontWeight="bold">Confirmar cancelación</AlertDialogHeader>
            <AlertDialogBody>
              {(() => {
                const t = confirmCancel.turno;
                const fechaLegible = t
                  ? new Date(`${t.fecha}T${t.hora}`).toLocaleString("es-AR", {
                      weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
                    })
                  : "";
                return (
                  <>
                    ¿Querés cancelar el turno del <b>{fechaLegible}</b>?
                    <br /><br />
                    <Badge colorScheme="yellow" variant="subtle">Importante</Badge>{" "}
                    Si este turno fue reservado usando una <b>bonificación</b>, <b>no se emitirá una nueva bonificación</b> al cancelarlo.
                  </>
                );
              })()}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelDialogRef} variant="secondary" onClick={cerrarConfirmacionCancelacion}>Volver</Button>
              <Button ml={3} variant="danger" onClick={confirmarCancelacion} isLoading={!!(confirmCancel.turno && cancelandoId === confirmCancel.turno.id)}>
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
