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

// Función para verificar solapamiento de disponibilidades
const verificarSolapamientoDisponibilidades = (disponibilidades) => {
  for (let i = 0; i < disponibilidades.length; i++) {
    for (let j = i + 1; j < disponibilidades.length; j++) {
      const disp1 = disponibilidades[i];
      const disp2 = disponibilidades[j];
      
      // Solo verificar si son del mismo lugar y día
      if (disp1.sede === disp2.sede && disp1.dia === disp2.dia) {
        // Convertir horas a minutos para comparar
        const horaInicio1 = tiempoAMinutos(disp1.hora_inicio);
        const horaFin1 = tiempoAMinutos(disp1.hora_fin);
        const horaInicio2 = tiempoAMinutos(disp2.hora_inicio);
        const horaFin2 = tiempoAMinutos(disp2.hora_fin);
        
        // Verificar solapamiento
        if (horaInicio1 < horaFin2 && horaInicio2 < horaFin1) {
          const diaNombre = diasSemana.find(d => d.value === disp1.dia)?.label || "Día";
          return `❌ No se puede guardar: El prestador no puede tener turnos solapados en ${diaNombre}. Los horarios ${disp1.hora_inicio}-${disp1.hora_fin} y ${disp2.hora_inicio}-${disp2.hora_fin} se superponen.`;
        }
      }
    }
  }
  return null;
};

