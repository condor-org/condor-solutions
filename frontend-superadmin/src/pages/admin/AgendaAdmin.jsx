import React, { useContext, useEffect, useMemo, useState } from "react";
import {
  Box, Stack, HStack, VStack, Text, Select, Tabs, TabList, TabPanels, Tab, TabPanel,
  useColorModeValue, Input as ChakraInput, Divider, Badge, useToast, Modal, ModalOverlay,
  ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton, useDisclosure,Wrap, WrapItem, Flex
} from "@chakra-ui/react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";


import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import Button from "../../components/ui/Button";
import { Input as CInput } from "@chakra-ui/react";

import {
  useBodyBg,
  useCardColors,
  useInputColors,
  useMutedText
} from "../../components/theme/tokens";

const LABELS_TIPO = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };
const DSEM = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

const hhmm = (h) => (h ? String(h).slice(0,5) : "");
const diaLabel = (i) => (Number.isInteger(i) && i >= 0 && i <= 6 ? DSEM[i] : `Día ${i ?? "-"}`);
const resumenDia = (slots = []) => {
  let total = slots.length;
  let reservados = 0;
  let soloAbonoDisp = 0; // disponibles marcados como solo abono
  for (const s of slots) {
    if (s.estado === "reservado") reservados += 1;
    else if (s.estado === "disponible" && s.reservado_para_abono) soloAbonoDisp += 1;
  }
  const disponibles = total - reservados;
  return { total, reservados, disponibles, soloAbonoDisp };
};
const AgendaAdmin = () => {
  const toast = useToast();
  

  const DSEM_JS = ["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];

  const fmtDDMMYYYY = (iso) => {
    if (!iso) return "—";
    const d = new Date(`${iso}T00:00:00`);
    const dd = String(d.getDate()).padStart(2,"0");
    const mm = String(d.getMonth()+1).padStart(2,"0");
    const yyyy = d.getFullYear();
    return `${dd}-${mm}-${yyyy}`;
  };

  const diaNombreFromISO = (iso) => {
    if (!iso) return "";
    const [y, m, d] = iso.split("-").map(Number);
    const dt = new Date(y, m - 1, d); // siempre local, sin sorpresas de TZ
    const DSEM_JS = ["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];
    return DSEM_JS[dt.getDay()] || "";
  };

  const { accessToken, logout, user: authUser } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken, logout) : null), [accessToken, logout]);
  const [me, setMe] = useState(null);
  useEffect(() => {
    if (authUser) {
      setMe(authUser);
    } else if (api) {
      api.get("auth/me/").then(r => setMe(r?.data)).catch(() => {});
    }
  }, [api, authUser]);

    // modal reservar
  const reservarDisc = useDisclosure();
  const [slotSeleccionado, setSlotSeleccionado] = useState(null); // {id, fecha, hora, estado, ...}
  const [usuarioId, setUsuarioId] = useState("");
  const [tipoCodigo, setTipoCodigo] = useState("");
  const [enviandoReserva, setEnviandoReserva] = useState(false);
  const [emitirBono, setEmitirBono] = useState(false);

  const myUserId = me?.id || null;
  const [reservarComoAdmin, setReservarComoAdmin] = useState(false);
  useEffect(() => {
    if (reservarComoAdmin && myUserId) setUsuarioId(String(myUserId));
  }, [reservarComoAdmin, myUserId]);

  
  const [expandedAbonoId, setExpandedAbonoId] = useState(null);
  const toggleAbono = (id) => setExpandedAbonoId(prev => (prev === id ? null : id));

  const confirmarLiberar = useDisclosure();
  const [slotALiberar, setSlotALiberar] = useState(null);
  const confirmarEliminarAbono = useDisclosure();
  const [abonoAEliminar, setAbonoAEliminar] = useState(null);
  const [eliminandoAbono, setEliminandoAbono] = useState(false);

  const onPedirConfirmLiberar = (slot) => {
    // si abro liberar, cierro reservar y limpio su estado
    setSlotSeleccionado(null);
    reservarDisc.onClose();
    setSlotALiberar(slot);
    confirmarLiberar.onOpen();
  };

  const onConfirmLiberar = async () => {
    if (!slotALiberar) return;
    await liberarTurno(slotALiberar, emitirBonoLiberar);
    setSlotALiberar(null);
    confirmarLiberar.onClose();
  };
  // tokens / colores
  const bg = useBodyBg();
  const card = useCardColors();
  const input = useInputColors();
  const muted = useMutedText();
  const hoverBg = useColorModeValue("gray.100", "gray.700");

  // --------- Filtros comunes ----------
  const [rangeType, setRangeType] = useState("day");
  const [tabIndex, setTabIndex] = useState(0); // 0: Turnos | 1: Abonos
  const isAbonosTab = tabIndex === 1;
  const [selectedDate, setSelectedDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  });
  const [sedeId, setSedeId] = useState("");
  const [prestadorId, setPrestadorId] = useState("");

  // catálogos
  const [sedes, setSedes] = useState([]);
  const [prestadores, setPrestadores] = useState([]);
  const [tiposClase, setTiposClase] = useState([]); // según sede
  const [loadingSedes, setLoadingSedes] = useState(false);
  const [loadingPrestadores, setLoadingPrestadores] = useState(false);
  

  const habilitarSuelto = async (turno) => {
    if (!api) return;
    try {
      await api.post("turnos/admin/marcar_reservado_para_abono/", {
        turno_id: Number(turno.id),
        reservado_para_abono: false,
      });
      toast({ title: "Turno habilitado como suelto", status: "success" });
      // refrescar según vista actual
      if (rangeType === "day") fetchDia(selectedDate);
      if (rangeType === "week") fetchSemana(selectedDate);
      if (rangeType === "month") fetchMes(selectedDate);
    } catch (e) {
      console.error("[AgendaAdmin] habilitar suelto:", e);
      toast({ title: "Error al habilitar turno", status: "error" });
    }
  };

  // turnos (día / semana)
  const [loadingTurnos, setLoadingTurnos] = useState(false);
  const [agendaDia, setAgendaDia] = useState([]);          // slots de un día
  const [agendaSemana, setAgendaSemana] = useState({});    // { 'YYYY-MM-DD': [slots] }

  // mes
  const [agendaMes, setAgendaMes] = useState({}); // { 'YYYY-MM-DD': [slots] }
  const [loadingMes, setLoadingMes] = useState(false);

  const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;

  const monthDays = (isoBase) => {
    const base = new Date(isoBase);
    const y = base.getFullYear();
    const m = base.getMonth(); // 0..11
    const first = new Date(y, m, 1);
    const last = new Date(y, m + 1, 0);
    const out = [];
    for (let d = new Date(first); d <= last; d.setDate(d.getDate() + 1)) {
      out.push(ymd(new Date(d)));
    }
    return out;
  };

 const fetchMes = async (fechaBase) => {
  if (!api || !sedeId || !prestadorId || !fechaBase) { setAgendaMes({}); return; }
  setLoadingMes(true);
  try {
    // Mes: también traemos TODO
    const url = `turnos/agenda/?scope=month&date=${fechaBase}&sede_id=${sedeId}&prestador_id=${prestadorId}&include_abonos=1`;
    const r = await api.get(url);
    const items = r?.data?.items ?? [];
    const grouped = items.reduce((acc, t) => {
      const k = String(t.fecha);
      (acc[k] ||= []).push(t);
      return acc;
    }, {});
    setAgendaMes(grouped);
  } catch (e) {
    console.error("[AgendaAdmin] mes:", e);
    setAgendaMes({});
    toast({ title: "No se pudieron cargar turnos del mes", status: "error" });
  } finally {
    setLoadingMes(false);
  }
};

  // usuarios (para reservar sin pago)
  const [usuarios, setUsuarios] = useState([]);
  const [busquedaUser, setBusquedaUser] = useState("");
  const usuariosFiltrados = useMemo(() => {
    const q = (busquedaUser || "").trim().toLowerCase();
    if (!q) return usuarios;
    return (usuarios || []).filter(u => {
      const campos = [u.nombre, u.apellido, u.email, u.telefono, u.username];
      return campos.some(c => (c || "").toString().toLowerCase().includes(q));
    });
  }, [usuarios, busquedaUser]);
  

  const [emitirBonoLiberar, setEmitirBonoLiberar] = useState(true);



  // ------- carga sedes / prestadores / tipos-clase -------
  useEffect(() => {
    if (!api) return;
    setLoadingSedes(true);
    fetchAllPaginatedResults("turnos/sedes/")
      .then(res => setSedes(res))
      .catch(err => { console.error("[AgendaAdmin] sedes:", err); toast({ title: "No se pudieron cargar las sedes", status: "error" }); })
      .finally(() => setLoadingSedes(false));
  }, [api, toast]);

  useEffect(() => {
    if (!api || !sedeId) { setPrestadores([]); setTiposClase([]); return; }
    setLoadingPrestadores(true);
    fetchAllPaginatedResults(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => setPrestadores(res))
      .catch(err => { console.error("[AgendaAdmin] prestadores:", err); toast({ title: "No se pudieron cargar los profesores", status: "error" }); })
      .finally(() => setLoadingPrestadores(false));

    // tipos clase por sede (para mapear a tipo_clase_id al reservar)
    fetchAllPaginatedResults(`padel/tipos-clase/?sede_id=${sedeId}`)
      .then(res => setTiposClase(res))
      .catch(err => { console.error("[AgendaAdmin] tipos-clase:", err); setTiposClase([]); });
  }, [api, sedeId, toast]);

  // ------- usuarios finales (para asignar reservas sin pago) -------
  useEffect(() => {
    if (!api) return;
    fetchAllPaginatedResults("auth/usuarios/?ordering=email")
      .then(data => {
        setUsuarios((Array.isArray(data) ? data : []).filter(u => u?.tipo_usuario === "usuario_final"));
      })
      .catch(e => { console.error("[AgendaAdmin] usuarios error:", e); setUsuarios([]); });
  }, [api]);

  // --------- fetch slots día/semana ----------
  const fetchDia = async (fecha) => {
  if (!api || !sedeId || !prestadorId || !fecha) { setAgendaDia([]); return; }
  try {
    // Admin: SIEMPRE traemos todo y, si estás en la pestaña Abonos, filtramos
    const url = `turnos/agenda/?scope=day&date=${fecha}&sede_id=${sedeId}&prestador_id=${prestadorId}&include_abonos=1`;
    const r = await api.get(url);
    const items = r?.data?.items ?? [];
    setAgendaDia(items);
  } catch (e) {
    console.error("[AgendaAdmin] turnos día:", e);
    setAgendaDia([]);
    toast({ title: "No se pudieron cargar turnos del día", status: "error" });
  }
};

  const addDays = (iso, n) => {
    const [y, m, d] = iso.split("-").map(Number);
    const base = new Date(y, m - 1, d); // local-safe
    base.setDate(base.getDate() + n);
    return `${base.getFullYear()}-${String(base.getMonth() + 1).padStart(2,"0")}-${String(base.getDate()).padStart(2,"0")}`;
  };

