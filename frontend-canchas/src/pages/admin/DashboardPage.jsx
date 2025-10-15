// src/pages/admin/DashboardPage.jsx
import React, { useContext, useEffect, useState } from "react";
import {
  Box,
  Heading,
  SimpleGrid,
  Text,
} from "@chakra-ui/react";
import { FaUserAlt, FaCalendarCheck, FaMoneyBillWave } from "react-icons/fa";
import { AuthContext } from "../../auth/AuthContext";
import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import Button from "../../components/ui/Button";
import SummaryCard from "../../components/dashboard/SummaryCard";
import { axiosAuth } from "../../utils/axiosAuth";
import { toast } from "react-toastify";
import { useCardColors, useMutedText } from "../../components/theme/tokens";

const DashboardPage = () => {
  const { user, accessToken } = useContext(AuthContext);

  const [usuariosCount, setUsuariosCount] = useState(null);
  const [turnosCount, setTurnosCount] = useState(null);
  const [pagosPendientes, setPagosPendientes] = useState(null);
  const [loading, setLoading] = useState(true);

  // feedback de la generación
  const [generando, setGenerando] = useState(false);
  const [resultado, setResultado] = useState(null);

  const cardColors = useCardColors();
  const mutedColor = useMutedText();

  // métricas dashboard
  useEffect(() => {
    if (!accessToken) return;
    setLoading(true);
    const api = axiosAuth(accessToken);
    Promise.all([
      api.get("auth/usuarios/"),
      api.get("turnos/"),
      api.get("pagos/pendientes/"),
    ])
      .then(([usuariosRes, turnosRes, pagosRes]) => {
        setUsuariosCount(Array.isArray(usuariosRes.data)
          ? usuariosRes.data.length
          : usuariosRes.data?.count ?? 0);
        setTurnosCount(Array.isArray(turnosRes.data)
          ? turnosRes.data.length
          : turnosRes.data?.count ?? 0);
        setPagosPendientes(Array.isArray(pagosRes.data)
          ? pagosRes.data.length
          : pagosRes.data?.count ?? 0);
      })
      .catch(() => toast.error("Error al cargar métricas del dashboard"))
      .finally(() => setLoading(false));
  }, [accessToken]);

  // GENERAR TURNOS DIRECTO (sin modal, sin parámetros)
  const handleGenerarTurnos = async () => {
    if (!accessToken) return;
    setGenerando(true);
    setResultado(null);
    const api = axiosAuth(accessToken);
    try {
      // Llama al endpoint que ya adaptaste para usar el service mensual y
      // devolver el mismo shape de siempre.
      // Si el endpoint quedó en "turnos/generar/", mantenelo:
      const res = await api.post("turnos/generar/", {}); 
      setResultado(res.data);

      toast.success(`¡Turnos generados! Total: ${res.data?.turnos_generados ?? 0}`);

      // opcional: refrescar “turnos activos” del header
      try {
        const tr = await api.get("turnos/");
        setTurnosCount(Array.isArray(tr.data) ? tr.data.length : tr.data?.count ?? 0);
      } catch { /* noop */ }
    } catch (err) {
      // muestra mensaje de error del backend si viene
      const msg = err?.response?.data?.error || "Error al generar turnos";
      console.error("[UI][turnos.generar][error]", err?.response?.data || err);
      toast.error(msg);
    } finally {
      setGenerando(false);
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
        <Heading size="md" mb={6}>
          {user?.nombre
          ? `${user.nombre} ${user.apellido || ""}`.trim()
          : user?.email}
        </Heading>

        <SimpleGrid columns={[1, 3]} spacing={6}>
          <SummaryCard
            title="Usuarios registrados"
            value={loading ? "--" : usuariosCount}
            icon={FaUserAlt}
          />
          <SummaryCard
            title="Turnos activos"
            value={loading ? "--" : turnosCount}
            icon={FaCalendarCheck}
          />
          <SummaryCard
            title="Pagos pendientes"
            value={loading ? "--" : pagosPendientes}
            icon={FaMoneyBillWave}
          />
        </SimpleGrid>

        <Box mt={8}>
          <Button onClick={handleGenerarTurnos} isLoading={generando}>
            Generar Turnos del Mes
          </Button>

          {resultado && (
            <Box mt={4} bg={cardColors.bg} color={cardColors.color} p={4} rounded="md" borderWidth="1px">
              <Text fontWeight="medium" mb={2}>
                Turnos generados: {resultado.turnos_generados}
              </Text>
              <Text fontSize="sm" color={mutedColor}>
                Profesores afectados: {resultado.profesores_afectados}
              </Text>
              {resultado.detalle?.length > 0 && (
                <Box mt={2}>
                  {resultado.detalle.map((d) => (
                    <Text key={d.profesor_id} fontSize="sm">
                      {d.nombre}: {d.turnos} turnos generados
                    </Text>
                  ))}
                </Box>
              )}
              {resultado.trace_id && (
                <Text mt={2} fontSize="xs" color={mutedColor}>
                  Trace ID: {resultado.trace_id}
                </Text>
              )}
            </Box>
          )}
        </Box>
      </Box>
    </PageWrapper>
  );
};

export default DashboardPage;
