// src/pages/notificaciones/NotificacionesAdminPage.jsx
import React, { useContext, useEffect, useMemo, useState, useCallback } from "react";
import {
  Box, Heading, HStack, VStack, Text, IconButton, Button,
  Badge, Divider, Checkbox, Skeleton, Tooltip, Select, useBreakpointValue
} from "@chakra-ui/react";
import { ArrowBackIcon, CheckIcon, RepeatIcon } from "@chakra-ui/icons";
import { FaExternalLinkAlt, FaBell, FaEnvelopeOpenText } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { emitNotificationsRefresh } from "../../utils/notificationsBus";

import { useBodyBg, useCardColors, useMutedText, useInputColors } from "../../components/theme/tokens";

const severityToScheme = (sev) => {
  switch (sev) {
    case "error":
    case "critical":
      return "red";
    case "warning":
      return "orange";
    default:
      return "blue";
  }
};
const formatWhen = (iso) => {
  try { return new Date(iso).toLocaleString(); } catch { return iso ?? ""; }
};

const LIMIT = 20;
const TYPE_OPTS = [
  { value: "", label: "Todos los tipos" },
  { value: "RESERVA_TURNO", label: "Reserva de turno" },
  { value: "RESERVA_ABONO", label: "Reserva de abono" },
  { value: "CANCELACION_TURNO", label: "Cancelación por usuario" },
  { value: "CANCELACIONES_TURNOS", label: "Cancelaciones administrativas" },
];