const fetchSemana = async (fechaBase) => {
  if (!api || !sedeId || !prestadorId || !fechaBase) { setAgendaSemana({}); return; }
  setLoadingTurnos(true);
  try {
    // Traemos TODO y filtramos en FE solo si pestaña Abonos
    const url = `turnos/agenda/?scope=week&date=${fechaBase}&sede_id=${sedeId}&prestador_id=${prestadorId}&include_abonos=1`;
    const r = await api.get(url);
    const items = r?.data?.items ?? [];
    const grouped = items.reduce((acc, t) => {
      const k = String(t.fecha);
      (acc[k] ||= []).push(t);
      return acc;
    }, {});
    setAgendaSemana(grouped);
  } catch (e) {
    console.error("[AgendaAdmin] semana:", e);
    setAgendaSemana({});
    toast({ title: "No se pudieron cargar turnos de la semana", status: "error" });
  } finally {
    setLoadingTurnos(false);
  }
};

// Función helper para obtener todos los resultados paginados
const fetchAllPaginatedResults = async (endpoint, params = {}) => {
  const allResults = [];
  let nextUrl = null;
  let page = 1;
  
  try {
    // Primera llamada
    const firstResponse = await api.get(endpoint, { params });
    const firstData = firstResponse?.data;
    
    if (Array.isArray(firstData)) {
      // Si es un array directo, no hay paginación
      return firstData;
    }
    
    // Si tiene estructura de paginación
    if (firstData?.results) {
      allResults.push(...firstData.results);
      nextUrl = firstData.next;
    } else {
      // Fallback: usar los datos directamente
      return Array.isArray(firstData) ? firstData : [];
    }
    
    // Continuar con las páginas siguientes
    while (nextUrl) {
      page++;
      const nextResponse = await api.get(nextUrl);
      const nextData = nextResponse?.data;
      
      if (nextData?.results) {
        allResults.push(...nextData.results);
        nextUrl = nextData.next;
      } else {
        break;
      }
      
      // Límite de seguridad para evitar bucles infinitos
      if (page > 100) {
        console.warn("[fetchAllPaginatedResults] Límite de páginas alcanzado (100)");
        break;
      }
    }
    
    return allResults;
  } catch (error) {
    console.error("[fetchAllPaginatedResults] Error:", error);
    return [];
  }
};

