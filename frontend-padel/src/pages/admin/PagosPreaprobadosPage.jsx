// src/pages/admin/PagosPreaprobadosPage.jsx
import React, { useEffect, useState, useContext, useMemo } from "react";
import {
  Box,
  Heading,
  Text,
  VStack,
  Flex,
  Button as ChakraButton,
  Spinner,
  Stack,
  HStack,
  useBreakpointValue,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Badge,
  Divider,
  InputGroup,
  InputLeftElement,
  Input,
  Select,
} from "@chakra-ui/react";
import { SearchIcon } from "@chakra-ui/icons";
import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { toast } from "react-toastify";
import {
  useBodyBg,
  useCardColors,
  useMutedText,
} from "../../components/theme/tokens";

const PagosPreaprobadosPage = () => {
  const { accessToken } = useContext(AuthContext);
  const [pagos, setPagos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // all, preaprobados, aprobados, rechazados
  const [usuarios, setUsuarios] = useState([]);

  const bg = useBodyBg();
  const card = useCardColors();
  const mutedText = useMutedText();
  const isMobile = useBreakpointValue({ base: true, md: false });

  // Filtrar pagos según la tab activa y búsqueda
  const filteredPagos = useMemo(() => {
    let filtered = pagos;
    
    // Filtro por tab
    if (activeTab === 1) filtered = filtered.filter(p => p.tipo === 'turno'); // Clases
    if (activeTab === 2) filtered = filtered.filter(p => p.tipo === 'abono'); // Abonos
    
    // Filtro por búsqueda (usuario)
    if (searchTerm) {
      filtered = filtered.filter(p => {
        const usuarioNombre = p.usuario_nombre || "";
        const usuarioEmail = p.usuario_email || "";
        const searchLower = searchTerm.toLowerCase();
        return usuarioNombre.toLowerCase().includes(searchLower) || 
               usuarioEmail.toLowerCase().includes(searchLower);
      });
    }
    
    return filtered;
  }, [pagos, activeTab, searchTerm]);

  // Contar pagos por tipo
  const counts = useMemo(() => {
    const turnos = pagos.filter(p => p.tipo === 'turno').length;
    const abonos = pagos.filter(p => p.tipo === 'abono').length;
    return { total: pagos.length, turnos, abonos };
  }, [pagos]);

  const fetchPagos = async () => {
    const api = axiosAuth(accessToken);
    setLoading(true);
    
    try {
      // Determinar qué filtro usar según el statusFilter
      let turnosUrl = "pagos/comprobantes/";
      let abonosUrl = "pagos/comprobantes-abono/";
      
      if (statusFilter === "preaprobados") {
        turnosUrl += "?solo_preaprobados=true";
        abonosUrl += "?solo_preaprobados=true";
      } else if (statusFilter === "aprobados") {
        turnosUrl += "?solo_aprobados=true";
        abonosUrl += "?solo_aprobados=true";
      } else if (statusFilter === "rechazados") {
        turnosUrl += "?solo_rechazados=true";
        abonosUrl += "?solo_rechazados=true";
      }
      
      // Hacer ambas llamadas en paralelo
      const [turnosRes, abonosRes] = await Promise.all([
        api.get(turnosUrl),
        api.get(abonosUrl)
      ]);
      
      // Combinar resultados y agregar tipo
      const turnos = (turnosRes.data.results || turnosRes.data).map(p => ({ ...p, tipo: 'turno' }));
      const abonos = (abonosRes.data.results || abonosRes.data).map(p => ({ ...p, tipo: 'abono' }));
      
      // Combinar y ordenar por fecha
      const combined = [...turnos, ...abonos].sort((a, b) => 
        new Date(b.created_at) - new Date(a.created_at)
      );
      
      setPagos(combined);
    } catch (error) {
      toast.error("Error al cargar pagos");
    } finally {
      setLoading(false);
    }
  };

  const fetchUsuarios = async () => {
    const api = axiosAuth(accessToken);
    try {
      const res = await api.get("auth/usuarios/");
      setUsuarios(res.data?.results || res.data || []);
    } catch (error) {
      console.error("Error al cargar usuarios:", error);
    }
  };

  useEffect(() => {
    if (accessToken) {
      fetchPagos();
      fetchUsuarios();
    }
  }, [accessToken, statusFilter]);

  const handleAccion = async (id, accion) => {
    const api = axiosAuth(accessToken);
    try {
      await api.patch(`pagos/comprobantes/${id}/${accion}/`);
      toast.success(accion === "aprobar" ? "Pago confirmado" : "Pago rechazado");
      fetchPagos(); // 🔁 Refrescar desde el backend
    } catch {
      toast.error("Error al actualizar el pago");
    }
  };

  const verComprobante = async (id) => {
    const api = axiosAuth(accessToken);
    try {
      const response = await api.get(`pagos/comprobantes/${id}/descargar/`, {
        responseType: "blob",
      });
      const fileURL = URL.createObjectURL(response.data);
      window.open(fileURL, "_blank");
    } catch {
      toast.error("Error al abrir el comprobante");
    }
  };

  // Función para obtener el nombre del mes
  const getMonthName = (monthNumber) => {
    const months = [
      "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];
    return months[monthNumber - 1] || "Mes desconocido";
  };


  // Componente para renderizar un pago de turno
  const renderTurnoPago = (p) => {
    // Determinar el estado basado en el filtro actual
    const isCompleted = statusFilter === "aprobados";
    const isRejected = statusFilter === "rechazados";
    const isPreapproved = statusFilter === "preaprobados";
    const showButtons = statusFilter === "preaprobados" || statusFilter === "all";

  return (
              <Box
                key={p.id}
                bg={card.bg}
                color={card.color}
                p={{ base: 4, md: 5 }}
                rounded="xl"
                boxShadow="2xl"
                borderWidth="1px"
        borderColor={isCompleted ? "green.300" : isRejected ? "red.300" : undefined}
              >
                <Stack
                  direction={{ base: "column", md: "row" }}
                  spacing={{ base: 3, md: 4 }}
                  justify="space-between"
                  align={{ base: "stretch", md: "start" }}
                >
                  <Box flex="1 1 auto" minW={0}>
            <HStack spacing={2} mb={2}>
              <Text fontWeight="bold" noOfLines={1}>
                Comprobante
                    </Text>
              <Badge colorScheme="blue" size="sm">
                Clase Individual
              </Badge>
              {isCompleted && (
                <Badge colorScheme="green" size="sm">
                  ✅ Completado
                </Badge>
              )}
              {isRejected && (
                <Badge colorScheme="red" size="sm">
                  ❌ Rechazado
                </Badge>
              )}
              {isPreapproved && (
                <Badge colorScheme="yellow" size="sm">
                  ⏳ Pendiente
                </Badge>
              )}
            </HStack>

                    <HStack spacing={2} wrap="wrap" mb={1}>
                      <Text fontSize="sm">Turno:</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        {p.turno_id}
                      </Text>
                    </HStack>

                    <Text fontSize="sm" color={mutedText} mb={1}>
                      Fecha: {new Date(p.created_at).toLocaleString()}
                    </Text>

                    <HStack spacing={2} wrap="wrap" mb={1}>
                      <Text fontSize="sm">Usuario:</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        {p.turno_usuario_nombre || p.usuario_nombre || "?"}
                      </Text>
                    </HStack>

                    <Text fontSize="sm" color={mutedText} mb={1} noOfLines={1}>
                      Email: {p.turno_usuario_email || p.usuario_email || "?"}
                    </Text>

                    <Text fontSize="sm" color={mutedText} mb={1}>
              Turno a las <b>{p.turno_hora || "?"}</b> con <b>{p.profesor_nombre || "?"}</b>
                    </Text>

                    <ChakraButton
                      colorScheme="blue"
                      size={{ base: "sm", md: "sm" }}
                      variant="outline"
                      mt={2}
                      onClick={() => verComprobante(p.id)}
                      w={{ base: "100%", md: "auto" }}
                    >
                      Ver comprobante
                    </ChakraButton>
                  </Box>

          {showButtons && (
            <Stack
              direction={{ base: "column", md: "row" }}
              spacing={2}
              w={{ base: "100%", md: "auto" }}
              align={{ base: "stretch", md: "center" }}
            >
              <ChakraButton
                colorScheme="green"
                onClick={() => handleAccion(p.id, "aprobar")}
                w={{ base: "100%", md: "auto" }}
              >
                Completar Pago
              </ChakraButton>
              <ChakraButton
                colorScheme="red"
                onClick={() => handleAccion(p.id, "rechazar")}
                w={{ base: "100%", md: "auto" }}
              >
                Rechazar
              </ChakraButton>
            </Stack>
          )}
        </Stack>
      </Box>
    );
  };

  // Componente para renderizar un pago de abono
  const renderAbonoPago = (p) => {
    // Determinar el estado basado en el filtro actual
    const isCompleted = statusFilter === "aprobados";
    const isRejected = statusFilter === "rechazados";
    const isPreapproved = statusFilter === "preaprobados";
    const showButtons = statusFilter === "preaprobados" || statusFilter === "all";
    
    return (
      <Box
        key={p.id}
        bg={card.bg}
        color={card.color}
        p={{ base: 4, md: 5 }}
        rounded="xl"
        boxShadow="2xl"
        borderWidth="1px"
        borderColor={isCompleted ? "green.300" : isRejected ? "red.300" : undefined}
      >
        <Stack
          direction={{ base: "column", md: "row" }}
          spacing={{ base: 3, md: 4 }}
          justify="space-between"
          align={{ base: "stretch", md: "start" }}
        >
          <Box flex="1 1 auto" minW={0}>
            <HStack spacing={2} mb={2}>
              <Text fontWeight="bold" noOfLines={1}>
                Comprobante
              </Text>
              <Badge colorScheme="purple" size="sm">
                Abono Mensual
              </Badge>
              {p.es_renovacion && (
                <Badge colorScheme="orange" size="sm">
                  Renovación
                </Badge>
              )}
              {isCompleted && (
                <Badge colorScheme="green" size="sm">
                  ✅ Completado
                </Badge>
              )}
              {isRejected && (
                <Badge colorScheme="red" size="sm">
                  ❌ Rechazado
                </Badge>
              )}
              {isPreapproved && (
                <Badge colorScheme="yellow" size="sm">
                  ⏳ Pendiente
                </Badge>
              )}
            </HStack>

            <HStack spacing={2} wrap="wrap" mb={1}>
              <Text fontSize="sm">Abono:</Text>
              <Text fontSize="sm" fontWeight="semibold">
                {p.abono_mes_id || "?"}
              </Text>
              <Text fontSize="sm" color={mutedText}>
                ({p.abono_mes_anio}-{String(p.abono_mes_mes).padStart(2, '0')})
              </Text>
            </HStack>

            {p.es_renovacion && (
              <HStack spacing={2} wrap="wrap" mb={1}>
                <Text fontSize="sm" color="orange.500" fontWeight="semibold">
                  🔄 Renovación de abono
                </Text>
                {p.abono_mes_fecha_limite_renovacion && (
                  <Text fontSize="sm" color={mutedText}>
                    (Límite: {new Date(p.abono_mes_fecha_limite_renovacion).toLocaleDateString()})
                  </Text>
                )}
              </HStack>
            )}

            <Text fontSize="sm" color={mutedText} mb={1}>
              Fecha: {new Date(p.created_at).toLocaleString()}
            </Text>

            <HStack spacing={2} wrap="wrap" mb={1}>
              <Text fontSize="sm">Usuario:</Text>
              <Text fontSize="sm" fontWeight="semibold">
                {p.usuario_nombre || "?"}
              </Text>
            </HStack>

            <Text fontSize="sm" color={mutedText} mb={1} noOfLines={1}>
              Email: {p.usuario_email || "?"}
            </Text>

            <Text fontSize="sm" color={mutedText} mb={1}>
              Mes: <b>{p.es_renovacion ? 
                getMonthName(p.abono_mes_mes === 12 ? 1 : p.abono_mes_mes + 1) : 
                getMonthName(p.abono_mes_mes)} {p.abono_mes_anio}</b>
            </Text>

            {p.abono_mes_precio && (
              <Text fontSize="sm" color={mutedText} mb={1}>
                Precio: <b>${p.abono_mes_precio}</b>
              </Text>
            )}

            <ChakraButton
              colorScheme="blue"
              size={{ base: "sm", md: "sm" }}
              variant="outline"
              mt={2}
              onClick={() => verComprobante(p.id)}
              w={{ base: "100%", md: "auto" }}
            >
              Ver comprobante
            </ChakraButton>
          </Box>

          {showButtons && (
                  <Stack
                    direction={{ base: "column", md: "row" }}
                    spacing={2}
                    w={{ base: "100%", md: "auto" }}
                    align={{ base: "stretch", md: "center" }}
                  >
                    <ChakraButton
                      colorScheme="green"
                      onClick={() => handleAccion(p.id, "aprobar")}
                      w={{ base: "100%", md: "auto" }}
                    >
                      Completar Pago
                    </ChakraButton>
                    <ChakraButton
                      colorScheme="red"
                      onClick={() => handleAccion(p.id, "rechazar")}
                      w={{ base: "100%", md: "auto" }}
                    >
                      Rechazar
                    </ChakraButton>
                  </Stack>
          )}
                </Stack>
              </Box>
    );
  };

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
        <Heading size={{ base: "md", md: "md" }} mb={{ base: 4, md: 6 }}>
          Pagos Preaprobados
        </Heading>

        {/* Barra de búsqueda y filtros */}
        <Stack 
          direction={{ base: "column", md: "row" }} 
          spacing={4} 
          mb={6}
          align={{ base: "stretch", md: "center" }}
        >
          <InputGroup maxW={{ base: "100%", md: "400px" }}>
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Buscar por usuario..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              bg={card.bg}
              color={card.color}
              _placeholder={{ color: "gray.400" }}
            />
          </InputGroup>
          
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            maxW={{ base: "100%", md: "200px" }}
            bg={card.bg}
            color={card.color}
          >
            <option value="all">Todos los estados</option>
            <option value="preaprobados">Solo preaprobados</option>
            <option value="aprobados">Solo aprobados</option>
            <option value="rechazados">Solo rechazados</option>
          </Select>
        </Stack>

        {loading ? (
          <Flex align="center" justify="center" h="120px">
            <Spinner />
          </Flex>
        ) : (
          <Tabs 
            index={activeTab} 
            onChange={setActiveTab}
            variant="enclosed"
            colorScheme="blue"
            isLazy
          >
            <TabList 
              flexWrap="wrap"
              borderBottom="2px solid"
              borderColor="gray.200"
              mb={4}
            >
              <Tab 
                fontSize={{ base: "sm", md: "md" }}
                px={{ base: 3, md: 4 }}
                py={{ base: 2, md: 3 }}
              >
                Todos
                <Badge ml={2} colorScheme="gray" size="sm">
                  {counts.total}
                </Badge>
              </Tab>
              <Tab 
                fontSize={{ base: "sm", md: "md" }}
                px={{ base: 3, md: 4 }}
                py={{ base: 2, md: 3 }}
              >
                Clases
                <Badge ml={2} colorScheme="blue" size="sm">
                  {counts.turnos}
                </Badge>
              </Tab>
              <Tab 
                fontSize={{ base: "sm", md: "md" }}
                px={{ base: 3, md: 4 }}
                py={{ base: 2, md: 3 }}
              >
                Abonos
                <Badge ml={2} colorScheme="purple" size="sm">
                  {counts.abonos}
                </Badge>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Tab: Todos */}
              <TabPanel px={0}>
                {filteredPagos.length === 0 ? (
                  <Text color={mutedText} textAlign="center" py={8}>
                    {searchTerm || statusFilter !== "all" 
                      ? "No se encontraron pagos con los filtros aplicados." 
                      : "No hay pagos registrados."}
                  </Text>
                ) : (
                  <VStack spacing={3} align="stretch">
                    {filteredPagos.map((p) => 
                      p.tipo === 'turno' ? renderTurnoPago(p) : renderAbonoPago(p)
                    )}
                  </VStack>
                )}
              </TabPanel>

              {/* Tab: Clases */}
              <TabPanel px={0}>
                {filteredPagos.length === 0 ? (
                  <Text color={mutedText} textAlign="center" py={8}>
                    No hay clases para aprobar.
                  </Text>
                ) : (
                  <VStack spacing={3} align="stretch">
                    {filteredPagos.map(renderTurnoPago)}
                  </VStack>
                )}
              </TabPanel>

              {/* Tab: Abonos */}
              <TabPanel px={0}>
                {filteredPagos.length === 0 ? (
                  <Text color={mutedText} textAlign="center" py={8}>
                    No hay abonos para aprobar.
                  </Text>
                ) : (
                  <VStack spacing={3} align="stretch">
                    {filteredPagos.map(renderAbonoPago)}
          </VStack>
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </Box>
    </PageWrapper>
  );
};

export default PagosPreaprobadosPage;