// src/pages/admin/SedesPage.jsx

import React, { useEffect, useState, useContext } from "react";
import Button from "../../components/ui/Button";
import { DeleteIcon, EditIcon, AddIcon } from "@chakra-ui/icons";
import {
  Box,
  Flex,
  Heading,
  Input,
  Text,
  VStack,
  useBreakpointValue,
  IconButton,
  Divider,
  FormControl,
  FormLabel,
  FormErrorMessage
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
  const { accessToken } = useContext(AuthContext);

  const [sedes, setSedes] = useState([]);
  const [form, setForm] = useState({ nombre: "", direccion: "", referente: "", telefono: "" });
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [config, setConfig] = useState({ alias: "", cbu: "", tiposClase: [] });
  const [errors, setErrors] = useState({ alias: "", cbu: "", tiposClase: {} });

  const bg = useBodyBg();
  const cardColors = useCardColors();
  const mutedText = useMutedText();
  const isMobile = useBreakpointValue({ base: true, md: false });

  // 🔹 Cargar sedes
  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);
    api.get("padel/sedes/")
      .then(res => setSedes(res.data.results || res.data))
      .catch(() => toast.error("Error al cargar sedes"));
  }, [accessToken]);

  const resetForm = () => {
    setForm({ nombre: "", direccion: "", referente: "", telefono: "" });
    setConfig({ alias: "", cbu: "", tiposClase: [] });
    setErrors({ alias: "", cbu: "", tiposClase: {} });
    setEditingId(null);
    setShowForm(false);
  };

  const handleNew = () => {
    resetForm();
    setShowForm(true);
  };

  const handleEdit = async (sedeId) => {
    setEditingId(sedeId);
    setShowForm(true);

    const api = axiosAuth(accessToken);
    try {
      const res = await api.get(`padel/sedes/${sedeId}/`);
      const sede = res.data;

      setForm({
        nombre: sede.nombre || "",
        direccion: sede.direccion || "",
        referente: sede.referente || "",
        telefono: sede.telefono || ""
      });

      const conf = sede.configuracion_padel || {};
      setConfig({
        alias: conf.alias || "",
        cbu: conf.cbu_cvu || "",
        tiposClase: conf.tipos_clase || []
      });

    } catch {
      toast.error("Error al cargar datos de sede");
    }
  };

  const validate = () => {
    let valid = true;
    const newErrors = { alias: "", cbu: "", tiposClase: {} };

    if (!config.alias.trim()) {
      newErrors.alias = "El alias es obligatorio";
      valid = false;
    }
    if (!/^\d{22}$/.test(config.cbu)) {
      newErrors.cbu = "El CBU debe tener 22 dígitos";
      valid = false;
    }
    config.tiposClase.forEach((t, idx) => {
      if (!t.nombre || (!t.precio && t.precio !== 0) || isNaN(t.precio)) {
        newErrors.tiposClase[idx] = "Datos inválidos";
        valid = false;
      }
    });

    setErrors(newErrors);
    return valid;
  };

  const handleAddTipoClase = () => {
    setConfig(prev => ({
      ...prev,
      tiposClase: [...prev.tiposClase, { nombre: "", precio: 0 }]
    }));
  };

  const handleRemoveTipoClase = (idx) => {
    setConfig(prev => {
      const tipos = [...prev.tiposClase];
      tipos.splice(idx, 1);
      return { ...prev, tiposClase: tipos };
    });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    if (!validate()) {
      toast.error("Corrige los errores antes de guardar");
      return;
    }
  
    const payload = {
      ...form,
      configuracion_padel: {
        alias: config.alias,
        cbu_cvu: config.cbu,
        tipos_clase: config.tiposClase
      }
    };
  
    const api = axiosAuth(accessToken);
    try {
      if (editingId) {
        await api.put(`padel/sedes/${editingId}/`, payload);
        toast.success("Sede actualizada");
      } else {
        await api.post("padel/sedes/", payload);
        toast.success("Sede creada");
      }
  
      resetForm();
      const res = await api.get("padel/sedes/");
      setSedes(res.data.results || res.data);
  
    } catch (error) {
      console.error("[handleSubmit][Error]", error);
      toast.error("Error al guardar sede");
    }
  };

  const handleDelete = async id => {
    if (!window.confirm("¿Querés eliminar esta sede?")) return;
    const api = axiosAuth(accessToken);
    try {
      await api.delete(`padel/sedes/${id}/`);
      toast.success("Sede eliminada");
      const res = await api.get("padel/sedes/");
      setSedes(res.data.results || res.data);
    } catch {
      toast.error("Error al eliminar sede");
    }
  };

  return (
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
          <Box as="form" onSubmit={handleSubmit} bg={cardColors.bg} p={4} rounded="md" mb={6}>
            <Input placeholder="Nombre" value={form.nombre} onChange={(e) => setForm(prev => ({ ...prev, nombre: e.target.value }))} required mb={4} />
            <Input placeholder="Dirección" value={form.direccion} onChange={(e) => setForm(prev => ({ ...prev, direccion: e.target.value }))} mb={4} />
            <Input placeholder="Referente" value={form.referente} onChange={(e) => setForm(prev => ({ ...prev, referente: e.target.value }))} mb={4} />
            <Input placeholder="Teléfono" value={form.telefono} onChange={(e) => setForm(prev => ({ ...prev, telefono: e.target.value }))} mb={4} />

            <Divider my={4} />
            <Heading size="sm" mb={2}>Configuración de Pago</Heading>
            <FormControl isInvalid={!!errors.alias} mb={3}>
              <FormLabel>Alias</FormLabel>
              <Input value={config.alias} onChange={(e) => setConfig(prev => ({ ...prev, alias: e.target.value }))} />
              {errors.alias && <FormErrorMessage>{errors.alias}</FormErrorMessage>}
            </FormControl>
            <FormControl isInvalid={!!errors.cbu} mb={3}>
              <FormLabel>CBU</FormLabel>
              <Input value={config.cbu} onChange={(e) => setConfig(prev => ({ ...prev, cbu: e.target.value }))} />
              {errors.cbu && <FormErrorMessage>{errors.cbu}</FormErrorMessage>}
            </FormControl>

            <Heading size="sm" mt={4} mb={2}>Tipos de Clase</Heading>
            {config.tiposClase.map((tipo, idx) => (
              <FormControl key={idx} isInvalid={!!errors.tiposClase[idx]} mb={2}>
                <Flex gap={2}>
                  <Input
                    value={tipo.nombre}
                    flex={2}
                    placeholder="Nombre tipo"
                    onChange={(e) => {
                      const nombre = e.target.value;
                      setConfig(prev => {
                        const tipos = [...prev.tiposClase];
                        tipos[idx] = { ...tipos[idx], nombre };
                        return { ...prev, tiposClase: tipos };
                      });
                    }}
                  />
                  <Input
                    type="number"
                    value={tipo.precio}
                    flex={1}
                    placeholder="Precio"
                    onChange={(e) => {
                      const precio = e.target.value;
                      setConfig(prev => {
                        const tipos = [...prev.tiposClase];
                        tipos[idx] = { ...tipos[idx], precio };
                        return { ...prev, tiposClase: tipos };
                      });
                    }}
                  />
                  <IconButton
                    icon={<DeleteIcon />}
                    aria-label="Eliminar tipo"
                    colorScheme="red"
                    size="sm"
                    onClick={() => handleRemoveTipoClase(idx)}
                  />
                </Flex>
                {errors.tiposClase[idx] && <FormErrorMessage>{errors.tiposClase[idx]}</FormErrorMessage>}
              </FormControl>
            ))}
            <Button leftIcon={<AddIcon />} onClick={handleAddTipoClase} size="sm" mt={2}>
              Agregar Tipo de Clase
            </Button>

            <Flex gap={4} mt={4}>
              <Button type="submit" colorScheme="green">{editingId ? "Actualizar" : "Crear"}</Button>
              <Button onClick={resetForm}>Cancelar</Button>
            </Flex>
          </Box>
        )}

        <VStack spacing={4} align="stretch">
          {sedes.map(sede => (
            <Flex key={sede.id} bg={cardColors.bg} p={4} rounded="md" justify="space-between" align="center">
              <Box>
                <Text fontWeight="bold">{sede.nombre}</Text>
                <Text fontSize="sm" color={mutedText}>{sede.direccion}</Text>
                <Text fontSize="sm" color={mutedText}>{sede.referente}</Text>
                <Text fontSize="sm" color={mutedText}>{sede.telefono}</Text>
              </Box>
              <Flex gap={2}>
                <IconButton icon={<EditIcon />} aria-label="Editar sede" onClick={() => handleEdit(sede.id)} size="sm" colorScheme="blue" />
                <IconButton icon={<DeleteIcon />} aria-label="Eliminar sede" onClick={() => handleDelete(sede.id)} size="sm" colorScheme="red" />
              </Flex>
            </Flex>
          ))}
        </VStack>
      </Box>
    </PageWrapper>
  );
};

export default SedesPage;