const fetchAbonosMes = async (fechaBase) => {
  if (!api) { setAbonosMes([]); return; }
  setLoadingAbonos(true);
  try {
    const [y, m] = fechaBase.split("-").map(Number);

    // --- Intento 1: filtros en el servidor (si están soportados) ---
    try {
      const params = { anio: y, mes: m };
      if (sedeId) params.sede_id = Number(sedeId);
      if (prestadorId) params.prestador_id = Number(prestadorId);

      // Usar la nueva función para obtener todos los resultados paginados
      const srvItems = await fetchAllPaginatedResults("padel/abonos/", params);

      // Si el backend soporta estos params, ya estamos:
      if (srvItems.length || sedeId || prestadorId) {
        setAbonosMes(srvItems);
        return;
      }
      // Si no había ítems pero tampoco había filtros de sede/profe, seguimos al fallback
    } catch {
      // Si el server no soporta esos params, seguimos al fallback
    }

    // --- Fallback: traer todo y filtrar en FE ---
    const all = await fetchAllPaginatedResults("padel/abonos/");

    // Resolver nombre de sede a partir del id seleccionado
    const sedeNombreSel = sedeId
      ? (sedes.find(s => String(s.id) === String(sedeId))?.nombre || "").trim().toLowerCase()
      : null;

    // Resolver referencia del prestador a partir del id seleccionado:
    // preferimos nombre_publico/nombre para comparar con el backend que devuelve "Nombre Apellido"
    const prestSel = prestadorId
      ? prestadores.find(p => String(p.id) === String(prestadorId))
      : null;
    const prestClaveSel = prestSel
      ? (prestSel.nombre_publico || prestSel.nombre || prestSel.email || "").trim().toLowerCase()
      : null;

    const filtrados = (all || []).filter(a => {
      // Mes/Año
      const okMes = Number(a.anio) === y && Number(a.mes) === m;

      // Sede: el endpoint devuelve "sede" como string (ej. "Belgrano")
      const okSede = !sedeNombreSel
        ? true
        : String(a.sede || "").trim().toLowerCase() === sedeNombreSel;

      // Prestador: el endpoint devuelve "prestador" como string (p.ej. "Lucas Profe").
      // Matcheamos exactamente por nombre y apellido del prestador elegido.
      const prestStr = String(a.prestador || "").trim().toLowerCase();
      const okPrest = !prestClaveSel
        ? true
        : prestStr === prestClaveSel;

      return okMes && okSede && okPrest;
    });

    setAbonosMes(filtrados);
  } catch (e) {
    console.error("[AgendaAdmin] abonos mes:", e);
    setAbonosMes([]);
    toast({ title: "No se pudieron cargar abonos del mes", status: "error" });
  } finally {
    setLoadingAbonos(false);
  }
};

  // disparadores
  useEffect(() => {
    if (isAbonosTab) {
      fetchAbonosMes(selectedDate);
      return;
    }
    if (!sedeId || !prestadorId) { setAgendaDia([]); setAgendaSemana({}); setAgendaMes({}); return; }
    if (rangeType === "day") fetchDia(selectedDate);
    if (rangeType === "week") fetchSemana(selectedDate);
    if (rangeType === "month") fetchMes(selectedDate);
    // eslint-disable-next-line
  }, [api, isAbonosTab, rangeType, selectedDate, sedeId, prestadorId]);

  // helpers
  const onPickRange = (val) => setRangeType(val);
  const onPickDate = (e) => setSelectedDate(e.target.value);

  // abrir modal reservar (slot disponible)
  
  const openReservar = async (slot) => {
    setSlotALiberar(null);
    confirmarLiberar.onClose();
    // si abro reservar, cierro liberar y limpio su estado
    setSlotALiberar(null);
    confirmarLiberar.onClose();
    try {
      const r = await api.get(`turnos/${slot.id}/`); // trae estado actualizado
      setSlotSeleccionado(r.data || slot);
      setTipoCodigo(r.data?.tipo_turno || "");
    } catch {
      setSlotSeleccionado(slot);
      setTipoCodigo(slot?.tipo_turno || "");
    }
    setUsuarioId("");
    setEmitirBono(false);
    setReservarComoAdmin(false);
    reservarDisc.onOpen();
  };
  
  const closeReservar = () => {
    reservarDisc.onClose();
    setSlotSeleccionado(null);
    setUsuarioId("");
    setTipoCodigo("");
    setEmitirBono(false);
    setReservarComoAdmin(false);
  };

  const tipoClaseIdFromCodigo = (codigo) => {
    const t = (tiposClase || []).find(tc => String(tc.codigo) === String(codigo));
    return t?.id ? Number(t.id) : null;
  };

  // reemplazá la función completa por esta:
  const reservarSinPago = async () => {
    if (!api || !slotSeleccionado) return;

    // si es "reservarme yo", forzamos el usuarioId = myUserId
    const finalUserId = reservarComoAdmin ? myUserId : Number(usuarioId) || null;

    if (!finalUserId) {
      toast({ title: "Seleccioná un usuario (o tildá 'Reserva Admin')", status: "warning" });
      return;
    }
    if (!tipoCodigo) {
      toast({ title: "Seleccioná un tipo", status: "warning" });
      return;
    }

    const tipo = (tiposClase || []).find(tc => String(tc.codigo) === String(tipoCodigo));
    const tipoId = tipo?.id ? Number(tipo.id) : null;
    if (!tipoId) {
        toast({ title: "Tipo de clase inválido para esta sede", status: "error" });
        return;
    }

    setEnviandoReserva(true);
    try {
      if (emitirBono) {
        await api.post("turnos/bonificaciones/crear-manual/", {
          usuario_id: Number(finalUserId),
          sede_id: Number(sedeId),
          tipo_clase_id: tipoId,
          motivo: `Bono emitido por admin para ${slotSeleccionado.fecha} ${String(slotSeleccionado.hora).slice(0,5)}`
        });
      }

      await api.post("turnos/admin/reservar/", {
        turno_id: Number(slotSeleccionado.id),
        usuario_id: Number(finalUserId),
        tipo_clase_id: tipoId,
        omitir_bloqueo_abono: Boolean(slotSeleccionado?.reservado_para_abono),
      });

      toast({ title: "Turno reservado", status: "success" });
      closeReservar();

      if (rangeType === "day") fetchDia(selectedDate);
      else if (rangeType === "week") fetchSemana(selectedDate);
      else fetchMes(selectedDate);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.message || "No se pudo reservar";
      console.error("[AgendaAdmin] reservar (admin):", e);
      toast({ title: "Error", description: msg, status: "error" });
    } finally {
      setEnviandoReserva(false);
    }
  };

  const liberarTurno = async (slot, emitirBono) => {
  if (!api || !slot?.id) return;
  try {
    await api.post("turnos/admin/liberar/", {
      turno_id: Number(slot.id),
      emitir_bonificacion: Boolean(emitirBono),
    });
    toast({ title: "Turno liberado", status: "success" });
    if (rangeType === "day")      fetchDia(selectedDate);
    else if (rangeType === "week") fetchSemana(selectedDate);
    else                           fetchMes(selectedDate);
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.message || "No se pudo liberar";
    console.error("[AgendaAdmin] liberar:", e);
    toast({ title: "Error", description: msg, status: "error" });
  }
};
  const pedirEliminarAbono = (abonoObj) => {
    if (!abonoObj) return;
    setAbonoAEliminar(abonoObj);
    confirmarEliminarAbono.onOpen();
  };

  const eliminarAbono = async () => {
    if (!api || !abonoAEliminar?.id) return;
    try {
      setEliminandoAbono(true);
      await api.delete(`padel/abonos/${abonoAEliminar.id}/`);
      toast({ title: "Abono eliminado y turnos liberados", status: "success" });
      setAbonoAEliminar(null);
      confirmarEliminarAbono.onClose();
      // refrescar listados
      fetchAbonosMes(selectedDate);
      if (!isAbonosTab) {
        if (rangeType === "day") fetchDia(selectedDate);
        else if (rangeType === "week") fetchSemana(selectedDate);
        else fetchMes(selectedDate);
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || "No se pudo eliminar el abono";
      toast({ title: "Error", description: msg, status: "error" });
    } finally {
      setEliminandoAbono(false);
    }
  };
  // ── Abonos (listado mensual)
  const [abonosMes, setAbonosMes] = useState([]);
  const [loadingAbonos, setLoadingAbonos] = useState(false);

  // ── Helper: resolver etiqueta de usuario de un slot (para modal liberar)

  const getSlotUsuarioLabel = (slot) => {
  const u = slot?.usuario;

  // si viene como string (email / username)
  if (typeof u === "string" && u.trim()) return u.trim();

  // si viene como objeto
  if (u && (u.email || u.username || u.nombre || u.apellido)) {
    const nom = [u.nombre, u.apellido].filter(Boolean).join(" ");
    return u.email || u.username || nom || "—";
  }

  // alias alternativos
  if (slot?.usuario_email) return slot.usuario_email;
  if (slot?.usuario_username) return slot.usuario_username;

  // si viniera como ID numérico
  const uid = slot?.usuario_id || (typeof slot?.usuario === "number" ? slot.usuario : null);
  if (uid) {
    if (uid === myUserId && (me?.email || me?.username)) return me.email || me.username;
    const found = (usuarios || []).find((x) => Number(x.id) === Number(uid));
    if (found) {
      const nom = [found.nombre, found.apellido].filter(Boolean).join(" ");
      return found.email || nom || "—";
    }
  }
  return "—";
};
const nombreUsuarioFromId = (uid) => {
  if (!uid) return "—";
  const found = (usuarios || []).find((x) => Number(x.id) === Number(uid));
  if (!found) return `Usuario ${uid}`;
  const nom = [found.nombre, found.apellido].filter(Boolean).join(" ");
  return nom || found.email || `Usuario ${uid}`;
};
  // UI helpers
const HeaderFiltros = (
  <VStack align="stretch" spacing={4}>
    {/* 3 botones grandes como en Home */}
    <Stack spacing={3} direction={{ base: "column", md: "row" }}>
      <Button
        size="lg"
        variant={rangeType === "day" ? "primary" : "secondary"}
        onClick={() => onPickRange("day")}
        w={{ base: "100%", md: "auto" }}
      >
        Día
      </Button>
      <Button
        size="lg"
        variant={rangeType === "week" ? "primary" : "secondary"}
        onClick={() => onPickRange("week")}
        w={{ base: "100%", md: "auto" }}
      >
        Semana
      </Button>
      <Button
        size="lg"
        variant={rangeType === "month" ? "primary" : "secondary"}
        onClick={() => onPickRange("month")}
        w={{ base: "100%", md: "auto" }}
      >
        Mes
      </Button>
    </Stack>

    {/* Filtros (una línea completa) */}
    <Stack
      direction={{ base: "column", md: "row" }}
      spacing={3}
      bg={card.bg}
      p={4}
      rounded="lg"
      borderWidth="1px"
      borderColor={input.border}
      align={{ base: "stretch", md: "center" }}
    >
      <ChakraInput
        type="date"
        value={selectedDate}
        onChange={onPickDate}
        bg={input.bg}
        borderColor={input.border}
        w={{ base: "100%", md: "auto" }}
      />

      <Select
        placeholder={loadingSedes ? "Cargando sedes..." : "Sede"}
        value={sedeId}
        onChange={(e) => {
          setSedeId(e.target.value);
          setPrestadorId("");
          setAgendaDia([]);
          setAgendaSemana({});
        }}
        bg={input.bg}
        borderColor={input.border}
        w={{ base: "100%", md: "auto" }}
      >
        {(sedes || []).map((s) => (
          <option key={s.id} value={s.id}>
            {s.nombre || `Sede ${s.id}`}
          </option>
        ))}
      </Select>

      <Select
        placeholder={
          sedeId
            ? loadingPrestadores
              ? "Cargando profesores..."
              : "Profesor"
            : "Elegí una sede primero"
        }
        value={prestadorId}
        onChange={(e) => setPrestadorId(e.target.value)}
        bg={input.bg}
        borderColor={input.border}
        isDisabled={!sedeId || loadingPrestadores}
        w={{ base: "100%", md: "auto" }}
      >
        {(prestadores || []).map((p) => (
          <option key={p.id} value={p.id}>
            {p.nombre_publico || p.nombre || p.email || `Profe ${p.id}`}
          </option>
        ))}
      </Select>
    </Stack>
  </VStack>
);

const SlotRow = ({ slot }) => {
  const reservado = slot.estado === "reservado";
  const [busy, setBusy] = React.useState(false);

  const toggleAbono = async (nuevoFlag) => {
    if (!api || busy) return;
    try {
      setBusy(true);
      await api.post("turnos/admin/marcar_reservado_para_abono/", {
        turno_id: Number(slot.id),
        reservado_para_abono: Boolean(nuevoFlag),
      });
      toast({
        title: nuevoFlag ? "Turno bloqueado solo para abonos" : "Turno habilitado para sueltos",
        status: "success",
      });
      if (rangeType === "day") fetchDia(selectedDate);
      else if (rangeType === "week") fetchSemana(selectedDate);
      else fetchMes(selectedDate);
    } catch (e) {
      console.error("[SlotRow][toggleAbono]", e);
      toast({
        title: "No se pudo actualizar el modo (abono/suelto)",
        description: e?.response?.data?.detail || e?.message,
        status: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack
      direction={{ base: "column", md: "row" }}
      key={slot.id}
      p={3}
      bg={card.bg}
      rounded="md"
      borderWidth="1px"
      borderColor={input.border}
      _hover={{ bg: hoverBg }}
      justify="space-between"
      align={{ base: "stretch", md: "center" }}
    >
      <HStack spacing={3} flex="1">
        <Badge colorScheme={reservado ? "red" : "green"} variant="solid">
          {reservado ? "Reservado" : "Disponible"}
        </Badge>
        <Text fontWeight="semibold">{String(slot.hora).slice(0, 5)}</Text>
        {reservado && (
          <Text color={muted} fontSize="sm">
            {getSlotUsuarioLabel(slot)}
          </Text>
        )}
        {"reservado_para_abono" in slot && slot.reservado_para_abono && (
          <Badge variant="outline">Solo abono</Badge>
        )}
      </HStack>

      <Wrap spacing={2} justify={{ base: "flex-start", md: "flex-end" }}>
        {/* Toggle abono/suelto si NO está reservado */}
        {!reservado && typeof slot.reservado_para_abono === "boolean" && (
          slot.reservado_para_abono ? (
            <WrapItem>
            <Button
              size="sm"
              variant="secondary"
              isDisabled={busy}
              onClick={() => toggleAbono(false)}
            >
              Habilitar sueltos
            </Button>
            </WrapItem>
          ) : (
            <WrapItem>
            <Button
              size="sm"
              variant="secondary"
              isDisabled={busy}
              onClick={() => toggleAbono(true)}
            >
              Marcar solo para abonos
            </Button>
            </WrapItem>
          )
        )}

        {/* Reservar si NO está reservado */}
        {!reservado && (
          <WrapItem>
          <Button size="sm" onClick={() => openReservar(slot)} isDisabled={busy}>
            Reservar
          </Button>
          </WrapItem>
        )}

        {/* Liberar si está reservado */}
        {reservado && (
          <WrapItem>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => onPedirConfirmLiberar(slot)}
            isDisabled={busy}
          >
            Liberar
          </Button>
          </WrapItem>
        )}
      </Wrap>
    </Stack>
  );
};

  const ListadoDia = () => (
    <VStack align="stretch" spacing={2}>
      {agendaDia.length === 0 ? (
        <Text color={muted}>No hay turnos para los filtros seleccionados.</Text>
      ) : agendaDia.map(t => <SlotRow key={t.id} slot={t} />)}
    </VStack>
  );

  const ListadoSemana = () => {
    const dias = Object.keys(agendaSemana).sort();
    return (
      <VStack align="stretch" spacing={4}>
        {dias.length === 0 && <Text color={muted}>No hay turnos para los filtros seleccionados.</Text>}
        {dias.map(d => (
          <Box key={d} p={3} bg={card.bg} rounded="lg" borderWidth="1px" borderColor={input.border}>
            <Stack direction={{ base: "column", md: "row" }} justify="space-between" mb={2} gap={2}>
              <Text fontWeight="bold">
                {diaNombreFromISO(d)} · {fmtDDMMYYYY(d)}
              </Text>
              <Badge variant="outline">{(agendaSemana[d] || []).length} slots</Badge>
            </Stack>
            <VStack align="stretch" spacing={2}>
              {(agendaSemana[d] || []).map(t => <SlotRow key={t.id} slot={t} />)}
            </VStack>
          </Box>
        ))}
      </VStack>
    );
  };
  const ListadoMes = () => {
  // Obtener el mes y año de la fecha seleccionada (parsear correctamente)
  const [año, mes, dia] = selectedDate.split('-').map(Number);
  const fechaSeleccionada = new Date(año, mes - 1, dia);
  const nombreMes = fechaSeleccionada.toLocaleDateString('es-ES', { month: 'long' });
  
  // Usar directamente los días que vienen del backend
  const diasConTurnos = Object.keys(agendaMes).sort();
  
  if (!diasConTurnos.length) return <Text color={muted}>{loadingMes ? "Cargando…" : "No hay turnos para este mes."}</Text>;
  
  // Función para obtener el nombre del día de la semana
  const obtenerDiaSemana = (fecha) => {
    // Parsear la fecha correctamente para evitar problemas de zona horaria
    const [año, mes, dia] = fecha.split('-').map(Number);
    const fechaObj = new Date(año, mes - 1, dia); // mes - 1 porque Date usa 0-11
    return fechaObj.toLocaleDateString('es-ES', { weekday: 'long' });
  };

  return (
    <VStack align="stretch" spacing={3}>
      {/* Título del mes */}
      <Box textAlign="center" mb={4}>
        <Text fontSize="lg" fontWeight="bold" color={card.color}>
          {nombreMes.charAt(0).toUpperCase() + nombreMes.slice(1)} {año}
        </Text>
      </Box>

      {/* Lista de días */}
      <VStack align="stretch" spacing={2}>
        {diasConTurnos.map((dia) => {
          const turnos = agendaMes[dia] || [];
          const total = turnos.length;
          const disponibles = turnos.filter(t => t.estado === 'disponible').length;
          const reservados = turnos.filter(t => t.estado === 'reservado').length;
          const diaSemana = obtenerDiaSemana(dia);
          const [año, mes, diaNum] = dia.split('-').map(Number);
          const numeroDia = diaNum;
          
          return (
            <Box
              key={dia}
              p={3}
              bg={card.bg}
              rounded="md"
              borderWidth="1px"
              borderColor={input.border}
              _hover={{ bg: hoverBg, cursor: "pointer" }}
              onClick={() => { setRangeType("day"); setSelectedDate(dia); }}
            >
              <HStack justify="space-between" align="center">
                <HStack spacing={3} align="center">
                  <Box>
                    <Text fontSize="lg" fontWeight="bold" color={card.color}>
                      {numeroDia}
                    </Text>
                    <Text fontSize="sm" color={muted} textTransform="capitalize">
                      {diaSemana}
                    </Text>
                  </Box>
                </HStack>
                
                <HStack spacing={4}>
                  <VStack spacing={1} align="center">
                    <Text fontSize="xs" color={muted}>Disponibles</Text>
                    <Badge size="sm" colorScheme="green">{disponibles}</Badge>
                  </VStack>
                  <VStack spacing={1} align="center">
                    <Text fontSize="xs" color={muted}>Reservados</Text>
                    <Badge size="sm" colorScheme="red">{reservados}</Badge>
                  </VStack>
                  <VStack spacing={1} align="center">
                    <Text fontSize="xs" color={muted}>Total</Text>
                    <Badge size="sm" colorScheme="gray">{total}</Badge>
                  </VStack>
                </HStack>
              </HStack>
            </Box>
          );
        })}
      </VStack>
    </VStack>
  );
};

  return (
    <PageWrapper>
      <Sidebar
        links={[
          { label: "Dashboard", path: "/admin" },
          { label: "Sedes", path: "/admin/sedes" },
          { label: "Profesores", path: "/admin/profesores" },
          { label: "Agenda", path: "/admin/agenda" },
          { label: "Usuarios", path: "/admin/usuarios" },
          { label: "Cancelaciones", path: "/admin/cancelaciones" },
          { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
          { label: "Abonos (Asignar)", path: "/admin/abonos" },
        ]}
      />

      <Box flex="1" p={{ base: 4, md: 8 }} bg={bg} color={card.color}>
        <HStack justify="space-between" mb={4} align={{ base: "stretch", md: "center" }}>
          <Text fontSize="2xl" fontWeight="bold">Agenda (Admin)</Text>
        </HStack>

        {HeaderFiltros}
        <Divider my={4} />

        <Tabs colorScheme="blue" variant="enclosed" index={tabIndex} onChange={setTabIndex}>
          <TabList>
            <Tab>Turnos</Tab>
            <Tab>Abonos</Tab>
          </TabList>
          <TabPanels>
            <TabPanel px={0} pt={4}>
              <VStack align="stretch" spacing={3}>
                <Box p={4} bg={card.bg} rounded="lg" borderWidth="1px" borderColor={input.border}>
                  <Text fontWeight="semibold" mb={2}>
                    {rangeType === "day"
                      ? "Turnos del día"
                      : rangeType === "week"
                      ? "Turnos de la semana"
                      : "Turnos del mes"}
                  </Text>
                  <Text color={muted}>
                    Fecha base: <b>{fmtDDMMYYYY(selectedDate)}</b> · <b>{diaNombreFromISO(selectedDate)}</b>
                    {sedeId ? <> · Sede: <b>{(sedes.find(s => String(s.id) === String(sedeId))?.nombre) || sedeId}</b></> : " · Sede: —"}
                    {prestadorId ? <> · Profe: <b>{prestadores.find(p => String(p.id) === String(prestadorId))?.nombre_publico || prestadorId}</b></> : " · Profe: —"}
                  </Text>

                  <Box mt={4}>
                    {rangeType === "day" ? <ListadoDia /> : rangeType === "week" ? <ListadoSemana /> : <ListadoMes />}
                  </Box>
                </Box>
              </VStack>
            </TabPanel>

            <TabPanel px={0} pt={4}>
              <VStack align="stretch" spacing={3}>
                <Box p={4} bg={card.bg} rounded="lg" borderWidth="1px" borderColor={input.border}>
                  <Text fontWeight="semibold" mb={2}>Abonos del mes</Text>
                  <Text color={muted}>
                    Mes: <b>{selectedDate.slice(0,7)}</b>
                    {sedeId ? <> · Sede: <b>{(sedes.find(s => String(s.id) === String(sedeId))?.nombre) || sedeId}</b></> : " · Sede: —"}
                    {prestadorId ? <> · Profe: <b>{prestadores.find(p => String(p.id) === String(prestadorId))?.nombre_publico || prestadorId}</b></> : " · Profe: —"}
                  </Text>

                  <Box mt={4}>
                    {loadingAbonos ? (
                      <Text color={muted}>Cargando…</Text>
                    ) : !sedeId ? (
                      <Text color="orange.500" fontWeight="semibold">
                        ⚠️ Por favor selecciona una sede para ver los abonos
                      </Text>
                    ) : abonosMes.length === 0 ? (
                      <Text color={muted}>No hay abonos para los filtros seleccionados.</Text>
                    ) : (
                      // NUEVO FORMATO: Agrupado por día (con o sin profesor seleccionado)
                      (() => {
                        // Agrupar abonos por día de semana
                        const abonosPorDia = abonosMes.reduce((acc, abono) => {
                          const dia = abono.dia_semana;
                          if (!acc[dia]) acc[dia] = [];
                          acc[dia].push(abono);
                          return acc;
                        }, {});

                        // Ordenar por día de semana (0=Lunes, 6=Domingo)
                        const diasOrdenados = Object.keys(abonosPorDia)
                          .map(Number)
                          .sort((a, b) => a - b);

                        return (
                          <VStack align="stretch" spacing={4}>
                            {diasOrdenados.map(dia => {
                              const abonosDelDia = abonosPorDia[dia].sort((a, b) => a.hora.localeCompare(b.hora));
                              return (
                                <Box key={dia} p={4} bg={card.bg} rounded="lg" borderWidth="1px" borderColor={input.border}>
                                  <Text fontSize="lg" fontWeight="bold" mb={3} color="blue.600">
                                    {diaLabel(dia)}:
                                  </Text>
                                  
                                  {abonosDelDia.length === 0 ? (
                                    <Text color={muted} fontStyle="italic">No hay abonos para este día</Text>
                                  ) : (
                                    <VStack align="stretch" spacing={2}>
                                      {abonosDelDia.map(abono => (
                                        <Box
                                          key={abono.id}
                                          p={3}
                                          bg="white"
                                          rounded="md"
                                          borderWidth="1px"
                                          borderColor="gray.200"
                                          _hover={{ bg: "gray.50" }}
                                        >
                                          <Flex justify="space-between" align="start" wrap="wrap" gap={3}>
                                            <VStack align="start" spacing={2} flex="1" minW={0}>
                                              <Text fontWeight="semibold">
                                                <Text as="span" color="blue.600">Hora:</Text> {hhmm(abono.hora)}hs
                                              </Text>
                                              <Text>
                                                <Text as="span" color="blue.600">Sede:</Text> {abono.sede || `Sede ${abono.sede_id ?? ""}`}
                                              </Text>
                                              <Text>
                                                <Text as="span" color="blue.600">Usuario:</Text> {abono.usuario || "N/A"}
                                              </Text>
                                              <Text>
                                                <Text as="span" color="blue.600">Profesor:</Text> {abono.prestador || "N/A"}
                                              </Text>
                                            </VStack>
                                            
                                            <Button
                                              size="sm"
                                              variant="secondary"
                                              colorScheme="red"
                                              onClick={() => pedirEliminarAbono(abono)}
                                              flexShrink={0}
                                              alignSelf="flex-start"
                                            >
                                              Eliminar
                                            </Button>
                                          </Flex>
                                        </Box>
                                      ))}
                                    </VStack>
                                  )}
                                </Box>
                              );
                            })}
                          </VStack>
                        );
                      })()
                    )}
                  </Box>
                </Box>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Box>

      {/* Modal: Reservar slot (sin pago) */}
<Modal isOpen={reservarDisc.isOpen} onClose={closeReservar} isCentered size="lg">
  <ModalOverlay />
  <ModalContent bg={card.bg} color={card.color}>
    <ModalHeader>Reservar turno</ModalHeader>
    <ModalCloseButton />
    <ModalBody>
      {slotSeleccionado && (
        <VStack align="stretch" spacing={3}>
          <Text fontSize="sm" color={muted}>
            {slotSeleccionado?.fecha || selectedDate} · {String(slotSeleccionado?.hora).slice(0,5)} hs
          </Text>

          <Box>
            <HStack justify="space-between" align="center" mb={2}>
              <Text fontWeight="semibold">Usuario</Text>
              <HStack>
                <input
                  type="checkbox"
                  checked={reservarComoAdmin}
                  onChange={(e) => setReservarComoAdmin(e.target.checked)}
                  style={{ transform: "scale(1.2)" }}
                />
                <Text fontSize="sm">Reservar como admin</Text>
              </HStack>
            </HStack>

            {!reservarComoAdmin && (
              <>
                <HStack spacing={2} mb={2}>
                  <CInput
                    placeholder="Buscar usuario…"
                    value={busquedaUser}
                    onChange={(e) => setBusquedaUser(e.target.value)}
                    bg={input.bg}
                    borderColor={input.border}
                  />
                  <Button variant="secondary" onClick={() => setBusquedaUser("")}>Limpiar</Button>
                </HStack>
                <Select
                  placeholder="Elegí un usuario"
                  value={usuarioId}
                  onChange={(e) => setUsuarioId(e.target.value)}
                  bg={input.bg}
                  borderColor={input.border}
                  isDisabled={reservarComoAdmin}
                >
                  {usuariosFiltrados.map(u => (
                    <option key={u.id} value={u.id}>
                      {(u.nombre || u.apellido) ? `${u.nombre || ""} ${u.apellido || ""} — ${u.email}` : u.email}
                    </option>
                  ))}
                </Select>
              </>
            )}

            {reservarComoAdmin && (
              <Text fontSize="sm" color={muted}>
                Se reservará a tu usuario: <b>{me?.email || me?.username || `ID ${myUserId}`}</b>
              </Text>
            )}
          </Box>

          <Box>
            <Text fontWeight="semibold" mb={2}>Tipo de clase</Text>
            <Select
              placeholder="Elegí el tipo"
              value={tipoCodigo}
              onChange={(e) => setTipoCodigo(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
            >
              {["x1","x2","x3","x4"].map(c => (
                <option key={c} value={c}>
                  {LABELS_TIPO[c]}
                </option>
              ))}
            </Select>
            <HStack mt={2}>
              <input
                type="checkbox"
                checked={emitirBono}
                onChange={(e) => setEmitirBono(e.target.checked)}
                style={{ transform: "scale(1.2)" }}
              />
              <Text fontSize="sm">Emitir bonificación manual al usuario (opcional)</Text>
            </HStack>
            <Text mt={1} fontSize="xs" color={muted}>
              Si está tildado, primero se emite la bonificación para esta sede y tipo, y luego se reserva el turno.
            </Text>
          </Box>
        </VStack>
      )}
    </ModalBody>
    <ModalFooter>
      <Stack direction={{ base: "column", md: "row" }} w="100%" gap={2}>
        <Button variant="secondary" onClick={closeReservar}>Cancelar</Button>
        <Button isLoading={enviandoReserva} onClick={reservarSinPago}>Confirmar</Button>
      </Stack>
    </ModalFooter>
  </ModalContent>
</Modal>
<Modal
  isOpen={confirmarLiberar.isOpen}
  onClose={() => { setSlotALiberar(null); confirmarLiberar.onClose(); }}
  isCentered
  size="lg"
>
  <ModalOverlay />
  <ModalContent bg={card.bg} color={card.color}>
    <ModalHeader>Confirmar liberación</ModalHeader>
    <ModalCloseButton />
    <ModalBody>
      {slotALiberar ? (
        <VStack align="stretch" spacing={3}>
          <Text><b>Fecha:</b> {String(slotALiberar.fecha || selectedDate)}</Text>
          <Text><b>Hora:</b> {String(slotALiberar.hora).slice(0,5)} hs</Text>
          <Text><b>Estado actual:</b> {slotALiberar.estado}</Text>

          {/* Usuario: mejora de lectura con múltiples posibles campos */}
          <Text>
            <b>Usuario:</b> {getSlotUsuarioLabel(slotALiberar)}
          </Text>

          {"lugar" in slotALiberar && (
            <Text><b>Sede:</b> {slotALiberar.lugar}</Text>
          )}
          {"prestador_nombre" in slotALiberar && (
            <Text><b>Prestador:</b> {slotALiberar.prestador_nombre || "—"}</Text>
          )}
          {"tipo_turno" in slotALiberar && (
            <Text><b>Tipo:</b> {LABELS_TIPO[slotALiberar.tipo_turno] || slotALiberar.tipo_turno || "—"}</Text>
          )}
          {slotALiberar?.reservado_para_abono && (
            <Text><b>Bloqueado por abono:</b> Sí</Text>
          )}

          {/* Toggle emitir bonificación */}
          <HStack mt={1}>
            <input
              type="checkbox"
              checked={emitirBonoLiberar}
              onChange={(e) => setEmitirBonoLiberar(e.target.checked)}
              style={{ transform: "scale(1.2)" }}
            />
            <Text fontSize="sm">Emitir bonificación al liberar</Text>
          </HStack>

          {/* Comentario dinámico */}
          <Text mt={1} color={muted} fontSize="sm">
            {emitirBonoLiberar
              ? "Esto libera el cupo y, si corresponde, emite una bonificación al usuario."
              : "Esto libera el cupo sin emitir bonificación."}
          </Text>
        </VStack>
      ) : null}
    </ModalBody>
    <ModalFooter>
      <Stack direction={{ base: "column", md: "row" }} w="100%" gap={2}>
        <Button variant="secondary" onClick={() => { setSlotALiberar(null); confirmarLiberar.onClose(); }}>
          Cancelar
        </Button>
        <Button onClick={onConfirmLiberar}>Confirmar</Button>
      </Stack>
    </ModalFooter>
  </ModalContent>
</Modal>
      {/* Modal: Eliminar abono */}
      <Modal
        isOpen={confirmarEliminarAbono.isOpen}
        onClose={() => { setAbonoAEliminar(null); confirmarEliminarAbono.onClose(); }}
        isCentered
        size="lg"
      >
        <ModalOverlay />
        <ModalContent bg={card.bg} color={card.color}>
          <ModalHeader>Eliminar abono</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {abonoAEliminar ? (
              <VStack align="stretch" spacing={3}>
                <Text>
                  Estás por eliminar el abono de <b>{abonoAEliminar.dia_semana_label || diaLabel(abonoAEliminar.dia_semana)}</b> a las <b>{hhmm(abonoAEliminar.hora)} hs</b>.
                </Text>
                <Text>
                  <b>Usuario:</b> {abonoAEliminar.usuario_nombre_completo || nombreUsuarioFromId(abonoAEliminar.usuario_id) || abonoAEliminar.usuario || "—"}
                </Text>
                <Text><b>Profesor:</b> {abonoAEliminar.prestador || `Profe ${abonoAEliminar.prestador_id ?? ""}`}</Text>
                <Text><b>Sede:</b> {abonoAEliminar.sede || `Sede ${abonoAEliminar.sede_id ?? ""}`}</Text>
                <Text color="red.400" fontWeight="bold">
                  CUIDADO: esto elimina el abono ya pago del Usuario: {abonoAEliminar.usuario_nombre_completo || nombreUsuarioFromId(abonoAEliminar.usuario_id) || abonoAEliminar.usuario || "—"}.
                </Text>
                <Text color={muted} fontSize="sm">
                  Esta acción liberará todos los turnos reservados y los turnos con prioridad asociados a este abono.
                </Text>
              </VStack>
            ) : null}
          </ModalBody>
          <ModalFooter>
            <Stack direction={{ base: "column", md: "row" }} w="100%" gap={2}>
              <Button
                variant="secondary"
                onClick={() => { setAbonoAEliminar(null); confirmarEliminarAbono.onClose(); }}
                isDisabled={eliminandoAbono}
                w={{ base: "100%", md: "auto" }}
              >
                Cancelar
              </Button>
              <Button onClick={eliminarAbono} isLoading={eliminandoAbono} w={{ base: "100%", md: "auto" }}>
                Confirmar
              </Button>
            </Stack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </PageWrapper>
  );
};

export default AgendaAdmin;