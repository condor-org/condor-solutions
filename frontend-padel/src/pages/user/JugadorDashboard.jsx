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
} from "@chakra-ui/react";
import { FaCalendarPlus, FaListUl, FaIdCard, FaClock, FaGift } from "react-icons/fa";
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

/* ========= Vista: Bonificaciones ========= */
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
        // mismo endpoint que usa el modal; sin tipo_clase_id -> traer todas
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
        const titulo =
          b.nombre ||
          b.titulo ||
          b.tipo_clase_nombre ||
          b.tipo_nombre ||
          `Bonificación | Clase: ${b.tipo_turno}`;

        const vence = fmtFecha(b.vigencia_hasta || b.expira_el || b.expires_at);
        const tipo = b.tipo_clase_nombre || b.tipo_nombre || b.tipo || null;
        const subtitulo = [tipo, vence ? `Vence: ${vence}` : null]
          .filter(Boolean)
          .join(" · ");

        const saldo =
          b.saldo ?? b.creditos ?? b.cantidad_restante ?? b.restante ?? null;
        const porcentaje = b.porcentaje ?? b.descuento ?? null;
        const estado = b.estado || b.status || null;

        return (
          <Box key={b.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
            <HStack justify="space-between" align="start">
              <Box>
                <Text fontWeight="semibold">{titulo}</Text>
                {subtitulo && (
                  <Text fontSize="sm" color={muted}>
                    {subtitulo}
                  </Text>
                )}
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

  // vistas: 'reservar' | 'mis' | 'abono' | 'bonis'
  const [view, setView] = useState("reservar");
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

      {/* ÚNICO lugar de acciones */}
      <HStack spacing={3} wrap="wrap">
        <Button onClick={() => quickTo("reservar")} variant="primary">
          <HStack><Icon as={FaCalendarPlus} /><Text>Reservar turno</Text></HStack>
        </Button>
        <Button onClick={() => quickTo("mis")} variant="secondary">
          <HStack><Icon as={FaListUl} /><Text>Mis reservas</Text></HStack>
        </Button>
        <Button onClick={() => quickTo("abono")} variant="secondary">
          <HStack><Icon as={FaIdCard} /><Text>Reservar abono</Text></HStack>
        </Button>
        <Button onClick={() => quickTo("bonis")} variant="secondary">
          <HStack><Icon as={FaGift} /><Text>Bonificaciones</Text></HStack>
        </Button>
      </HStack>
    </Box>
  );

  return (
    <Box minH="100vh" bg={bg} color={card.color}>
      <Box maxW="5xl" mx="auto" px={4} py={8}>
        <Heading as="h2" size="xl" mb={6}>
          Bienvenido, {user?.nombre}
        </Heading>

        <ProximoTurnoCard />

        {/* Contenido según vista seleccionada */}
        <Box id="dashboard-content" mt={8}>
          {view === "reservar" && <ReservarTurno onClose={() => {}} />}
          {view === "mis" && <ReservarTurno onClose={() => {}} defaultMisTurnos />}
          {view === "abono" && <ReservarAbono onClose={() => {}} />}
          {view === "bonis" && <BonificacionesList />}
        </Box>
      </Box>
    </Box>
  );
};

export default JugadorDashboard;
