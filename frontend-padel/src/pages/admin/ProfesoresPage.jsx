// src/pages/admin/ProfesoresPage.jsx

import React, { useEffect, useState, useContext } from "react";
import { Table, Thead, Tbody, Tr, Th, Td, useColorModeValue } from "@chakra-ui/react";


import {
  useBodyBg,
  useCardColors,
  useModalColors,
  useInputColors,
  useMutedText
} from "../../components/theme/tokens";
import {
  Box,
  Grid,
  Heading,
  Text,
  VStack,
  Select,
  IconButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Flex,
  Input as ChakraInput,
  Stack,
  useBreakpointValue,
} from "@chakra-ui/react";
import { DeleteIcon, EditIcon } from "@chakra-ui/icons";
import { axiosAuth } from "../../utils/axiosAuth";
import { AuthContext } from "../../auth/AuthContext";
import { toast } from "react-toastify";

import Sidebar from "../../components/layout/Sidebar";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import PageWrapper from "../../components/layout/PageWrapper";

const diasSemana = [
  { value: 0, label: "Lunes" },
  { value: 1, label: "Martes" },
  { value: 2, label: "Miércoles" },
  { value: 3, label: "Jueves" },
  { value: 4, label: "Viernes" },
  { value: 5, label: "Sábado" },
  { value: 6, label: "Domingo" },
];

const FIELD_PROPS = {
  height: "40px",
  fontSize: "16px",
  bg: "gray.700",
  color: "white",
  border: "1px solid",
  borderColor: "gray.600",
  _focus: { borderColor: "blue.400" },
  width: "100%",
  minW: 0,
  maxW: "100%",
};

const GRID_TEMPLATE = "1.2fr 1fr 1fr 1fr 48px";

