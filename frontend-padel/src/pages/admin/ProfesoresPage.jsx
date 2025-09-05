// src/pages/admin/ProfesoresPage.jsx
import React, { useEffect, useState, useContext, useMemo } from "react";
import {
  Box, Heading, Text, VStack, Select, IconButton, Modal, ModalOverlay, ModalContent,
  ModalHeader, ModalCloseButton, ModalBody, ModalFooter, useDisclosure, Flex, Input as ChakraInput,
  Stack, useBreakpointValue, SimpleGrid, Table, Thead, Tbody, Tr, Th, Td, useColorModeValue, ButtonGroup, HStack, Divider
} from "@chakra-ui/react";
import { DeleteIcon, EditIcon } from "@chakra-ui/icons";
import { axiosAuth } from "../../utils/axiosAuth";
import { AuthContext } from "../../auth/AuthContext";
import { toast } from "react-toastify";
import Sidebar from "../../components/layout/Sidebar";
import Button from "../../components/ui/Button";
import PageWrapper from "../../components/layout/PageWrapper";

import {
  useBodyBg, useCardColors, useModalColors, useInputColors, useMutedText
} from "../../components/theme/tokens";

const diasSemana = [
  { value: 0, label: "Lunes" }, { value: 1, label: "Martes" }, { value: 2, label: "Miércoles" },
  { value: 3, label: "Jueves" }, { value: 4, label: "Viernes" }, { value: 5, label: "Sábado" }, { value: 6, label: "Domingo" },
];

const FIELD_PROPS = { height: "40px", fontSize: "16px", width: "100%", minW: 0, maxW: "100%" };
const GRID_TEMPLATE = "1.2fr 1fr 1fr 1fr 48px";

