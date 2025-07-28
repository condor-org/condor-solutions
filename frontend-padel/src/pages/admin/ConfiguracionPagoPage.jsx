import React, { useEffect, useState, useContext } from "react";
import { Box, Text, VStack } from "@chakra-ui/react";
import Sidebar from "../../components/layout/Sidebar";
import PageWrapper from "../../components/layout/PageWrapper";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import { toast } from "react-toastify";

import FormSection from "../../components/ui/FormSection";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";

import { useCardColors, useInputColors, useMutedText } from "../../components/theme/tokens";




const ConfiguracionPagoPage = () => {
  const { accessToken, user, logout } = useContext(AuthContext);
  const [destinatario, setDestinatario] = useState("");
  const [cbu, setCbu] = useState("");
  const [alias, setAlias] = useState("");
  const [monto, setMonto] = useState("");
  const [tiempoMax, setTiempoMax] = useState(60);
  const [loading, setLoading] = useState(false);
  const cardColors = useCardColors();
  const inputColors = useInputColors();
  const labelColor = useMutedText();

  useEffect(() => {
    if (!accessToken) return;
    const api = axiosAuth(accessToken);

    api
      .get("pagos/configuracion/")
      .then((res) => {
        const config = res.data;
        if (config) {
          setDestinatario(config.destinatario || "");
          setCbu(config.cbu || "");
          setAlias(config.alias || "");
          setMonto(config.monto_esperado || "");
          setTiempoMax(config.tiempo_maximo_minutos || 60);
        }
      })
      .catch(() => {
        toast.error("Error al cargar la configuración de pago");
      });
  }, [accessToken]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const api = axiosAuth(accessToken);
    try {
      await api.put("pagos/configuracion/", {
        destinatario,
        cbu,
        alias,
        monto_esperado: monto,
        tiempo_maximo_minutos: tiempoMax,
      });
      toast.success("Configuración guardada");
    } catch {
      toast.error("Error al guardar configuración");
    } finally {
      setLoading(false);
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
        <Box flex="1" p={[2, 4, 8]} minH="100vh">
            <FormSection
              title="Configuración de Pago"
              description="Completa los datos necesarios para activar los pagos automatizados."
            >
              <Box as="form" onSubmit={handleSubmit}>
                <VStack spacing={4} align="stretch">
                  <Box>
                    <Text fontWeight="medium" fontSize="sm" color={labelColor} mb={1}>
                      Destinatario
                    </Text>
                    <Input
                      placeholder="Destinatario"
                      value={destinatario}
                      onChange={(e) => setDestinatario(e.target.value)}
                    />
                  </Box>
                  <Box>
                    <Text fontWeight="medium" fontSize="sm" color={labelColor} mb={1}>
                      CBU
                    </Text>
                    <Input
                      placeholder="CBU"
                      value={cbu}
                      onChange={(e) => setCbu(e.target.value)}
                    />
                  </Box>
                  <Box>
                    <Text fontWeight="medium" fontSize="sm" color={labelColor} mb={1}>
                      Alias
                    </Text>
                    <Input
                      placeholder="Alias"
                      value={alias}
                      onChange={(e) => setAlias(e.target.value)}
                    />
                  </Box>
                  <Box>
                    <Text fontWeight="medium" fontSize="sm" color={labelColor} mb={1}>
                      Monto esperado
                    </Text>
                    <Input
                      placeholder="Monto esperado"
                      type="number"
                      value={monto}
                      onChange={(e) => setMonto(e.target.value)}
                    />
                  </Box>
                  <Box>
                    <Text fontWeight="medium" fontSize="sm" color={labelColor} mb={1}>
                      Tiempo máximo (minutos)
                    </Text>
                    <Input
                      placeholder="Tiempo máximo"
                      type="number"
                      value={tiempoMax}
                      onChange={(e) => setTiempoMax(e.target.value)}
                    />
                  </Box>
                  <Button type="submit" isLoading={loading}>
                    Guardar
                  </Button>
                </VStack>
              </Box>
            </FormSection>
          </Box>
      </PageWrapper>
    </>
  );
};

export default ConfiguracionPagoPage;
