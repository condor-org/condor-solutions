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
  AlertDialogFooter,
  Switch,
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
      page = 1;
      const results = data?.results ?? [];
      items.push(...results);

      if (!data?.next || results.length === 0 || page >= maxPages) break;

      const isAbsolute = typeof data.next === "string" && /^https?:\/\//i.test(data.next);
      if (isAbsolute) {
        // Extraer la ruta relativa de la URL absoluta
        const url = new URL(data.next);
        const relativePath = url.pathname + url.search;
        res = await api.get(relativePath);
      } else {
        const nextOffset = (currentParams.offset ?? 0)  (currentParams.limit ?? pageSize);
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

const toISO = (v) => {
  if (!v) return "";
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(v)) {
    const [d, m, y] = v.split("/").map(Number);
    return `${y}-${String(m).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
  }
  return String(v);
};

const mapFromDetalleMuestra = (data) => {
  const det = Array.isArray(data?.detalle_muestra) ? data.detalle_muestra : [];
  return det.map(d => ({
    id: d.turno_id,
    estado_previo: d.estado_previo,
    usuario_id: d.usuario_id,
    emitio_bono: d.emitio_bono,
    bono_id: d.bono_id,
    razon_skip: d.razon_skip
  }));
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
  const [horaDesde, setHoraDesde] = useState("");   // 🕒 NUEVO
  const [horaHasta, setHoraHasta] = useState("");   // 🕒 NUEVO
  const [motivo, setMotivo] = useState("");
  const [dryRun, setDryRun] = useState(false);      // 🎚️ NUEVO (por defecto cancela real)

  // Datos
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);

  // Preview
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [coincidencias, setCoincidencias] = useState([]);
  const [resumen, setResumen] = useState(null);

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

  /* Buscar (dry-run SIEMPRE para preview) */
  const preview = useCallback(async () => {
    if (!api) return;

    if (modo === "masiva") {
      if (!sedeId) return toast({ title: "Elegí una sede", status: "warning" });
      if (!desde || !hasta) return toast({ title: "Completá el rango de fechas", status: "warning" });
    } else {
      if (!profesorId) return toast({ title: "Elegí un profesor", status: "warning" });
      if (!desde || !hasta) return toast({ title: "Completá el rango de fechas", status: "warning" });
    }

    setLoadingPreview(true);
    setCoincidencias([]);
    setResumen(null);

    try {
      let res;
      if (modo === "profesor") {
        const body = {
          fecha_inicio: toISO(desde),
          fecha_fin: toISO(hasta),
          ...(sedeId ? { sede_id: Number(sedeId) } : {}),
          ...(horaDesde ? { hora_inicio: horaDesde } : {}),  // 🕒 NUEVO
          ...(horaHasta ? { hora_fin: horaHasta } : {}),     // 🕒 NUEVO
          dry_run: true
        };
        res = await api.post(`turnos/prestadores/${Number(profesorId)}/cancelar_en_rango/`, body);
      } else {
        const body = {
          sede_id: Number(sedeId),
          fecha_inicio: toISO(desde),
          fecha_fin: toISO(hasta),
          ...(horaDesde ? { hora_inicio: horaDesde } : {}),  // 🕒 NUEVO
          ...(horaHasta ? { hora_fin: horaHasta } : {}),     // 🕒 NUEVO
          dry_run: true
        };
        res = await api.post("turnos/admin/cancelar_por_sede/", body);
      }

      setResumen(res.data || null);

      let lista = mapFromDetalleMuestra(res.data);

      if (lista.some(x => x.estado_previo === "reservado")) {
        try {
          const reservados = await fetchAllPages(api, "turnos/", {
            params: { estado: "reservado", upcoming: 1 },
            pageSize: 400,
            logTag: "admin-cancel-preview-lookup"
          });
          const byId = new Map(reservados.map(t => [t.id, t]));
          lista = lista.map(x => (byId.has(x.id) ? { ...x, ...byId.get(x.id) } : x));
        } catch (e) {
          console.warn("[preview][lookup turnos] no se pudo enriquecer", e);
        }
      }

      setCoincidencias(lista);
      if (lista.length === 0) {
        toast({ title: "No hay turnos coincidentes para ese rango.", status: "info" });
      }
    } catch (e) {
      console.error("[cancelaciones.preview] error", e?.response?.data || e);
      toast({ title: "Error al buscar turnos", status: "error" });
    } finally {
      setLoadingPreview(false);
    }
  }, [api, modo, profesorId, sedeId, desde, hasta, horaDesde, horaHasta, toast]);

  /* Ejecutar cancelación real o simulada (según toggle) */
  const runCancel = async () => {
    if (!api) return;
    if (!coincidencias.length) return;

    setCancelling(true);
    try {
      let res;
      if (modo === "profesor") {
        const body = {
          fecha_inicio: toISO(desde),
          fecha_fin: toISO(hasta),
          ...(sedeId ? { sede_id: Number(sedeId) } : {}),
          ...(horaDesde ? { hora_inicio: horaDesde } : {}),  // 🕒 NUEVO
          ...(horaHasta ? { hora_fin: horaHasta } : {}),     // 🕒 NUEVO
          ...(motivo ? { motivo } : {}),
          dry_run: !!dryRun                                  // 🎚️ NUEVO
        };
        res = await api.post(`turnos/prestadores/${Number(profesorId)}/cancelar_en_rango/`, body);
      } else {
        const body = {
          sede_id: Number(sedeId),
          fecha_inicio: toISO(desde),
          fecha_fin: toISO(hasta),
          ...(horaDesde ? { hora_inicio: horaDesde } : {}),  // 🕒 NUEVO
          ...(horaHasta ? { hora_fin: horaHasta } : {}),     // 🕒 NUEVO
          ...(motivo ? { motivo } : {}),
          dry_run: !!dryRun                                   // 🎚️ NUEVO
        };
        res = await api.post("turnos/admin/cancelar_por_sede/", body);
      }

      const tot = res?.data?.totales;
      toast({
        title: dryRun ? "Simulación ejecutada" : "Cancelación realizada",
        description: tot
          ? `Cancelados: ${tot.cancelados} · Reservados en el rango: ${tot.reservados}`
          : (dryRun ? "Simulación finalizada" : "Cancelación finalizada"),
        status: "success",
        duration: 6000
      });

      setResumen(res.data || null);
      confirmDlg.onClose();
      await preview(); // refrescar previsualización
    } catch (e) {
      console.error("[cancelaciones.runCancel] error", e?.response?.data || e);
      toast({ title: "Error al cancelar turnos", status: "error" });
    } finally {
      setCancelling(false);
    }
  };

  return (
    <PageWrapper>
      <Sidebar
        links={[
          { label: "Dashboard", path: "/admin" },
          { label: "Sedes", path: "/admin/sedes" },
          { label: "Profesores", path: "/admin/profesores" },
          { label: "Agenda", path: "/admin/agenda" },
          { label: "Usuarios", path: "/admin/usuarios" },
          { label: "Cancelaciones", path: "/admin/cancelaciones" },
          { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
          { label: "Abonos (Asignar)", path: "/admin/abonos" },
        ]}
      />

      <Box flex="1" p={[4, 6, 8]}>
        <Heading size="md" mb={6}>Cancelaciones</Heading>

        <Box bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl" p={{ base: 4, md: 6 }}>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Box>
              <Text fontWeight="semibold" mb={1}>Sede</Text>
              <Select value={sedeId} onChange={(e) => setSedeId(e.target.value)} placeholder="Elegí una sede"  size={{ base: "sm", md: "md" }}>
                {sedes.map(s => (
                  <option key={s.id} value={s.id}>{s.nombre || s.alias || `Sede #${s.id}`}</option>
                ))}
              </Select>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Modo</Text>
              <RadioGroup value={modo} onChange={setModo}>
                <Stack direction={{ base: "column", md: "row" }} spacing={{ base: 2, md: 6 }}>
                  <Radio value="profesor" size={{ base: "sm", md: "md" }}>Por profesor</Radio>
                  <Radio value="masiva" size={{ base: "sm", md: "md" }}>Masiva (por sede)</Radio>
                </Stack>
              </RadioGroup>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Profesor</Text>
              <Select
                value={profesorId}
                onChange={(e) => setProfesorId(e.target.value)}
                placeholder={modo === "profesor" ? "Elegí un profesor" : "— no aplica —"}
                isDisabled={modo !== "profesor"}
                size={{ base: "sm", md: "md" }}
              >
                {profesores.map(p => (
                  <option key={p.id} value={p.id}>{p.nombre || p.email || `Profesor #${p.id}`}</option>
                ))}
              </Select>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Desde (fecha)</Text>
              <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} size={{ base: "sm", md: "md" }}/>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>Hasta (fecha)</Text>
              <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} size={{ base: "sm", md: "md" }}/>
            </Box>

            <Box gridColumn={{ base: "auto", md: "1 / -1" }}>
              <Text fontWeight="semibold" mb={1}>Motivo (interno)</Text>
              <Textarea
                placeholder="Ej.: Profesor enfermo / Corte de luz / Lluvia"
                rows={3}
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                size={{ base: "sm", md: "md" }}
              />
            </Box>

            {/* 🕒 NUEVO: RANGO HORARIO */}
            <Box>
              <Text fontWeight="semibold" mb={1}>Desde (hora)</Text>
              <Input type="time" value={horaDesde} onChange={(e) => setHoraDesde(e.target.value)} size={{ base: "sm", md: "md" }}/>
            </Box>
            <Box>
              <Text fontWeight="semibold" mb={1}>Hasta (hora)</Text>
              <Input type="time" value={horaHasta} onChange={(e) => setHoraHasta(e.target.value)} size={{ base: "sm", md: "md" }}/>
            </Box>
          </SimpleGrid>

          <Stack
            mt={6}
            spacing={{ base: 3, md: 6 }}
            direction={{ base: "column", md: "row" }}
            align={{ base: "stretch", md: "center" }}
            flexWrap="nowrap"
          >
            {/* 🎚️ Toggle de simulación (no wrap) */}
            <HStack minW={{ md: "260px" }}>
              <Switch
                id="dry-run"
                isChecked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              <Text htmlFor="dry-run" whiteSpace="nowrap">
                Sólo simular (no cancela)
              </Text>
            </HStack>

            {/* Botones con ancho fijo en desktop para evitar “saltos” */}
            <Stack
              direction={{ base: "column", md: "row" }}
              spacing={3}
              w={{ base: "100%", md: "auto" }}
              flex="1 1 auto"
            >
              <Button
                onClick={preview}
                variant="primary"
                isFullWidth
                w={{ base: "100%", md: "180px" }}
              >
                Buscar turnos
              </Button>
              <Button
                variant={dryRun ? "secondary" : "danger"}
                onClick={confirmDlg.onOpen}
                isDisabled={coincidencias.length === 0}
                isFullWidth
                w={{ base: "100%", md: "260px" }}
              >
                {dryRun ? "Simular cancelación" : `Cancelar seleccionados (${coincidencias.length})`}
              </Button>
            </Stack>
          </Stack>

          {resumen?.totales && (
            <Box mt={6} p={3} borderWidth="1px" rounded="md">
              <Text fontWeight="semibold" mb={2}>Totales (vista previa)</Text>
              <HStack spacing={3} wrap="wrap">
                <Badge>En rango: {resumen.totales.en_rango}</Badge>
                <Badge colorScheme="green">Reservados: {resumen.totales.reservados}</Badge>
                <Badge colorScheme="red">Cancelarían: {resumen.totales.cancelados}</Badge>
              </HStack>
            </Box>
          )}

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
              {coincidencias.map((t) => {
                const isPretty = t.fecha && t.hora; // enriquecido
                return (
                  <Box key={t.id} p={3} bg={card.bg} rounded="md" borderWidth="1px">
                    <Stack direction={{ base: "column", md: "row" }} justify="space-between" align="start" spacing={{ base: 2, md: 3 }}>
                      <Box flex="1 1 auto">
                        <Text fontWeight="semibold">
                          {isPretty
                            ? (t.lugar_nombre || t.lugar || "Sede")
                            : `Turno #${t.id}`}
                        </Text>
                        <Text fontSize="sm" color={muted} noOfLines={{ base: 3, md: undefined }}>
                        {isPretty
                          ? [
                              t.fecha,
                              t.hora?.slice(0,5),
                              (t.lugar_nombre || t.lugar || "Sede"),
                              // Profesor
                              (t.prestador_nombre || t.profesor_nombre || t.profesor || null),
                              // Usuario (quién reservó) — mostramos nombre/alias/email si está
                              (t.usuario || t.usuario_nombre || t.usuario_alias || t.usuario_email || (t.usuario_id ? `Usuario #${t.usuario_id}` : null))
                            ]
                              .filter(Boolean)
                              .join(" · ")
                          : `Estado previo: ${t.estado_previo}${
                              t.usuario || t.usuario_nombre || t.usuario_alias || t.usuario_email
                                ? ` · ${(t.usuario || t.usuario_nombre || t.usuario_alias || t.usuario_email)}`
                                : (t.usuario_id ? ` · Usuario #${t.usuario_id}` : "")
                            }`
                        }
                        </Text>
                        <HStack mt={2} spacing={2}>
                          <Badge colorScheme={t.estado_previo === "reservado" ? "green" : "gray"} variant="subtle">
                            {t.estado_previo}
                          </Badge>
                          {t.prestador_nombre && <Badge variant="outline">{t.prestador_nombre}</Badge>}
                        </HStack>
                      </Box>
                      <Badge variant="subtle" alignSelf={{ base: "flex-start", md: "center" }}>#{t.id}</Badge>
                    </Stack>
                  </Box>
                );
              })}
            </VStack>
          )}
        </Box>
      </Box>

      {/* Confirmación */}
      <AlertDialog isOpen={confirmDlg.isOpen} onClose={confirmDlg.onClose} isCentered>
        <AlertDialogOverlay />
        <AlertDialogContent bg={card.bg} color={card.color}>
          <AlertDialogHeader fontWeight="bold">
            {dryRun ? "Confirmar simulación" : "Confirmar cancelación"}
          </AlertDialogHeader>
          <AlertDialogBody>
            {dryRun ? (
              <>Se ejecutará una <b>simulación</b> (no se modifican turnos).</>
            ) : (
              <>Vas a cancelar <b>{coincidencias.length}</b> turno(s).</>
            )}
            {modo === "profesor" && profesorId ? (
              <>
                <br />
                Profesor ID: <b>{profesorId}</b>
              </>
            ) : null}
            {(desde || hasta) && (
              <>
                <br />
                Rango fecha: <b>{desde || "—"}</b> a <b>{hasta || "—"}</b>
              </>
            )}
            {(horaDesde || horaHasta) && (
              <>
                <br />
                Rango hora: <b>{horaDesde || "—"}</b> a <b>{horaHasta || "—"}</b>
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
            <Button ml={3} variant={dryRun ? "secondary" : "danger"} onClick={runCancel} isLoading={cancelling}>
              {dryRun ? "Simular" : "Confirmar"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageWrapper>
  );
};

export default CancelacionesPage;
