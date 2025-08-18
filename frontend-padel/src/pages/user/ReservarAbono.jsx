// src/pages/usuario/ReservarAbono.jsx
import React, { useContext, useEffect, useMemo, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import {
  Box, Text, HStack, VStack, Select, useToast, Badge, Divider,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, useDisclosure
} from "@chakra-ui/react";
import Button from "../../components/ui/Button";
import { useCardColors, useInputColors, useModalColors, useMutedText } from "../../components/theme/tokens";
import ReservaPagoModal from "../../components/modals/ReservaPagoModal";

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
  const [tiposAbono, setTiposAbono] = useState([]);

  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);

  const toast = useToast();
  const card = useCardColors();
  const input = useInputColors();
  const modal = useModalColors();
  const muted = useMutedText();

  const pagoDisc = useDisclosure();

  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [diaSemana, setDiaSemana] = useState("");
  const [horaFiltro, setHoraFiltro] = useState(""); // opcional

  const [configPago, setConfigPago] = useState({ alias: "", cbu_cvu: "" });

  const [tipoAbono, setTipoAbono] = useState(""); // nuevo filtro requerido
  const [abonosLibres, setAbonosLibres] = useState([]);
  const [loadingDisponibles, setLoadingDisponibles] = useState(false);

  const [seleccion, setSeleccion] = useState(null); // {sede, prestador, dia_semana, hora, tipo_clase}
  const [archivo, setArchivo] = useState(null);
  const [usarBonificaciones, setUsarBonificaciones] = useState(false);
  const [enviandoReserva, setEnviandoReserva] = useState(false);

  const now = new Date();
  const anioActual = now.getFullYear();
  const mesActual = now.getMonth() + 1; // 1..12

  // 1) cargar sedes
  useEffect(() => {
    if (!api) return;
    api.get("turnos/sedes/")
      .then(res => setSedes(res.data.results || res.data || []))
      .catch(() => setSedes([]));
  }, [api]);

  // 2) cargar profesores por sede
  useEffect(() => {
    if (!api || !sedeId) { setProfesores([]); return; }
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => setProfesores(res.data.results || res.data || []))
      .catch(() => setProfesores([]));
  }, [api, sedeId]);

  // 3) config pago (alias / CBU) basado en sede
  useEffect(() => {
    if (!sedeId) { setConfigPago({ alias: "", cbu_cvu: "" }); return; }
    const sede = sedes.find(s => String(s.id) === String(sedeId));
    setConfigPago({ alias: sede?.alias || "", cbu_cvu: sede?.cbu_cvu || "" });
  }, [sedeId, sedes]);

  // 4) buscar abonos disponibles cuando haya filtros completos
  useEffect(() => {
    const ready = api && sedeId && profesorId && (diaSemana !== "") && tipoAbono; // 👈 exige tipo
    if (!ready) {
      console.debug("[ReservarAbono] filtros incompletos", { sedeId, profesorId, diaSemana, tipoAbono });
      setAbonosLibres([]);
      return;
    }
  
    const params = new URLSearchParams({
      sede_id: String(sedeId),
      prestador_id: String(profesorId),
      dia_semana: String(diaSemana),
      anio: String(anioActual),
      mes: String(mesActual),
      tipo_codigo: String(tipoAbono), // 👈 si tu API lo soporta
    });
    if (horaFiltro) params.append("hora", horaFiltro);
  
    setLoadingDisponibles(true);
    api.get(`padel/abonos/disponibles/?${params.toString()}`)
      .then(res => {
        let data = res.data.results || res.data || [];
        // Filtro por si el backend todavía no filtra por tipo.
        data = data.filter(d => d?.tipo_clase?.codigo === tipoAbono);
        setAbonosLibres(Array.isArray(data) ? data : []);
      })
      .catch((e) => {
        console.error("[ReservarAbono] Error cargando disponibles:", e);
        setAbonosLibres([]);
        toast({ title: "No se pudieron cargar abonos libres", status: "error", duration: 4000 });
      })
      .finally(() => setLoadingDisponibles(false));
  }, [api, sedeId, profesorId, diaSemana, horaFiltro, tipoAbono, anioActual, mesActual, toast]);
  

  useEffect(() => {
    if (!api || !sedeId) { setTiposAbono([]); return; }
    api.get(`padel/tipos-abono/?sede_id=${sedeId}`)
      .then(res => setTiposAbono(res.data.results || res.data || []))
      .catch(() => setTiposAbono([]));
  }, [api, sedeId]);
  
  const precioAbonoPorCodigo = useMemo(() => {
    const map = {};
    (tiposAbono || []).forEach(a => { map[a.codigo] = Number(a.precio); });
    return map;
  }, [tiposAbono]);
  
  const abrirPago = (item) => {
    // item esperado: {hora, tipo_clase:{id,nombre,precio}}
    setSeleccion({
      sede: Number(sedeId),
      prestador: Number(profesorId),
      dia_semana: Number(diaSemana),
      hora: item?.hora,
      tipo_clase: item?.tipo_clase, // objeto
    });
    setArchivo(null);
    setUsarBonificaciones(false);
    pagoDisc.onOpen();
  };

  const confirmarReservaAbono = async () => {
    if (!seleccion) return;
    if (!usarBonificaciones && !archivo) {
      toast({
        title: "Falta comprobante",
        description: "Subí el comprobante o activá 'Usar bonificaciones'.",
        status: "warning",
        duration: 5000,
      });
      return;
    }

    const form = new FormData();
    form.append("sede", String(seleccion.sede));
    form.append("prestador", String(seleccion.prestador));
    form.append("dia_semana", String(seleccion.dia_semana));
    form.append("hora", seleccion.hora);
    form.append("tipo_clase", String(seleccion.tipo_clase?.id));
    form.append("anio", String(anioActual));
    form.append("mes", String(mesActual));
    if (usarBonificaciones) {
      form.append("usar_bonificaciones", "true");
    } else if (archivo) {
      form.append("comprobante", archivo);
    }

    setEnviandoReserva(true);
    try {
      await api.post("padel/abonos/", form, { headers: { "Content-Type": "multipart/form-data" } });
      toast({
        title: "Abono reservado",
        description: "Se reservaron tus turnos del mes y quedó prioridad para el siguiente.",
        status: "success",
        duration: 4500,
      });
      pagoDisc.onClose();
      onClose?.();
    } catch (e) {
      const msg = e?.response?.data?.error || e?.response?.data?.detail || "No se pudo reservar el abono";
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
      console.error("[ReservarAbono][POST /padel/abonos/]", e);
    } finally {
      setEnviandoReserva(false);
    }
  };

  return (
    <Box w="100%" maxW="1000px" mx="auto" mt={8} p={6} bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl">
      <HStack justify="space-between" mb={4} align="end">
        <Text fontSize="2xl" fontWeight="bold">Reservar Abono Mensual</Text>
        <Button variant="secondary" onClick={onClose}>Cerrar</Button>
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
              {/* Si querés, podés poblar esto dinámicamente con horas válidas (8..22) */}
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
            {(sedeId && profesorId && diaSemana !== "" && !tipoAbono) && (
              <Text color={muted} mb={2}>Elegí un tipo de abono para ver disponibilidad.</Text>
            )}

          </Text>
          

          {!loadingDisponibles && abonosLibres.length === 0 && (sedeId && profesorId && diaSemana !== "") ? (
            <Text color={muted}>No hay abonos libres para los filtros seleccionados.</Text>
          ) : null}

          <VStack align="stretch" spacing={3}>
            {abonosLibres.map((item, idx) => {
              // 👇 calcular precio del abono según el código del item
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

      {/* Modal de Pago (reutilizado) */}
      <ReservaPagoModal
        isOpen={pagoDisc.isOpen}
        onClose={pagoDisc.onClose}
        // ⚠️ Reusamos las props esperadas:
        // "turno" se usa para mostrar info. Pasamos una estructura amigable.
        turno={seleccion ? {
          fecha: `Mes ${mesActual}/${anioActual}`, // display-friendly
          hora: seleccion.hora,
          estado: "abono",
          lugar: sedeId,
        } : null}
        tipoClase={seleccion?.tipo_clase || null}
        archivo={archivo}
        onArchivoChange={setArchivo}
        onRemoveArchivo={() => setArchivo(null)}
        onConfirmar={confirmarReservaAbono}
        loading={enviandoReserva}
        // Para abonos el tiempo puede no aplicar; dejamos undefined.
        tiempoRestante={undefined}
        // Para abonos: placeholder simple. Si en el futuro aplican bonos múltiples, lo expandimos.
        bonificaciones={[]}
        usarBonificado={usarBonificaciones}
        setUsarBonificado={setUsarBonificaciones}
        alias={configPago.alias}
        cbuCvu={configPago.cbu_cvu}
      />
    </Box>
  );
};

export default ReservarAbono;