const ProfesoresPage = () => {
  const { accessToken, user } = useContext(AuthContext);

  // UI tokens
  const bg = useBodyBg();
  const card = useCardColors();
  const modalTok = useModalColors();
  const input = useInputColors();
  const mutedText = useMutedText();
  const hoverBg = useColorModeValue("gray.200", "gray.700");
  const isMobile = useBreakpointValue({ base: true, md: false });

  // State
  const [profesores, setProfesores] = useState([]);
  const [sedes, setSedes] = useState([]);
  const [editingId, setEditingId] = useState(null);

  // form
  const [nombre, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [nombrePublico, setNombrePublico] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [especialidad, setEspecialidad] = useState("");
  const [password, setPassword] = useState("");
  const [clienteId, setClienteId] = useState("");

  // disponibilidades
  const [disponibilidades, setDisponibilidades] = useState([]);

  // bloqueos
  const [bloqueos, setBloqueos] = useState([]);
  const [bloqueosPendientes, setBloqueosPendientes] = useState([]);
  const [nuevoBloqueo, setNuevoBloqueo] = useState({ lugar: "", fecha_inicio: "", fecha_fin: "", motivo: "" });
  const bloqueoIncompleto = !nuevoBloqueo.fecha_inicio || !nuevoBloqueo.fecha_fin;

  // efectos / data
  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);
    api.get("turnos/prestadores/").then(r => setProfesores(r.data.results || r.data)).catch(() => toast.error("Error cargando profesores"));
    api.get("turnos/sedes/").then(r => setSedes(r.data.results || r.data)).catch(() => toast.error("Error cargando sedes"));
  }, [accessToken]);

  // modals
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isModalReservadosOpen, onOpen: openModalReservados, onClose: closeModalReservados
  } = useDisclosure();
  const [turnosReservadosAfectados, setTurnosReservadosAfectados] = useState([]);
  const [prestadorIdActivo, setPrestadorIdActivo] = useState(null);
  const [bloqueoIdActual, setBloqueoIdActual] = useState(null);

  // helpers
  const resetForm = () => {
    setEditingId(null);
    setNombre(""); setApellido(""); setNombrePublico("");
    setEmail(""); setTelefono(""); setEspecialidad(""); setPassword(""); setClienteId("");
    setDisponibilidades([]);
    setBloqueos([]); setBloqueosPendientes([]);
    setNuevoBloqueo({ lugar: "", fecha_inicio: "", fecha_fin: "", motivo: "" });
  };

  const openForCreate = () => { resetForm(); onOpen(); };

  const fetchBloqueos = async (profesorId) => {
    const api = axiosAuth(accessToken);
    try {
      const res = await api.get(`turnos/prestadores/${profesorId}/bloqueos/`);
      setBloqueos(res.data.results || res.data);
    } catch { setBloqueos([]); }
  };

  const openForEdit = (p) => {
    setEditingId(p.id);
    setEmail(p.email || ""); setTelefono(p.telefono || "");
    setNombrePublico(p.nombre_publico || ""); setEspecialidad(p.especialidad || "");
    setNombre(p.nombre || ""); setApellido(p.apellido || "");
    setDisponibilidades((p.disponibilidades || []).map(d => ({
      sede: d.lugar, dia: d.dia_semana, hora_inicio: d.hora_inicio, hora_fin: d.hora_fin
    })));
    fetchBloqueos(p.id);
    onOpen();
  };

  // Disponibilidades ops
  const agregarDisponibilidad = () => setDisponibilidades(prev => [...prev, { sede: "", dia: 0, hora_inicio: "08:00", hora_fin: "10:00" }]);
  const eliminarDisponibilidad = (idx) => setDisponibilidades(prev => prev.filter((_, i) => i !== idx));
  const actualizarDisponibilidad = (idx, field, value) => setDisponibilidades(prev => prev.map((d, i) => i === idx ? { ...d, [field]: value } : d));

  // Guardado
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nombre.trim()) return toast.error("El nombre es obligatorio.");
    if (!apellido.trim()) return toast.error("El apellido es obligatorio.");
    if (!nombrePublico.trim()) return toast.error("El nombre público es obligatorio.");
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return toast.error("Ingresá un email válido.");
    if (!editingId && password.length < 6) return toast.error("La contraseña debe tener al menos 6 caracteres.");
    if (disponibilidades.some(d => !d.sede)) return toast.error("Completá la sede en cada disponibilidad.");
    if (user.tipo_usuario === "super_admin" && (!clienteId || isNaN(clienteId))) return toast.error("ID de cliente inválido.");

    const payload = {
      nombre, apellido, email, telefono, especialidad, nombre_publico: nombrePublico, activo: true,
      ...(password && { password }),
      ...(user.tipo_usuario === "super_admin" && { cliente: parseInt(clienteId) }),
      disponibilidades: disponibilidades.map(d => ({ lugar: d.sede, dia_semana: d.dia, hora_inicio: d.hora_inicio, hora_fin: d.hora_fin }))
    };
    const api = axiosAuth(accessToken);
    try {
      let prestadorId;
      if (editingId) {
        await api.put(`turnos/prestadores/${editingId}/`, payload);
        toast.success("Profesor actualizado");
        prestadorId = editingId;
      } else {
        const res = await api.post("turnos/prestadores/", payload);
        toast.success("Profesor creado");
        prestadorId = res.data.id;
      }
      setPrestadorIdActivo(prestadorId);

      // bloqueos pendientes
      for (const b of bloqueosPendientes) {
        const resB = await api.post(`turnos/prestadores/${prestadorId}/bloqueos/`, { ...b, activo: true, lugar: b.lugar || null });
        const { id, turnos_reservados_afectados = [] } = resB.data;
        if (turnos_reservados_afectados.length > 0) {
          setBloqueoIdActual(id);
          setTurnosReservadosAfectados(turnos_reservados_afectados);
          openModalReservados();
        }
      }
      setBloqueosPendientes([]);

      onClose(); resetForm();
      const res = await api.get("turnos/prestadores/");
      setProfesores(res.data.results || res.data);
    } catch (err) {
      console.error("[PROFESORES] Error guardando:", err.response?.data || err.message);
      toast.error("Error al guardar el prestador");
    }
  };

  const handleDelete = async (id, nombre) => {
    if (!window.confirm(`¿Eliminar al profesor "${nombre}"?`)) return;
    const api = axiosAuth(accessToken);
    try {
      await api.delete(`turnos/prestadores/${id}/`);
      toast.success("Profesor eliminado");
      const res = await api.get("turnos/prestadores/");
      setProfesores(res.data.results || res.data);
      if (editingId === id) { onClose(); resetForm(); }
    } catch { toast.error("Error al eliminar profesor"); }
  };

  // Bloqueos UI ops
  const handleAgregarBloqueo = () => {
    if (bloqueoIncompleto) return toast.error("Completá todas las fechas");
    if (nuevoBloqueo.fecha_fin < nuevoBloqueo.fecha_inicio) return toast.error("La fecha fin no puede ser anterior a la de inicio");
    setBloqueosPendientes(prev => [...prev, { ...nuevoBloqueo, activo: true }]);
    setNuevoBloqueo({ lugar: "", fecha_inicio: "", fecha_fin: "", motivo: "" });
    toast.info("Bloqueo agregado (pendiente de guardar)");
  };

  const handleEliminarBloqueo = async (bloqueoId) => {
    if (!editingId) return;
    const api = axiosAuth(accessToken);
    try {
      await api.delete(`turnos/prestadores/${editingId}/bloqueos/`, { data: { id: bloqueoId } });
      setBloqueos(prev => prev.filter(b => b.id !== bloqueoId));
      toast.success("Bloqueo eliminado");
      fetchBloqueos(editingId);
    } catch { toast.error("No se pudo eliminar"); }
  };

  const handleForzarCancelacionReservados = async () => {
    const api = axiosAuth(accessToken);
    try {
      if (!prestadorIdActivo) return toast.error("No se pudo determinar el profesor.");
      await api.post(`turnos/prestadores/${prestadorIdActivo}/forzar_cancelacion_reservados/`, { bloqueo_id: bloqueoIdActual });
      toast.success("Turnos reservados cancelados.");
      closeModalReservados();
      fetchBloqueos(prestadorIdActivo);
      setPrestadorIdActivo(null);
    } catch { toast.error("Error al cancelar turnos reservados"); }
  };

  // ---------- Subcomponentes compactos ----------
  const DisponibilidadRowDesktop = ({ d, i }) => (
    <GridRow template={GRID_TEMPLATE}>
      <SelectBase value={d.sede || ""} onChange={(e) => actualizarDisponibilidad(i, "sede", e.target.value)} placeholder="Seleccioná sede">
        {sedes.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
      </SelectBase>
      <SelectBase value={d.dia} onChange={(e) => actualizarDisponibilidad(i, "dia", parseInt(e.target.value))}>
        {diasSemana.map(dia => <option key={dia.value} value={dia.value}>{dia.label}</option>)}
      </SelectBase>
      <TimeBase value={d.hora_inicio} onChange={(e) => actualizarDisponibilidad(i, "hora_inicio", e.target.value)} />
      <TimeBase value={d.hora_fin} onChange={(e) => actualizarDisponibilidad(i, "hora_fin", e.target.value)} />
      <IconButton aria-label="Eliminar disponibilidad" icon={<DeleteIcon />} colorScheme="red" size="md" onClick={() => eliminarDisponibilidad(i)} />
    </GridRow>
  );

  const DisponibilidadCardMobile = ({ d, i }) => (
    <Box bg={card.bg} color={card.color} rounded="md" p={2} mb={1} borderWidth={1} borderColor={input.borderColor}>
      <VStack spacing={2} align="stretch">
        <FieldLabel>Sede</FieldLabel>
        <SelectBase value={d.sede || ""} onChange={(e) => actualizarDisponibilidad(i, "sede", e.target.value)} placeholder="Seleccioná sede">
          {sedes.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
        </SelectBase>

        <FieldLabel>Día</FieldLabel>
        <SelectBase value={d.dia} onChange={(e) => actualizarDisponibilidad(i, "dia", parseInt(e.target.value))}>
          {diasSemana.map(dia => <option key={dia.value} value={dia.value}>{dia.label}</option>)}
        </SelectBase>

        <FieldLabel>Hora inicio</FieldLabel>
        <TimeBase value={d.hora_inicio} onChange={(e) => actualizarDisponibilidad(i, "hora_inicio", e.target.value)} />

        <FieldLabel>Hora fin</FieldLabel>
        <TimeBase value={d.hora_fin} onChange={(e) => actualizarDisponibilidad(i, "hora_fin", e.target.value)} />

        <Button variant="secondary" leftIcon={<DeleteIcon />} onClick={() => eliminarDisponibilidad(i)} w="100%">
          Eliminar
        </Button>
      </VStack>
    </Box>
  );

  const BloqueoItem = ({ b, idx }) => (
    <Flex key={b.id ?? `pend-${idx}`} align="center" justify="space-between" bg={card.bg} color={card.color}
      rounded="md" px={3} py={2} borderWidth={1} borderColor={input.borderColor} wrap="wrap">
      <Box>
        <Text fontSize="sm">
          <b>{b.lugar_nombre || "Todas las sedes"}</b> — {b.fecha_inicio} a {b.fecha_fin}
          {b.motivo && <span style={{ color: "#aaa" }}> — {b.motivo}</span>}
          {b.pendiente && <span style={{ color: "#f0a" }}> (pendiente)</span>}
        </Text>
      </Box>
      <IconButton
        icon={<DeleteIcon />} aria-label="Eliminar bloqueo" colorScheme="red" variant="ghost" size="sm"
        onClick={() => b.pendiente ? setBloqueosPendientes(prev => prev.filter((_, j) => j !== idx)) : handleEliminarBloqueo(b.id)}
      />
    </Flex>
  );

  // ---------- Presentación ----------
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

      <Box flex="1" p={{ base: 4, md: 8 }} bg={bg} color={card.color}>
        <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "center" }} mb={4} spacing={3}>
          <Heading size="md">Administrar Profesores</Heading>
          <Button onClick={openForCreate} size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
            Agregar Profesor
          </Button>
        </Stack>

        {profesores.length === 0 ? (
          <Text textAlign="center" opacity={0.7} fontStyle="italic">No hay profesores cargados.</Text>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
            {profesores.map((p) => (
              <Flex key={p.id} bg={card.bg} color={card.color} p={4} rounded="md" boxShadow="md"
                    role="group" _hover={{ bg: hoverBg, cursor: "pointer" }}
                    direction={{ base: "column", md: "row" }} align={{ base: "stretch", md: "center" }} justify="space-between"
                    onClick={(e) => { if (e.target.closest("button")) return; openForEdit(p); }}>
                <Box flex="1" mr={{ md: 4 }}>
                  <Text fontWeight="bold" noOfLines={{ base: 1, md: undefined }}>
                    {p.nombre_publico || "Sin nombre público"}
                  </Text>
                  <Text fontSize="sm" color={mutedText} noOfLines={{ base: 1, md: undefined }}>
                    {p.email || "Sin email"}
                  </Text>
                </Box>
                <ButtonGroup mt={{ base: 3, md: 0 }} size="sm" spacing="2" w={{ base: "100%", md: "auto" }}>
                  <IconButton icon={<EditIcon />} aria-label="Editar" onClick={() => openForEdit(p)} />
                  <IconButton icon={<DeleteIcon />} aria-label="Eliminar" onClick={() => handleDelete(p.id, p.nombre)} colorScheme="red" />
                </ButtonGroup>
              </Flex>
            ))}
          </SimpleGrid>
        )}

        {/* MODAL FORM */}
        <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm(); }} isCentered size={isMobile ? "full" : "4xl"}>
          <ModalOverlay />
          <ModalContent bg={modalTok.bg} color={modalTok.color} maxW={isMobile ? "100vw" : "900px"} mx={isMobile ? 1 : "auto"}  sx={{
                'input, select, textarea': {
                  fontSize: { base: '16px', md: 'inherit' }
                }
              }}>
            <ModalHeader>{editingId ? "Editar Profesor" : "Nuevo Profesor"}</ModalHeader>
            <ModalCloseButton />
            <ModalBody maxH="70vh" overflowY="auto">
              <form id="prof-form" onSubmit={handleSubmit}>
              <VStack spacing={4} align="stretch">
                <ChakraInput
                  placeholder="Nombre"
                  value={nombre}
                  onChange={e => setNombre(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                <ChakraInput
                  placeholder="Apellido"
                  value={apellido}
                  onChange={e => setApellido(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                <ChakraInput
                  placeholder="Email"
                  type="email"
                  inputMode="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                <ChakraInput
                  placeholder="Teléfono"
                  inputMode="tel"
                  value={telefono}
                  onChange={e => setTelefono(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                <ChakraInput
                  placeholder="Especialidad"
                  value={especialidad}
                  onChange={e => setEspecialidad(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                <ChakraInput
                  placeholder="Nombre Público"
                  value={nombrePublico}
                  onChange={e => setNombrePublico(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                <ChakraInput
                  placeholder="Contraseña (dejar vacío para no cambiar)"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  size="md"
                  fontSize={{ base: "16px", md: "inherit" }}
                />
                {user.tipo_usuario === "super_admin" && (
                  <ChakraInput
                    placeholder="ID del Cliente"
                    inputMode="numeric"
                    value={clienteId}
                    onChange={e => setClienteId(e.target.value)}
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                  />
                )}
              </VStack>


                <Heading size="xs" mt={6} mb={3}>Disponibilidades</Heading>
                <Box bg={card.bg} color={card.color} p={{ base: 2, md: 4 }} rounded="md">
                  {!isMobile && (
                    <GridRow template={GRID_TEMPLATE} mb={2} fontWeight="semibold" fontSize="sm" alignItems="center">
                      <Box>Sede</Box><Box>Día</Box><Box>Hora inicio</Box><Box>Hora fin</Box><Box />
                    </GridRow>
                  )}

                  <VStack spacing={3} align="stretch">
                    {disponibilidades.map((d, i) =>
                      isMobile
                        ? <DisponibilidadCardMobile key={i} d={d} i={i} />
                        : <DisponibilidadRowDesktop key={i} d={d} i={i} />
                    )}
                  </VStack>

                  <Flex mt={3}>
                    <Button variant="secondary" onClick={agregarDisponibilidad} size="md" type="button" w="100%">
                      Agregar Disponibilidad
                    </Button>
                  </Flex>
                </Box>

                {editingId ? (
                  <>
                    <Heading size="xs" mt={6} mb={3}>Bloqueos de calendario</Heading>
                    <Box bg={card.bg} color={card.color} p={{ base: 2, md: 4 }} rounded="md" mb={3}>
                      <VStack spacing={3} align="stretch">
                        {bloqueos.length === 0 && bloqueosPendientes.length === 0 && (
                          <Text color={mutedText} fontSize="sm" textAlign="center">No hay bloqueos para este profesor.</Text>
                        )}
                        {[...bloqueos, ...bloqueosPendientes.map((b, i) => ({ ...b, id: `pend-${i}`, pendiente: true }))].map((b, idx) =>
                          <BloqueoItem key={b.id ?? `pend-${idx}`} b={b} idx={idx} />
                        )}
                      </VStack>

                      <Stack direction={{ base: "column", md: "row" }} mt={4} spacing={2}>
                        <SelectBase flex={1} placeholder="Todas las sedes"
                          value={nuevoBloqueo.lugar} onChange={e => setNuevoBloqueo(n => ({ ...n, lugar: e.target.value }))}>
                          <option value="">Todas las sedes</option>
                          {sedes.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                        </SelectBase>
                        <TimeDateBase type="date" value={nuevoBloqueo.fecha_inicio} onChange={e => setNuevoBloqueo(n => ({ ...n, fecha_inicio: e.target.value }))} />
                        <TimeDateBase type="date" value={nuevoBloqueo.fecha_fin} onChange={e => setNuevoBloqueo(n => ({ ...n, fecha_fin: e.target.value }))} />
                        <TimeDateBase placeholder="Motivo (opcional)" value={nuevoBloqueo.motivo} onChange={e => setNuevoBloqueo(n => ({ ...n, motivo: e.target.value }))} />
                        <Button onClick={handleAgregarBloqueo} variant="secondary" size="md" minW={{ base: "100%", md: "110px" }} isDisabled={bloqueoIncompleto}>
                          Agregar Bloqueo
                        </Button>
                      </Stack>
                    </Box>
                  </>
                ) : (
                  <Text color={mutedText} fontSize="sm" mt={6}>Guardá el profesor antes de cargar bloqueos de calendario.</Text>
                )}
              </form>
            </ModalBody>
            <ModalFooter>
              <Stack direction={{ base: "column", md: "row" }} w="100%">
                <Button type="submit" form="prof-form" size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
                  {editingId ? "Actualizar" : "Crear"}
                </Button>
                <Button variant="secondary" onClick={() => { onClose(); resetForm(); }} size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
                  Cancelar
                </Button>
              </Stack>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* MODAL TURNOS AFECTADOS */}
        <Modal isOpen={isModalReservadosOpen} onClose={closeModalReservados} isCentered size={isMobile ? "full" : "xl"} scrollBehavior="inside">
          <ModalOverlay />
          <ModalContent bg={modalTok.bg} color={modalTok.color} maxW="90vw">
            <ModalHeader>⚠️ Turnos Reservados Afectados ({turnosReservadosAfectados.length})</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Text mb={4}>
                El bloqueo afectó <b>{turnosReservadosAfectados.length}</b> turnos. 📲 Contactá a los usuarios si vas a forzar la cancelación.
              </Text>
              <Box maxH="400px" overflowY="auto" borderWidth={1} borderColor={input.borderColor} rounded="md">
                <Table variant="unstyled" size="sm">
                  <Thead>
                    <Tr><Th>🆔</Th><Th>📅 Fecha</Th><Th>⏰ Hora</Th><Th>👤 Usuario</Th><Th>📧 Email</Th></Tr>
                  </Thead>
                  <Tbody>
                    {turnosReservadosAfectados.map(t => (
                      <Tr key={t.id} _hover={{ bg: hoverBg }}>
                        <Td>{t.id}</Td><Td>{t.fecha}</Td><Td>{t.hora}</Td><Td>{t.usuario}</Td><Td>{t.email}</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </ModalBody>
            <ModalFooter>
              <HStack spacing={2} wrap="wrap">
                <Button variant="secondary" onClick={() => {
                  // export simple .txt
                  const lines = [
                    `📝 Reporte de Turnos Reservados Afectados`,
                    `🆔 Bloqueo ID: ${bloqueoIdActual}`,
                    `👨‍🏫 Profesor id=${editingId}`,
                    `📊 Total afectados: ${turnosReservadosAfectados.length}`,
                    ``,
                    ...turnosReservadosAfectados.map(t => `🆔 ${t.id} │ ${t.fecha} │ ${t.hora} │ ${t.usuario} │ ${t.email}`)
                  ].join("\n");
                  const blob = new Blob([lines], { type: "text/plain;charset=utf-8" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url; a.download = `bloqueo_${bloqueoIdActual}_turnos.txt`; a.click();
                  URL.revokeObjectURL(url);
                }}>
                  📥 Descargar
                </Button>
                <Button colorScheme="red" onClick={handleForzarCancelacionReservados}>❌ Forzar cancelación</Button>
                <Button variant="ghost" onClick={closeModalReservados}>Cerrar</Button>
              </HStack>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </Box>
    </PageWrapper>
  );
};

/* --------- Helpers UI (compactos) --------- */
const GridRow = ({ template, children, ...rest }) => (
  <Box display="grid" gridTemplateColumns={template} gap={3} {...rest}>{children}</Box>
);

const FieldLabel = ({ children }) => (
  <Text fontSize="xs" opacity={0.8} mb={1}>{children}</Text>
);

const SelectBase = (props) => {
  const input = useInputColors();
  return <Select bg={input.bg} color={input.color} {...FIELD_PROPS} {...props} />;
};

const TimeBase = (props) => {
  const input = useInputColors();
  return <ChakraInput type="time" bg={input.bg} color={input.color} {...FIELD_PROPS} {...props} />;
};

const TimeDateBase = (props) => {
  const input = useInputColors();
  return <ChakraInput bg={input.bg} color={input.color} {...FIELD_PROPS} {...props} />;
};

export default ProfesoresPage;