const ProfesoresPage = () => {
  const { accessToken, logout, user } = useContext(AuthContext);

  const [profesores, setProfesores] = useState([]);
  const [sedes, setSedes] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [especialidad, setEspecialidad] = useState("");
  const [disponibilidades, setDisponibilidades] = useState([]);



  const modalBg = useColorModeValue("white", "gray.900");
  const modalColor = useColorModeValue("gray.800", "white");
  const borderColor = useColorModeValue("gray.300", "gray.700");
  
  const bg = useBodyBg();
  const card = useCardColors();
  const modal = useModalColors();
  const input = useInputColors();
  const mutedText = useMutedText();
  


  // ---------- Bloqueos ----------
  const [bloqueos, setBloqueos] = useState([]);
  const [nuevoBloqueo, setNuevoBloqueo] = useState({
    lugar: "",
    fecha_inicio: "",
    fecha_fin: "",
    motivo: ""
  });
  const [turnosReservadosAfectados, setTurnosReservadosAfectados] = useState([]);
  const [bloqueoIdActual, setBloqueoIdActual] = useState(null);
  const {
    isOpen: isModalReservadosOpen,
    onOpen: openModalReservados,
    onClose: closeModalReservados,
  } = useDisclosure();


  const isMobile = useBreakpointValue({ base: true, md: false });

  const { isOpen, onOpen, onClose } = useDisclosure();

  const resetForm = () => {
    setEditingId(null);
    setNombre("");
    setEmail("");
    setTelefono("");
    setEspecialidad("");
    setDisponibilidades([]);
    setBloqueos([]);
    setNuevoBloqueo({
      lugar: "",
      fecha_inicio: "",
      fecha_fin: "",
      motivo: ""
    });
  };

  const openForCreate = () => {
    resetForm();
    onOpen();
  };

  const openForEdit = (profesor) => {
    setEditingId(profesor.id);
    setNombre(profesor.nombre || "");
    setEmail(profesor.email || "");
    setTelefono(profesor.telefono || "");
    setEspecialidad(profesor.especialidad || "");
    setDisponibilidades(
      profesor.disponibilidades?.map(d => ({
        sede: d.lugar,
        dia: d.dia_semana,
        hora_inicio: d.hora_inicio,
        hora_fin: d.hora_fin
      })) || []
    );
    fetchBloqueos(profesor.id);
    onOpen();
  };

  // ---------- Bloqueos: Backend integration ----------
  const fetchBloqueos = async (profesorId) => {
    const apiInstance = axiosAuth(accessToken);
    try {
      const res = await apiInstance.get(`turnos/prestadores/${profesorId}/bloqueos/`);
      setBloqueos(res.data.results || res.data);
    } catch {
      setBloqueos([]);
    }
  };
  const descargarListadoTurnos = () => {
    // Buscamos el bloqueo recién creado en el array de bloqueos
    const bloqueosList = bloqueos; // el state que guardás en fetchBloqueos
    const bloqueoInfo = bloqueosList.find(b => b.id === bloqueoIdActual) || {};
  
    const headerLines = [
      `📝 Reporte de Turnos Reservados Afectados`,
      `🆔 Bloqueo ID: ${bloqueoIdActual}`,
      `👨‍🏫 Profesor: ${user?.nombre || "–"} (id=${editingId})`,
      `📅 Rango: ${bloqueoInfo.fecha_inicio} → ${bloqueoInfo.fecha_fin}`,
      `📊 Total afectados: ${turnosReservadosAfectados.length}`,
      ``,
      `📲 Por favor, contactá a cada usuario si decidís cancelar su turno.`,
      ``,
    ];
  
    const bodyLines = turnosReservadosAfectados.map(t =>
      `🆔 ${t.id} │ 📅 ${t.fecha} │ ⏰ ${t.hora} │ 👤 ${t.usuario} │ 📧 ${t.email}`
    );
  
    const contenido = [...headerLines, ...bodyLines].join("\n");
    const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href    = url;
    link.download = `bloqueo_${bloqueoIdActual}_turnos.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
  
  
  const handleForzarCancelacionReservados = async () => {
    const apiInstance = axiosAuth(accessToken);
    try {
      await apiInstance.post(
        `turnos/prestadores/${editingId}/forzar_cancelacion_reservados/`,
        { bloqueo_id: bloqueoIdActual }
      );
      toast.success("Turnos reservados cancelados.");
      closeModalReservados();
      fetchBloqueos(editingId);
    } catch {
      toast.error("Error al cancelar turnos reservados");
    }
  };
  
  const handleAgregarBloqueo = async () => {
    if (!editingId || !nuevoBloqueo.fecha_inicio || !nuevoBloqueo.fecha_fin) {
      toast.error("Completá todas las fechas");
      return;
    }
    if (nuevoBloqueo.fecha_fin < nuevoBloqueo.fecha_inicio) {
      toast.error("La fecha fin no puede ser anterior a la de inicio");
      return;
    }
  
    const apiInstance = axiosAuth(accessToken);
    try {
      const body = {
        lugar: nuevoBloqueo.lugar || null,
        fecha_inicio: nuevoBloqueo.fecha_inicio,
        fecha_fin: nuevoBloqueo.fecha_fin,
        motivo: nuevoBloqueo.motivo,
        activo: true,
      };
      const res = await apiInstance.post(
        `turnos/prestadores/${editingId}/bloqueos/`,
        body
      );
      console.log("handleAgregarBloqueo ► res.data:", res.data);
  
      const { turnos_reservados_afectados = [], id: bloqueoId } = res.data;
      setBloqueoIdActual(bloqueoId);
      setTurnosReservadosAfectados(turnos_reservados_afectados);
  
      if (turnos_reservados_afectados.length > 0) {
        toast.warning(
          `Bloqueo creado. ${turnos_reservados_afectados.length} turnos reservados requieren tu decisión.`,
          { autoClose: false }
        );
        openModalReservados();
      } else {
        toast.success("Bloqueo creado con éxito. No hay turnos reservados afectados.");
      }
  
      setNuevoBloqueo({ lugar: "", fecha_inicio: "", fecha_fin: "", motivo: "" });
      fetchBloqueos(editingId);
    } catch (err) {
      console.error(err);
      toast.error("Error al crear bloqueo");
    }
  };
  const handleEliminarBloqueo = async (bloqueoId) => {
    if (!editingId) return;
    const api = axiosAuth(accessToken);
    try {
      await api.delete(
        `turnos/prestadores/${editingId}/bloqueos/`,
        { data: { id: bloqueoId } }
      );
      // 1) Eliminamos localmente para feedback inmediato
      setBloqueos(prev => prev.filter(b => b.id !== bloqueoId));
      toast.success("Bloqueo eliminado");
      // 2) Re-fetch para asegurarnos de reflejar el estado real
      fetchBloqueos(editingId);
    } catch (err) {
      console.error(err);
      toast.error("No se pudo eliminar");
    }
  };
  
  // ---------- Disponibilidades ----------
  const agregarDisponibilidad = () => {
    setDisponibilidades([
      ...disponibilidades,
      { sede: "", dia: 0, hora_inicio: "08:00", hora_fin: "10:00" }
    ]);
  };

  const eliminarDisponibilidad = (idx) => {
    setDisponibilidades(disponibilidades.filter((_, i) => i !== idx));
  };

  const actualizarDisponibilidad = (idx, field, value) => {
    setDisponibilidades(prev =>
      prev.map((d, i) => i === idx ? { ...d, [field]: value } : d)
    );
  };

  // ---------- Profesores y sedes ----------

  useEffect(() => {
    if (!accessToken) return;
    const apiInstance = axiosAuth(accessToken);

    apiInstance.get("turnos/prestadores/")
      .then(res => setProfesores(res.data.results || res.data))
      .catch(() => toast.error("Error cargando profesores"));

    apiInstance.get("turnos/sedes/")
      .then(res => setSedes(res.data.results || res.data))
      .catch(() => toast.error("Error cargando sedes"));
  }, [accessToken]);

  // ---------- Submit ----------
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nombre.trim()) {
      toast.error("El nombre es obligatorio");
      return;
    }
    // Validación de email elegante
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.error("Ingresá un email válido.");
      return;
    }
    // Validación de disponibilidades: todas deben tener sede
    if (disponibilidades.some(d => !d.sede)) {
      toast.error("Completá la sede en cada disponibilidad.");
      return;
    }
    if (user.tipo_usuario === "super_admin") {
      data.cliente = prompt("ID del cliente a asignar al profesor:");
    }

    const apiInstance = axiosAuth(accessToken);
    const data = {
      nombre,
      email,
      telefono,
      especialidad,
      activo: true,
      disponibilidades: disponibilidades.map(d => ({
        lugar: d.sede,
        dia_semana: d.dia,
        hora_inicio: d.hora_inicio,
        hora_fin: d.hora_fin
      })),
    };

    try {
      if (editingId) {
        await apiInstance.put(`turnos/prestadores/${editingId}/`, data);
        toast.success("Profesor actualizado");
      } else {
        await apiInstance.post("turnos/prestadores/", data);
        toast.success("Profesor creado");
      }
      onClose();
      resetForm();
      apiInstance.get("turnos/prestadores/")
        .then(res => setProfesores(res.data.results || res.data));
    } catch {
      toast.error("Error al guardar profesor");
    }
  };

  const handleDelete = async (id, nombre) => {
    if (!window.confirm(`¿Eliminar al profesor "${nombre}"?`)) return;
    const apiInstance = axiosAuth(accessToken);
    try {
      await apiInstance.delete(`turnos/prestadores/${id}/`);
      toast.success("Profesor eliminado");
      apiInstance.get("turnos/prestadores/")
        .then(res => setProfesores(res.data.results || res.data));
      if (editingId === id) {
        onClose();
        resetForm();
      }
    } catch {
      toast.error("Error al eliminar profesor");
    }
  };

  // ---------- Validación para botón "Agregar Bloqueo" ----------
  const bloqueoIncompleto = !nuevoBloqueo.fecha_inicio || !nuevoBloqueo.fecha_fin;

  return (
    <>
      <PageWrapper>
        <Sidebar
          links={[
            { label: "Dashboard", path: "/admin" },
            { label: "Sedes", path: "/admin/sedes" },
            { label: "Profesores", path: "/admin/profesores" },
            { label: "Usuarios", path: "/admin/usuarios" },
            { label: "Configuración Pago", path: "/admin/configuracion-pago" },
            { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
          ]}
        />
        <Box flex="1" p={[8]} bg={bg} color={card.color}>
          <Heading size="md" mb={4}>Administrar Profesores</Heading>
          <Flex justify="flex-end" mb={4}>
            <Button onClick={openForCreate} size={isMobile ? "md" : "lg"}>
              Agregar Profesor
            </Button>
          </Flex>
  
          {profesores.length === 0 ? (
            <Text textAlign="center" opacity={0.7} fontStyle="italic">
              No hay profesores cargados.
            </Text>
          ) : (
            <VStack spacing={4} align="stretch">
              {profesores.map((p) => (
                <Flex
                  key={p.id}
                  bg={card.bg}
                  color={card.color}
                  p={4}
                  rounded="md"
                  justify="space-between"
                  align="center"
                  boxShadow="md"
                  direction={isMobile ? "column" : "row"}
                >
                  <Box>
                    <Text fontWeight="bold">{p.nombre}</Text>
                    <Text fontSize="sm" color={mutedText}>
                      {p.email || "Sin email"}
                    </Text>
                  </Box>
                  <Flex gap={2} mt={isMobile ? 2 : 0}>
                    <IconButton
                      icon={<EditIcon />}
                      aria-label="Editar profesor"
                      onClick={() => openForEdit(p)}
                      size="sm"
                      colorScheme="blue"
                    />
                    <IconButton
                      icon={<DeleteIcon />}
                      aria-label="Eliminar profesor"
                      onClick={() => handleDelete(p.id, p.nombre)}
                      size="sm"
                      colorScheme="red"
                    />
                  </Flex>
                </Flex>
              ))}
            </VStack>
          )}
  
          {/* MODAL DE FORMULARIO */}
          <Modal
            isOpen={isOpen}
            onClose={() => { onClose(); resetForm(); }}
            isCentered
            size={isMobile ? "full" : "4xl"}
          >
            <ModalOverlay />
            <ModalContent
              bg={modal.bg}
              color={modal.color}
              maxW={isMobile ? "100vw" : "900px"}
              mx={isMobile ? 1 : "auto"}
            >
              <ModalHeader>
                {editingId ? "Editar Profesor" : "Nuevo Profesor"}
              </ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                <form id="prof-form" onSubmit={handleSubmit}>
                  <VStack spacing={4} align="stretch">
                    <Input label="Nombre" value={nombre} onChange={e => setNombre(e.target.value)} />
                    <Input label="Email" value={email} onChange={e => setEmail(e.target.value)} type="email" />
                    <Input label="Teléfono" value={telefono} onChange={e => setTelefono(e.target.value)} />
                    <Input label="Especialidad" value={especialidad} onChange={e => setEspecialidad(e.target.value)} />
                  </VStack>
                  <Heading size="xs" mt={6} mb={3}>Disponibilidades</Heading>
                  <Box bg={card.bg} color={card.color} p={[2, 4]} rounded="md">
                    {!isMobile && (
                      <Grid
                        templateColumns={GRID_TEMPLATE}
                        mb={2}
                        fontWeight="semibold"
                        color={card.color}
                        fontSize="sm"
                        alignItems="center"
                      >
                        <Box>Sede</Box>
                        <Box>Día</Box>
                        <Box>Hora inicio</Box>
                        <Box>Hora fin</Box>
                        <Box></Box>
                      </Grid>
                    )}
  
                    <VStack spacing={3} align="stretch">
                      {disponibilidades.map((d, i) =>
                        isMobile ? (
                          <Box
                            key={i}
                            bg={card.bg}
                            color={card.color}
                            rounded="md"
                            p={2}
                            mb={1}
                            borderWidth={1}
                            borderColor={input.borderColor}
                          >
                            <Stack spacing={2}>
                              <Box>
                                <Text fontSize="xs" color={mutedText} mb={1}>Sede</Text>
                                <Select
                                  bg={input.bg}
                                  color={input.color}
                                  value={d.sede || ""}
                                  onChange={e => actualizarDisponibilidad(i, "sede", e.target.value)}
                                  placeholder="Seleccioná sede"
                                  {...FIELD_PROPS}
                                >
                                  {sedes.map(s => (
                                    <option key={s.id} value={s.id}>{s.nombre}</option>
                                  ))}
                                </Select>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color={mutedText} mb={1}>Día</Text>
                                <Select
                                  bg={input.bg}
                                  color={input.color}
                                  value={d.dia}
                                  onChange={e => actualizarDisponibilidad(i, "dia", parseInt(e.target.value))}
                                  {...FIELD_PROPS}
                                >
                                  {diasSemana.map(dia => (
                                    <option key={dia.value} value={dia.value}>{dia.label}</option>
                                  ))}
                                </Select>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color={mutedText} mb={1}>Hora inicio</Text>
                                <ChakraInput
                                  bg={input.bg}
                                  color={input.color}
                                  type="time"
                                  value={d.hora_inicio}
                                  onChange={e => actualizarDisponibilidad(i, "hora_inicio", e.target.value)}
                                  {...FIELD_PROPS}
                                />
                              </Box>
                              <Box>
                                <Text fontSize="xs" color={mutedText} mb={1}>Hora fin</Text>
                                <ChakraInput
                                  bg={input.bg}
                                  color={input.color}
                                  type="time"
                                  value={d.hora_fin}
                                  onChange={e => actualizarDisponibilidad(i, "hora_fin", e.target.value)}
                                  {...FIELD_PROPS}
                                />
                              </Box>
                              <Flex>
                                <Button
                                  leftIcon={<DeleteIcon />}
                                  colorScheme="red"
                                  variant="solid"
                                  size="md"
                                  w="100%"
                                  onClick={() => eliminarDisponibilidad(i)}
                                >
                                  Eliminar
                                </Button>
                              </Flex>
                            </Stack>
                          </Box>
                        ) : 
                          <Grid
                            key={i}
                            templateColumns={GRID_TEMPLATE}
                            gap={3}
                            alignItems="center"
                          >
                            <Select
                              bg={input.bg}
                              color={input.color}
                              value={d.sede || ""}
                              onChange={e => actualizarDisponibilidad(i, "sede", e.target.value)}
                              placeholder="Seleccioná sede"
                              {...FIELD_PROPS}
                            >
                              {sedes.map(s => (
                                <option key={s.id} value={s.id}>{s.nombre}</option>
                              ))}
                            </Select>
                            <Select
                              bg={input.bg}
                              color={input.color}
                              value={d.dia}
                              onChange={e => actualizarDisponibilidad(i, "dia", parseInt(e.target.value))}
                              {...FIELD_PROPS}
                            >
                              {diasSemana.map(dia => (
                                <option key={dia.value} value={dia.value}>{dia.label}</option>
                              ))}
                            </Select>
                            <ChakraInput
                              bg={input.bg}
                              color={input.color}
                              type="time"
                              value={d.hora_inicio}
                              onChange={e => actualizarDisponibilidad(i, "hora_inicio", e.target.value)}
                              {...FIELD_PROPS}
                            />
                            <ChakraInput
                              bg={input.bg}
                              color={input.color}
                              type="time"
                              value={d.hora_fin}
                              onChange={e => actualizarDisponibilidad(i, "hora_fin", e.target.value)}
                              {...FIELD_PROPS}
                            />
                            <IconButton
                              icon={<DeleteIcon />}
                              aria-label="Eliminar disponibilidad"
                              colorScheme="red"
                              size="md"
                              onClick={() => eliminarDisponibilidad(i)}
                            />
                          </Grid>
                        )}
                        
                        </VStack>
                        <Flex mt={3}>
                          <Button
                            variant="secondary"
                            onClick={agregarDisponibilidad}
                            size="md"
                            type="button"
                            w="100%"
                          >
                            Agregar Disponibilidad
                          </Button>
                        </Flex>
                        </Box>
                        
                        {/* ---------- Bloqueos de calendario SOLO en modo editar ---------- */}
                        {editingId ? (
                          <>
                            <Heading size="xs" mt={6} mb={3}>Bloqueos de calendario</Heading>
                            <Box bg={card.bg} color={card.color} p={[2, 4]} rounded="md" mb={3}>
                              <VStack spacing={3} align="stretch">
                                {bloqueos.length === 0 && (
                                  <Text color={mutedText} fontSize="sm" textAlign="center">
                                    No hay bloqueos para este profesor.
                                  </Text>
                                )}
                                {bloqueos.map((b) => (
                                  <Flex
                                    key={b.id}
                                    align="center"
                                    justify="space-between"
                                    bg={card.bg}
                                    color={card.color}
                                    rounded="md"
                                    px={3}
                                    py={2}
                                    borderWidth={1}
                                    borderColor={input.borderColor}
                                    wrap="wrap"
                                  >
                                    <Box>
                                      <Text fontSize="sm" color={card.color}>
                                        <b>{b.lugar_nombre || "Todas las sedes"}</b> - {b.fecha_inicio} a {b.fecha_fin}
                                        {b.motivo && <span style={{ color: "#aaa" }}> — {b.motivo}</span>}
                                      </Text>
                                    </Box>
                                    <IconButton
                                      icon={<DeleteIcon />}
                                      aria-label="Eliminar bloqueo"
                                      colorScheme="red"
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleEliminarBloqueo(b.id)}
                                    />
                                  </Flex>
                                ))}
                              </VStack>
                              <Stack direction={["column", "row"]} mt={4} spacing={2}>
                                <Box flex={1}>
                                  <Select
                                    bg={input.bg}
                                    color={input.color}
                                    placeholder="Todas las sedes"
                                    value={nuevoBloqueo.lugar}
                                    onChange={e => setNuevoBloqueo(n => ({ ...n, lugar: e.target.value }))}
                                    {...FIELD_PROPS}
                                  >
                                    <option value="">Todas las sedes</option>
                                    {sedes.map(s => (
                                      <option key={s.id} value={s.id}>{s.nombre}</option>
                                    ))}
                                  </Select>
                                </Box>
                                <Box flex={1}>
                                  <ChakraInput
                                    bg={input.bg}
                                    color={input.color}
                                    type="date"
                                    placeholder="Fecha inicio"
                                    value={nuevoBloqueo.fecha_inicio}
                                    onChange={e => setNuevoBloqueo(n => ({ ...n, fecha_inicio: e.target.value }))}
                                    {...FIELD_PROPS}
                                  />
                                </Box>
                                <Box flex={1}>
                                  <ChakraInput
                                    bg={input.bg}
                                    color={input.color}
                                    type="date"
                                    placeholder="Fecha fin"
                                    value={nuevoBloqueo.fecha_fin}
                                    onChange={e => setNuevoBloqueo(n => ({ ...n, fecha_fin: e.target.value }))}
                                    {...FIELD_PROPS}
                                  />
                                </Box>
                                <Box flex={2}>
                                  <ChakraInput
                                    bg={input.bg}
                                    color={input.color}
                                    placeholder="Motivo (opcional)"
                                    value={nuevoBloqueo.motivo}
                                    onChange={e => setNuevoBloqueo(n => ({ ...n, motivo: e.target.value }))}
                                    {...FIELD_PROPS}
                                  />
                                </Box>
                                <Button
                                  onClick={handleAgregarBloqueo}
                                  variant="secondary"
                                  size="md"
                                  minW={["100%", "110px"]}
                                  isDisabled={bloqueoIncompleto}
                                >
                                  Agregar Bloqueo
                                </Button>
                              </Stack>
                            </Box>
                          </>
                        ) : (
                          <Text color={mutedText} fontSize="sm" mt={6}>
                            Guardá el profesor antes de cargar bloqueos de calendario.
                          </Text>
                        )}
                        
                        </form>
                        </ModalBody>
                        
                                  <ModalFooter>
                                    <Button type="submit" form="prof-form" size="lg" mr={3} w={isMobile ? "100%" : undefined}>
                                      {editingId ? "Actualizar" : "Crear"}
                                    </Button>
                                    <Button
                                      variant="secondary"
                                      onClick={() => { onClose(); resetForm(); }}
                                      size="lg"
                                      w={isMobile ? "100%" : undefined}
                                    >
                                      Cancelar
                                    </Button>
                                  </ModalFooter>
                                  </ModalContent>
                                  </Modal>
                    
                                  {/* === MODAL DE TURNOS RESERVADOS AFECTADOS === */}
                                  <Modal
                                    isOpen={isModalReservadosOpen}
                                    onClose={closeModalReservados}
                                    isCentered
                                    size="xl"
                                    scrollBehavior="inside"
                                  >
                                    <ModalOverlay />
                                      <ModalContent 
                                        bg={modal.bg} 
                                        color={modal.color}
                                        maxW="90vw"
                                      >
                                      <ModalHeader>
                                        ⚠️ Turnos Reservados Afectados ({turnosReservadosAfectados.length})
                                      </ModalHeader>
                                      <ModalCloseButton />
                                      <ModalBody>
                                        <Text mb={4}>
                                          El bloqueo afectó <b>{turnosReservadosAfectados.length}</b> turnos.
                                          📲 Contactá a los usuarios si vas a forzar la cancelación.
                                        </Text>
                                        <Box maxH="400px" overflowY="auto" borderWidth={1} borderColor={input.borderColor} rounded="md">
                                          <Table _hover={{ bg: card.iconColor }} variant="unstyled" size="sm">
                                            <Thead bg={card.bg}>
                                              <Tr>
                                                <Th>🆔 ID</Th>
                                                <Th>📅 Fecha</Th>
                                                <Th>⏰ Hora</Th>
                                                <Th>👤 Usuario</Th>
                                                <Th>📧 Email</Th>
                                              </Tr>
                                            </Thead>
                                            <Tbody>
                                              {turnosReservadosAfectados.map(t => (
                                                <Tr key={t.id} _hover={{ bg: card.iconColor }}>
                                                  <Td>{t.id}</Td>
                                                  <Td>{t.fecha}</Td>
                                                  <Td>{t.hora}</Td>
                                                  <Td>{t.usuario}</Td>
                                                  <Td>{t.email}</Td>
                                                </Tr>
                                              ))}
                                            </Tbody>
                                          </Table>
                                        </Box>
                                      </ModalBody>
                                      <ModalFooter>
                                        <Button variant="secondary" mr={3} onClick={descargarListadoTurnos}>
                                          📥 Descargar listado
                                        </Button>
                                        <Button colorScheme="red" mr={3} onClick={handleForzarCancelacionReservados}>
                                          ❌ Forzar cancelación
                                        </Button>
                                        <Button variant="ghost" onClick={closeModalReservados}>
                                          Cerrar
                                        </Button>
                                      </ModalFooter>
                                    </ModalContent>
                                  </Modal>
                          </Box>
                        </PageWrapper>
                      </>
                    );
                  };

                  export default ProfesoresPage;
