// src/pages/admin/UsuariosPage.jsx

import React, { useEffect, useState, useContext } from "react";
import {
  Box, Flex, Heading, Text, VStack, Modal, ModalOverlay, ModalContent,
  ModalHeader, ModalCloseButton, ModalBody, ModalFooter, useDisclosure,
  IconButton, Switch, Stack, HStack, useBreakpointValue, Divider,
  useColorModeValue, Select, SimpleGrid, ButtonGroup, InputGroup, InputLeftElement,
  Tabs, TabList, Tab, TabPanels, TabPanel, Badge
} from "@chakra-ui/react";
import { DeleteIcon, EditIcon, SearchIcon } from "@chakra-ui/icons";
import Sidebar from "../../components/layout/Sidebar";
import Button from "../../components/ui/Button";
import { Input as ChakraInput } from "@chakra-ui/react";
import PageWrapper from "../../components/layout/PageWrapper";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { toast } from "react-toastify";

// Componentes del modal mejorado
import InfoCard from "../../components/ui/InfoCard";
import BonificacionesList from "../../components/admin/BonificacionesList";
import AbonosList from "../../components/admin/AbonosList";
import TurnosSueltosList from "../../components/admin/TurnosSueltosList";

import {
  useBodyBg,
  useCardColors,
  useModalColors,
  useInputColors,
  useMutedText
} from "../../components/theme/tokens";

