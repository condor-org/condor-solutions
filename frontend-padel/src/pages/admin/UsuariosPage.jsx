// src/pages/admin/UsuariosPage.jsx

import React, { useEffect, useState, useContext } from "react";
import {
  Box, Flex, Heading, Text, VStack, Modal, ModalOverlay, ModalContent,
  ModalHeader, ModalCloseButton, ModalBody, ModalFooter, useDisclosure,
  IconButton, Switch, Stack, HStack, useBreakpointValue, Divider,
  useColorModeValue, Select, SimpleGrid, ButtonGroup, InputGroup, InputLeftElement
} from "@chakra-ui/react";
import { DeleteIcon, EditIcon, SearchIcon } from "@chakra-ui/icons";
import Sidebar from "../../components/layout/Sidebar";
import Button from "../../components/ui/Button";
import { Input as ChakraInput } from "@chakra-ui/react";
import PageWrapper from "../../components/layout/PageWrapper";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { toast } from "react-toastify";

import {
  useBodyBg,
  useCardColors,
  useModalColors,
  useInputColors,
  useMutedText
} from "../../components/theme/tokens";

const UsuariosPage = () => {
  const { accessToken } = useContext(AuthContext);
  const hoverBg = useColorModeValue("gray.200", "gray.700");
  const [usuarios, setUsuarios] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [nombre, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [telefono, setTelefono] = useState("");
  const [tipoUsuario, setTipoUsuario] = useState("usuario_final");
  const [email, setEmail] = useState("");
  const [activo, setActivo] = useState(true);
  const [password, setPassword] = useState("");
  const [detalleUsuario, setDetalleUsuario] = useState(null);
  const [tipoTurnoBono, setTipoTurnoBono] = useState("individual");

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
        const res = await axiosAuth(accessToken).get("/turnos/bonificados/mios/");
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

  const reloadUsuarios = () => {
    const api = axiosAuth(accessToken);
    api.get("auth/usuarios/")
      .then(res => setUsuarios(res.data.results || res.data || []))
      .catch(() => toast.error("Error cargando usuarios"));
  };

  const resetForm = () => {
    setEditingId(null);
    setNombre("");
    setApellido("");
    setTelefono("");
    setTipoUsuario("usuario_final");
    setEmail("");
    setActivo(true);
    setPassword("");
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
    setPassword("");
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
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.error("Ingresá un email válido.");
      return;
    }

    const api = axiosAuth(accessToken);
    const data = {
      nombre,
      apellido,
      telefono,
      tipo_usuario: tipoUsuario,
      email,
      is_active: activo,
    };

    if (editingId) {
      if (password.trim()) data.password = password;
    } else {
      if (!password.trim()) {
        toast.error("La contraseña es obligatoria para crear un usuario.");
        return;
      }
      data.password = password;
    }

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

  // lista filtrada (performante)
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
    const api = axiosAuth(accessToken);
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
          { label: "Usuarios", path: "/admin/usuarios" },
          { label: "Cancelaciones", path: "/admin/cancelaciones" },
          { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
          { label: "Abonos (Asignar)", path: "/admin/abonos" },
        ]}
      />

      {/* Wrapper consistente */}
      <Box flex="1" p={{ base: 4, md: 8 }} bg={bg} color={card.color}>
        {/* Header responsivo */}
        <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "center" }} mb={4} spacing={3}>
          <Heading size="md">Administrar Usuarios</Heading>

          <InputGroup
            size={{ base: "md", md: "lg" }}
            w={{ base: "100%", md: "320px" }}
          >
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

        {/* Secciones en cards responsivas */}
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
                {editingId ? (
                  // Edición: campo opcional para cambiar password
                  <ChakraInput
                    placeholder="Nueva contraseña (opcional)"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                  />
                ) : (
                  // Creación: password obligatoria
                  <ChakraInput
                    placeholder="Contraseña"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                  />
                )}

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

        {/* MODAL detalle usuario */}
        <Modal isOpen={isOpenDetalle} onClose={onCloseDetalle} isCentered size={isMobile ? "full" : "md"}>
          <ModalOverlay />
          <ModalContent bg={modal.bg} color={modal.color}>
            <ModalHeader>Detalle de Usuario</ModalHeader>
            <ModalCloseButton />
            <ModalBody maxH="70vh" overflowY="auto">
              {detalleUsuario && (
                <VStack spacing={2} align="stretch">
                  <Text fontWeight="bold">Nombre:</Text>
                  <Text noOfLines={{ base: 1, md: undefined }}>{detalleUsuario.nombre}</Text>
                  <Text fontWeight="bold">Apellido:</Text>
                  <Text noOfLines={{ base: 1, md: undefined }}>{detalleUsuario.apellido}</Text>
                  <Text fontWeight="bold">Teléfono:</Text>
                  <Text>{detalleUsuario.telefono || "No informado"}</Text>
                  <Text fontWeight="bold">Tipo de usuario:</Text>
                  <Text>{detalleUsuario.tipo_usuario || "No informado"}</Text>
                  <Divider />
                  <Text fontWeight="bold">Email:</Text>
                  <Text noOfLines={{ base: 2, md: undefined }}>{detalleUsuario.email}</Text>
                  <Text fontWeight="bold">Username:</Text>
                  <Text noOfLines={{ base: 1, md: undefined }}>{detalleUsuario.username}</Text>
                  <Text fontWeight="bold">Activo:</Text>
                  <Text color={detalleUsuario.is_active ? "green.400" : "red.400"}>
                    {detalleUsuario.is_active ? "Sí" : "No"}
                  </Text>
                  <Text fontWeight="bold">Es staff:</Text>
                  <Text color={detalleUsuario.is_staff ? "green.400" : "red.400"}>
                    {detalleUsuario.is_staff ? "Sí" : "No"}
                  </Text>
                </VStack>
              )}

              {detalleUsuario?.tipo_usuario === "usuario_final" && (
                <Box mt={4} p={4} bg={card.bg} borderRadius="md" borderWidth="1px">
                  <Text fontWeight="bold" mb={2}>Emitir Bonificación Manual</Text>
                  <VStack spacing={3} align="stretch">
                  <ChakraInput
                    placeholder="Motivo"
                    value={motivoBonificacion}
                    onChange={(e) => setMotivoBonificacion(e.target.value)}
                    size="md"
                    fontSize={{ base: "16px", md: "inherit" }}
                  />

                    <Select
                      size={{ base: "sm", md: "md" }}
                      value={tipoTurnoBono}
                      onChange={(e) => setTipoTurnoBono(e.target.value)}
                    >
                      <option value="individual">Individual</option>
                      <option value="x2">2 Personas</option>
                      <option value="x3">3 Personas</option>
                      <option value="x4">4 Personas</option>
                    </Select>
                    <Button
                      isLoading={cargandoBono}
                      w={{ base: "100%", md: "auto" }}
                      onClick={async () => {
                        if (!motivoBonificacion.trim()) {
                          toast.error("El motivo es obligatorio");
                          return;
                        }
                        setCargandoBono(true);
                        const api = axiosAuth(accessToken);
                        try {
                          await api.post("/turnos/bonificaciones/crear-manual/", {
                            usuario_id: detalleUsuario.id,
                            motivo: motivoBonificacion,
                            tipo_turno: tipoTurnoBono,
                          });
                          toast.success("Bonificación emitida correctamente");
                          setMotivoBonificacion("");
                        } catch {
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
            </ModalBody>
            <ModalFooter>
              <Button onClick={onCloseDetalle} size={{ base: "md", md: "lg" }} w={{ base: "100%", md: "auto" }}>
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
