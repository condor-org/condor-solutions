// src/pages/usuario/JugadorDashboard.jsx
import React, { useContext, useEffect, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import Button from "../../components/ui/Button";
import ReservarTurno from "./ReservarTurno";
import ReservarAbono from "./ReservarAbono";
import {
  Box,
  Heading,
  Text,
  HStack,
  VStack,
  Icon,
  Badge,
  Divider,
  Stack,
  Skeleton,
  useToast,
  SimpleGrid,
} from "@chakra-ui/react";
import { FaCalendarPlus, FaIdCard, FaClock, FaGift } from "react-icons/fa";
import { useBodyBg, useCardColors, useMutedText } from "../../components/theme/tokens";
import { axiosAuth } from "../../utils/axiosAuth";

/* ========= Helpers ========= */
async function fetchAllPages(
  api,
  url,
  { params = {}, maxPages = 50, pageSize = 100, logTag = "fetchAllPages" } = {}
) {
  const items = [];
  let nextUrl = url;
  let page = 0;
  let currentParams = { ...params, limit: params.limit ?? pageSize, offset: params.offset ?? 0 };

  try {
    let res = await api.get(nextUrl, { params: currentParams });
    let data = res.data;

    if (!("results" in data) && !("next" in data)) {
      const arr = Array.isArray(data) ? data : data?.results || [];
      return arr;
    }

    while (true) {
      page += 1;
      const results = data?.results ?? [];
      items.push(...results);
      if (!data?.next || results.length === 0 || page >= maxPages) break;

      const isAbsolute = typeof data.next === "string" && /^https?:\/\//i.test(data.next);
      if (isAbsolute) res = await api.get(data.next);
      else {
        const nextOffset = (currentParams.offset ?? 0) + (currentParams.limit ?? pageSize);
        currentParams = { ...currentParams, offset: nextOffset };
        res = await api.get(nextUrl, { params: currentParams });
      }
      data = res.data;
    }
  } catch (err) {
    console.error(`[${logTag}] Error al paginar`, { url, params, err });
  }
  return items;
}

const toLocalDate = (t) => {
  if (!t?.fecha || !t?.hora) return null;
  const dt = new Date(`${t.fecha}T${t.hora}`);
  return isNaN(dt) ? null : dt;
};

/* ========= Vista: Bonificaciones (inline, como antes) ========= */
const BonificacionesList = () => {
  const { accessToken } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const toast = useToast();
  const card = useCardColors();
  const muted = useMutedText();

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);

    (async () => {
      setLoading(true);
      try {
        const res = await api.get("turnos/bonificados/mios/");
        const data = Array.isArray(res.data) ? res.data : (res.data?.bonificaciones || []);
        setItems(data || []);
      } catch (e) {
        console.error("Error cargando bonificaciones", e);
        toast({
          title: "No se pudieron cargar las bonificaciones",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
        setItems([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [accessToken, toast]);

  const fmtFecha = (v) =>
    v ? new Date(v).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" }) : null;

  if (loading) {
    return (
      <Stack spacing={3}>
        <Skeleton height="90px" rounded="lg" />
        <Skeleton height="90px" rounded="lg" />
        <Skeleton height="90px" rounded="lg" />
      </Stack>
    );
  }

  if (!items.length) {
    return <Text color={muted}>No tenés bonificaciones.</Text>;
  }

  return (
    <VStack align="stretch" spacing={3}>
      {items.map((b) => {
        const motivo = b.motivo || "Bonificación";
        const tipoTurno = b.tipo_turno || "-";
        const creada = fmtFecha(b.fecha_creacion);
        const vence = b.valido_hasta ? fmtFecha(b.valido_hasta) : "Sin vencimiento";

        const titulo = `Bonificación por: ${motivo}`;
        const subtitulo = [
          `Clase: ${tipoTurno}`,
          creada ? `Emitida: ${creada}` : null,
          `Vence: ${vence}`
        ].filter(Boolean).join(" · ");

        const saldo = b.saldo ?? b.creditos ?? b.cantidad_restante ?? b.restante ?? null;
        const porcentaje = b.porcentaje ?? b.descuento ?? null;
        const estado = b.estado || b.status || null;

        return (
          <Box key={b.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
            <HStack justify="space-between" align="start">
              <Box>
                <Text fontWeight="semibold">{titulo}</Text>
                <Text fontSize="sm" color={muted}>{subtitulo}</Text>

                <HStack mt={2} spacing={2}>
                  {saldo !== null && (
                    <Badge colorScheme="green" variant="subtle">
                      saldo: {saldo}
                    </Badge>
                  )}
                  {porcentaje !== null && (
                    <Badge variant="outline">{porcentaje}% off</Badge>
                  )}
                  {estado && (
                    <Badge colorScheme="gray" variant="subtle">
                      {estado}
                    </Badge>
                  )}
                </HStack>
              </Box>
            </HStack>
          </Box>
        );
      })}
    </VStack>
  );
};

/* ========= Página ========= */
const JugadorDashboard = () => {
  const { user, accessToken } = useContext(AuthContext);

  // vistas: 'clases' | 'abono' | 'bonis'
  const [view, setView] = useState("clases");
  const [proximoTurno, setProximoTurno] = useState(null);

  const bg = useBodyBg();
  const card = useCardColors();

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);

    (async () => {
      const turnos = await fetchAllPages(api, "turnos/", {
        params: { estado: "reservado", upcoming: 1 },
        pageSize: 100,
        logTag: "dashboard-turnos",
      });

      const ahora = new Date();
      const futurosOrdenados = (turnos || [])
        .map((t) => ({ ...t, _dt: toLocalDate(t) }))
        .filter((t) => t._dt && t._dt >= ahora)
        .sort((a, b) => a._dt - b._dt);

      setProximoTurno(futurosOrdenados[0] || null);
    })();
  }, [accessToken]);

  const quickTo = (nextView) => {
    setView(nextView);
    const el = document.getElementById("dashboard-content");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const ProximoTurnoCard = () => (
    <Box w="100%" bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl" p={{ base: 4, md: 6 }}>
      <HStack justify="space-between" align="center" mb={2}>
        <HStack>
          <Icon as={FaClock} />
          <Text fontWeight="bold">Próximo turno</Text>
        </HStack>
        {proximoTurno ? (
          <Badge colorScheme="green" variant="subtle">reservado</Badge>
        ) : (
          <Badge colorScheme="gray" variant="subtle">sin reservas</Badge>
        )}
      </HStack>

      {proximoTurno ? (
        <Box>
          <Text fontSize="lg" fontWeight="semibold">
            {proximoTurno.lugar || proximoTurno.lugar_nombre || "Sede"}
          </Text>
          <Text mt={1}>
            {proximoTurno.fecha?.slice(5)} · {proximoTurno.hora?.slice(0, 5)} hs
          </Text>
        </Box>
      ) : (
        <Text>Cuando tengas una reserva próxima aparecerá aquí.</Text>
      )}

      <Divider my={4} />

      {/* Acciones */}
      <SimpleGrid columns={{ base: 2, sm: 2, md: 3 }} spacing={3} mt={2}>
        <Button
          onClick={() => quickTo("clases")}
          variant="primary"
          w="100%"
          size={{ base: "sm", md: "md" }}
          py={{ base: 5, md: 0 }}
        >
          <HStack w="100%" justify="center">
            <Icon as={FaCalendarPlus} />
            <Text>Clases sueltas</Text>
          </HStack>
        </Button>

        <Button
          onClick={() => quickTo("abono")}
          variant="secondary"
          w="100%"
          size={{ base: "sm", md: "md" }}
          py={{ base: 5, md: 0 }}
        >
          <HStack w="100%" justify="center">
            <Icon as={FaIdCard} />
            <Text>Abonos</Text>
          </HStack>
        </Button>

        <Button
          onClick={() => quickTo("bonis")}
          variant="secondary"
          w="100%"
          size={{ base: "sm", md: "md" }}
          py={{ base: 5, md: 0 }}
        >
          <HStack w="100%" justify="center">
            <Icon as={FaGift} />
            <Text>Bonificaciones</Text>
          </HStack>
        </Button>
      </SimpleGrid>
    </Box>
  );

  return (
    <Box minH="100vh" bg={bg} color={card.color}>
      <Box maxW="5xl" mx="auto" px={4} py={8}>
        <Heading as="h2" size={{ base: "lg", md: "xl" }} mb={{ base: 4, md: 6 }} lineHeight="1.2">
          Bienvenido,
          <Box as="span" display="block" fontWeight="semibold">
            {user?.email}
          </Box>
        </Heading>

        <ProximoTurnoCard />

        {/* Contenido según vista seleccionada */}
        <Box id="dashboard-content" mt={8}>
          {view === "clases" && <ReservarTurno onClose={() => {}} />}
          {view === "abono" && <ReservarAbono onClose={() => {}} />}
          {view === "bonis" && <BonificacionesList />}
        </Box>
      </Box>
    </Box>
  );
};

export default JugadorDashboard;
