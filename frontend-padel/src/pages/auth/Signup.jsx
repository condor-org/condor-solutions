// src/pages/auth/Signup.jsx
import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../../auth/AuthContext";
import { Box, Heading, VStack, Checkbox, Text } from "@chakra-ui/react";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import { toast } from "react-toastify";

const RAW_BASE = process.env.REACT_APP_API_BASE_URL || "";
const API_BASE = RAW_BASE.replace(/\/+$/, "");
const API = `${API_BASE}/api`;

const Signup = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setAuthFromOAuth } = useAuth();

  // viene desde OAuthCallback vía navigate state
  const { pendingToken: stPT, prefill = {}, returnTo = "/" } = location.state || {};
  // fallback por query (?pt=...)
  const queryPT = new URLSearchParams(window.location.search).get("pt");
  const pendingToken = useMemo(() => stPT || queryPT || "", [stPT, queryPT]);

  const [nombre, setNombre] = useState(prefill.given_name || "");
  const [apellido, setApellido] = useState(prefill.family_name || "");
  const [telefono, setTelefono] = useState("");
  const [aceptaTos, setAceptaTos] = useState(false);
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!pendingToken) {
      toast.error("Falta el token de registro. Volvé a iniciar sesión.");
      navigate("/login", { replace: true });
      return;
    }
    if (!nombre.trim() || !apellido.trim()) {
      toast.error("Completá nombre y apellido.");
      return;
    }
    if (!telefono.trim() || telefono.replace(/\D/g, "").length < 6) {
      toast.error("Ingresá un teléfono válido.");
      return;
    }
    if (!aceptaTos) {
      toast.error("Debés aceptar los Términos y Condiciones.");
      return;
    }

    try {
      setSending(true);
      const res = await axios.post(`${API}/auth/oauth/onboard/`, {
        pending_token: pendingToken,
        nombre: nombre.trim(),
        apellido: apellido.trim(),
        telefono: telefono.trim(),
        acepta_tos: true,
      });

      // { ok, access, refresh, user, return_to }
      await setAuthFromOAuth(res.data);
      navigate(res?.data?.return_to || returnTo || "/", { replace: true });
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.reason ||
        err?.message ||
        "No pudimos completar el registro.";
      console.error("[Signup] Error:", err?.response?.status, msg);
      toast.error(typeof msg === "string" ? msg : "Error en el registro.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Box maxW="md" mx="auto" px={4} py={8}>
      <Heading size="md" mb={6}>Completá tu registro</Heading>
      <Box as="form" onSubmit={handleSubmit}>
        <Input label="Email" type="email" value={prefill.email || ""} disabled />

        <Input label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <Input label="Apellido" value={apellido} onChange={(e) => setApellido(e.target.value)} required />
        <Input label="Teléfono" value={telefono} onChange={(e) => setTelefono(e.target.value)} />

        <VStack align="start" spacing={3} mt={3}>
          <Checkbox isChecked={aceptaTos} onChange={(e) => setAceptaTos(e.target.checked)}>
            Acepto los Términos y Condiciones
          </Checkbox>
          <Text fontSize="sm" color="gray.500">
            Tu cuenta se asociará al club actual (según el subdominio).
          </Text>
        </VStack>

        <Button type="submit" width="full" mt={4} disabled={sending}>
          {sending ? "Creando..." : "Crear cuenta"}
        </Button>
      </Box>
    </Box>
  );
};

export default Signup;