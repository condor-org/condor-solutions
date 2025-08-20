// src/pages/user/ReservarAbono.jsx
import React, { useContext, useEffect, useMemo, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import {
  Box, Text, HStack, VStack, Select, useToast, Badge, Divider, useDisclosure,
} from "@chakra-ui/react";
import Button from "../../components/ui/Button";
import { useCardColors, useInputColors, useMutedText } from "../../components/theme/tokens";
// 👇 Import CON extensión .jsx (clave para evitar que resuelva a un objeto módulo)
import ReservaPagoModalAbono from "../../components/modals/ReservaPagoModalAbono.jsx";

const DIAS = [
  { value: 0, label: "Lunes" },
  { value: 1, label: "Martes" },
  { value: 2, label: "Miércoles" },
  { value: 3, label: "Jueves" },
  { value: 4, label: "Viernes" },
  { value: 5, label: "Sábado" },
  { value: 6, label: "Domingo" },
];
const LABELS = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };

const ABONO_OPCIONES = [
  { codigo: "x1", nombre: "Individual" },
  { codigo: "x2", nombre: "2 Personas" },
  { codigo: "x3", nombre: "3 Personas" },
  { codigo: "x4", nombre: "4 Personas" },
];

const ReservarAbono = ({ onClose }) => {
  console.groupCollapsed("%c[ReservarAbono] mount", "color:#09f");
  console.debug("[ReservarAbono] typeof ReservaPagoModalAbono =", typeof ReservaPagoModalAbono);
  console.groupEnd();

  const [tiposAbono, setTiposAbono] = useState([]);

  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => {
    const inst = accessToken ? axiosAuth(accessToken) : null;
    console.debug("[ReservarAbono] axiosAuth instanciado?", !!inst);
    return inst;
  }, [accessToken]);

  const toast = useToast();
  const card = useCardColors();
  const input = useInputColors();
  const muted = useMutedText();

  const pagoDisc = useDisclosure();

  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [diaSemana, setDiaSemana] = useState("");
  const [horaFiltro, setHoraFiltro] = useState(""); // opcional

  const [configPago, setConfigPago] = useState({ alias: "", cbu_cvu: "" });

  const [tipoAbono, setTipoAbono] = useState(""); // requerido
  const [abonosLibres, setAbonosLibres] = useState([]);
  const [loadingDisponibles, setLoadingDisponibles] = useState(false);

  const [seleccion, setSeleccion] = useState(null); // {sede, prestador, dia_semana, hora, tipo_clase}
  const [archivo, setArchivo] = useState(null);
  const [bonosDisponibles, setBonosDisponibles] = useState([]);
  const [selectedBonos, setSelectedBonos] = useState([]);
  const [enviandoReserva, setEnviandoReserva] = useState(false);

  const now = new Date();
  const anioActual = now.getFullYear();
  const mesActual = now.getMonth() + 1; // 1..12

  // 1) cargar sedes
  useEffect(() => {
    if (!api) return;
    console.debug("[ReservarAbono] GET turnos/sedes/");
    api.get("turnos/sedes/")
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        console.debug("[ReservarAbono] sedes len:", Array.isArray(data) ? data.length : "n/a", data);
        setSedes(Array.isArray(data) ? data : []);
      })
      .catch((e) => {
        console.error("[ReservarAbono] sedes error:", e);
        setSedes([]);
      });
  }, [api]);

  // 2) cargar profesores por sede
  useEffect(() => {
    if (!api || !sedeId) { setProfesores([]); return; }
    console.debug("[ReservarAbono] GET turnos/prestadores/?lugar_id=", sedeId);
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        console.debug("[ReservarAbono] profesores len:", Array.isArray(data) ? data.length : "n/a", data);
        setProfesores(Array.isArray(data) ? data : []);
      })
      .catch((e) => {
        console.error("[ReservarAbono] profesores error:", e);
        setProfesores([]);
      });
  }, [api, sedeId]);

  // 3) config pago (alias / CBU) basado en sede
  useEffect(() => {
    if (!sedeId) { setConfigPago({ alias: "", cbu_cvu: "" }); return; }
    const sede = sedes.find(s => String(s.id) === String(sedeId));
    console.debug("[ReservarAbono] setConfigPago desde sede", sede);
    setConfigPago({ alias: sede?.alias || "", cbu_cvu: sede?.cbu_cvu || "" });
  }, [sedeId, sedes]);

  // 4) buscar abonos disponibles cuando haya filtros completos
  useEffect(() => {
    const ready = api && sedeId && profesorId && (diaSemana !== "") && tipoAbono;
    console.debug("[ReservarAbono] filtros", { sedeId, profesorId, diaSemana, tipoAbono, horaFiltro, ready });

    if (!ready) {
      setAbonosLibres([]);
      return;
    }

    const params = new URLSearchParams({
      sede_id: String(sedeId),
      prestador_id: String(profesorId),
      dia_semana: String(diaSemana),
      anio: String(anioActual),
      mes: String(mesActual),
      tipo_codigo: String(tipoAbono),
    });
    if (horaFiltro) params.append("hora", horaFiltro);

    setLoadingDisponibles(true);
    const url = `padel/abonos/disponibles/?${params.toString()}`;
    console.debug("[ReservarAbono] GET", url);
    api.get(url)
      .then(res => {
        let data = res?.data?.results ?? res?.data ?? [];
        console.debug("[ReservarAbono] disponibles raw len=", Array.isArray(data) ? data.length : "n/a", data);
        data = Array.isArray(data) ? data.filter(d => d?.tipo_clase?.codigo === tipoAbono) : [];
        console.debug("[ReservarAbono] disponibles filtrados len=", data.length);
        setAbonosLibres(data);
      })
      .catch((e) => {
        console.error("[ReservarAbono] disponibles error:", e);
        setAbonosLibres([]);
        toast({ title: "No se pudieron cargar abonos libres", status: "error", duration: 4000 });
      })
      .finally(() => setLoadingDisponibles(false));
  }, [api, sedeId, profesorId, diaSemana, horaFiltro, tipoAbono, anioActual, mesActual, toast]);

  // Tipos de abono c/precio por sede (para mostrar precio mensual)
  useEffect(() => {
    if (!api || !sedeId) { setTiposAbono([]); return; }
    console.debug("[ReservarAbono] GET padel/tipos-abono/?sede_id=", sedeId);
    api.get(`padel/tipos-abono/?sede_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        console.debug("[ReservarAbono] tiposAbono len:", Array.isArray(data) ? data.length : "n/a", data);
        setTiposAbono(Array.isArray(data) ? data : []);
      })
      .catch((e) => {
        console.error("[ReservarAbono] tiposAbono error:", e);
        setTiposAbono([]);
      });
  }, [api, sedeId]);

  const precioAbonoPorCodigo = useMemo(() => {
    const map = {};
    (tiposAbono || []).forEach(a => { map[a.codigo] = Number(a.precio); });
    console.debug("[ReservarAbono] precioAbonoPorCodigo", map);
    return map;
  }, [tiposAbono]);

  const precioAbonoActual = (tipoCodigo, tipoObj) => {
    // 1) preferí precios de /padel/tipos-abono (map por código)
    if (tipoCodigo && precioAbonoPorCodigo[tipoCodigo] != null) {
      return Number(precioAbonoPorCodigo[tipoCodigo]);
    }
    // 2) fallback por si la API ya trae precio en item.tipo_clase
    if (tipoObj && tipoObj.precio != null) return Number(tipoObj.precio);
    return 0;
  };

  // abrir modal y traer bonos vigentes del tipo
    const abrirPago = async (item) => {
      const codigo = item?.tipo_clase?.codigo;
      const precioAbono = Number(precioAbonoPorCodigo[codigo] ?? 0);      // precio mensual del abono
      const precioUnit = Number(item?.tipo_clase?.precio ?? 0);           // precio por clase (descuento por bono)
      console.debug("[ReservarAbono] abrirPago", { codigo, precioAbono, precioUnit, item });
    
    console.groupCollapsed("%c[ReservarAbono] abrirPago", "color:#0a0");
    console.debug("item =", item);
    const payloadSel = {
      sede: Number(sedeId),
      prestador: Number(profesorId),
      dia_semana: Number(diaSemana),
      hora: item?.hora,
      tipo_clase: item?.tipo_clase,
      precio_abono: precioAbono,
      precio_unitario: precioUnit,
    };
    console.debug("seleccion =>", payloadSel);
    setSeleccion(payloadSel);
    setArchivo(null);
    setSelectedBonos([]);

    // chequeo de tipo del componente del modal ANTES de abrir
    console.debug("typeof ReservaPagoModalAbono =", typeof ReservaPagoModalAbono);
    if (typeof ReservaPagoModalAbono !== "function") {
      console.error("[ReservarAbono] ReservaPagoModalAbono NO es function", ReservaPagoModalAbono);
    }
    pagoDisc.onOpen();

    try {
      if (api && item?.tipo_clase?.id) {
        const url = `turnos/bonificados/mios/?tipo_clase_id=${item.tipo_clase.id}`;
        console.debug("[ReservarAbono] GET", url);
        const res = await api.get(url);
        const bonos = res?.data?.results ?? res?.data ?? [];
        console.debug("[ReservarAbono] bonosDisponibles len=", Array.isArray(bonos) ? bonos.length : "n/a", bonos);
        setBonosDisponibles(Array.isArray(bonos) ? bonos : []);
      } else {
        console.debug("[ReservarAbono] sin tipo_clase.id => bonos vacíos");
        setBonosDisponibles([]);
      }
    } catch (e) {
      console.error("[ReservarAbono] bonosDisponibles error:", e);
      setBonosDisponibles([]);
    }
    console.groupEnd();
  };

  // confirmar: 1) crear abono (JSON), 2) subir comprobante + bonos
  const confirmarReservaAbono = async (bonosIds = []) => {
    console.groupCollapsed("%c[ReservarAbono] confirmarReservaAbono", "color:#a50");
    console.debug("seleccion =", seleccion);
    console.debug("archivo =", archivo);
    console.debug("bonosIds =", bonosIds);

    if (!seleccion) {
      console.error("[ReservarAbono] no hay selección");
      console.groupEnd();
      return;
    }
     // cálculo local del total estimado
    const unit = Number(seleccion?.precio_unitario ?? 0);
    const abonoPrice = Number(seleccion?.precio_abono ?? 0);
    const totalEstimado = Math.max(0, abonoPrice - (Number(bonosIds?.length || 0) * unit));
    console.debug("[ReservarAbono] confirmar -> precios", {
      abonoPrice, unit, bonos: bonosIds?.length || 0, totalEstimado, tieneArchivo: !!archivo
    });

    // si total > 0 → necesitamos comprobante
    if (!archivo && totalEstimado > 0) {
      toast({
        title: "Falta comprobante",
        description: "Subí el comprobante o seleccioná bonificaciones suficientes para cubrir el abono.",
        status: "warning",
        duration: 5000,
      });
      console.warn("[ReservarAbono] faltó comprobante");
      console.groupEnd();
      return;
    }

    setEnviandoReserva(true);
    try {
      const monto = precioAbonoActual(seleccion?.tipo_clase?.codigo, seleccion?.tipo_clase);
      const totalEstimado = Math.max(0, monto - (Number(bonosIds?.length || 0) * Number(seleccion?.precio_unitario ?? 0)));

      const fd = new FormData();
      fd.append("sede", seleccion.sede);
      fd.append("prestador", seleccion.prestador);
      fd.append("dia_semana", seleccion.dia_semana);
      fd.append("hora", seleccion.hora);
      fd.append("tipo_clase", seleccion.tipo_clase?.id);
      fd.append("anio", anioActual);
      fd.append("mes", mesActual);
      fd.append("monto", monto);
      fd.append("monto_esperado", totalEstimado);

      if (archivo) {
        fd.append("archivo", archivo);
      }

      (bonosIds || []).forEach((id) => {
        fd.append("bonificaciones_ids", String(id));
      });

      console.debug("[ReservarAbono] POST /padel/abonos/reservar/ form:", Object.fromEntries(fd.entries()));

      await api.post("padel/abonos/reservar/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast({
        title: "Abono reservado",
        description: "Pago registrado. Turnos del mes reservados y prioridad del próximo.",
        status: "success",
        duration: 4500,
      });
      pagoDisc.onClose();
      onClose?.();
    } catch (e) {
      const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || "No se pudo reservar el abono";
      console.error("[ReservarAbono] ERROR confirmarReservaAbono:", e);
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
    } finally {
      setEnviandoReserva(false);
      console.groupEnd();
    }
  };

  const modalIsRenderable = typeof ReservaPagoModalAbono === "function";

  return (
    <Box w="100%" maxW="1000px" mx="auto" mt={8} p={6} bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl">
      <HStack justify="space-between" mb={4} align="end">
        <Text fontSize="2xl" fontWeight="bold">Reservar Abono Mensual</Text>
      </HStack>

      <VStack align="stretch" spacing={3}>
        <HStack>
          <Box flex={1}>
            <Text fontSize="sm" mb={1} color={muted}>Sede</Text>
            <Select value={sedeId} onChange={e => setSedeId(e.target.value)} bg={input.bg} borderColor={input.border}>
              <option value="">Seleccioná</option>
              {sedes.map(s => <option key={s.id} value={s.id}>{s.nombre || s.nombre_publico || `Sede ${s.id}`}</option>)}
            </Select>
          </Box>

          <Box flex={1}>
            <Text fontSize="sm" mb={1} color={muted}>Profesor</Text>
            <Select value={profesorId} onChange={e => setProfesorId(e.target.value)} bg={input.bg} borderColor={input.border} isDisabled={!sedeId}>
              <option value="">Seleccioná</option>
              {profesores.map(p => <option key={p.id} value={p.id}>{p.nombre || p.email || `Profe ${p.id}`}</option>)}
            </Select>
          </Box>

          <Box flex={1}>
            <Text fontSize="sm" mb={1} color={muted}>Día de la semana</Text>
            <Select value={diaSemana} onChange={e => setDiaSemana(e.target.value)} bg={input.bg} borderColor={input.border} isDisabled={!profesorId}>
              <option value="">Seleccioná</option>
              {DIAS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </Select>
          </Box>

          <Box flex={1}>
            <Text fontSize="sm" mb={1} color={muted}>Tipo de abono</Text>
            <Select
              value={tipoAbono}
              onChange={e => setTipoAbono(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              isDisabled={!profesorId}
            >
              <option value="">Seleccioná</option>
              {ABONO_OPCIONES.map(op => (
                <option key={op.codigo} value={op.codigo}>{op.nombre}</option>
              ))}
            </Select>
          </Box>

          <Box flex={1}>
            <Text fontSize="sm" mb={1} color={muted}>Hora (opcional)</Text>
            <Select value={horaFiltro} onChange={e => setHoraFiltro(e.target.value)} bg={input.bg} borderColor={input.border} isDisabled={diaSemana === ""}>
              <option value="">Todas</option>
              {Array.from({ length: 15 }).map((_, i) => {
                const h = (8 + i).toString().padStart(2, "0") + ":00:00";
                return <option key={h} value={h}>{h.slice(0,5)}</option>;
              })}
            </Select>
          </Box>
        </HStack>

        <Divider my={2} />

        <Box>
          <Text fontWeight="semibold" mb={2}>
            Abonos libres {loadingDisponibles ? "— cargando..." : ""}
          </Text>
          {(sedeId && profesorId && diaSemana !== "" && !tipoAbono) && (
            <Text color={muted} mb={2}>Elegí un tipo de abono para ver disponibilidad.</Text>
          )}

          {!loadingDisponibles && abonosLibres.length === 0 && (sedeId && profesorId && diaSemana !== "") ? (
            <Text color={muted}>No hay abonos libres para los filtros seleccionados.</Text>
          ) : null}

          <VStack align="stretch" spacing={3}>
            {abonosLibres.map((item, idx) => {
              const codigo = item?.tipo_clase?.codigo;
              const pAbono = precioAbonoPorCodigo[codigo];

              return (
                <Box
                  key={`${item?.hora || "hora"}-${idx}`}
                  p={3}
                  bg={card.bg}
                  rounded="md"
                  borderWidth="1px"
                  borderColor={input.border}
                  _hover={{ boxShadow: "lg", cursor: "pointer", opacity: 0.95 }}
                  onClick={() => abrirPago(item)}
                >
                  <HStack justify="space-between" align="center">
                    <Box>
                      <Text fontWeight="semibold">
                        {DIAS.find(d => String(d.value) === String(diaSemana))?.label} · {item?.hora?.slice(0,5)} hs
                      </Text>
                      <HStack mt={1} spacing={2}>
                        <Badge variant="outline">
                          {item?.tipo_clase?.nombre || LABELS[item?.tipo_clase?.codigo] || "Tipo"}
                        </Badge>
                        <Badge colorScheme="green">
                          ${Number(pAbono ?? item?.tipo_clase?.precio ?? 0).toLocaleString("es-AR")}
                        </Badge>
                      </HStack>
                    </Box>
                    <Button variant="primary">Seleccionar</Button>
                  </HStack>
                </Box>
              );
            })}
          </VStack>
        </Box>
      </VStack>

      {/* Modal de Pago para Abono */}
      {modalIsRenderable ? (
        <ReservaPagoModalAbono
          isOpen={pagoDisc.isOpen}
          onClose={pagoDisc.onClose}
          turno={seleccion ? {
            fecha: `Mes ${mesActual}/${anioActual}`,
            hora: seleccion.hora,
            estado: "abono",
            lugar: sedeId,
          } : null}
          tipoClase={seleccion?.tipo_clase || null}
          precioAbono={seleccion?.precio_abono ?? 0}
          precioUnitario={seleccion?.precio_unitario ?? 0}
          archivo={archivo}
          onArchivoChange={setArchivo}
          onRemoveArchivo={() => setArchivo(null)}
          onConfirmar={(ids) => confirmarReservaAbono(ids)}
          loading={enviandoReserva}
          tiempoRestante={undefined}
          bonificaciones={bonosDisponibles}
          selectedBonos={selectedBonos}
          setSelectedBonos={setSelectedBonos}
          alias={configPago.alias}
          cbuCvu={configPago.cbu_cvu}
        />
      ) : (
        // Fallback visible si el import está mal (evita pantalla en blanco)
        <Box mt={4} p={4} borderWidth="1px" rounded="md" bg="red.50" color="red.700">
          El componente de pago no se pudo cargar. Ver consola para detalles.
        </Box>
      )}
    </Box>
  );
};

export default ReservarAbono;