// Función helper para convertir tiempo a minutos
const tiempoAMinutos = (tiempo) => {
  const [hora, minutos] = tiempo.split(':').map(Number);
  return hora * 60 + minutos;
};

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

  // nuevo modal de confirmación de borrado
  const confirmarEliminar = useDisclosure();
  const [prestadorAEliminar, setPrestadorAEliminar] = useState(null);
  const [eliminando, setEliminando] = useState(false);

  const [turnosReservadosAfectados, setTurnosReservadosAfectados] = useState([]);
  const [prestadorIdActivo, setPrestadorIdActivo] = useState(null);

  // helpers
  const resetForm = () => {
    setEditingId(null);
    setNombre(""); setApellido(""); setNombrePublico("");
    setEmail(""); setTelefono(""); setEspecialidad(""); setPassword(""); setClienteId("");
    setDisponibilidades([]);
  };

  const openForCreate = () => { resetForm(); onOpen(); };

  const openForEdit = (p) => {
    setEditingId(p.id);
    setEmail(p.email || ""); setTelefono(p.telefono || "");
    setNombrePublico(p.nombre_publico || ""); setEspecialidad(p.especialidad || "");
    setNombre(p.nombre || ""); setApellido(p.apellido || "");
    setDisponibilidades((p.disponibilidades || []).map(d => ({
      sede: d.lugar, dia: d.dia_semana, hora_inicio: d.hora_inicio, hora_fin: d.hora_fin
    })));
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
    
    // Validar solapamiento de disponibilidades
    const disponibilidadesValidas = disponibilidades.filter(d => d.sede && d.sede !== "");
    const haySolapamiento = verificarSolapamientoDisponibilidades(disponibilidadesValidas);
    if (haySolapamiento) return toast.error(haySolapamiento);

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

      onClose(); resetForm();
      const res = await api.get("turnos/prestadores/");
      setProfesores(res.data.results || res.data);
    } catch (err) {
      console.error("[PROFESORES] Error guardando:", err.response?.data || err.message);
      const errorData = err.response?.data;
      
      // Manejar errores específicos de solapamiento del backend
      if (errorData && typeof errorData === 'object') {
        // Caso 1: Array directo de errores (formato actual del backend)
        if (Array.isArray(errorData)) {
          toast.error(errorData[0]);
          return;
        }
        // Caso 2: non_field_errors
        if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
          toast.error(errorData.non_field_errors[0]);
          return;
        }
        // Caso 3: Buscar errores de disponibilidades
        for (const [field, errors] of Object.entries(errorData)) {
          if (field.includes('disponibilidad') && Array.isArray(errors)) {
            toast.error(errors[0]);
            return;
          }
        }
      }
      
      toast.error("Error al guardar el prestador");
    }
  };

  // ✅ NUEVO flujo: pedir confirmación con Modal y luego eliminar
  const pedirEliminarPrestador = (prestador) => {
    setPrestadorAEliminar(prestador);
    confirmarEliminar.onOpen();
  };

  const eliminarPrestadorConfirm = async () => {
    if (!prestadorAEliminar) return;
    const api = axiosAuth(accessToken);
    setEliminando(true);
    try {
      await api.delete(`turnos/prestadores/${prestadorAEliminar.id}/?force=true`); // fuerza borrado de turnos
      toast.success("Profesor eliminado con sus turnos");
      const res = await api.get("turnos/prestadores/");
      setProfesores(res.data.results || res.data);
      if (editingId === prestadorAEliminar.id) { onClose(); resetForm(); }
      confirmarEliminar.onClose();
      setPrestadorAEliminar(null);
    } catch (err) {
      const data = err.response?.data;
      const msg = typeof data === "string" ? data : (data?.detail || "Error al eliminar profesor");
      const s = data?.stats;
      toast.error(s ? `${msg} (total=${s.turnos_total}, futuros=${s.turnos_futuros}, reservados=${s.turnos_reservados}, abono=${s.turnos_con_abono})` : msg);
      console.error("[DELETE prestador] fallo:", data || err.message);
    } finally {
      setEliminando(false);
    }
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

  // ---------- Presentación ----------
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
                  <IconButton icon={<DeleteIcon />} aria-label="Eliminar" onClick={() => pedirEliminarPrestador(p)} colorScheme="red" />
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
                        ? <DisponibilidadCardMobile key={`mobile-${i}-${d.sede}-${d.dia}-${d.hora_inicio}-${d.hora_fin}`} d={d} i={i} />
                        : <DisponibilidadRowDesktop key={`desktop-${i}-${d.sede}-${d.dia}-${d.hora_inicio}-${d.hora_fin}`} d={d} i={i} />
                    )}
                  </VStack>

                  <Flex mt={3}>
                    <Button variant="secondary" onClick={agregarDisponibilidad} size="md" type="button" w="100%">
                      Agregar Disponibilidad
                    </Button>
                  </Flex>
                </Box>
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

        {/* MODAL: Confirmar eliminación de profesor */}
        <Modal
          isOpen={confirmarEliminar.isOpen}
          onClose={() => { setPrestadorAEliminar(null); confirmarEliminar.onClose(); }}
          isCentered
          size="lg"
        >
          <ModalOverlay />
          <ModalContent bg={modalTok.bg} color={modalTok.color}>
            <ModalHeader>Eliminar profesor</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              {prestadorAEliminar && (
                <VStack align="stretch" spacing={3}>
                  <Text>
                    Estás por eliminar al profesor{" "}
                    <b>
                      {prestadorAEliminar.nombre_publico ||
                        `${prestadorAEliminar.nombre || ""} ${prestadorAEliminar.apellido || ""}`.trim() ||
                        `#${prestadorAEliminar.id}`}
                    </b>.
                  </Text>
                  {prestadorAEliminar.email && <Text><b>Email:</b> {prestadorAEliminar.email}</Text>}
                  <Text color="red.400" fontWeight="bold">
                    CUIDADO: se eliminarán <u>todos sus turnos asociados</u> (incluyendo futuros, reservados y los con abono).
                  </Text>
                  <Text fontSize="sm" opacity={0.8}>
                    Esta acción es irreversible.
                  </Text>
                </VStack>
              )}
            </ModalBody>
            <ModalFooter>
              <HStack>
                <Button
                  variant="secondary"
                  onClick={() => { setPrestadorAEliminar(null); confirmarEliminar.onClose(); }}
                  isDisabled={eliminando}
                >
                  Cancelar
                </Button>
                <Button
                  colorScheme="red"
                  onClick={eliminarPrestadorConfirm}
                  isLoading={eliminando}
                >
                  Eliminar definitivamente
                </Button>
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