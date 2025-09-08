// src/pages/admin/ReservarAbonoAdmin.jsx
import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import {
  Box, Text, HStack, VStack, Select, useToast, Badge, Divider, useDisclosure,
  FormControl, FormLabel, Stack, InputGroup, InputLeftElement, useColorModeValue,
  AlertDialog, AlertDialogOverlay, AlertDialogContent, AlertDialogHeader,
  AlertDialogBody, AlertDialogFooter
} from "@chakra-ui/react";
import { SearchIcon, CheckIcon } from "@chakra-ui/icons";
import { Input as ChakraInput } from "@chakra-ui/react";

import Button from "../../components/ui/Button";
import PageWrapper from "../../components/layout/PageWrapper";
import Sidebar from "../../components/layout/Sidebar";
import { useCardColors, useInputColors, useMutedText } from "../../components/theme/tokens";

const DIAS = [
  { value: 0, label: "Lunes" }, { value: 1, label: "Martes" }, { value: 2, label: "Miércoles" },
  { value: 3, label: "Jueves" }, { value: 4, label: "Viernes" }, { value: 5, label: "Sábado" }, { value: 6, label: "Domingo" },
];
const LABELS = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };
const ABONO_OPCIONES = [
  { codigo: "x1", nombre: "Individual" },
  { codigo: "x2", nombre: "2 Personas" },
  { codigo: "x3", nombre: "3 Personas" },
  { codigo: "x4", nombre: "4 Personas" },
];

