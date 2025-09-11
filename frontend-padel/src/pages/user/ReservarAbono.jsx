// src/pages/user/ReservarAbono.jsx
import React, { useContext, useEffect, useMemo, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import {
  Box, Text, HStack, VStack, Select, useToast, Badge, Divider, useDisclosure,
  FormControl, FormLabel, Stack, Skeleton, Alert, AlertIcon,
} from "@chakra-ui/react";

import Button from "../../components/ui/Button";
import { useCardColors, useInputColors, useMutedText } from "../../components/theme/tokens";
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
  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);

  const toast = useToast();
  const card = useCardColors();
  const input = useInputColors();
  const muted = useMutedText();

  const pagoDisc = useDisclosure();

  // Mis abonos
  const [loadingAbonos, setLoadingAbonos] = useState(true);
  const [misAbonos, setMisAbonos] = useState([]);
  const [abonosPorVencer, setAbonosPorVencer] = useState([]); // 👈 nuevos
  const [showRenewBanner, setShowRenewBanner] = useState(false);
  const [renovandoAbonoId, setRenovandoAbonoId] = useState(null);

  // Reserva NUEVA (filtros)
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [diaSemana, setDiaSemana] = useState("");
  const [horaFiltro, setHoraFiltro] = useState("");
  const [tiposAbono, setTiposAbono] = useState([]);
  const [tipoAbono, setTipoAbono] = useState("");
  const [abonosLibres, setAbonosLibres] = useState([]);
  const [loadingDisponibles, setLoadingDisponibles] = useState(false);
  const [selectedBonos, setSelectedBonos] = useState([]);

  // Selección activa (nuevo o renovación)
  const [seleccion, setSeleccion] = useState(null);
  const [archivo, setArchivo] = useState(null);
  const [bonificaciones, setBonificaciones] = useState([]);
  const [usarBonificado, setUsarBonificado] = useState(false); // compat
  const [enviando, setEnviando] = useState(false);
  const [modoRenovacion, setModoRenovacion] = useState(false);

  // Alias/CBU (para modal)
  const [alias, setAlias] = useState("");
  const [cbuCvu, setCbuCvu] = useState("");
  const configPago = { tiempo_maximo_minutos: 15 };

  const now = new Date();
  const anioActual = now.getFullYear();
  const mesActual = now.getMonth() + 1;

  const sedeSel = useMemo(
  () => sedes.find(s => String(s.id) === String(sedeId)) || null,
  [sedes, sedeId]
  );
  const profSel = useMemo(
    () => profesores.find(p => String(p.id) === String(profesorId)) || null,
    [profesores, profesorId]
  );

    // Helpers
  const fmtHora = (h) => (h || "").slice(0, 5);
  const proximoMes = (anio, mes) => (mes === 12 ? { anio: anio + 1, mes: 1 } : { anio, mes: mes + 1 });

  // 1) Cargar “Mis abonos”
  useEffect(() => {
    if (!api) return;
    setLoadingAbonos(true);
    api.get("padel/abonos/mios/")
      .then((res) => {
        const data = res?.data?.results ?? res?.data ?? [];
        const arr = Array.isArray(data) ? data : [];
        setMisAbonos(arr);
        const porVencer = arr.filter(
          (a) => a?.ventana_renovacion === true && !a?.renovado && a?.estado_vigencia === "activo"
        );
        setAbonosPorVencer(porVencer);
        setShowRenewBanner(porVencer.length > 0);
      })
      .catch(() => {
        setMisAbonos([]);
        setAbonosPorVencer([]);
        setShowRenewBanner(false);
      })
      .finally(() => setLoadingAbonos(false));
  }, [api]);

  // 2) sedes
  useEffect(() => {
    if (!api) return;
    api.get("turnos/sedes/")
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setSedes(Array.isArray(data) ? data : []);
      })
      .catch(() => setSedes([]));
  }, [api]);

  // 3) profesores por sede
  useEffect(() => {
    if (!api || !sedeId) { setProfesores([]); return; }
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setProfesores(Array.isArray(data) ? data : []);
      })
      .catch(() => setProfesores([]));
  }, [api, sedeId]);

  // 4) alias / CBU
  useEffect(() => {
    if (!sedeId) { setAlias(""); setCbuCvu(""); return; }
    const sede = sedes.find(s => String(s.id) === String(sedeId));
    setAlias(sede?.alias || "");
    setCbuCvu(sede?.cbu_cvu || "");
  }, [sedeId, sedes]);

  // 5) abonos disponibles (nueva reserva)
  useEffect(() => {
    const ready = api && sedeId && profesorId && (diaSemana !== "") && tipoAbono;
    if (!ready) { setAbonosLibres([]); return; }

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
    api.get(`padel/abonos/disponibles/?${params.toString()}`)
      .then(res => {
        let data = res?.data?.results ?? res?.data ?? [];
        data = Array.isArray(data) ? data.filter(d => d?.tipo_clase?.codigo === tipoAbono) : [];
        setAbonosLibres(data);
      })
      .catch(() => {
        setAbonosLibres([]);
        toast({ title: "No se pudieron cargar abonos libres", status: "error", duration: 4000 });
      })
      .finally(() => setLoadingDisponibles(false));
  }, [api, sedeId, profesorId, diaSemana, horaFiltro, tipoAbono, anioActual, mesActual, toast]);

  // Tipos de abono con precio
  useEffect(() => {
    if (!api || !sedeId) { setTiposAbono([]); return; }
    api.get(`padel/tipos-abono/?sede_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setTiposAbono(Array.isArray(data) ? data : []);
      })
      .catch(() => setTiposAbono([]));
  }, [api, sedeId]);

  const precioAbonoPorCodigo = useMemo(() => {
    const map = {};
    (tiposAbono || []).forEach(a => { map[a.codigo] = Number(a.precio); });
    return map;
  }, [tiposAbono]);

  const precioAbonoActual = (tipoCodigo, tipoObj) => {
    if (tipoCodigo && precioAbonoPorCodigo[tipoCodigo] != null) return Number(precioAbonoPorCodigo[tipoCodigo]);
    if (tipoObj && tipoObj.precio != null) return Number(tipoObj.precio);
    return 0;
  };

  // --- Abrir modal (nueva reserva) ---
  const abrirPagoReservaNueva = async (item) => {
    const codigo = item?.tipo_clase?.codigo;
    const precioAbono = Number(precioAbonoPorCodigo[codigo] ?? 0);
    const precioUnit = Number(item?.tipo_clase?.precio ?? 0);

    setSeleccion({
      sede: Number(sedeId),
      prestador: Number(profesorId),
      dia_semana: Number(diaSemana),
      hora: item?.hora,
      tipo_clase: item?.tipo_clase,
      precio_abono: precioAbono,
      precio_unitario: precioUnit,
      anio: anioActual,
      mes: mesActual,
    });
    setModoRenovacion(false);
    setArchivo(null);
    setUsarBonificado(false);

    try {
      if (api && item?.tipo_clase?.id) {
        const res = await api.get(`turnos/bonificados/mios/?tipo_clase_id=${item.tipo_clase.id}`);
        const bonos = res?.data?.results ?? res?.data ?? [];
        setBonificaciones(Array.isArray(bonos) ? bonos : []);
      } else {
        setBonificaciones([]);
      }
    } catch {
      setBonificaciones([]);
    }
    pagoDisc.onOpen();
  };

  // --- Abrir modal (renovación) ---
  const abrirRenovarAbono = async (abono) => {
    setRenovandoAbonoId(abono.id);

    const sede = sedes.find(s => String(s.id) === String(abono.sede_id));
    setAlias(sede?.alias || ""); setCbuCvu(sede?.cbu_cvu || "");

    const { anio, mes } = proximoMes(Number(abono.anio), Number(abono.mes));

    let precioAbono = 0;
    let precioUnit = 0;
    try {
      const [r1, r2] = await Promise.all([
        api.get(`padel/tipos-abono/?sede_id=${abono.sede_id}`),
        api.get(`padel/tipos-clase/?sede_id=${abono.sede_id}`),
      ]);
      const tiposAb = (r1?.data?.results ?? r1?.data ?? []);
      const tiposCl = (r2?.data?.results ?? r2?.data ?? []);
      const ta = tiposAb.find(x => x.codigo === abono.tipo_clase_codigo);
      const tc = tiposCl.find(x => x.codigo === abono.tipo_clase_codigo);
      precioAbono = Number(ta?.precio ?? 0);
      precioUnit = Number(tc?.precio ?? 0);
    } catch {
      precioAbono = 0; precioUnit = 0;
    }

    setSeleccion({
      sede: abono.sede_id,
      prestador: abono.prestador_id,
      dia_semana: abono.dia_semana,
      hora: abono.hora,
      tipo_clase: { id: abono.tipo_clase_id, codigo: abono.tipo_clase_codigo, precio: precioUnit },
      precio_abono: precioAbono,
      precio_unitario: precioUnit,
      anio, mes,
      abono_id: abono.id, // 👈 clave para renovación
    });
    setModoRenovacion(true);
    setArchivo(null);
    setUsarBonificado(false);

    try {
      if (api && abono?.tipo_clase_id) {
        const res = await api.get(`turnos/bonificados/mios/?tipo_clase_id=${abono.tipo_clase_id}`);
        const bonos = res?.data?.results ?? res?.data ?? [];
        setBonificaciones(Array.isArray(bonos) ? bonos : []);
      } else {
        setBonificaciones([]);
      }
    } catch {
      setBonificaciones([]);
    }
    pagoDisc.onOpen();
  };

  // --- Confirmar (nueva o renovación) ---
  const onConfirmarPago = async (bonosIds = []) => {
    if (!seleccion) return;

    const unit = Number(seleccion?.precio_unitario ?? 0);
    const abonoPrice = Number(seleccion?.precio_abono ?? 0);
    const totalEstimado = Math.max(0, abonoPrice - (bonosIds.length * unit));

    if (!archivo && totalEstimado > 0) {
      toast({
        title: "Falta comprobante",
        description: "Subí el comprobante o seleccioná bonificaciones suficientes para cubrir el abono.",
        status: "warning",
        duration: 5000,
      });
      return;
    }

    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("sede", seleccion.sede);
      fd.append("prestador", seleccion.prestador);
      fd.append("dia_semana", seleccion.dia_semana);
      fd.append("hora", seleccion.hora);
      fd.append("tipo_clase", seleccion.tipo_clase?.id);
      fd.append("anio", seleccion.anio);
      fd.append("mes", seleccion.mes);
      fd.append("monto", abonoPrice);
      fd.append("monto_esperado", totalEstimado);
      if (seleccion?.abono_id) {
        fd.append("abono_id", seleccion.abono_id); // 👈 indica RENOVACIÓN al backend
      }
      if (archivo) fd.append("archivo", archivo);
      (bonosIds || []).forEach((id) => fd.append("bonificaciones_ids", String(id)));

      await api.post("padel/abonos/reservar/", fd, { headers: { "Content-Type": "multipart/form-data" } });

      toast({
        title: modoRenovacion ? "Abono renovado" : "Abono reservado",
        description: modoRenovacion ? "Se aplicará al próximo mes." : "Pago registrado.",
        status: "success",
        duration: 4500,
      });

      pagoDisc.onClose();
      setArchivo(null);
      setUsarBonificado(false);
      setSeleccion(null);

      if (modoRenovacion) {
        setMisAbonos(prev =>
          prev.map(a =>
            a.id === renovandoAbonoId ? { ...a, renovado: true, ventana_renovacion: false } : a
          )
        );
        // actualizar banner localmente para que deje de avisar
        setAbonosPorVencer(prev => prev.filter(a => a.id !== renovandoAbonoId));
        setShowRenewBanner(prev => {
          const quedan = abonosPorVencer.filter(a => a.id !== renovandoAbonoId);
          return quedan.length > 0;
        });
        setRenovandoAbonoId(null);
      } else {
        onClose?.();
      }
    } catch (e) {
      const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || "No se pudo completar la operación";
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
    } finally {
      setEnviando(false);
    }
  };

  const modalIsRenderable = typeof ReservaPagoModalAbono === "function";

  // === UI ===
  return (
    <Box w="100%" maxW="1000px" mx="auto" mt={8} p={6} bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl">
      
      {showRenewBanner && (
        <Alert status="warning" mb={4} rounded="md">
          <AlertIcon />
          <Box>
            <Text fontWeight="semibold" mb={1}>
              Tenés abonos por vencer en menos de 7 días:
            </Text>
            <VStack align="stretch" spacing={1}>
              {abonosPorVencer.map((a) => (
                <HStack key={a.id} justify="space-between">
                  <Text fontSize="sm">
                    {a.dia_semana_label} · {fmtHora(a.hora)} hs — vence {a.vence_el || "—"} ({String(a.mes).padStart(2,"0")}/{a.anio})
                  </Text>
                </HStack>
              ))}
            </VStack>
          </Box>
        </Alert>
      )}

      {/* === Mis abonos (arriba) === */}
      <Box mb={6}>
        <Text fontWeight="semibold" mb={2}>Mis abonos</Text>
        {loadingAbonos ? (
          <Stack>
            <Skeleton height="70px" rounded="md" />
            <Skeleton height="70px" rounded="md" />
          </Stack>
        ) : !misAbonos.length ? (
          <Text color={muted}>No tenés abonos.</Text>
        ) : (
          <VStack align="stretch" spacing={3}>
            {misAbonos.map((a) => {
              const elegible = (a.ventana_renovacion === true) && !a.renovado && a.estado_vigencia === "activo";
              return (
                <Box
                  key={a.id}
                  p={3}
                  bg={card.bg}
                  rounded="md"
                  borderWidth="1px"
                  borderColor={input.border}
                >
                  <HStack justify="space-between" align="start">
                    <Box>
                      <Text fontWeight="semibold">
                        {DIAS.find(d => d.value === Number(a.dia_semana))?.label} · {fmtHora(a.hora)} hs
                      </Text>
                      <Text fontSize="sm" color={muted}>
                        {String(a.mes).padStart(2, "0")}/{a.anio} · {a.sede_nombre || "Sede"} · {a.prestador_nombre || "Profesor"}
                      </Text>
                      <HStack mt={2} spacing={2} flexWrap="wrap" rowGap={2}>
                        <Badge colorScheme={a.estado_vigencia === "activo" ? "green" : "gray"}>
                          {a.estado_vigencia}
                        </Badge>
                        {a.renovado ? (
                          <Badge colorScheme="purple" variant="subtle">renovado</Badge>
                        ) : (
                          <Badge variant="outline">vence {a.vence_el || "—"}</Badge>
                        )}
                        <Badge variant="outline">{(a?.tipo_clase_codigo || "").toUpperCase()}</Badge>
                      </HStack>
                    </Box>
                    <Button
                      size="sm"
                      variant={elegible ? "primary" : "secondary"}
                      isDisabled={!elegible}
                      onClick={() => abrirRenovarAbono(a)}
                    >
                      Renovar
                    </Button>
                  </HStack>
                </Box>
              );
            })}
          </VStack>
        )}
      </Box>

      <Divider my={4} />

      <HStack justify="space-between" mb={4} align="end">
        <Text fontSize="2xl" fontWeight="bold">Reservar Abono Mensual</Text>
      </HStack>

      {/* === Reserva NUEVA === */}
      <VStack align="stretch" spacing={3}>
        <Stack
          direction={{ base: "column", md: "row" }}
          spacing={4}
          align={{ base: "stretch", md: "end" }}
          mb={6}
          w="100%"
        >
          {/* Sede */}
          <FormControl flex={1} minW={0}>
            <FormLabel color={muted}>Sede</FormLabel>
            <Select
              value={sedeId}
              placeholder="Seleccioná"
              onChange={(e) => {
                setSedeId(e.target.value);
                setProfesorId("");
                setDiaSemana("");
                setTipoAbono("");
                setHoraFiltro("");
              }}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {sedes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre || s.nombre_publico || `Sede ${s.id}`}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Profesor */}
          <FormControl flex={1} minW={0} isDisabled={!sedeId}>
            <FormLabel color={muted}>Profesor</FormLabel>
            <Select
              value={profesorId}
              placeholder="Seleccioná"
              onChange={(e) => setProfesorId(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {profesores.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre || p.email || `Profe ${p.id}`}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Día de la semana */}
          <FormControl flex={1} minW={0} isDisabled={!profesorId}>
            <FormLabel color={muted}>Día de la semana</FormLabel>
            <Select
              value={diaSemana}
              placeholder="Seleccioná"
              onChange={(e) => setDiaSemana(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {DIAS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Tipo de abono */}
          <FormControl flex={1} minW={0} isDisabled={!profesorId}>
            <FormLabel color={muted}>Tipo de abono</FormLabel>
            <Select
              value={tipoAbono}
              placeholder="Seleccioná"
              onChange={(e) => setTipoAbono(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {ABONO_OPCIONES.map((op) => (
                <option key={op.codigo} value={op.codigo}>
                  {op.nombre}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Hora (opcional) */}
          <FormControl flex={1} minW={0} isDisabled={diaSemana === ""}>
            <FormLabel color={muted}>Hora (opcional)</FormLabel>
            <Select
              value={horaFiltro}
              onChange={(e) => setHoraFiltro(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              <option value="">Todas</option>
              {Array.from({ length: 15 }).map((_, i) => {
                const h = (8 + i).toString().padStart(2, "0") + ":00:00";
                return (
                  <option key={h} value={h}>
                    {h.slice(0, 5)}
                  </option>
                );
              })}
            </Select>
          </FormControl>
        </Stack>

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
                  onClick={() => abrirPagoReservaNueva(item)}
                >
                  <HStack justify="space-between" align="center">
                    <Box>
                      <Text fontWeight="semibold">
                        {DIAS.find(d => String(d.value) === String(diaSemana))?.label} · {fmtHora(item?.hora)} hs
                      </Text>

                      {/* SUBLINE igual que en "Mis abonos": MM/AAAA · Sede · Profesor */}
                      <Text fontSize="sm" color={muted}>
                        {String(mesActual).padStart(2, "0")}/{anioActual}
                        {" · "}
                        {sedeSel?.nombre || sedeSel?.nombre_publico || `Sede ${sedeId}`}
                        {" · "}
                        {profSel?.nombre_publico || profSel?.nombre || profSel?.email || `Profe ${profesorId}`}
                      </Text>

                      <HStack mt={2} spacing={2}>
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

      {/* Modal */}
      {modalIsRenderable ? (
        <ReservaPagoModalAbono
          isOpen={pagoDisc.isOpen}
          onClose={pagoDisc.onClose}
          alias={alias}
          cbuCvu={cbuCvu}
          turno={
            seleccion
              ? { fecha: `Mes ${String(seleccion.mes).padStart(2,"0")}/${seleccion.anio}`, hora: seleccion.hora }
              : null
          }
          tipoClase={seleccion?.tipo_clase || null}
          precioAbono={seleccion?.precio_abono ?? 0}
          precioUnitario={seleccion?.precio_unitario ?? 0}
          archivo={archivo}
          onArchivoChange={setArchivo}
          onRemoveArchivo={() => setArchivo(null)}
          onConfirmar={(ids) => onConfirmarPago(ids)}
          loading={enviando}
          tiempoRestante={configPago?.tiempo_maximo_minutos ? configPago.tiempo_maximo_minutos * 60 : undefined}
          bonificaciones={bonificaciones}
          selectedBonos={selectedBonos}
          setSelectedBonos={setSelectedBonos}
        />
      ) : (
        <Box mt={4} p={4} borderWidth="1px" rounded="md" bg="red.50" color="red.700">
          El componente de pago no se pudo cargar.
        </Box>
      )}
    </Box>
  );
};

export default ReservarAbono;
