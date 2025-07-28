// src/pages/admin/UsuariosPage.jsx

import React, { useEffect, useState, useContext } from "react";
import {
  Box, Flex, Heading, Text, VStack, Modal, ModalOverlay, ModalContent,
  ModalHeader, ModalCloseButton, ModalBody, ModalFooter, useDisclosure,
  IconButton, Switch, Stack, useBreakpointValue, Divider, useColorModeValue, Select
} from "@chakra-ui/react";
import { DeleteIcon, EditIcon } from "@chakra-ui/icons";
import Sidebar from "../../components/layout/Sidebar";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
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
  const { user, logout, accessToken } = useContext(AuthContext);
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
  

  useEffect(() => {
    if (!accessToken) return;
    reloadUsuarios();
  }, [accessToken]);

  const reloadUsuarios = () => {
    const api = axiosAuth(accessToken);
    api.get("auth/usuarios/")
      .then(res => setUsuarios(res.data.results || res.data))
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
    setActivo(u.is_active);
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
      if (password.trim()) {
        data.password = password;
      }
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
          : Object.values(errorResponse).flat().join(" | ") || "Error al guardar usuario";
  
      toast.error(errorMessage);
    }
  };
  
  
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
        <Box flex="1" p={[2, 4, 8]} bg={bg} color={card.color}>
          <Heading size="md" mb={4}>Administrar Usuarios</Heading>
          <Flex justify="flex-end" mb={4}>
            <Button onClick={openForCreate} size={isMobile ? "md" : "lg"}>
              Agregar Usuario
            </Button>
          </Flex>
  
          {usuarios.length === 0 ? (
            <Text color={mutedText} textAlign="center">No hay usuarios cargados.</Text>
          ) : (
            <VStack spacing={3} align="stretch">
              {usuarios.map((u) => (
                <Flex
                  key={u.id}
                  bg={card.bg}
                  color={card.color}
                  p={4}
                  rounded="md"
                  justify="space-between"
                  align="center"
                  boxShadow="md"
                  direction={isMobile ? "column" : "row"}
                  _hover={{ cursor: "pointer", bg: card.iconColor }}
                  onClick={e => {
                    if (e.target.closest("button")) return;
                    handleOpenDetalle(u);
                  }}
                >
                  <Box>
                    <Text fontWeight="bold">{u.nombre} {u.apellido}</Text>
                    <Text fontSize="sm" color={mutedText}>{u.email}</Text>
                    <Text fontSize="sm" color={u.is_active ? "green.400" : "red.400"}>
                      {u.is_active ? "Activo" : "Inactivo"}
                    </Text>
                  </Box>
                  <Flex gap={2} mt={isMobile ? 2 : 0}>
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
                  </Flex>
                </Flex>
              ))}
            </VStack>
          )}
  
          {/* MODAL crear/editar */}
          <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm(); }} isCentered size={isMobile ? "full" : "md"}>
            <ModalOverlay />
            <ModalContent bg={modal.bg} color={modal.color}>
              <ModalHeader>{editingId ? "Editar Usuario" : "Agregar Usuario"}</ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                <form id="usuario-form" onSubmit={handleSubmit}>
                  <VStack spacing={4} align="stretch">
                    <Input label="Nombre" value={nombre} onChange={e => setNombre(e.target.value)} />
                    <Input label="Apellido" value={apellido} onChange={e => setApellido(e.target.value)} />
                    <Input label="Teléfono" value={telefono} onChange={e => setTelefono(e.target.value)} />
                    <Select bg={input.bg} color={input.color} value={tipoUsuario} onChange={e => setTipoUsuario(e.target.value)}>
                      <option value="admin_cliente">Admin del Cliente</option>
                      <option value="empleado_cliente">Empleado del Cliente</option>
                      <option value="usuario_final">Usuario Final</option>
                    </Select>
                    <Input label="Email" value={email} onChange={e => setEmail(e.target.value)} type="email" />
                    {!editingId && (
                      <Input label="Contraseña" value={password} onChange={e => setPassword(e.target.value)} type="password" autoComplete="new-password" />
                    )}
                    <Stack direction="row" align="center">
                      <Text>Activo</Text>
                      <Switch isChecked={activo} onChange={e => setActivo(e.target.checked)} colorScheme="green" />
                    </Stack>
                  </VStack>
                </form>
              </ModalBody>
              <ModalFooter>
                <Button type="submit" form="usuario-form" size="lg" mr={3}>
                  {editingId ? "Guardar" : "Crear"}
                </Button>
                <Button variant="secondary" onClick={() => { onClose(); resetForm(); }} size="lg">
                  Cancelar
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
  
          {/* MODAL detalle usuario */}
          <Modal isOpen={isOpenDetalle} onClose={onCloseDetalle} isCentered size={isMobile ? "full" : "md"}>
            <ModalOverlay />
            <ModalContent bg={modal.bg} color={modal.color}>
              <ModalHeader>Detalle de Usuario</ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                {detalleUsuario && (
                  <VStack spacing={2} align="stretch">
                    <Text fontWeight="bold">Nombre:</Text>
                    <Text>{detalleUsuario.nombre}</Text>
                    <Text fontWeight="bold">Apellido:</Text>
                    <Text>{detalleUsuario.apellido}</Text>
                    <Text fontWeight="bold">Teléfono:</Text>
                    <Text>{detalleUsuario.telefono || "No informado"}</Text>
                    <Text fontWeight="bold">Tipo de usuario:</Text>
                    <Text>{detalleUsuario.tipo_usuario || "No informado"}</Text>
                    <Divider />
                    <Text fontWeight="bold">Email:</Text>
                    <Text>{detalleUsuario.email}</Text>
                    <Text fontWeight="bold">Username:</Text>
                    <Text>{detalleUsuario.username}</Text>
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
              </ModalBody>
              <ModalFooter>
                <Button onClick={onCloseDetalle} size="lg">
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

export default UsuariosPage;
