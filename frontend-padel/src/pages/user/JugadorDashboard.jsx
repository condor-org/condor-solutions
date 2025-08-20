// src/pages/usuario/JugadorDashboard.jsx
import React, { useContext, useEffect, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import Button from "../../components/ui/Button";
import ReservarTurno from "./ReservarTurno";
import ReservarAbono from "./ReservarAbono";
import {
  Box,
  Heading,
  Flex,
  Text,
  HStack,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Icon,
  Badge,
  Divider,
  useBreakpointValue,
} from "@chakra-ui/react";
import { FaCalendarPlus, FaListUl, FaIdCard, FaClock } from "react-icons/fa";

import {
  useBodyBg,
  useCardColors,
} from "../../components/theme/tokens";

import { axiosAuth } from "../../utils/axiosAuth";

// Helper genérico para traer todas las páginas de un endpoint DRF
async function fetchAllPages(api, url, { params = {}, maxPages = 50, pageSize = 100, logTag = "fetchAllPages" } = {}) {
  const items = [];
  let nextUrl = url;
  let page = 0;
  let currentParams = { ...params, limit: params.limit ?? pageSize, offset: params.offset ?? 0 };

  try {
    let res = await api.get(nextUrl, { params: currentParams });
    let data = res.data;

    // Si no es paginado, normalizamos
    if (!("results" in data) && !("next" in data)) {
      console.debug(`[${logTag}] Respuesta no paginada. Normalizando.`, { url: nextUrl });
      const arr = Array.isArray(data) ? data : (data?.results || []);
      return arr;
    }

    while (true) {
      page += 1;
      const results = data?.results ?? [];
      items.push(...results);

      console.debug(
        `[${logTag}] Página ${page} | acumulados=${items.length} | next=${data?.next ?? "null"}`
      );

      if (!data?.next) break;
      if (results.length === 0) {
        console.warn(`[${logTag}] Corte por results.length === 0 en página ${page}.`);
        break;
      }
      if (page >= maxPages) {
        console.error(`[${logTag}] Corte por maxPages=${maxPages}.`, { url });
        break;
      }

      const isAbsolute = typeof data.next === "string" && /^https?:\/\//i.test(data.next);
      if (isAbsolute) {
        res = await api.get(data.next);
      } else {
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

// Helper para componer Date local a partir de fecha/hora (evita TZ issues)
const toLocalDate = (t) => {
  if (!t?.fecha || !t?.hora) return null;
  const dt = new Date(`${t.fecha}T${t.hora}`);
  return isNaN(dt) ? null : dt;
};

const JugadorDashboard = () => {
  const { user, accessToken } = useContext(AuthContext);
  const [tabIndex, setTabIndex] = useState(0); // 0=Reservar, 1=Mis Reservas, 2=Abono
  const [proximoTurno, setProximoTurno] = useState(null);

  const bg = useBodyBg();
  const card = useCardColors();

  const isMobile = useBreakpointValue({ base: true, md: false });

  // Cargar sólo lo necesario para el hero: próximo turno
  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);

    (async () => {
      const turnos = await fetchAllPages(api, "turnos/", {
        params: { estado: "reservado", upcoming: 1 },
        pageSize: 100,
        logTag: "dashboard-turnos"
      });

      const ahora = new Date();
      const futurosOrdenados = turnos
        .map(t => ({ ...t, _dt: toLocalDate(t) }))
        .filter(t => t._dt && t._dt >= ahora)
        .sort((a, b) => a._dt - b._dt);

      setProximoTurno(futurosOrdenados.length > 0 ? futurosOrdenados[0] : null);
    })();
  }, [accessToken]);

  const quickTo = (idx) => {
    setTabIndex(idx);
    // scroll suave al área de Tabs si estás en mobile
    const el = document.getElementById("dashboard-tabs");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const ProximoTurnoCard = () => (
    <Box
      w="100%"
      bg={card.bg}
      color={card.color}
      rounded="xl"
      boxShadow="2xl"
      p={{ base: 4, md: 6 }}
    >
      <HStack justify="space-between" align="center" mb={2}>
        <HStack>
          <Icon as={FaClock} />
          <Text fontWeight="bold">Próximo turno</Text>
        </HStack>
        {proximoTurno ? (
          <Badge colorScheme="green" variant="subtle">
            reservado
          </Badge>
        ) : (
          <Badge colorScheme="gray" variant="subtle">
            sin reservas
          </Badge>
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

      {/* Quick actions con tus estilos (Button custom) */}
      <HStack spacing={3} wrap="wrap">
        <Button onClick={() => quickTo(0)} variant="primary">
          <HStack>
            <Icon as={FaCalendarPlus} />
            <Text>Reservar turno</Text>
          </HStack>
        </Button>
        <Button onClick={() => quickTo(1)} variant="secondary">
          <HStack>
            <Icon as={FaListUl} />
            <Text>Mis reservas</Text>
          </HStack>
        </Button>
        <Button onClick={() => quickTo(2)} variant="secondary">
          <HStack>
            <Icon as={FaIdCard} />
            <Text>Reservar abono</Text>
          </HStack>
        </Button>
      </HStack>
    </Box>
  );

  return (
    <Box minH="100vh" bg={bg} color={card.color}>
      <Box maxW="5xl" mx="auto" px={4} py={8}>
        <Heading as="h2" size="xl" mb={6} textAlign="center">
          Bienvenido, {user?.email}
        </Heading>

        {/* Hero compacto con próximo turno + quick actions */}
        <ProximoTurnoCard />

        {/* Tabs principales */}
        <Box id="dashboard-tabs" mt={8}>
          <Tabs
            index={tabIndex}
            onChange={setTabIndex}
            isFitted
            variant="enclosed"
          >
            <TabList mb="1em">
              <Tab>Reservar Turno</Tab>
              <Tab>Mis Reservas</Tab>
              <Tab>Reservar Abono</Tab>
            </TabList>

            <TabPanels>
              <TabPanel px={isMobile ? 0 : 2}>
                {/* Mismo componente, sin modal */}
                <ReservarTurno onClose={() => { /* noop */ }} />
              </TabPanel>

              <TabPanel px={isMobile ? 0 : 2}>
                {/* Reutilizamos el mismo componente en modo "Mis Reservas" */}
                <ReservarTurno onClose={() => { /* noop */ }} defaultMisTurnos />
              </TabPanel>

              <TabPanel px={isMobile ? 0 : 2}>
                <ReservarAbono onClose={() => { /* noop */ }} />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Box>
      </Box>
    </Box>
  );
};

export default JugadorDashboard;
