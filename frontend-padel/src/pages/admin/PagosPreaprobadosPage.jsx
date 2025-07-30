import React, { useEffect, useState, useContext } from "react";
import {
  Box,
  Heading,
  Text,
  VStack,
  Flex,
  Button as ChakraButton,
  Spinner,
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
  const { user, logout, accessToken } = useContext(AuthContext);
  const [pagos, setPagos] = useState([]);
  const [loading, setLoading] = useState(true);

  const bg = useBodyBg();
  const card = useCardColors();
  const mutedText = useMutedText();

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
          { label: "Configuración Pago", path: "/admin/configuracion-pago" },
          { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
        ]}
      />
      <Box flex="1" p={[2, 4, 8]} bg={bg} color={card.color}>
        <Heading size="md" mb={4}>
          Pagos Preaprobados
        </Heading>
        {loading ? (
          <Flex align="center" justify="center" h="100px">
            <Spinner color="blue.300" />
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
                p={4}
                rounded="md"
                boxShadow="md"
              >
                <Flex
                  justify="space-between"
                  align="flex-start"
                  wrap="wrap"
                  gap={3}
                >
                  <Box minW={["100%", "260px"]}>
                    <Text fontWeight="bold" mb={1}>
                      Comprobante #{p.id}
                    </Text>
                    <Text fontSize="sm" mb={1}>
                      Turno: {p.turno_id}
                    </Text>
                    <Text fontSize="sm" color={mutedText} mb={1}>
                      Fecha: {new Date(p.created_at).toLocaleString()}
                    </Text>
                    <Text fontSize="sm" mb={1}>
                      Usuario: <b>{p.turno_usuario_nombre || p.usuario_nombre || "?"}</b>
                    </Text>
                    <Text fontSize="sm" color={mutedText} mb={1}>
                      Email: {p.turno_usuario_email || p.usuario_email || "?"}
                    </Text>
                    <Text fontSize="sm" color={mutedText} mb={1}>
                      Turno a las <b>{p.turno_hora || "?"}</b> con <b>{p.profesor_nombre || "?"}</b>
                    </Text>

                    <ChakraButton
                      colorScheme="blue"
                      size="sm"
                      variant="outline"
                      mt={2}
                      onClick={() => verComprobante(p.id)}
                    >
                      Ver comprobante
                    </ChakraButton>
                  </Box>
                  <Flex gap={2}>
                    <ChakraButton
                      colorScheme="green"
                      onClick={() => handleAccion(p.id, "aprobar")}
                    >
                      Completar Pago
                    </ChakraButton>
                    <ChakraButton
                      colorScheme="red"
                      onClick={() => handleAccion(p.id, "rechazar")}
                    >
                      Rechazar
                    </ChakraButton>
                  </Flex>
                </Flex>
              </Box>
            ))}
          </VStack>
        )}
      </Box>
    </PageWrapper>
  );
};

export default PagosPreaprobadosPage;
