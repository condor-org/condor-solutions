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
  { codigo: "personalizado", nombre: "Personalizado" },
];

const ReservarAbonoAdmin = () => {
  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);
  const toast = useToast();

  const card = useCardColors();
  const input = useInputColors();
  const muted = useMutedText();
  const hoverBg = useColorModeValue("gray.100", "gray.700");

  // ===== ESTADOS DEL COMPONENTE =====
  // Estados de datos del backend (arrays que se llenan con llamadas HTTP)
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  
  // Estados de filtros del usuario (valores seleccionados en los dropdowns)
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
  const [tiposClase, setTiposClase] = useState([]);
  const [diasDisponibles, setDiasDisponibles] = useState([]);
  
  // configuración personalizada
  const [configuracionPersonalizada, setConfiguracionPersonalizada] = useState([]);

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

  // profesores - cargar todos los profesores de la sede
  useEffect(() => {
    if (!api || !sedeId) { 
      setProfesores([]); 
      setProfesorId(""); // Limpiar selección de profesor
      return; 
    }
    
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setProfesores(Array.isArray(data) ? data : []);
      })
      .catch(e => { 
        console.error("[AbonoAdmin] profesores error:", e); 
        setProfesores([]); 
      });
  }, [api, sedeId]);

  // 3) Filtrar días disponibles basado en la disponibilidad del profesor
  useEffect(() => {
    if (!profesorId || !sedeId) {
      setDiasDisponibles([]);
      setDiaSemana(""); // Limpiar selección de día
      return;
    }

    const profesor = profesores.find(p => String(p.id) === String(profesorId));
    if (!profesor?.disponibilidades) {
      setDiasDisponibles([]);
      setDiaSemana(""); // Limpiar selección de día
      return;
    }

    // Filtrar disponibilidades para la sede actual
    const disponibilidadesSede = profesor.disponibilidades.filter(
      disp => String(disp.lugar) === String(sedeId)
    );

    // Extraer días de la semana únicos
    const diasUnicos = [...new Set(disponibilidadesSede.map(disp => disp.dia_semana))];
    setDiasDisponibles(diasUnicos);
    setDiaSemana(""); // Limpiar selección de día
  }, [profesorId, sedeId, profesores]);

  useEffect(() => {
    if (!api || !sedeId) { setTiposAbono([]); return; }
    api.get(`padel/tipos-abono/?sede_id=${sedeId}`)
      .then(res => setTiposAbono(res?.data?.results ?? res?.data ?? []))
      .catch(e => { console.error("[AbonoAdmin] tiposAbono error:", e); setTiposAbono([]); });
  }, [api, sedeId]);

  useEffect(() => {
    if (!api || !sedeId) { 
      console.log('🔍 DEBUG tiposClase - No hay api o sedeId:', { api: !!api, sedeId });
      setTiposClase([]); 
      return; 
    }
    
    console.log('🔍 DEBUG tiposClase - Cargando tipos de clase para sede:', sedeId);
    
    api.get(`padel/tipos-clase/?sede_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        console.log('🔍 DEBUG tiposClase - Respuesta del backend:', data);
        setTiposClase(data);
      })
      .catch(e => { 
        console.error("🚨 DEBUG tiposClase - Error:", e); 
        setTiposClase([]); 
      });
  }, [api, sedeId]);

  // 4) Cargar abonos disponibles
  // GET /api/padel/abonos/disponibles/ → Abonos libres para reservar
  // - Ya no usa tipo_codigo: el backend calculará precios dinámicamente
  // - Para personalizados: procesa datos para mostrar solo horas disponibles
  // - Para normales: usa los datos tal como vienen del backend
  useEffect(() => {
    const ready = api && sedeId && profesorId && (diaSemana !== "") && tipoAbono;
    if (!ready) { setAbonosLibres([]); return; }

    const params = new URLSearchParams({
      sede_id: String(sedeId),
      prestador_id: String(profesorId),
      dia_semana: String(diaSemana),
      anio: String(anioActual),
      mes: String(mesActual),
    });
    
    // Ya no necesitamos tipo_codigo para obtener disponibilidad
    // El backend calculará precios dinámicamente
    
    if (horaFiltro) params.append("hora", horaFiltro);

    setLoadingDisponibles(true);
    api.get(`padel/abonos/disponibles/?${params.toString()}`)
      .then(res => {
        let data = res?.data?.results ?? res?.data ?? [];
        
        if (tipoAbono === "personalizado") {
          // Para abonos personalizados, mostrar todas las horas disponibles
          // pero marcar cada una como "Personalizado" sin tipo_clase específico
          data = data.map(item => ({
            hora: item.hora,
            tipo_clase: null // No hay tipo específico, se configurará en el modal
          }));
        } else {
          // Para abonos normales, usar los datos tal como vienen del backend
          data = Array.isArray(data) ? data : [];
        }
        
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

  // ======= CONFIGURACIÓN PERSONALIZADA =======
  const agregarTipoClase = () => {
    console.log('🔍 DEBUG agregarTipoClase - tiposClase.length:', tiposClase.length);
    console.log('🔍 DEBUG agregarTipoClase - tiposClase:', tiposClase);
    
    if (tiposClase.length === 0) {
      console.log('🚨 DEBUG agregarTipoClase - No hay tipos de clase disponibles');
      return;
    }
    
    const nuevoTipo = {
      tipo_clase_id: tiposClase[0].id,
      cantidad: 1,
      codigo: tiposClase[0].codigo
    };
    
    console.log('🔍 DEBUG agregarTipoClase - nuevoTipo:', nuevoTipo);
    console.log('🔍 DEBUG agregarTipoClase - configuracionPersonalizada actual:', configuracionPersonalizada);
    
    setConfiguracionPersonalizada([...configuracionPersonalizada, nuevoTipo]);
  };

  const removerTipoClase = (index) => {
    const nuevaConfig = configuracionPersonalizada.filter((_, i) => i !== index);
    setConfiguracionPersonalizada(nuevaConfig);
  };

  const actualizarTipoClase = (index, campo, valor) => {
    const nuevaConfig = [...configuracionPersonalizada];
    nuevaConfig[index] = { ...nuevaConfig[index], [campo]: valor };
    
    // Si se cambia el tipo_clase_id, actualizar también el codigo
    if (campo === 'tipo_clase_id') {
      const tipoClase = tiposClase.find(tc => tc.id === valor);
      if (tipoClase) {
        nuevaConfig[index].codigo = tipoClase.codigo;
      }
    }
    
    setConfiguracionPersonalizada(nuevaConfig);
  };

  const calcularMontoPersonalizado = () => {
    return configuracionPersonalizada.reduce((total, config) => {
      const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
      if (tipoClase) {
        return total + (Number(tipoClase.precio) * config.cantidad);
      }
      return total;
    }, 0);
  };

  // Función para mapear tipo de abono a tipo de clase
  const mapearTipoAbonoATipoClase = (tipoAbono) => {
    console.log('🔍 DEBUG mapearTipoAbonoATipoClase:', { tipoAbono, tiposClase: tiposClase.length });
    
    // El tipoAbono ya viene como código (x1, x2, x3, x4) desde el dropdown
    // Solo necesitamos encontrar el tipo de clase que coincida con ese código
    const tipoClase = tiposClase.find(tc => tc.codigo === tipoAbono);
    console.log('🔍 DEBUG tipoClase encontrado:', { tipoAbono, tipoClase });
    
    return tipoClase?.id;
  };

  // 12) Cálculo de turnos disponibles
  // Cuenta turnos reales disponibles para el día y hora específicos del mes
  const calcularMaximoTurnos = () => {
    // Calcular turnos del mes independientemente de abonosLibres
    const hoy = new Date();
    const anio = hoy.getFullYear();
    const mes = hoy.getMonth() + 1;
    const diaSemanaSeleccionado = Number(diaSemana) || 0; // 0 = lunes
    
    // Contar cuántos turnos quedan en el mes para el día de la semana seleccionado
    const diasEnMes = new Date(anio, mes, 0).getDate();
    let diasRestantes = 0;
    
    for (let dia = 1; dia <= diasEnMes; dia++) {
      const fecha = new Date(anio, mes - 1, dia);
      if (fecha.getDay() === diaSemanaSeleccionado && fecha >= hoy) {
        diasRestantes++;
      }
    }
    
    return diasRestantes;
  };

  // Calcular turnos ya asignados en la configuración personalizada
  const calcularTurnosAsignados = () => {
    return configuracionPersonalizada.reduce((total, config) => {
      return total + (config.cantidad || 0);
    }, 0);
  };

  // Calcular turnos restantes disponibles
  const calcularTurnosRestantes = () => {
    return calcularMaximoTurnos() - calcularTurnosAsignados();
  };

  // ======= ACCIONES =======
  const handleClickAbono = (item) => {
    if (!usuarioId) {
      toast({ title: "Seleccioná un usuario", status: "warning", duration: 3000 });
      return;
    }
    setAbonoSeleccionado(item);
    confirmDisc.onOpen();
  };

  // 19) Confirmación de asignación
  // Procesa asignación directa sin validaciones de pago
  const confirmarAsignacion = async () => {
    if (!api || !abonoSeleccionado || !usuarioId) return;

    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("sede", String(sedeId));
      fd.append("prestador", String(profesorId));
      fd.append("dia_semana", String(diaSemana));
      fd.append("hora", abonoSeleccionado?.hora);
      fd.append("anio", anioActual);
      fd.append("mes", mesActual);
      fd.append("usuario_id", String(usuarioId));
      fd.append("forzar_admin", "true");

      if (tipoAbono === "personalizado") {
        // Para abonos personalizados
        console.log('🔍 DEBUG abono personalizado - configuracionPersonalizada:', configuracionPersonalizada);
        console.log('🔍 DEBUG abono personalizado - tiposClase:', tiposClase);
        console.log('🔍 DEBUG abono personalizado - calcularMaximoTurnos:', calcularMaximoTurnos());
        
        const monto = calcularMontoPersonalizado();
        console.log('🔍 DEBUG abono personalizado - monto calculado:', monto);
        
        fd.append("monto", String(monto));
        fd.append("monto_esperado", String(monto));
        fd.append("configuracion_personalizada", JSON.stringify(configuracionPersonalizada));
      } else {
        // Para abonos normales
        const tipoClaseId = mapearTipoAbonoATipoClase(tipoAbono);
        console.log('🔍 DEBUG abono normal - tipoAbono:', tipoAbono, 'tipoClaseId:', tipoClaseId);
        
        if (!tipoClaseId) {
          throw new Error(`No se encontró tipo de clase para: ${tipoAbono}`);
        }
        
        const tipoClase = tiposClase.find(tc => tc.id === tipoClaseId);
        const monto = tipoClase ? Number(tipoClase.precio) * calcularMaximoTurnos() : 0;
        
        console.log('🔍 DEBUG abono normal - monto calculado:', monto);
        
        fd.append("tipo_clase", tipoClaseId);
        fd.append("monto", String(monto));
        fd.append("monto_esperado", String(monto));
      }

      await api.post("padel/abonos/reservar/", fd, { headers: { "Content-Type": "multipart/form-data" } });
      
      toast({
        title: "Abono asignado",
        description: `Asignado a ${usuarioSeleccionado?.email || usuarioSeleccionado?.nombre || "usuario"}.`,
        status: "success", duration: 4500,
      });
      
      confirmDisc.onClose();
      setAbonoSeleccionado(null);
      setConfiguracionPersonalizada([]); // Limpiar configuración
    } catch (e) {
      const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || "No se pudo asignar el abono";
      console.error("[AbonoAdmin] ERROR reservar:", e);
      toast({ title: "Error", description: msg, status: "error", duration: 5000 });
    } finally {
      setEnviando(false);
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
          { label: "Agenda", path: "/admin/agenda" },
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
                onChange={(e) => {
                  setProfesorId(e.target.value);
                  setDiaSemana(""); // Limpiar día al cambiar profesor
                }}
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
              <FormLabel color={muted}>
                Día de la semana
                {profesorId && diasDisponibles.length > 0 && (
                  <Text as="span" fontSize="xs" color={muted} ml={2}>
                    (solo días disponibles)
                  </Text>
                )}
              </FormLabel>
              <Select
                value={diaSemana}
                placeholder="Seleccioná"
                onChange={(e) => setDiaSemana(e.target.value)}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
              >
                {DIAS.filter(d => !profesorId || diasDisponibles.includes(d.value)).map((d) => (
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
              <FormLabel color={muted}>
                Hora {tipoAbono === "personalizado" ? "(requerido)" : "(opcional)"}
              </FormLabel>
              <Select
                value={horaFiltro}
                onChange={(e) => setHoraFiltro(e.target.value)}
                bg={input.bg}
                borderColor={input.border}
                size={{ base: "md", md: "sm" }}
                rounded="md"
                isRequired={tipoAbono === "personalizado"}
              >
                <option value="">{tipoAbono === "personalizado" ? "Seleccioná una hora" : "Todas"}</option>
                {Array.from({ length: 15 }).map((_, i) => {
                  const h = (8 + i).toString().padStart(2, "0") + ":00:00";
                  return <option key={h} value={h}>{h.slice(0, 5)}</option>;
                })}
              </Select>
            </FormControl>
          </Stack>

          <Divider my={2} />

          {/* Configuración personalizada */}
          {tipoAbono === "personalizado" && (
            <Box mb={6} p={4} bg={card.bg} rounded="lg" borderWidth="1px" borderColor={input.border}>
              <HStack justify="space-between" mb={3}>
                <VStack align="start" spacing={1}>
                  <Text fontWeight="semibold">Configuración del Abono Personalizado</Text>
                  <Text fontSize="sm" color={muted}>
                    Total de turnos disponibles: {calcularMaximoTurnos()} | 
                    Turnos asignados: {calcularTurnosAsignados()} | 
                    Restantes: {calcularTurnosRestantes()}
                  </Text>
                </VStack>
                <Button
                  size="sm"
                  onClick={agregarTipoClase}
                  isDisabled={
                    tiposClase.length === 0 || 
                    calcularTurnosRestantes() <= 0 ||
                    (tipoAbono === "personalizado" && !horaFiltro)
                  }
                >
                  Agregar Tipo de Clase
                </Button>
              </HStack>
              
              {!horaFiltro && tipoAbono === "personalizado" ? (
                <Text color="orange.500" textAlign="center" py={4}>
                  ⚠️ Seleccioná una hora específica para configurar el abono personalizado.
                </Text>
              ) : configuracionPersonalizada.length === 0 ? (
                <Text color={muted} textAlign="center" py={4}>
                  No hay tipos de clase configurados. Agregá al menos uno para continuar.
                </Text>
              ) : (
                <VStack align="stretch" spacing={3}>
                  {configuracionPersonalizada.map((config, index) => {
                    const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
                    return (
                      <HStack key={index} spacing={3} align="end">
                        <FormControl flex={2}>
                          <FormLabel fontSize="sm">Tipo de Clase</FormLabel>
                          <Select
                            value={config.tipo_clase_id}
                            onChange={(e) => actualizarTipoClase(index, 'tipo_clase_id', Number(e.target.value))}
                            bg={input.bg}
                            borderColor={input.border}
                            size="sm"
                          >
                          {tiposClase.map(tc => (
                            <option key={tc.id} value={tc.id}>
                              {tc.nombre || LABELS[tc.codigo]}
                            </option>
                          ))}
                          </Select>
                        </FormControl>
                        
                        <FormControl flex={1}>
                          <FormLabel fontSize="sm">Cantidad de clases de este tipo</FormLabel>
                          <Select
                            value={config.cantidad}
                            onChange={(e) => actualizarTipoClase(index, 'cantidad', Number(e.target.value))}
                            bg={input.bg}
                            borderColor={input.border}
                            size="sm"
                          >
                            {Array.from({ length: Math.min(config.cantidad + calcularTurnosRestantes(), calcularMaximoTurnos()) }, (_, i) => i + 1).map(num => (
                              <option key={num} value={num}>
                                {num} {num === 1 ? 'clase' : 'clases'}
                              </option>
                            ))}
                          </Select>
                        </FormControl>
                        
                      <Box flex={1}>
                        <Text fontSize="sm" color={muted}>Cantidad</Text>
                        <Text fontWeight="semibold">
                          {config.cantidad} {config.cantidad === 1 ? 'clase' : 'clases'}
                        </Text>
                      </Box>
                        
                      </HStack>
                    );
                  })}
                  
                  <Divider />
                  
                <HStack justify="space-between" align="center">
                  <VStack align="start" spacing={1}>
                    <Text fontWeight="bold" fontSize="lg">Configuración del Abono:</Text>
                    {calcularTurnosAsignados() > calcularMaximoTurnos() && (
                      <Text fontSize="sm" color="red.500">
                        ⚠️ Excede el límite de turnos disponibles
                      </Text>
                    )}
                  </VStack>
                  <VStack align="end" spacing={1}>
                    <Text fontWeight="bold" fontSize="lg" color={calcularTurnosAsignados() > calcularMaximoTurnos() ? "red.500" : "blue.500"}>
                      {configuracionPersonalizada.reduce((total, config) => total + config.cantidad, 0)} turnos configurados
                    </Text>
                    <Text fontSize="sm" color={muted}>
                      de {calcularMaximoTurnos()} disponibles
                    </Text>
                  </VStack>
                </HStack>
                </VStack>
              )}
            </Box>
          )}

          {/* Abonos libres */}
          <Box>
            <Text fontWeight="semibold" mb={2}>
              Abonos libres {loadingDisponibles ? "— cargando..." : ""}
            </Text>
            {(sedeId && profesorId && diaSemana !== "" && !tipoAbono) && (
              <Text color={muted} mb={2}>Elegí un tipo de abono para ver disponibilidad.</Text>
            )}
            {tipoAbono === "personalizado" && configuracionPersonalizada.length === 0 && (
              <Text color={muted} mb={2}>Configurá al menos un tipo de clase para continuar.</Text>
            )}
            {!loadingDisponibles && abonosLibres.length === 0 && (sedeId && profesorId && diaSemana !== "") ? (
              <Text color={muted}>No hay abonos libres para los filtros seleccionados.</Text>
            ) : null}

            <VStack align="stretch" spacing={3}>
              {tipoAbono === "personalizado" ? (
                // Para abonos personalizados, mostrar solo 1 elemento
                <Box
                  key="personalizado"
                  p={3}
                  bg={card.bg}
                  rounded="md"
                  borderWidth="1px"
                  borderColor={input.border}
                  _hover={{ boxShadow: "lg", cursor: usuarioId ? "pointer" : "not-allowed", bg: hoverBg }}
                  onClick={() => handleClickAbono({ hora: horaFiltro || "Personalizado" })}
                >
                  <HStack justify="space-between" align="center">
                    <Box>
                      <Text fontWeight="semibold">
                        {DIAS.find(d => String(d.value) === String(diaSemana))?.label} · {horaFiltro ? horaFiltro.slice(0, 5) : "Personalizado"} hs
                      </Text>
                      <HStack mt={1} spacing={2}>
                        <Badge colorScheme="purple">Personalizado</Badge>
                        <Badge colorScheme="blue">Asignación gratuita</Badge>
                      </HStack>
                    </Box>
                    <Button
                      variant="primary" 
                      isDisabled={
                        !usuarioId || 
                        configuracionPersonalizada.length === 0 ||
                        calcularTurnosAsignados() > calcularMaximoTurnos()
                      }
                    >
                      Asignar
                    </Button>
                  </HStack>
                </Box>
              ) : (
                // Para abonos normales, mostrar todos los disponibles
                abonosLibres.map((item, idx) => {
                  const codigo = item?.tipo_clase?.codigo;
                  const pAbono = precioAbonoPorCodigo[codigo];
                  // Para admin no mostramos precios
                  const montoMostrar = 0;
                  
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
                            <Badge colorScheme="blue">
                              Asignación gratuita
                            </Badge>
                          </HStack>
                        </Box>
                        <Button
                          variant="primary" 
                          isDisabled={!usuarioId}
                        >
                          Asignar
                        </Button>
                      </HStack>
                    </Box>
                  );
                })
              )}
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
            {tipoAbono === "personalizado" ? (
              <>
                <Text fontWeight="semibold" mt={2}>Configuración personalizada:</Text>
                {configuracionPersonalizada.map((config, index) => {
                  const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
                  return (
                    <Text key={index} fontSize="sm" ml={2}>
                      • {tipoClase?.nombre || LABELS[tipoClase?.codigo]} x{config.cantidad} clases
                    </Text>
                  );
                })}
                <Text fontWeight="bold" mt={2}>
                  Total: {configuracionPersonalizada.reduce((total, config) => total + config.cantidad, 0)} turnos
                </Text>
              </>
            ) : (
              <Text>
                {`Tipo: ${abonoSeleccionado?.tipo_clase?.nombre || LABELS[abonoSeleccionado?.tipo_clase?.codigo] || "-"}`}
              </Text>
            )}
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
