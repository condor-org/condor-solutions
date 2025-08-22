// src/pages/admin/CancelacionesPage.jsx
import React, {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import {
  Box,
  Heading,
  Text,
  HStack,
  VStack,
  SimpleGrid,
  Select,
  Input,
  Textarea,
  RadioGroup,
  Radio,
  Stack,
  Skeleton,
  Badge,
  useToast,
  useDisclosure,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter
} from "@chakra-ui/react";

import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import Button from "../../components/ui/Button";

import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { useCardColors, useMutedText } from "../../components/theme/tokens";

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
      const arr = Array.isArray(data) ? data : (data?.results || []);
      return arr;
    }

    while (true) {
      page += 1;
      const results = data?.results ?? [];
      items.push(...results);

      if (!data?.next || results.length === 0 || page >= maxPages) break;

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

const toLocalDate = (t) => {
  if (!t?.fecha || !t?.hora) return null;
  const dt = new Date(`${t.fecha}T${t.hora}`);
  return isNaN(dt) ? null : dt;
};

/* ========= Page ========= */
const CancelacionesPage = () => {
  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);

  const toast = useToast();
  const card = useCardColors();
  const muted = useMutedText();

  // Filtros
  const [sedeId, setSedeId] = useState("");
  const [modo, setModo] = useState("profesor"); // 'profesor' | 'masiva'
  const [profesorId, setProfesorId] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [motivo, setMotivo] = useState("");

  // Datos
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);

  // Preview
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [coincidencias, setCoincidencias] = useState([]);

  // Confirm
  const confirmDlg = useDisclosure();
  const [cancelling, setCancelling] = useState(false);

  /* Cargar sedes */
  useEffect(() => {
    if (!api) return;
    api.get("turnos/sedes/")
      .then(res => setSedes(res.data?.results || res.data || []))
      .catch(() => setSedes([]));
  }, [api]);

  /* Cargar profesores por sede */
  useEffect(() => {
    if (!api || !sedeId) {
      setProfesores([]);
      setProfesorId("");
      return;
    }
    api.get("turnos/prestadores/", { params: { lugar_id: sedeId } })
      .then(res => setProfesores(res.data?.results || res.data || []))
      .catch(() => setProfesores([]));
  }, [api, sedeId]);

  const aplicarFiltrosLocales = useCallback((turnos) => {
    let out = Array.isArray(turnos) ? [...turnos] : [];

    if (sedeId) out = out.filter(t => String(t.lugar_id) === String(sedeId));
    if (modo === "profesor" && profesorId) out = out.filter(t => String(t.prestador_id) === String(profesorId));
    if (desde) out = out.filter(t => (t.fecha ?? "") >= desde);
    if (hasta) out = out.filter(t => (t.fecha ?? "") <= hasta);

    const ahora = new Date();
    out = out
      .map(t => ({ ...t, _dt: toLocalDate(t) }))
      .filter(t => t._dt && t._dt >= ahora)
      .sort((a, b) => a._dt - b._dt);

    return out;
  }, [sedeId, profesorId, modo, desde, hasta]);

  const preview = useCallback(async () => {
    if (!api) return;
    if (!sedeId) return toast({ title: "Elegí una sede", status: "warning" });
    if (modo === "profesor" && !profesorId) return toast({ title: "Elegí un profesor", status: "warning" });

    setLoadingPreview(true);
    setCoincidencias([]);
    try {
      // ✅ Igual que en usuario: reservados + próximos (+ filtros opcionales)
      const params = { estado: "reservado", upcoming: 1 };
      if (sedeId) params.lugar_id = sedeId;
      if (modo === "profesor" && profesorId) params.prestador_id = profesorId;

      const turnos = await fetchAllPages(api, "turnos/", {
        params,
        pageSize: 200,
        logTag: "admin-cancelaciones"
      });

      const lista = aplicarFiltrosLocales(turnos);
      setCoincidencias(lista);
      if (lista.length === 0) {
        toast({ title: "No hay turnos para cancelar con esos filtros", status: "info" });
      }
    } catch (e) {
      console.error("[preview] error", e);
      toast({ title: "Error al buscar turnos", status: "error" });
    } finally {
      setLoadingPreview(false);
    }
  }, [api, sedeId, profesorId, modo, aplicarFiltrosLocales, toast]);

  const runCancel = async () => {
    if (!api || coincidencias.length === 0) return;
    setCancelling(true);

    let ok = 0, fail = 0;
    for (const t of coincidencias) {
      try {
        await api.post("turnos/cancelar/", {
          turno_id: t.id,
          motivo_admin: motivo || "Cancelación masiva por administración"
        });
        ok += 1;
      } catch (e) {
        fail += 1;
      }
    }
    setCancelling(false);
    confirmDlg.onClose();

    toast({
      title: "Cancelación masiva finalizada",
      description: `Cancelados: ${ok} · Fallidos: ${fail}`,
      status: fail > 0 ? "warning" : "success",
      duration: 6000
    });

    // refresco
    preview();
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
          { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" }
        ]}
      />

      <Box flex="1" p={[4, 6, 8]}>
        <Heading size="md" mb={6}>Cancelaciones</Heading>

        <Box bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl" p={{ base: 4, md: 6 }}>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Box>
              <Text fontWeight="semibold" mb={1}>Sede</Text>
              <Select value={sedeId} onChange={(e) => setSedeId(e.target.value)} placeholder="Elegí una sede">
                {sedes.map(s => (
                  <option key={s.id} value={s.id}>{s.nombre || s.alias || `Sede #${s.id}`}</option>
                ))}
              </Select>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Modo</Text>
              <RadioGroup value={modo} onChange={setModo}>
                <HStack spacing={6}>
                  <Radio value="profesor">Por profesor</Radio>
                  <Radio value="masiva">Masiva (por rango)</Radio>
                </HStack>
              </RadioGroup>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Profesor</Text>
              <Select
                value={profesorId}
                onChange={(e) => setProfesorId(e.target.value)}
                placeholder={modo === "profesor" ? "Elegí un profesor" : "— no aplica —"}
                isDisabled={modo !== "profesor"}
              >
                {profesores.map(p => (
                  <option key={p.id} value={p.id}>{p.nombre || p.email || `Profesor #${p.id}`}</option>
                ))}
              </Select>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Desde (fecha)</Text>
              <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
              <Text fontSize="xs" color={muted} mt={1}>Opcional (filtro local).</Text>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Hasta (fecha)</Text>
              <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
              <Text fontSize="xs" color={muted} mt={1}>Opcional (filtro local).</Text>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Motivo (interno)</Text>
              <Textarea
                placeholder="Ej.: Profesor enfermo / Corte de luz / Lluvia"
                rows={3}
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
              />
            </Box>
          </SimpleGrid>

          <HStack mt={6} spacing={3}>
            <Button onClick={preview} variant="primary">Buscar turnos</Button>
            <Button
              variant="danger"
              onClick={confirmDlg.onOpen}
              isDisabled={coincidencias.length === 0}
            >
              Cancelar seleccionados ({coincidencias.length})
            </Button>
          </HStack>

          <Heading size="sm" mt={8} mb={3}>Previsualización</Heading>

          {loadingPreview ? (
            <Stack spacing={3}>
              <Skeleton height="78px" rounded="md" />
              <Skeleton height="78px" rounded="md" />
              <Skeleton height="78px" rounded="md" />
            </Stack>
          ) : coincidencias.length === 0 ? (
            <Text color={muted}>No hay turnos para mostrar.</Text>
          ) : (
            <VStack align="stretch" spacing={3}>
              {coincidencias.map((t) => (
                <Box key={t.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
                  <HStack justify="space-between" align="start">
                    <Box>
                      <Text fontWeight="semibold">{t.lugar_nombre || t.lugar || "Sede"}</Text>
                      <Text fontSize="sm" color={muted}>
                        {t.fecha} · {t.hora?.slice(0, 5)} {t.prestador_nombre ? `· ${t.prestador_nombre}` : ""}
                      </Text>
                      <HStack mt={2} spacing={2}>
                        <Badge colorScheme="green" variant="subtle">reservado</Badge>
                        {t.prestador_nombre && <Badge variant="outline">{t.prestador_nombre}</Badge>}
                      </HStack>
                    </Box>
                    <Badge variant="subtle">#{t.id}</Badge>
                  </HStack>
                </Box>
              ))}
            </VStack>
          )}
        </Box>
      </Box>

      {/* Confirmación */}
      <AlertDialog isOpen={confirmDlg.isOpen} onClose={confirmDlg.onClose} isCentered>
        <AlertDialogOverlay />
        <AlertDialogContent bg={card.bg} color={card.color}>
          <AlertDialogHeader fontWeight="bold">Confirmar cancelación</AlertDialogHeader>
          <AlertDialogBody>
            Vas a cancelar <b>{coincidencias.length}</b> turno(s).
            {modo === "profesor" && profesorId ? (
              <>
                <br />
                Profesor ID: <b>{profesorId}</b>
              </>
            ) : null}
            {(desde || hasta) && (
              <>
                <br />
                Rango: <b>{desde || "—"}</b> a <b>{hasta || "—"}</b>
              </>
            )}
            {motivo && (
              <>
                <br />
                Motivo: <i>{motivo}</i>
              </>
            )}
            <br />
            <Text mt={3} color={muted}>
              Se aplicará la política de bonificaciones vigente para cada usuario.
            </Text>
          </AlertDialogBody>
          <AlertDialogFooter>
            <Button variant="secondary" onClick={confirmDlg.onClose}>Volver</Button>
            <Button ml={3} variant="danger" onClick={runCancel} isLoading={cancelling}>
              Confirmar
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageWrapper>
  );
};

export default CancelacionesPage;
