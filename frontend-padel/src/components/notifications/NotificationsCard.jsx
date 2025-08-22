import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  Box, HStack, VStack, Text, IconButton, Badge, Button, Divider, Tooltip, Skeleton, Link,
} from "@chakra-ui/react";
import { AuthContext } from "../../auth/AuthContext";
import { useCardColors, useMutedText } from "../theme/tokens";
import { axiosAuth } from "../../utils/axiosAuth";
import { CheckIcon, RepeatIcon } from "@chakra-ui/icons";
import { FaBell, FaExternalLinkAlt, FaEnvelopeOpenText } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

const severityToScheme = (sev) => {
  switch (sev) {
    case "error": return "red";
    case "warning": return "orange";
    default: return "blue";
  }
};
const formatWhen = (iso) => {
  try { return new Date(iso).toLocaleString(); } catch { return iso ?? ""; }
};

const NotificationsCard = ({ limit = 5, pollMs = 60000, anchorId }) => {
  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);
  const card = useCardColors();
  const muted = useMutedText();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!api) return;
    setLoading(true);
    try {
      const res = await api.get("notificaciones/", { params: { limit, offset: 0 } });
      const data = res.data?.results ?? res.data ?? [];
      setItems(data);
      const rc = await api.get("notificaciones/unread_count/");
      setUnreadCount(rc.data?.unread_count ?? 0);
      console.debug("[NotificationsCard] loaded", { count: data.length, unread: rc.data?.unread_count });
    } catch (err) {
      console.error("[NotificationsCard] load error", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (!pollMs) return;
    const id = setInterval(load, pollMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const toggleRead = async (n) => {
    if (!api) return;
    const nextUnread = !n.unread;
    setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, unread: nextUnread } : x)));
    setUnreadCount((c) => Math.max(0, c + (nextUnread ? +1 : -1)));
    try {
      await api.patch(`notificaciones/${n.id}/read/`, { unread: nextUnread });
    } catch (err) {
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, unread: !nextUnread } : x)));
      setUnreadCount((c) => Math.max(0, c + (nextUnread ? -1 : +1)));
      console.error("[NotificationsCard] toggle read failed", err);
    }
  };

  const markAll = async () => {
    if (!api) return;
    setBusy(true);
    try {
      await api.post("notificaciones/read_all/");
      await load();
    } catch (err) {
      console.error("[NotificationsCard] markAll failed", err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box
      id={anchorId}
      w="100%"
      bg={card.bg}
      color={card.color}
      rounded="xl"
      boxShadow="2xl"
      p={{ base: 4, md: 6 }}
      display="flex"
      flexDirection="column"
      minH="0"
    >
      <HStack justify="space-between" mb={2}>
        <HStack spacing={2}>
          <FaBell />
          <Text fontWeight="bold">Notificaciones</Text>
          {unreadCount > 0 && (
            <Badge colorScheme="orange" variant="solid">
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </HStack>

        <HStack spacing={3}>
          <Link fontSize="sm" onClick={() => navigate("/notificaciones")}>
            Ver todas
          </Link>
          <Tooltip label="Marcar todas como leídas">
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<CheckIcon />}
              onClick={markAll}
              isLoading={busy}
            >
              Marcar todas
            </Button>
          </Tooltip>
          <Tooltip label="Actualizar">
            <IconButton
              aria-label="Actualizar"
              icon={<RepeatIcon />}
              size="sm"
              variant="ghost"
              onClick={load}
              isDisabled={loading}
            />
          </Tooltip>
        </HStack>
      </HStack>

      <Divider my={3} />

      {loading ? (
        <VStack align="stretch" spacing={3}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} height="64px" rounded="md" />
          ))}
        </VStack>
      ) : items.length === 0 ? (
        <HStack color={muted}>
          <FaEnvelopeOpenText />
          <Text fontSize="sm">No tenés notificaciones por ahora.</Text>
        </HStack>
      ) : (
        <VStack align="stretch" spacing={3} flex="1 1 auto" minH={0}>
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
                  <Text fontSize="sm" color={muted} noOfLines={2}>{n.body}</Text>
                  <Text fontSize="xs" color={muted}>{formatWhen(n.created_at)}</Text>
                </VStack>

                <VStack spacing={1}>
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
        </VStack>
      )}
    </Box>
  );
};

export default NotificationsCard;
