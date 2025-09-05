// src/pages/admin/PagosPreaprobadosPage.jsx
import React, { useEffect, useState, useContext } from "react";
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
} from "@chakra-ui/react";
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

  const bg = useBodyBg();
  const card = useCardColors();
  const mutedText = useMutedText();
  const isMobile = useBreakpointValue({ base: true, md: false });

  const fetchPagos = () => {
    const api = axiosAuth(accessToken);
    setLoading(true);
    api
      .get("pagos/comprobantes/?solo_preaprobados=true")
      .then((res) => setPagos(res.data.results || res.data))
      .catch(() => toast.error("Error al cargar pagos preaprobados"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (accessToken) fetchPagos();
  }, [accessToken]);

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
      <Box flex="1" p={{ base: 4, md: 8 }} bg={bg} color={card.color}>
        <Heading size={{ base: "md", md: "md" }} mb={{ base: 4, md: 6 }}>
          Pagos Preaprobados
        </Heading>

        {loading ? (
          <Flex align="center" justify="center" h="120px">
            <Spinner />
          </Flex>
        ) : pagos.length === 0 ? (
          <Text color={mutedText} textAlign="center">
            No hay pagos para aprobar.
          </Text>
        ) : (
          <VStack spacing={3} align="stretch">
            {pagos.map((p) => (
              <Box
                key={p.id}
                bg={card.bg}
                color={card.color}
                p={{ base: 4, md: 5 }}
                rounded="xl"
                boxShadow="2xl"
                borderWidth="1px"
              >
                {/* Contenedor responsive: columna en mobile, fila en desktop */}
                <Stack
                  direction={{ base: "column", md: "row" }}
                  spacing={{ base: 3, md: 4 }}
                  justify="space-between"
                  align={{ base: "stretch", md: "start" }}
                >
                  {/* Bloque de datos */}
                  <Box flex="1 1 auto" minW={0}>
                    <Text fontWeight="bold" mb={1} noOfLines={1}>
                      Comprobante #{p.id}
                    </Text>

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
                      Turno a las{" "}
                      <b>{p.turno_hora || "?"}</b> con{" "}
                      <b>{p.profesor_nombre || "?"}</b>
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

                  {/* Acciones */}
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
                </Stack>
              </Box>
            ))}
          </VStack>
        )}
      </Box>
    </PageWrapper>
  );
};

export default PagosPreaprobadosPage;
