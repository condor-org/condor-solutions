// src/pages/admin/DashboardPage.jsx

import React, { useContext, useEffect, useState } from "react";
import {
  Box,
  Heading,
  SimpleGrid,
  Text,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Select,
  VStack,
  NumberInput,
  NumberInputField,
  useBreakpointValue,
  useDisclosure
} from "@chakra-ui/react";
import { FaUserAlt, FaCalendarCheck, FaMoneyBillWave } from "react-icons/fa";
import { AuthContext } from "../../auth/AuthContext";
import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import Button from "../../components/ui/Button";
import SummaryCard from "../../components/dashboard/SummaryCard";
import { axiosAuth } from "../../utils/axiosAuth";
import { toast } from "react-toastify";
import { useCardColors, useModalColors, useMutedText } from "../../components/theme/tokens";
import ChakraButton from "../../components/ui/Button";



const meses = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
];

const DashboardPage = () => {
  const { user, logout, accessToken } = useContext(AuthContext);

  const [usuariosCount, setUsuariosCount] = useState(null);
  const [turnosCount, setTurnosCount] = useState(null);
  const [pagosPendientes, setPagosPendientes] = useState(null);
  const [profesores, setProfesores] = useState([]);
  const [loading, setLoading] = useState(true);

  const { isOpen, onOpen, onClose } = useDisclosure();
  const [anio, setAnio] = useState(new Date().getFullYear());
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [duracion, setDuracion] = useState(60);
  const [profesorId, setProfesorId] = useState("");
  const [generando, setGenerando] = useState(false);
  const [resultado, setResultado] = useState(null);

  const isMobile = useBreakpointValue({ base: true, md: false });

  const modalColors = useModalColors();
  const cardColors = useCardColors();
  const mutedColor = useMutedText();

  useEffect(() => {
    if (!accessToken) return;
    setLoading(true);
    const api = axiosAuth(accessToken);
    Promise.all([
      api.get("auth/usuarios/"),
      api.get("turnos/"),
      api.get("pagos/pendientes/"),
      api.get("turnos/prestadores/")
    ])
      .then(([usuariosRes, turnosRes, pagosRes, profesRes]) => {
        setUsuariosCount(Array.isArray(usuariosRes.data)
          ? usuariosRes.data.length
          : usuariosRes.data?.count ?? 0);
        setTurnosCount(Array.isArray(turnosRes.data)
          ? turnosRes.data.length
          : turnosRes.data?.count ?? 0);
        setPagosPendientes(Array.isArray(pagosRes.data)
          ? pagosRes.data.length
          : pagosRes.data?.count ?? 0);
        setProfesores(profesRes.data.results || profesRes.data || []);
      })
      .catch(() => toast.error("Error al cargar métricas del dashboard"))
      .finally(() => setLoading(false));
  }, [accessToken]);

  const handleGenerarTurnos = async (e) => {
    e.preventDefault();
    setGenerando(true);
    setResultado(null);
    const api = axiosAuth(accessToken);
    try {
      const body = {
        fecha_inicio: `${anio}-${mes.toString().padStart(2, "0")}-01`,
        fecha_fin: `${anio}-${mes.toString().padStart(2, "0")}-31`, // simple y seguro para producción
        duracion_minutos: Number(duracion),
      };
      if (profesorId) body.prestador_id = Number(profesorId);
  
      const res = await api.post("turnos/generar/", body);
      setResultado(res.data);
      toast.success(`¡Turnos generados! Total: ${res.data.turnos_generados}`);
    } catch (err) {
      toast.error("Error al generar turnos");
    } finally {
      setGenerando(false);
    }
  };
  

  return (
    <>
      <PageWrapper>
        <Sidebar
          links={[
            { label: "Dashboard", path: "/admin" },
            { label: "Sedes", path: "/admin/sedes" },
            { label: "Profesores", path: "/admin/profesores" },
            { label: "Usuarios", path: "/admin/usuarios" },
            { label: "Configuración Pago", path: "/admin/configuracion-pago" },
            { label: "Pagos Preaprobados", path: "/admin/pagos-preaprobados" },
          ]}
        />
        <Box flex="1" p={[4, 6, 8]}>
          <Heading size="md" mb={6}>
            Bienvenido, {user?.email}
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
            <Button onClick={onOpen}>Generar Turnos</Button>
          </Box>
        </Box>
      </PageWrapper>

      <Modal
        isOpen={isOpen}
        onClose={() => {
          onClose();
          setResultado(null);
        }}
        isCentered
        size={isMobile ? "full" : "md"}
      >
        <ModalOverlay />
        <ModalContent bg={modalColors.bg} color={modalColors.color}>
          <ModalHeader>Generar Turnos del Mes</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <form id="gen-turnos-form" onSubmit={handleGenerarTurnos}>
              <VStack spacing={4} align="stretch">
                <Box>
                  <Text fontWeight="medium" fontSize="sm" color={mutedColor} mb={1}>
                    Año
                  </Text>
                  <NumberInput value={anio} min={2024} max={2100} onChange={(_, v) => setAnio(v || "")}>
                    <NumberInputField />
                  </NumberInput>
                </Box>
                <Box>
                  <Text fontWeight="medium" fontSize="sm" color={mutedColor} mb={1}>
                    Mes
                  </Text>
                  <Select value={mes} onChange={e => setMes(e.target.value)}>
                    {meses.map((nombre, idx) => (
                      <option key={idx + 1} value={idx + 1}>{nombre}</option>
                    ))}
                  </Select>
                </Box>
                <Box>
                  <Text fontWeight="medium" fontSize="sm" color={mutedColor} mb={1}>
                    Duración (minutos)
                  </Text>
                  <NumberInput value={duracion} min={15} max={240} onChange={(_, v) => setDuracion(v || "")}>
                    <NumberInputField />
                  </NumberInput>
                </Box>
                <Box>
                  <Text fontWeight="medium" fontSize="sm" color={mutedColor} mb={1}>
                    Profesor
                  </Text>
                  <Select value={profesorId} onChange={e => setProfesorId(e.target.value)}>
                    <option value="">Todos los profesores</option>
                    {profesores.map(p => (
                      <option key={p.id} value={p.id}>{p.nombre}</option>
                    ))}
                  </Select>
                </Box>
              </VStack>
            </form>
            {resultado && (
              <Box mt={4} bg={cardColors.bg} color={cardColors.color} p={4} rounded="md">
                <Text fontWeight="medium" mb={2}>
                  Turnos generados: {resultado.turnos_generados}
                </Text>
                <Text fontSize="sm" color={mutedColor}>
                  Profesores afectados: {resultado.profesores_afectados}
                </Text>
                {resultado.detalle?.length > 0 && (
                  <Box mt={2}>
                    {resultado.detalle.map(d => (
                      <Text key={d.profesor_id} fontSize="sm">
                        {d.nombre}: {d.turnos} turnos generados
                      </Text>
                    ))}
                  </Box>
                )}
              </Box>
            )}
          </ModalBody>
          <ModalFooter>
            <ChakraButton type="submit" form="gen-turnos-form" isLoading={generando}>
              Generar
            </ChakraButton>
            <ChakraButton variant="ghost" ml={3} onClick={() => {
              onClose();
              setResultado(null);
            }}>
              Cancelar
            </ChakraButton>
          </ModalFooter>
          </ModalContent>
        </Modal>
      </>
    );
  };
  
  export default DashboardPage;
  