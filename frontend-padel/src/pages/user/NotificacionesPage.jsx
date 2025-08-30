// src/pages/notificaciones/NotificacionesPage.jsx
import React, { useContext, useEffect, useMemo, useState, useCallback } from "react";
import {
  Box,
  Heading,
  HStack,
  VStack,
  Text,
  IconButton,
  Button,
  Badge,
  Divider,
  Checkbox,
  Skeleton,
  Tooltip,
  useBreakpointValue,
  useDisclosure,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  SimpleGrid,
  Stack,
} from "@chakra-ui/react";
import { ArrowBackIcon, CheckIcon, RepeatIcon, DeleteIcon, ViewIcon } from "@chakra-ui/icons";
import { FaBell, FaEnvelopeOpenText } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { emitNotificationsRefresh } from "../../utils/notificationsBus";

import { useBodyBg, useCardColors, useMutedText } from "../../components/theme/tokens";

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

  const isMobile = useBreakpointValue({ base: true, md: false });

  const [items, setItems] = useState([]);
  const [nextOffset, setNextOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busyAll, setBusyAll] = useState(false);
  const [busyDelete, setBusyDelete] = useState(false);

  const delAllDlg = useDisclosure();

  const [unreadOnly, setUnreadOnly] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Modal de detalle
  const detailDlg = useDisclosure();
  const [selected, setSelected] = useState(null);

  const openDetail = (n) => {
    setSelected(n);
    detailDlg.onOpen();
  };

  const closeDetail = () => {
    setSelected(null);
    detailDlg.onClose();
  };

  const fetchPage = useCallback(
    async ({ offset = 0, merge = false } = {}) => {
      if (!api) return;

      const res = await api.get("notificaciones/", { params: { limit: LIMIT, offset } });
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
    [api]
  );

  const loadFirstPage = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    try {
      await fetchPage({ offset: 0, merge: false });
      const rc = await api.get("notificaciones/unread_count/");
      setUnreadCount(rc.data?.unread_count ?? 0);
    } catch (err) {
      console.error("[NotificacionesPage] load error", err);
    } finally {
      setLoading(false);
    }
  }, [api, fetchPage]);

  useEffect(() => { loadFirstPage(); }, [loadFirstPage]);

  const loadMore = async () => {
    if (!api || !hasMore || loadingMore) return;
    setLoadingMore(true);
    try {
      await fetchPage({ offset: nextOffset, merge: true });
    } catch (err) {
      console.error("[NotificacionesPage] loadMore error", err);
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
      console.error("[NotificacionesPage] markAll failed", err);
    } finally {
      setBusyAll(false);
    }
  };

  const deleteAllShown = async () => {
    if (!api) return;
    const ids = visible.map((n) => n.id);
    if (ids.length === 0) {
      delAllDlg.onClose();
      return;
    }
    setBusyDelete(true);
    try {
      await api.post("notificaciones/bulk_delete/", { ids });
      emitNotificationsRefresh();
      await loadFirstPage();
    } catch (err) {
      console.error("[NotificacionesPage] deleteAllShown failed", err);
    } finally {
      setBusyDelete(false);
      delAllDlg.onClose();
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
      console.error("[NotificacionesPage] toggle read failed", err);
    }
  };

  // Filtro client-side (no rompemos el paginado del backend)
  const visible = unreadOnly ? items.filter((n) => n.unread) : items;

  // ➕ Volver
  const goBack = () => {
    if (window.history.length > 1) navigate(-1);
    else navigate("/jugador");
  };

  // Pretty JSON seguro
  const pretty = (obj) => {
    try { return JSON.stringify(obj ?? {}, null, 2); } catch { return String(obj ?? ""); }
  };

  return (
    <Box minH="100vh" bg={bg}>
      <Box maxW="5xl" mx="auto" px={4} py={8}>
        {/* Header */}
        <Stack spacing={{ base: 2, md: 3 }} mb={4}>
          {/* Fila 1: volver + título (badge incluido). Acciones solo desktop a la derecha */}
          <HStack justify="space-between" align="center">
            <HStack spacing={3} align="center">
              <Tooltip label="Volver">
                <Button onClick={goBack} leftIcon={<ArrowBackIcon />} variant="ghost" size="sm">
                  Volver
                </Button>
              </Tooltip>
              <FaBell />
              <Heading as="h2" size={{ base: "md", md: "lg" }}>Notificaciones</Heading>
              {unreadCount > 0 && (
                <Badge colorScheme="orange" variant="solid">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </Badge>
              )}
            </HStack>

            {/* Acciones en desktop */}
            <HStack spacing={2} display={{ base: "none", md: "flex" }}>
              <Tooltip label="Refrescar">
                <IconButton
                  aria-label="Refrescar"
                  icon={<RepeatIcon />}
                  onClick={loadFirstPage}
                  variant="ghost"
                />
              </Tooltip>
              <Tooltip label="Marcar todas como leídas">
                <Button leftIcon={<CheckIcon />} variant="solid" onClick={markAll} isLoading={busyAll}>
                  Marcar
                </Button>
              </Tooltip>
              <Tooltip label="Borrar todas las mostradas">
                <Button
                  leftIcon={<DeleteIcon />}
                  variant="outline"
                  colorScheme="red"
                  onClick={delAllDlg.onOpen}
                  isLoading={busyDelete}
                >
                  Borrar
                </Button>
              </Tooltip>
            </HStack>
          </HStack>

          {/* Acciones en mobile: grid 3 columnas */}
          <SimpleGrid columns={3} spacing={2} display={{ base: "grid", md: "none" }}>
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
                size="sm"
              >
                Marcar
              </Button>
            </Tooltip>
            <Tooltip label="Borrar todas las mostradas">
              <Button
                leftIcon={<DeleteIcon />}
                variant="outline"
                colorScheme="red"
                onClick={delAllDlg.onOpen}
                isLoading={busyDelete}
                size="sm"
              >
                Borrar
              </Button>
            </Tooltip>
          </SimpleGrid>
        </Stack>

        {/* Filtros */}
        <Stack direction={{ base: "column", md: "row" }} mb={4} spacing={4}>
          <Checkbox
            isChecked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
            colorScheme="orange"
          >
            Sólo no leídas
          </Checkbox>
        </Stack>

        <Box bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl" p={{ base: 4, md: 6 }}>
          <Divider mb={4} />

          {loading ? (
            <VStack align="stretch" spacing={3}>
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} height={{ base: "56px", md: "64px" }} rounded="md" />
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
                  <Stack
                    direction={{ base: "column", md: "row" }}
                    justify="space-between"
                    align={{ base: "stretch", md: "start" }}
                    spacing={{ base: 2, md: 3 }}
                  >
                    <VStack align="start" spacing={1} w="full">
                      <HStack>
                        <Badge colorScheme={severityToScheme(n.severity)}>{n.type}</Badge>
                        {n.unread && <Badge colorScheme="orange">Nuevo</Badge>}
                      </HStack>
                      <Text fontWeight="semibold" noOfLines={1}>{n.title}</Text>
                      <Text
                        fontSize="sm"
                        color={muted}
                        whiteSpace="pre-wrap"
                        noOfLines={{ base: 3, md: undefined }}
                      >
                        {n.body}
                      </Text>
                      <Text fontSize="xs" color={muted}>{formatWhen(n.created_at)}</Text>
                    </VStack>

                    <HStack spacing={2} justify={{ base: "flex-end", md: "flex-start" }} align="center">
                      <Tooltip label="Ver detalles">
                        <IconButton
                          aria-label="Ver detalles"
                          icon={<ViewIcon />}
                          size="sm"
                          variant="outline"
                          onClick={() => openDetail(n)}
                        />
                      </Tooltip>
                      <Button size="xs" variant="ghost" onClick={() => toggleRead(n)}>
                        {n.unread ? "Marcar leída" : "Marcar no leída"}
                      </Button>
                    </HStack>
                  </Stack>
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

      {/* Confirmación borrar todas (las visibles) */}
      <AlertDialog isOpen={delAllDlg.isOpen} onClose={delAllDlg.onClose} isCentered size={{ base: "xs", md: "md" }}>
        <AlertDialogOverlay />
        <AlertDialogContent>
          <AlertDialogHeader fontWeight="bold">Borrar notificaciones</AlertDialogHeader>
          <AlertDialogBody>
            Vas a borrar <b>{visible.length}</b> notificación(es) <i>de la lista mostrada</i>.
            Esta acción no se puede deshacer.
          </AlertDialogBody>
          <AlertDialogFooter>
            <Button onClick={delAllDlg.onClose} variant="ghost">Cancelar</Button>
            <Button ml={3} colorScheme="red" onClick={deleteAllShown} isLoading={busyDelete}>
              Borrar todas
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Modal de detalles */}
      <Modal isOpen={detailDlg.isOpen} onClose={closeDetail} size={{ base: "full", md: "lg" }} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Detalle de notificación</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {!selected ? null : (
              <VStack align="stretch" spacing={3}>
                <HStack>
                  <Badge colorScheme={severityToScheme(selected.severity)}>{selected.type}</Badge>
                  {selected.unread && <Badge colorScheme="orange">Nuevo</Badge>}
                </HStack>
                <Text fontWeight="semibold">{selected.title}</Text>
                <Text whiteSpace="pre-wrap">{selected.body}</Text>
                <Text fontSize="sm" color={muted}>
                  Creada: {formatWhen(selected.created_at)}
                </Text>

                {selected.metadata && Object.keys(selected.metadata || {}).length > 0 && (
                  <Box>
                    <Text fontWeight="semibold" mb={1}>Metadata</Text>
                    <Box
                      as="pre"
                      fontSize="sm"
                      p={3}
                      bg="gray.50"
                      borderWidth="1px"
                      rounded="md"
                      overflowX="auto"
                    >
                      {pretty(selected.metadata)}
                    </Box>
                  </Box>
                )}
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button onClick={closeDetail}>Cerrar</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default NotificacionesPage;