const ReservarAbonoAdmin = () => {
  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);
  const toast = useToast();

  const card = useCardColors();
  const input = useInputColors();
  const muted = useMutedText();
  const hoverBg = useColorModeValue("gray.100", "gray.700");

  // filtros principales
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [diaSemana, setDiaSemana] = useState("");
  const [tipoAbono, setTipoAbono] = useState("");
  const [horaFiltro, setHoraFiltro] = useState("");

  // usuarios destino
  const [usuarios, setUsuarios] = useState([]); // solo usuario_final (filtrado al cargar)
  const [busquedaUser, setBusquedaUser] = useState("");
  const [usuarioId, setUsuarioId] = useState("");

  // disponibilidad y precios
  const [abonosLibres, setAbonosLibres] = useState([]);
  const [loadingDisponibles, setLoadingDisponibles] = useState(false);
  const [tiposAbono, setTiposAbono] = useState([]);

  // confirmación (sin modal de pago)
  const confirmDisc = useDisclosure();
  const cancelRef = useRef(null);
  const [abonoSeleccionado, setAbonoSeleccionado] = useState(null);
  const [enviando, setEnviando] = useState(false);

  // fecha actual
  const now = new Date();
  const anioActual = now.getFullYear();
  const mesActual = now.getMonth() + 1; // 1..12

  // ======= CARGAS =======
  useEffect(() => {
    if (!api) return;
    api.get("turnos/sedes/")
      .then(res => setSedes(res?.data?.results ?? res?.data ?? []))
      .catch(e => { console.error("[AbonoAdmin] sedes error:", e); setSedes([]); });
  }, [api]);

  useEffect(() => {
    if (!api) return;
    // Traemos todos, y nos quedamos SOLO con usuario_final
    api.get("auth/usuarios/?ordering=email")
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        const finales = (Array.isArray(data) ? data : []).filter(u => u?.tipo_usuario === "usuario_final");
        setUsuarios(finales);
      })
      .catch(e => { console.error("[AbonoAdmin] usuarios error:", e); setUsuarios([]); });
  }, [api]);

  useEffect(() => {
    if (!api || !sedeId) { setProfesores([]); return; }
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => setProfesores(res?.data?.results ?? res?.data ?? []))
      .catch(e => { console.error("[AbonoAdmin] prestadores error:", e); setProfesores([]); });
  }, [api, sedeId]);

  useEffect(() => {
    if (!api || !sedeId) { setTiposAbono([]); return; }
    api.get(`padel/tipos-abono/?sede_id=${sedeId}`)
      .then(res => setTiposAbono(res?.data?.results ?? res?.data ?? []))
      .catch(e => { console.error("[AbonoAdmin] tiposAbono error:", e); setTiposAbono([]); });
  }, [api, sedeId]);

  // abonos libres
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

    const url = `padel/abonos/disponibles/?${params.toString()}`;
    setLoadingDisponibles(true);
    api.get(url)
      .then(res => {
        let data = res?.data?.results ?? res?.data ?? [];
        data = Array.isArray(data) ? data.filter(d => d?.tipo_clase?.codigo === tipoAbono) : [];
        setAbonosLibres(data);
      })
      .catch(e => {
        console.error("[AbonoAdmin] disponibles error:", e);
        setAbonosLibres([]);
        toast({ title: "No se pudieron cargar abonos libres", status: "error", duration: 4000 });
      })
      .finally(() => setLoadingDisponibles(false));
  }, [api, sedeId, profesorId, diaSemana, horaFiltro, tipoAbono, anioActual, mesActual, toast]);

  // ======= MEMOS / HELPERS =======
  const usuariosFiltrados = useMemo(() => {
    const q = (busquedaUser || "").trim().toLowerCase();
    if (!q) return usuarios;
    return (usuarios || []).filter(u => {
      const campos = [u.nombre, u.apellido, u.email, u.telefono, u.username];
      return campos.some(c => (c || "").toString().toLowerCase().includes(q));
    });
  }, [usuarios, busquedaUser]);

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

  const usuarioSeleccionado = useMemo(
    () => (usuarios || []).find(u => String(u.id) === String(usuarioId)) || null,
    [usuarios, usuarioId]
  );

  // ======= ACCIONES =======
  const handleClickAbono = (item) => {
    if (!usuarioId) {
      toast({ title: "Seleccioná un usuario", status: "warning", duration: 3000 });
      return;
    }
    setAbonoSeleccionado(item);
    confirmDisc.onOpen();
  };

  const confirmarAsignacion = async () => {
    if (!api || !abonoSeleccionado || !usuarioId) return;

    const codigo = abonoSeleccionado?.tipo_clase?.codigo;
    const monto = precioAbonoActual(codigo, abonoSeleccionado?.tipo_clase);

    const fd = new FormData();
    fd.append("sede", String(sedeId));
    fd.append("prestador", String(profesorId));
    fd.append("dia_semana", String(diaSemana));
    fd.append("hora", abonoSeleccionado?.hora);
    fd.append("tipo_clase", abonoSeleccionado?.tipo_clase?.id);
    fd.append("anio", anioActual);
    fd.append("mes", mesActual);
    fd.append("monto", String(monto));
    fd.append("monto_esperado", String(monto));
    fd.append("usuario_id", String(usuarioId));
    fd.append("forzar_admin", "true");

    try {
      await api.post("padel/abonos/reservar/", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast({
        title: "Abono asignado",
        description: `Asignado a ${usuarioSeleccionado?.email || usuarioSeleccionado?.nombre || "usuario"}.`,
        status: "success", duration: 4500,
      });
      confirmDisc.onClose();
      setAbonoSeleccionado(null);
    } catch (e) {
      const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || "No se pudo asignar el abono";
      console.error("[AbonoAdmin] ERROR reservar:", e);
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
    }
  };

  // ---------- UI ----------
  return (
    <PageWrapper>
      <Sidebar
        links={[
          { label: "Dashboard", path: "/admin" },
          { label: "Sedes", path: "/admin/sedes" },
          { label: "Profesores", path: "/admin/profesores" },
          { label: "Usuarios", path: "/admin/usuarios" },
          { label: "Cancelaciones", path: "/admin/cancelaciones" },
          { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
          { label: "Abonos (Asignar)", path: "/admin/abonos" },
        ]}
      />

      <Box flex="1" p={{ base: 4, md: 8 }} bg={card.bg} color={card.color}>
        <HStack justify="space-between" mb={4} align="end">
          <Text fontSize="2xl" fontWeight="bold">Asignar Abono a Usuario</Text>
        </HStack>

        {/* Usuario destino */}
        <Box mb={6} p={4} bg={card.bg} rounded="lg" borderWidth="1px" borderColor={input.border}>
          <Text fontWeight="semibold" mb={3}>Usuario destino</Text>

          <Stack direction={{ base: "column", md: "row" }} spacing={3} align="stretch">
            {/* Buscador como en Usuarios */}
            <InputGroup w={{ base: "100%", md: "380px" }}>
              <InputLeftElement pointerEvents="none">
                <SearchIcon color="gray.400" />
              </InputLeftElement>
              <ChakraInput
                placeholder="Buscar usuario por nombre, email, teléfono…"
                value={busquedaUser}
                onChange={(e) => setBusquedaUser(e.target.value)}
                bg={input.bg}
                color={input.color}
                _placeholder={{ color: "gray.400" }}
                borderRadius="full"
              />
            </InputGroup>

            <HStack spacing={2}>
              <Button
                variant="secondary"
                onClick={() => { setBusquedaUser(""); }}
              >
                Limpiar
              </Button>
              {usuarioSeleccionado && (
                <Button variant="ghost" onClick={() => setUsuarioId("")}>
                  Quitar selección
                </Button>
              )}
            </HStack>
          </Stack>

          {/* Lista elegante de usuario_final */}
          <Box
            mt={4}
            borderWidth="1px"
            borderColor={input.border}
            rounded="md"
            maxH="320px"
            overflowY="auto"
            bg={card.bg}
          >
            <VStack align="stretch" spacing={2} p={2}>
              {usuariosFiltrados.length === 0 && (
                <Text color={muted} px={2} py={3}>No se encontraron usuarios finales.</Text>
              )}
              {usuariosFiltrados.map(u => {
                const seleccionado = String(usuarioId) === String(u.id);
                return (
                  <HStack
                    key={u.id}
                    justify="space-between"
                    align="center"
                    p={3}
                    bg={seleccionado ? hoverBg : card.bg}
                    borderWidth="1px"
                    borderColor={seleccionado ? "blue.400" : input.border}
                    rounded="md"
                    role="button"
                    _hover={{ bg: hoverBg, cursor: "pointer" }}
                    onClick={() => setUsuarioId(String(u.id))}
                  >
                    <Box>
                      <Text fontWeight="semibold">
                        {(`${u.nombre || ""} ${u.apellido || ""}`).trim() || u.email}
                      </Text>
                      <Text fontSize="sm" color={muted}>{u.email}</Text>
                    </Box>
                    <HStack>
                      {seleccionado && <Badge colorScheme="green" variant="solid">Seleccionado</Badge>}
                      {seleccionado && <CheckIcon />}
                    </HStack>
                  </HStack>
                );
              })}
            </VStack>
          </Box>
        </Box>

        {/* Filtros de abono */}
        <VStack align="stretch" spacing={3}>
          <Stack
            direction={{ base: "column", md: "row" }}
            spacing={4}
            align={{ base: "stretch", md: "end" }}
            mb={4}
            w="100%"
          >
            <FormControl flex={1} minW={0}>
              <FormLabel color={muted}>Sede</FormLabel>
              <Select
                value={sedeId}
                placeholder="Seleccioná"
                onChange={(e) => {
                  setSedeId(e.target.value);
                  setProfesorId(""); setDiaSemana(""); setTipoAbono(""); setHoraFiltro("");
                }}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
              >
                {sedes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nombre || s.nombre_publico || `Sede ${s.id}`}
                  </option>
                ))}
              </Select>
            </FormControl>

            <FormControl flex={1} minW={0} isDisabled={!sedeId}>
              <FormLabel color={muted}>Profesor</FormLabel>
              <Select
                value={profesorId}
                placeholder="Seleccioná"
                onChange={(e) => setProfesorId(e.target.value)}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
              >
                {profesores.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre || p.email || `Profe ${p.id}`}
                  </option>
                ))}
              </Select>
            </FormControl>

            <FormControl flex={1} minW={0} isDisabled={!profesorId}>
              <FormLabel color={muted}>Día de la semana</FormLabel>
              <Select
                value={diaSemana}
                placeholder="Seleccioná"
                onChange={(e) => setDiaSemana(e.target.value)}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
              >
                {DIAS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </Select>
            </FormControl>

            <FormControl flex={1} minW={0} isDisabled={!profesorId}>
              <FormLabel color={muted}>Tipo de abono</FormLabel>
              <Select
                value={tipoAbono}
                placeholder="Seleccioná"
                onChange={(e) => setTipoAbono(e.target.value)}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
              >
                {ABONO_OPCIONES.map((op) => (
                  <option key={op.codigo} value={op.codigo}>{op.nombre}</option>
                ))}
              </Select>
            </FormControl>

            <FormControl flex={1} minW={0} isDisabled={diaSemana === ""}>
              <FormLabel color={muted}>Hora (opcional)</FormLabel>
              <Select
                value={horaFiltro}
                onChange={(e) => setHoraFiltro(e.target.value)}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
              >
                <option value="">Todas</option>
                {Array.from({ length: 15 }).map((_, i) => {
                  const h = (8 + i).toString().padStart(2, "0") + ":00:00";
                  return <option key={h} value={h}>{h.slice(0, 5)}</option>;
                })}
              </Select>
            </FormControl>
          </Stack>

          <Divider my={2} />

          {/* Abonos libres */}
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
                    _hover={{ boxShadow: "lg", cursor: usuarioId ? "pointer" : "not-allowed", bg: hoverBg }}
                    onClick={() => handleClickAbono(item)}
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
                      <Button variant="primary" isDisabled={!usuarioId}>
                        Asignar
                      </Button>
                    </HStack>
                  </Box>
                );
              })}
            </VStack>
          </Box>
        </VStack>
      </Box>

      {/* Dialogo de confirmación */}
      <AlertDialog
        isOpen={confirmDisc.isOpen}
        leastDestructiveRef={cancelRef}
        onClose={confirmDisc.onClose}
        isCentered
      >
        <AlertDialogOverlay />
        <AlertDialogContent>
          <AlertDialogHeader fontWeight="bold">Confirmar asignación</AlertDialogHeader>
          <AlertDialogBody>
            {usuarioSeleccionado ? (
              <>
                <Text mb={2}>Vas a asignar el abono a:</Text>
                <Text fontWeight="semibold">
                  {`${usuarioSeleccionado?.nombre || ""} ${usuarioSeleccionado?.apellido || ""}`.trim() || usuarioSeleccionado?.email}
                </Text>
                <Text color={muted}>{usuarioSeleccionado?.email}</Text>
                <Divider my={3} />
              </>
            ) : null}
            <Text>
              {`Día: ${DIAS.find(d => String(d.value) === String(diaSemana))?.label || "-"}`} · {`Hora: ${abonoSeleccionado?.hora?.slice(0,5) || "-"}`}
            </Text>
            <Text>
              {`Tipo: ${abonoSeleccionado?.tipo_clase?.nombre || LABELS[abonoSeleccionado?.tipo_clase?.codigo] || "-"}`}
            </Text>
            <Text mt={2} fontSize="sm" color={muted}>
              * No se solicitará comprobante. Se registrará como asignado por admin.
            </Text>
          </AlertDialogBody>
          <AlertDialogFooter>
            <Button ref={cancelRef} onClick={confirmDisc.onClose} variant="secondary">
              Cancelar
            </Button>
            <Button onClick={confirmarAsignacion} isLoading={enviando} ml={3}>
              Confirmar
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageWrapper>
  );
};

export default ReservarAbonoAdmin;
