// src/pages/auth/OAuthCallback.jsx
import React, { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { exchangeCodeForTokens } from "../../auth/oauthClient";
import { Box, Spinner, Text } from "@chakra-ui/react";
import { toast } from "react-toastify";

const OAuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setAuthFromOAuth } = useAuth();

  useEffect(() => {
    const run = async () => {
      try {
        // 1) Leer query params
        const params = new URLSearchParams(location.search);
        const code = params.get("code");
        const state = params.get("state");

        if (!code || !state) {
          console.error("[OAuth CB] Faltan query params", { code: !!code, state: !!state });
          toast.error("No se pudo completar el inicio de sesión (falta code/state).");
          navigate("/login", { replace: true });
          return;
        }

        // 2) Intercambiar code por tokens en backend
        const data = await exchangeCodeForTokens({ code, state }); // { access, refresh, user, return_to? }

        // 3) Setear sesión completa (tokens + user + refresh proactivo)
        await setAuthFromOAuth(data);

        // 4) Redirigir a return_to o default
        const dest = data?.return_to || "/";
        navigate(dest, { replace: true });
      } catch (err) {
        const resp = err?.response;
        const detail = resp?.data?.detail || resp?.data || err?.message;
        console.error("[OAuth CB] Error en callback:", {
          status: resp?.status,
          data: resp?.data,
          detail,
        });
        // feedback al usuario
        toast.error(
          typeof detail === "string" ? detail :
          "No se pudo completar el inicio de sesión."
        );
        navigate("/login", { replace: true });
      }
    };

    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Box minH="60vh" display="flex" alignItems="center" justifyContent="center" flexDir="column" gap={4}>
      <Spinner size="lg" />
      <Text fontSize="sm" color="gray.500">Procesando inicio de sesión…</Text>
    </Box>
  );
};

export default OAuthCallback;