const UsuariosPage = () => {
  const { accessToken, logout } = useContext(AuthContext);
  const hoverBg = useColorModeValue("gray.200", "gray.700");
  const [usuarios, setUsuarios] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [nombre, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [telefono, setTelefono] = useState("");
  const [tipoUsuario, setTipoUsuario] = useState("usuario_final");
  const [email, setEmail] = useState("");
  const [activo, setActivo] = useState(true);
  const [detalleUsuario, setDetalleUsuario] = useState(null);
  const [cargandoUsuarios, setCargandoUsuarios] = useState(false);

  // Sedes / Tipos de clase para emitir bonificación
  const [sedes, setSedes] = useState([]);
  const [tiposClase, setTiposClase] = useState([]);
  const [selectedSedeId, setSelectedSedeId] = useState("");
  const [selectedTipoClaseId, setSelectedTipoClaseId] = useState("");
  const [loadingTipos, setLoadingTipos] = useState(false);
  const LABELS_TIPO = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };

  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isOpenDetalle,
    onOpen: onOpenDetalle,
    onClose: onCloseDetalle,
  } = useDisclosure();

  const isMobile = useBreakpointValue({ base: true, md: false });

  const bg = useBodyBg();
  const card = useCardColors();
  const modal = useModalColors();
  const input = useInputColors();
  const mutedText = useMutedText();

  const [motivoBonificacion, setMotivoBonificacion] = useState("");
  const [cargandoBono, setCargandoBono] = useState(false);
  const [bonificaciones, setBonificaciones] = useState([]);

  useEffect(() => {
    const fetchBonificaciones = async () => {
      try {
        const res = await axiosAuth(accessToken, logout).get("/turnos/bonificados/mios/");
        setBonificaciones(res.data || []);
      } catch (e) {
        console.error("Error al obtener bonificaciones:", e);
      }
    };
    if (accessToken) fetchBonificaciones();
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    reloadUsuarios();
  }, [accessToken]);

  // Carga de sedes al abrir el modal de detalle (mismo approach que SedesPage)
  useEffect(() => {
    if (!isOpenDetalle || !accessToken) return;
    
    const api = axiosAuth(accessToken, logout);
    setSelectedSedeId("");
    setSelectedTipoClaseId("");
    setTiposClase([]);
    api.get("padel/sedes/")
      .then(res => setSedes(res.data?.results || res.data || []))
      .catch(() => toast.error("No se pudieron cargar las sedes"));
  }, [isOpenDetalle, accessToken]);

  // Al elegir sede, pedir su detalle y extraer configuracion_padel.tipos_clase
  useEffect(() => {
    if (!selectedSedeId || !accessToken) return;
    
    const api = axiosAuth(accessToken, logout);
    setLoadingTipos(true);
    (async () => {
      try {
        const r = await api.get(`padel/sedes/${selectedSedeId}/`);
        const conf = r.data?.configuracion_padel;
        setTiposClase(conf?.tipos_clase || []);
      } catch (e) {
        setTiposClase([]);
        toast.error("No se pudieron cargar los tipos de clase de la sede");
      } finally {
        setLoadingTipos(false);
      }
    })();
  }, [selectedSedeId, accessToken]);

  const reloadUsuarios = async () => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken, logout);
    const PAGE_SIZE = 200;
  
    setCargandoUsuarios(true);
    try {
      let url = `auth/usuarios/?page_size=${PAGE_SIZE}`;
      const acumulado = [];
      let safety = 0;
      let firstData = null; // guarda la 1ra respuesta para el caso "array directo"
  
      while (url && safety < 200) {
        const { data } = await api.get(url);
        if (firstData === null) firstData = data;
  
        const items = Array.isArray(data) ? data : (data.results || []);
        if (Array.isArray(items) && items.length) acumulado.push(...items);
  
        // Procesar URL de paginación (absoluta o relativa)
        let nextUrl = (data.next && String(data.next).trim()) ? String(data.next) : null;
        if (nextUrl) {
          // Si es una URL absoluta, extraer solo el path
          if (nextUrl.startsWith('http://') || nextUrl.startsWith('https://')) {
            try {
              const urlObj = new URL(nextUrl);
              const fullPath = urlObj.pathname + urlObj.search;
              // Remover el prefijo /api si existe para evitar /api/api/
              nextUrl = fullPath.startsWith('/api/') ? fullPath.slice(4) : fullPath;
            } catch (e) {
              // Si falla el parsing, intentar extraer manualmente
              const match = nextUrl.match(/https?:\/\/[^\/]+(\/.*)/);
              if (match) {
                const fullPath = match[1];
                nextUrl = fullPath.startsWith('/api/') ? fullPath.slice(4) : fullPath;
              }
            }
          }
          // Si ya es relativa, usarla tal como está
        }
        url = nextUrl;
        safety += 1;
      }
  
      // Si no hubo paginación y la API responde un array directo
      if (acumulado.length === 0) {
        if (Array.isArray(firstData)) {
          setUsuarios(firstData);
        } else {
          setUsuarios(firstData?.results || []);
        }
      } else {
        setUsuarios(acumulado);
      }
    } catch (e) {
      console.error("[Usuarios] Error paginando:", e?.response?.data || e?.message);
      toast.error("Error cargando usuarios");
    } finally {
      setCargandoUsuarios(false);
    }
  };
  
  const resetForm = () => {
    setEditingId(null);
    setNombre("");
    setApellido("");
    setTelefono("");
    setTipoUsuario("usuario_final");
    setEmail("");
    setActivo(true);
  };

  const openForCreate = () => {
    resetForm();
    onOpen();
  };

  const openForEdit = (u) => {
    setEditingId(u.id);
    setNombre(u.nombre || "");
    setApellido(u.apellido || "");
    setTelefono(u.telefono || "");
    setTipoUsuario(u.tipo_usuario || "usuario_final");
    setEmail(u.email || "");
    setActivo(!!u.is_active);
    onOpen();
  };

  const handleOpenDetalle = (u) => {
    setDetalleUsuario(u);
    onOpenDetalle();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nombre.trim()) {
      toast.error("El nombre es obligatorio");
      return;
    }
    // (Se mantiene tu validación original)

    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.error("Ingresá un email válido.");
      return;
    }

    
    const api = axiosAuth(accessToken, logout);
    const data = {
      nombre,
      apellido,
      telefono,
      tipo_usuario: tipoUsuario,
      email,
      is_active: activo,
    };

    try {
      if (editingId) {
        await api.put(`auth/usuarios/${editingId}/`, data);
        toast.success("Usuario actualizado");
      } else {
        await api.post("auth/usuarios/", data);
        toast.success("Usuario creado");
      }
      onClose();
      resetForm();
      reloadUsuarios();
    } catch (err) {
      console.error("Detalle del error:", err.response?.data || err.message);
      const errorResponse = err.response?.data;
      const errorMessage =
        typeof errorResponse === "string"
          ? errorResponse
          : Object.values(errorResponse || {}).flat().join(" | ") || "Error al guardar usuario";
      toast.error(errorMessage);
    }
  };

  const [busqueda, setBusqueda] = useState("");

  const usuariosFiltrados = React.useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return usuarios;
    return usuarios.filter((u) => {
      const campos = [
        u.nombre,
        u.apellido,
        u.email,
        u.telefono,
        u.username,
        u.tipo_usuario,
      ];
      return campos.some((c) => (c || "").toString().toLowerCase().includes(q));
    });
  }, [usuarios, busqueda]);

  const usuariosFinales = usuariosFiltrados.filter(u => u.tipo_usuario === "usuario_final");
  const empleados = usuariosFiltrados.filter(u => u.tipo_usuario === "empleado_cliente");
  const admins = usuariosFiltrados.filter(u => u.tipo_usuario === "admin_cliente");

  const handleDelete = async (id, email) => {
    if (!window.confirm(`¿Eliminar el usuario "${email}"?`)) return;
    
    const api = axiosAuth(accessToken, logout);
    try {
      await api.delete(`auth/usuarios/${id}/`);
      toast.success("Usuario eliminado");
      reloadUsuarios();
      if (editingId === id) {
        onClose();
        resetForm();
      }
    } catch {
      toast.error("Error al eliminar usuario");
    }
  };

  const Section = ({ title, items }) => (
    <>
      <Heading size="sm" mt={8} mb={2}>{title}</Heading>
      {items.length === 0 ? (
        <Text color={mutedText}>No hay {title.toLowerCase()} cargados.</Text>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
          {items.map((u) => (
            <Flex
              key={u.id}
              bg={card.bg}
              color={card.color}
              p={4}
              rounded="md"
              boxShadow="md"
              role="group"
              _hover={{ bg: hoverBg, cursor: "pointer" }}
              direction={{ base: "column", md: "row" }}
              align={{ base: "stretch", md: "center" }}
              justify="space-between"
              onClick={(e) => {
                if (e.target.closest("button")) return;
                handleOpenDetalle(u);
              }}
            >
              <Box flex="1" mr={{ md: 4 }}>
                <Text fontWeight="bold" noOfLines={{ base: 1, md: undefined }}>
                  {u.nombre} {u.apellido}
                </Text>
                <Text fontSize="sm" color={mutedText} noOfLines={{ base: 1, md: undefined }}>
                  {u.email}
                </Text>
                <Text fontSize="sm" color={u.is_active ? "green.400" : "red.400"}>
                  {u.is_active ? "Activo" : "Inactivo"}
                </Text>
              </Box>

              <ButtonGroup
                mt={{ base: 3, md: 0 }}
                size="sm"
                isAttached={false}
                spacing="2"
                w={{ base: "100%", md: "auto" }}
                justifyContent={{ base: "stretch", md: "flex-end" }}
              >
                <IconButton
                  icon={<EditIcon />}
                  aria-label="Editar"
                  onClick={() => openForEdit(u)}
                  size="sm"
                  colorScheme="blue"
                />
                <IconButton
                  icon={<DeleteIcon />}
                  aria-label="Eliminar"
                  onClick={() => handleDelete(u.id, u.email)}
                  size="sm"
                  colorScheme="red"
                />
              </ButtonGroup>
            </Flex>
          ))}
        </SimpleGrid>
      )}
    </>
  );

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
          <Heading size="md">Administrar Usuarios</Heading>

          <InputGroup size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "320px" }}>
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <ChakraInput
              placeholder="Buscar usuario..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              bg={input.bg}
              color={input.color}
              _placeholder={{ color: "gray.400" }}
              borderRadius="full"
              pr="4"
            />
          </InputGroup>

          <Button onClick={openForCreate} size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
            Agregar Usuario
          </Button>
        </Stack>

        <Section title="Usuarios" items={usuariosFinales} />
        <Section title="Profesores" items={empleados} />
        <Section title="Administradores" items={admins} />

        {/* MODAL crear/editar */}
        <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm(); }} isCentered size={isMobile ? "full" : "md"}>
          <ModalOverlay />
          <ModalContent bg={modal.bg} color={modal.color} sx={{
              'input, select, textarea': {
                fontSize: { base: '16px', md: 'inherit' }
              }
            }}>
            <ModalHeader>{editingId ? "Editar Usuario" : "Agregar Usuario"}</ModalHeader>
            <ModalCloseButton />
            <ModalBody maxH="70vh" overflowY="auto">
              <form id="usuario-form" onSubmit={handleSubmit}>
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
                    placeholder="Teléfono"
                    inputMode="tel"
                    value={telefono}
                    onChange={e => setTelefono(e.target.value)}
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                  />
                  <Select
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                    bg={input.bg}
                    color={input.color}
                    value={tipoUsuario}
                    onChange={e => setTipoUsuario(e.target.value)}
                  >
                    <option value="admin_cliente">Admin del Cliente</option>
                    <option value="empleado_cliente">Empleado del Cliente</option>
                    <option value="usuario_final">Usuario Final</option>
                  </Select>
                  <ChakraInput
                    placeholder="Email"
                    type="email"
                    inputMode="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                  />

                  <HStack justify="space-between">
                    <Text>Activo</Text>
                    <Switch isChecked={activo} onChange={e => setActivo(e.target.checked)} colorScheme="green" />
                  </HStack>
                </VStack>
              </form>
            </ModalBody>
            <ModalFooter>
              <Stack direction={{ base: "column", md: "row" }} w="100%">
                <Button type="submit" form="usuario-form" size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
                  {editingId ? "Guardar" : "Crear"}
                </Button>
                <Button variant="secondary" onClick={() => { onClose(); resetForm(); }} size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
                  Cancelar
                </Button>
              </Stack>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* MODAL detalle usuario - MEJORADO */}
        <Modal 
          isOpen={isOpenDetalle} 
          onClose={onCloseDetalle} 
          isCentered 
          size={isMobile ? "full" : "xl"}
        >
          <ModalOverlay />
          <ModalContent bg={modal.bg} color={modal.color} maxH="90vh">
            <ModalHeader>
              <Flex align="center" justify="space-between" wrap="wrap" gap={2}>
                <Text fontSize="xl" fontWeight="bold">
                  {detalleUsuario?.nombre} {detalleUsuario?.apellido}
                </Text>
                <Badge 
                  colorScheme={detalleUsuario?.is_active ? "green" : "red"}
                  size="lg"
                >
                  {detalleUsuario?.is_active ? "Activo" : "Inactivo"}
                </Badge>
              </Flex>
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody maxH="70vh" overflowY="auto">
              {detalleUsuario && (
                <Tabs variant="enclosed" colorScheme="blue">
                  <TabList>
                    <Tab>👤 Información</Tab>
                    <Tab>🎁 Bonificaciones</Tab>
                    <Tab>📅 Abonos</Tab>
                    <Tab>🏓 Clases Sueltas</Tab>
                  </TabList>

                  <TabPanels>
                    {/* TAB 1: Información Usuario */}
                    <TabPanel>
                      <VStack spacing={4} align="stretch">
                        <InfoCard 
                          label="Nombre y Apellido"
                          value={`${detalleUsuario.nombre} ${detalleUsuario.apellido}`}
                        />
                        <InfoCard 
                          label="Teléfono"
                          value={detalleUsuario.telefono}
                          copyButton={true}
                        />
                        <InfoCard 
                          label="Email"
                          value={detalleUsuario.email}
                          copyButton={true}
                        />
                        <InfoCard 
                          label="Tipo de Usuario"
                          value={detalleUsuario.tipo_usuario}
                        />
                        <InfoCard 
                          label="Username"
                          value={detalleUsuario.username}
                        />
                        <InfoCard 
                          label="Es Staff"
                          value={detalleUsuario.is_staff ? "Sí" : "No"}
                        />
                      </VStack>
                    </TabPanel>

                    {/* TAB 2: Bonificaciones */}
                    <TabPanel>
                      <VStack spacing={4} align="stretch">
                        <BonificacionesList 
                          usuarioId={detalleUsuario.id}
                          accessToken={accessToken}
                          logout={logout}
                          onRefresh={() => {
                            // Refrescar datos si es necesario
                          }}
                        />
                        
                        {/* Formulario para asignar nueva bonificación */}
                        {detalleUsuario.tipo_usuario === "usuario_final" && (
                          <Box p={4} bg={card.bg} borderRadius="md" borderWidth="1px">
                            <Text fontWeight="bold" mb={3}>🎁 Asignar Nueva Bonificación</Text>
                            <VStack spacing={3} align="stretch">
                              <ChakraInput
                                placeholder="Motivo"
                                value={motivoBonificacion}
                                onChange={(e) => setMotivoBonificacion(e.target.value)}
                                size="md"
                                fontSize={{ base: "16px", md: "inherit" }}
                              />

                              {/* Sede */}
                              <Select
                                size={{ base: "sm", md: "md" }}
                                placeholder="Seleccioná la sede"
                                value={selectedSedeId}
                                onChange={(e) => {
                                  setSelectedSedeId(e.target.value);
                                  setSelectedTipoClaseId("");
                                }}
                              >
                                {(sedes || []).map((s) => (
                                  <option key={s.id} value={s.id}>{s.nombre}</option>
                                ))}
                              </Select>

                              {/* Tipo de clase */}
                              <Select
                                size={{ base: "sm", md: "md" }}
                                placeholder={selectedSedeId ? (loadingTipos ? "Cargando tipos..." : "Seleccioná el tipo de clase") : "Elegí una sede primero"}
                                value={selectedTipoClaseId}
                                onChange={(e) => setSelectedTipoClaseId(e.target.value)}
                                isDisabled={!selectedSedeId || loadingTipos}
                              >
                                {(tiposClase || []).map((tc) => (
                                  <option key={tc.id} value={tc.id}>
                                    {(LABELS_TIPO[tc.codigo] || tc.codigo)?.toString()} — ${Number(tc.precio).toLocaleString("es-AR")}
                                  </option>
                                ))}
                              </Select>

                              <Button
                                isLoading={cargandoBono}
                                isDisabled={
                                  !motivoBonificacion.trim() ||
                                  !selectedSedeId ||
                                  !selectedTipoClaseId
                                }
                                w={{ base: "100%", md: "auto" }}
                                onClick={async () => {
                                  if (!motivoBonificacion.trim()) {
                                    toast.error("El motivo es obligatorio");
                                    return;
                                  }
                                  if (!selectedSedeId) {
                                    toast.error("Seleccioná la sede");
                                    return;
                                  }
                                  if (!selectedTipoClaseId) {
                                    toast.error("Seleccioná el tipo de clase");
                                    return;
                                  }
                                  setCargandoBono(true);
                                  
                                  const api = axiosAuth(accessToken, logout);
                                  try {
                                    await api.post("/turnos/bonificaciones/crear-manual/", {
                                      usuario_id: detalleUsuario.id,
                                      sede_id: Number(selectedSedeId),
                                      tipo_clase_id: Number(selectedTipoClaseId),
                                      motivo: motivoBonificacion,
                                    });
                                    toast.success("Bonificación emitida correctamente");
                                    setMotivoBonificacion("");
                                    setSelectedSedeId("");
                                    setSelectedTipoClaseId("");
                                    setTiposClase([]);
                                  } catch (err) {
                                    console.error("Emitir bonificación manual:", err?.response?.data || err?.message);
                                    toast.error("Error al emitir bonificación");
                                  } finally {
                                    setCargandoBono(false);
                                  }
                                }}
                              >
                                Emitir Bono
                              </Button>
                            </VStack>
                          </Box>
                        )}
                      </VStack>
                    </TabPanel>

                    {/* TAB 3: Abonos */}
                    <TabPanel>
                      <AbonosList 
                        usuarioId={detalleUsuario.id}
                        accessToken={accessToken}
                        logout={logout}
                        onRenovar={() => {
                          // Lógica de renovación si es necesaria
                        }}
                        onCancelar={() => {
                          // Lógica de cancelación si es necesaria
                        }}
                      />
                    </TabPanel>

                    {/* TAB 4: Clases Sueltas */}
                    <TabPanel>
                      <TurnosSueltosList 
                        usuarioId={detalleUsuario.id}
                        accessToken={accessToken}
                        logout={logout}
                        onCancelar={() => {
                          // Lógica de cancelación si es necesaria
                        }}
                      />
                    </TabPanel>
                  </TabPanels>
                </Tabs>
              )}
            </ModalBody>
            <ModalFooter>
              <Button 
                onClick={onCloseDetalle} 
                size={{ base: "md", md: "lg" }} 
                w={{ base: "100%", md: "auto" }}
              >
                Cerrar
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </Box>
    </PageWrapper>
  );
};

export default UsuariosPage;