const NotificacionesAdminPage = () => {
  const { accessToken, user } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);

  const navigate = useNavigate();
  const bg = useBodyBg();
  const card = useCardColors();
  const muted = useMutedText();
  const input = useInputColors();

  const isMobile = useBreakpointValue({ base: true, md: false });

  const [items, setItems] = useState([]);
  const [nextOffset, setNextOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busyAll, setBusyAll] = useState(false);

  const [unreadOnly, setUnreadOnly] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);

  // Seguridad por rol (si entran por URL)
  useEffect(() => {
    if (!user) return;
    const role = user?.tipo_usuario;
    if (role !== "admin_cliente" && role !== "super_admin") {
      navigate("/notificaciones");
    }
  }, [user, navigate]);

  // ✅ NO depende de `items`; usa setItems(prev => ...) cuando mergea
  const fetchPage = useCallback(
    async ({ offset = 0, merge = false } = {}) => {
      if (!api) return;

      const params = { limit: LIMIT, offset };
      if (unreadOnly) params.unread = 1;
      if (typeFilter) params.type = typeFilter;

      const res = await api.get("notificaciones/", { params });
      const data = res.data?.results ?? res.data ?? [];

      if (merge) {
        setItems((prev) => {
          const byId = new Map(prev.map((n) => [n.id, n]));
          data.forEach((n) => byId.set(n.id, n));
          return Array.from(byId.values());
        });
      } else {
        setItems(data);
      }

      setNextOffset(offset + data.length);
      setHasMore(Boolean(res.data?.next) && data.length > 0);
    },
    [api, unreadOnly, typeFilter]
  );

  // ✅ No depende de items.length
  const loadFirstPage = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    try {
      await fetchPage({ offset: 0, merge: false });
      const rc = await api.get("notificaciones/unread_count/");
      setUnreadCount(rc.data?.unread_count ?? 0);
    } catch (err) {
      console.error("[NotificacionesAdminPage] load error", err);
    } finally {
      setLoading(false);
    }
  }, [api, fetchPage]);

  // ✅ Solo re-carga cuando cambian filtros/api (a través de fetchPage)
  useEffect(() => {
    loadFirstPage();
  }, [loadFirstPage]);

  const loadMore = async () => {
    if (!api || !hasMore || loadingMore) return;
    setLoadingMore(true);
    try {
      await fetchPage({ offset: nextOffset, merge: true });
    } catch (err) {
      console.error("[NotificacionesAdminPage] loadMore error", err);
    } finally {
      setLoadingMore(false);
    }
  };

  const markAll = async () => {
    if (!api) return;
    setBusyAll(true);
    try {
      await api.post("notificaciones/read_all/");
      emitNotificationsRefresh();
      await loadFirstPage();
    } catch (err) {
      console.error("[NotificacionesAdminPage] markAll failed", err);
    } finally {
      setBusyAll(false);
    }
  };

  const toggleRead = async (n) => {
    if (!api) return;
    const nextUnread = !n.unread;
    // Optimistic
    setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, unread: nextUnread } : x)));
    setUnreadCount((c) => Math.max(0, c + (nextUnread ? +1 : -1)));
    try {
      await api.patch(`notificaciones/${n.id}/read/`, { unread: nextUnread });
      emitNotificationsRefresh();
    } catch (err) {
      // rollback
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, unread: !nextUnread } : x)));
      setUnreadCount((c) => Math.max(0, c + (nextUnread ? -1 : +1)));
      console.error("[NotificacionesAdminPage] toggle read failed", err);
    }
  };

  const goBack = () => {
    if (window.history.length > 1) navigate(-1);
    else navigate("/admin");
  };

  return (
    <Box minH="100vh" bg={bg}>
      <Box maxW="6xl" mx="auto" px={4} py={8}>
        <HStack justify="space-between" align="center" mb={4}>
          <HStack spacing={3}>
            <Tooltip label="Volver">
              <Button onClick={goBack} leftIcon={<ArrowBackIcon />} variant="ghost" size="sm">
                Volver
              </Button>
            </Tooltip>
            <FaBell />
            <Heading as="h2" size="lg">Notificaciones (Admin)</Heading>
            {unreadCount > 0 && (
              <Badge colorScheme="orange" variant="solid">
                {unreadCount > 99 ? "99+" : unreadCount}
              </Badge>
            )}
          </HStack>

          <HStack spacing={2}>
            <Tooltip label="Refrescar">
              <IconButton aria-label="Refrescar" icon={<RepeatIcon />} onClick={loadFirstPage} variant="ghost" />
            </Tooltip>
            <Tooltip label="Marcar todas como leídas">
              <Button leftIcon={<CheckIcon />} variant="solid" onClick={markAll} isLoading={busyAll}>
                Marcar todas
              </Button>
            </Tooltip>
          </HStack>
        </HStack>

        <HStack mb={4} spacing={4} align="center">
          <Checkbox
            isChecked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
            colorScheme="orange"
          >
            Sólo no leídas
          </Checkbox>

          <HStack>
            <Text fontSize="sm" color={muted}>Tipo:</Text>
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              size="sm"
              maxW="260px"
              bg={input.bg}
            >
              {TYPE_OPTS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </Select>
          </HStack>
        </HStack>

        <Box bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl" p={{ base: 4, md: 6 }}>
          <Divider mb={4} />

          {loading ? (
            <VStack align="stretch" spacing={3}>
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} height="64px" rounded="md" />
              ))}
            </VStack>
          ) : items.length === 0 ? (
            <HStack color={muted}>
              <FaEnvelopeOpenText />
              <Text>No hay notificaciones para mostrar.</Text>
            </HStack>
          ) : (
            <VStack align="stretch" spacing={3}>
              {items.map((n) => (
                <Box
                  key={n.id}
                  borderWidth="1px"
                  rounded="md"
                  p={3}
                  bg={n.unread ? "orange.50" : "transparent"}
                >
                  <HStack justify="space-between" align="start">
                    <VStack align="start" spacing={1} w="full">
                      <HStack>
                        <Badge colorScheme={severityToScheme(n.severity)}>{n.type}</Badge>
                        {n.unread && <Badge colorScheme="orange">Nuevo</Badge>}
                      </HStack>
                      <Text fontWeight="semibold" noOfLines={1}>{n.title}</Text>
                      <Text fontSize="sm" color={muted} whiteSpace="pre-wrap">{n.body}</Text>
                      <Text fontSize="xs" color={muted}>{formatWhen(n.created_at)}</Text>
                    </VStack>

                    <VStack spacing={1} minW={isMobile ? "auto" : "120px"}>
                      {n.deeplink_path && (
                        <Tooltip label="Ir">
                          <IconButton
                            aria-label="Ir"
                            icon={<FaExternalLinkAlt />}
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(n.deeplink_path)}
                          />
                        </Tooltip>
                      )}
                      <Button size="xs" variant="ghost" onClick={() => toggleRead(n)}>
                        {n.unread ? "Marcar leída" : "Marcar no leída"}
                      </Button>
                    </VStack>
                  </HStack>
                </Box>
              ))}

              {hasMore && (
                <HStack justify="center" pt={2}>
                  <Button onClick={loadMore} isLoading={loadingMore} variant="outline">
                    Cargar más
                  </Button>
                </HStack>
              )}
            </VStack>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default NotificacionesAdminPage;
