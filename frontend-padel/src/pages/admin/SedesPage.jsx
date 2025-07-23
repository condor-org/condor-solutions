import React, { useEffect, useState, useContext } from "react";
import Button from "../../components/ui/Button";
import { DeleteIcon, EditIcon } from "@chakra-ui/icons";
import {
  Box,
  Flex,
  Heading,
  Input,
  Text,
  VStack,
  useBreakpointValue,
  IconButton
} from "@chakra-ui/react";
import { axiosAuth } from "../../utils/axiosAuth";
import { AuthContext } from "../../auth/AuthContext";
import { toast } from "react-toastify";
import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import {
  useBodyBg,
  useCardColors,
  useMutedText
} from "../../components/theme/tokens";

const SedesPage = () => {
  const { accessToken, user, logout } = useContext(AuthContext);

  const [sedes, setSedes] = useState([]);
  const [form, setForm] = useState({
    nombre: "",
    direccion: "",
    referente: "",
    telefono: ""
  });
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const bg = useBodyBg(); // fondo general
  const cardColors = useCardColors(); // fondo y texto de tarjetas
  const mutedText = useMutedText();   // texto secundario

  const isMobile = useBreakpointValue({ base: true, md: false });

  useEffect(() => {
    if (!accessToken) return;

    const apiInstance = axiosAuth(accessToken);

    const loadSedes = () => {
      apiInstance.get("turnos/sedes/")
        .then(res => setSedes(res.data.results || res.data))
        .catch(() => toast.error("Error al cargar sedes"));
    };

    loadSedes();
  }, [accessToken]);

  const handleChange = e => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const resetForm = () => {
    setForm({
      nombre: "",
      direccion: "",
      referente: "",
      telefono: ""
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleNew = () => {
    resetForm();
    setShowForm(true);
  };

  const handleSubmit = async e => {
    e.preventDefault();
    const apiInstance = axiosAuth(accessToken);

    try {
      if (editingId) {
        await apiInstance.put(`turnos/sedes/${editingId}/`, form);
        toast.success("Sede actualizada");
      } else {
        await apiInstance.post("turnos/sedes/", form);
        toast.success("Sede creada");
      }

      resetForm();
      const res = await apiInstance.get("turnos/sedes/");
      setSedes(res.data.results || res.data);

    } catch {
      toast.error("Error al guardar sede");
    }
  };

  const handleEdit = sede => {
    setEditingId(sede.id);
    setForm({
      nombre: sede.nombre || "",
      direccion: sede.direccion || "",
      referente: sede.referente || "",
      telefono: sede.telefono || ""
    });
    setShowForm(true);
  };

  const handleDelete = async id => {
    if (!window.confirm("¿Querés eliminar esta sede?")) return;

    const apiInstance = axiosAuth(accessToken);

    try {
      await apiInstance.delete(`turnos/sedes/${id}/`);
      toast.success("Sede eliminada");

      const res = await apiInstance.get("turnos/sedes/");
      setSedes(res.data.results || res.data);

      if (editingId === id) resetForm();

    } catch {
      toast.error("Error al eliminar sede");
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
        <Box flex="1" p={8} bg={bg} color={cardColors.color}>
          <Heading size="md" mb={4}>Sedes</Heading>

          <Flex justify="flex-end" mb={6}>
            <Button onClick={handleNew} size={isMobile ? "md" : "lg"}>
              Crear nueva sede
            </Button>
          </Flex>

          {showForm && (
            <Box
              as="form"
              onSubmit={handleSubmit}
              bg={cardColors.bg}
              color={cardColors.color}
              p={4}
              rounded="md"
              mb={6}
            >
              <Input
                name="nombre"
                placeholder="Nombre"
                value={form.nombre}
                onChange={handleChange}
                required
                mb={4}
              />
              <Input
                name="direccion"
                placeholder="Dirección"
                value={form.direccion}
                onChange={handleChange}
                mb={4}
              />
              <Input
                name="referente"
                placeholder="Referente"
                value={form.referente}
                onChange={handleChange}
                mb={4}
              />
              <Input
                name="telefono"
                placeholder="Teléfono"
                value={form.telefono}
                onChange={handleChange}
                mb={4}
              />

              <Flex gap={4}>
                <Button type="submit" colorScheme="green">
                  {editingId ? "Actualizar" : "Crear"}
                </Button>
                <Button onClick={resetForm}>Cancelar</Button>
              </Flex>
            </Box>
          )}

          <VStack spacing={4} align="stretch">
            {sedes.map(sede => (
              <Flex
                key={sede.id}
                bg={cardColors.bg}
                color={cardColors.color}
                p={4}
                rounded="md"
                justify="space-between"
                align="center"
              >
                <Box>
                  <Text fontWeight="bold">{sede.nombre}</Text>
                  <Text fontSize="sm" color={mutedText}>{sede.direccion}</Text>
                  <Text fontSize="sm" color={mutedText}>{sede.referente}</Text>
                  <Text fontSize="sm" color={mutedText}>{sede.telefono}</Text>
                </Box>

                <Flex gap={2} mt={isMobile ? 2 : 0}>
                  <IconButton
                    icon={<EditIcon />}
                    aria-label="Editar sede"
                    onClick={() => handleEdit(sede)}
                    size="sm"
                    colorScheme="blue"
                  />
                  <IconButton
                    icon={<DeleteIcon />}
                    aria-label="Eliminar sede"
                    onClick={() => handleDelete(sede.id)}
                    size="sm"
                    colorScheme="red"
                  />
                </Flex>
              </Flex>
            ))}
          </VStack>
        </Box>
      </PageWrapper>
    </>
  );
};

export default SedesPage;
