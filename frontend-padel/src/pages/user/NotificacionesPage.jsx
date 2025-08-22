// src/pages/notificaciones/NotificacionesPage.jsx
import React, { useContext, useEffect, useMemo, useState, useCallback } from "react";
import {
  Box, Heading, HStack, VStack, Text, IconButton, Button,
  Badge, Divider, Checkbox, Skeleton, Tooltip, useBreakpointValue
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

const NotificacionesPage = () => {
  const { accessToken } = useContext(AuthContext);
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
  const [unreadCount, setUnreadCount] = useState(0);

  const loadFirstPage = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    try {
      const res = await api.get("notificaciones/", { params: { limit: LIMIT, offset: 0 } });
      const data = res.data?.results ?? res.data ?? [];
      setItems(data);
      setNextOffset(data.length);
      setHasMore(Boolean(res.data?.next));
      // unread count
      const rc = await api.get("notificaciones/unread_count/");
      setUnreadCount(rc.data?.unread_count ?? 0);
      console.debug("[NotificacionesPage] loaded", { count: data.length });
    } catch (err) {
      console.error("[NotificacionesPage] load error", err);
    } finally {
      setLoading(false);
    }
  }, [api]);

  const loadMore = async () => {
    if (!api || !hasMore || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await api.get("notificaciones/", { params: { limit: LIMIT, offset: nextOffset } });
      const data = res.data?.results ?? res.data ?? [];
      // de-dup por id por seguridad
      const byId = new Map(items.map(n => [n.id, n]));
      data.forEach(n => byId.set(n.id, n));
      const merged = Array.from(byId.values());
      setItems(merged);
      setNextOffset(nextOffset + data.length);
      setHasMore(Boolean(res.data?.next) && data.length > 0);
    } catch (err) {
      console.error("[NotificacionesPage] loadMore error", err);
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => { loadFirstPage(); }, [loadFirstPage]);

  const markAll = async () => {
    if (!api) return;
    setBusyAll(true);
    try {
      await api.post("notificaciones/read_all/");
      emitNotificationsRefresh(); // sincroniza campanita
      await loadFirstPage();     // resetea lista y contador
    } catch (err) {
      console.error("[NotificacionesPage] markAll failed", err);
    } finally {
      setBusyAll(false);
    }
  };

  const toggleRead = async (n) => {
    if (!api) return;
    const nextUnread = !n.unread;
    // Optimistic
    setItems(prev => prev.map(x => (x.id === n.id ? { ...x, unread: nextUnread } : x)));
    setUnreadCount(c => Math.max(0, c + (nextUnread ? +1 : -1)));
    try {
      await api.patch(`notificaciones/${n.id}/read/`, { unread: nextUnread });
      emitNotificationsRefresh();
    } catch (err) {
      // rollback
      setItems(prev => prev.map(x => (x.id === n.id ? { ...x, unread: !nextUnread } : x)));
      setUnreadCount(c => Math.max(0, c + (nextUnread ? -1 : +1)));
      console.error("[NotificacionesPage] toggle read failed", err);
    }
  };

  // Filtro client-side (no rompemos el paginado del backend)
  const visible = unreadOnly ? items.filter(n => n.unread) : items;

  // ➕ Volver
  const goBack = () => {
    if (window.history.length > 1) navigate(-1);
    else navigate("/jugador");
  };

  return (
    <Box minH="100vh" bg={bg}>
      <Box maxW="5xl" mx="auto" px={4} py={8}>
        <HStack justify="space-between" align="center" mb={4}>
          <HStack spacing={3}>
            <Tooltip label="Volver">
              <Button
                onClick={goBack}
                leftIcon={<ArrowBackIcon />}
                variant="ghost"
                size="sm"
              >
                Volver
              </Button>
            </Tooltip>
            <FaBell />
            <Heading as="h2" size="lg">Notificaciones</Heading>
            {unreadCount > 0 && (
              <Badge colorScheme="orange" variant="solid">
                {unreadCount > 99 ? "99+" : unreadCount}
              </Badge>
            )}
          </HStack>

          <HStack spacing={2}>
            <Tooltip label="Refrescar">
              <IconButton
                aria-label="Refrescar"
                icon={<RepeatIcon />}
                onClick={loadFirstPage}
                variant="ghost"
              />
            </Tooltip>
            <Tooltip label="Marcar todas como leídas">
              <Button
                leftIcon={<CheckIcon />}
                variant="solid"
                onClick={markAll}
                isLoading={busyAll}
              >
                Marcar todas
              </Button>
            </Tooltip>
          </HStack>
        </HStack>

        <HStack mb={4} spacing={4}>
          <Checkbox
            isChecked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
            colorScheme="orange"
          >
            Sólo no leídas
          </Checkbox>
          {/* espacio para futuros filtros (severity, búsqueda, etc.) */}
        </HStack>

        <Box bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl" p={{ base: 4, md: 6 }}>
          <Divider mb={4} />

          {loading ? (
            <VStack align="stretch" spacing={3}>
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} height="64px" rounded="md" />
              ))}
            </VStack>
          ) : visible.length === 0 ? (
            <HStack color={muted}>
              <FaEnvelopeOpenText />
              <Text>No hay notificaciones para mostrar.</Text>
            </HStack>
          ) : (
            <VStack align="stretch" spacing={3}>
              {visible.map((n) => (
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
                      {n.metadata && Object.keys(n.metadata).length > 0 && (
                        <Text fontSize="xs" color={muted}>
                          {/* mostrar campos de metadata si hace falta */}
                        </Text>
                      )}
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

export default NotificacionesPage;
