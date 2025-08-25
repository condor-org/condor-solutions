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
  FormErrorMessage,
  Select,
  Alert,
  AlertIcon
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

const ABONO_OPCIONES = [
  { codigo: "x1", nombre: "Abono Individual" },
  { codigo: "x2", nombre: "Abono 2 Personas" },
  { codigo: "x3", nombre: "Abono 3 Personas" },
  { codigo: "x4", nombre: "Abono 4 Personas" },
];

const CLASE_OPCIONES = [
  { codigo: "x1", nombre: "Individual" },
  { codigo: "x2", nombre: "2 Personas" },
  { codigo: "x3", nombre: "3 Personas" },
  { codigo: "x4", nombre: "4 Personas" },
];

const SedesPage = () => {
  
  const { accessToken } = useContext(AuthContext);

  const [sedes, setSedes] = useState([]);
  const [form, setForm] = useState({ nombre: "", direccion: "", referente: "", telefono: "" });
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [config, setConfig] = useState({ alias: "", cbu: "", tiposClase: [], tiposAbono: [] });
  const [errors, setErrors] = useState({ alias: "", cbu: "", tiposClase: {}, tiposAbono: {} });

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
    setConfig({ alias: "", cbu: "", tiposClase: [], tiposAbono: [] });
    setErrors({ alias: "", cbu: "", tiposClase: {}, tiposAbono: {} });
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

      // Tipos de Clase: normalizo y agrego nombre legible desde el código
      const tiposClase = (conf.tipos_clase || []).map(t => ({
        ...(t.id ? { id: t.id } : {}),
        codigo: t.codigo,
        nombre: (CLASE_OPCIONES.find(o => o.codigo === t.codigo)?.nombre) || t.codigo,
        precio: String(t.precio ?? ""),
        activo: !!t.activo,
      }));

      // Tipos de Abono: normalizo y agrego nombre legible desde el código
      const tiposAbono = (conf.tipos_abono || []).map(t => ({
        ...(t.id ? { id: t.id } : {}),
        codigo: t.codigo,
        nombre: (ABONO_OPCIONES.find(o => o.codigo === t.codigo)?.nombre) || t.codigo,
        precio: String(t.precio ?? ""),
        activo: !!t.activo,
      }));

      setConfig({
        alias: conf.alias || "",
        cbu: conf.cbu_cvu || "",
        tiposClase,
        tiposAbono,
      });


      
    } catch {
      toast.error("Error al cargar datos de sede");
    }
  };

  const validate = () => {
    let valid = true;
    const newErrors = { alias: "", cbu: "", tiposClase: {}, tiposAbono: {} };
  
    if (!config.alias.trim()) { newErrors.alias = "El alias es obligatorio"; valid = false; }
    if (!/^\d{22}$/.test(config.cbu)) { newErrors.cbu = "El CBU debe tener 22 dígitos"; valid = false; }
  
    // Tipos de Clase
    (config.tiposClase || []).forEach((t, idx) => {
      const inval = !t?.codigo || t?.precio === "" || isNaN(Number(t?.precio));
      if (inval) { newErrors.tiposClase[idx] = "Datos inválidos"; valid = false; }
    });
  
    // Tipos de Abono
    (config.tiposAbono || []).forEach((t, idx) => {
      const inval = !t?.codigo || t?.precio === "" || isNaN(Number(t?.precio));
      if (inval) { newErrors.tiposAbono[idx] = "Datos inválidos"; valid = false; }
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
        tipos_clase: (config.tiposClase || []).map(t => ({
          ...(t.id ? { id: t.id } : {}),
          codigo: t.codigo,
          precio: t.precio,
          activo: t.activo ?? true,
        })),
        tipos_abono: (config.tiposAbono || []).map(t => ({
          ...(t.id ? { id: t.id } : {}),
          codigo: t.codigo,
          precio: t.precio,
          activo: t.activo ?? true,
        })),
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
          { label: "Cancelaciones", path: "/admin/cancelaciones" },
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
                <Flex gap={2} wrap="wrap">
                  <Select
                    value={tipo.codigo || ""}
                    flex="2"
                    placeholder="Seleccionar tipo de clase"
                    onChange={(e) => {
                      const codigo = e.target.value;
                      const opcion = CLASE_OPCIONES.find(o => o.codigo === codigo);
                      setConfig(prev => {
                        const arr = [...prev.tiposClase];
                        arr[idx] = { ...arr[idx], codigo, nombre: opcion?.nombre || "" };
                        return { ...prev, tiposClase: arr };
                      });
                    }}
                  >
                    {CLASE_OPCIONES.map(op => (
                      <option key={op.codigo} value={op.codigo}>{op.nombre}</option>
                    ))}
                  </Select>

                  <Input
                    type="number"
                    value={tipo.precio}
                    flex="1"
                    placeholder="Precio"
                    onChange={(e) => {
                      const precio = e.target.value;
                      setConfig(prev => {
                        const arr = [...prev.tiposClase];
                        arr[idx] = { ...arr[idx], precio };
                        return { ...prev, tiposClase: arr };
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

            <Button leftIcon={<AddIcon />} onClick={() => {
              setConfig(prev => ({
                ...prev,
                tiposClase: [...prev.tiposClase, { codigo: "", nombre: "", precio: 0, activo: true }]
              }));
            }} size="sm" mt={2}>
              Agregar Tipo de Clase
            </Button>


            <Heading size="sm" mt={6} mb={2}>Tipos de Abono</Heading>

            {(config.tiposAbono?.length ?? 0) === 0 && (
              <Alert status="warning" mb={3} rounded="md">
                <AlertIcon />
                Ningún abono configurado. Agregá al menos uno para habilitar la venta de abonos en esta sede.
              </Alert>
            )}

            {config.tiposAbono.map((tipo, idx) => (
              <FormControl key={idx} isInvalid={!!errors.tiposAbono[idx]} mb={2}>
                <Flex gap={2} wrap="wrap">
                <Select
                  value={tipo.codigo || ""}
                  flex="2"
                  placeholder="Seleccionar tipo de abono"
                  onChange={(e) => {
                    const codigo = e.target.value;
                    const opcion = ABONO_OPCIONES.find(o => o.codigo === codigo);
                    setConfig(prev => {
                      const arr = [...prev.tiposAbono];
                      arr[idx] = {
                        ...arr[idx],
                        codigo,
                        nombre: opcion?.nombre || "",
                      };
                      return { ...prev, tiposAbono: arr };
                    });
                  }}
                >
                  {ABONO_OPCIONES.map(op => (
                    <option key={op.codigo} value={op.codigo}>
                      {op.nombre}
                    </option>
                  ))}
                </Select>

                  <Input
                    type="number"
                    value={tipo.precio}
                    flex="1"
                    placeholder="Precio mensual del abono"
                    onChange={(e) => {
                      const precio = e.target.value;
                      setConfig(prev => {
                        const arr = [...prev.tiposAbono];
                        arr[idx] = { ...arr[idx], precio };
                        return { ...prev, tiposAbono: arr };
                      });
                    }}
                  />
                  <Select
                    value={tipo.activo ? "1" : "0"}
                    flex="1"
                    onChange={(e) => {
                      const activo = e.target.value === "1";
                      setConfig(prev => {
                        const arr = [...prev.tiposAbono];
                        arr[idx] = { ...arr[idx], activo };
                        return { ...prev, tiposAbono: arr };
                      });
                    }}
                  >
                    <option value="1">Activo</option>
                    <option value="0">Inactivo</option>
                  </Select>
                  <IconButton
                    icon={<DeleteIcon />}
                    aria-label="Eliminar tipo"
                    colorScheme="red"
                    size="sm"
                    onClick={() => {
                      setConfig(prev => {
                        const arr = [...prev.tiposAbono];
                        arr.splice(idx, 1);
                        return { ...prev, tiposAbono: arr };
                      });
                    }}
                  />
                </Flex>
                {errors.tiposAbono[idx] && <FormErrorMessage>{errors.tiposAbono[idx]}</FormErrorMessage>}
              </FormControl>
            ))}

            <Button leftIcon={<AddIcon />} onClick={() => {
              setConfig(prev => ({
                ...prev,
                tiposAbono: [...prev.tiposAbono, { codigo: "", nombre: "", precio: 0, activo: true }]
              }));
            }} size="sm" mt={2}>
              Agregar Tipo de Abono
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
