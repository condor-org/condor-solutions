// src/pages/auth/OAuthCallback.jsx
import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { exchangeCodeForTokens, readRuntimeConfig } from "../../auth/oauthClient";
import { Box, Spinner, Text } from "@chakra-ui/react";
import { toast } from "react-toastify";

function nowTs() {
  return new Date().toISOString();
}

const OAuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setAuthFromOAuth } = useAuth();
  const ranRef = useRef(false); // evita doble ejecución en StrictMode/dev

  useEffect(() => {
    const traceId = `cb_page_${Date.now()}`;

    const run = async () => {
      if (ranRef.current) {
        console.warn(`[OAuthCB][${traceId}] Already ran once. Skipping duplicate render.`);
        return;
      }
      ranRef.current = true;

      // Lectura de params
      const params = new URLSearchParams(location.search);
      const code = params.get("code");
      const state = params.get("state");

      const hasCodeVerifier = !!sessionStorage.getItem("oauth_code_verifier");
      const { API, OAUTH_REDIRECT_URI } = readRuntimeConfig();

      console.log(`[OAuthCB][${traceId}] ${nowTs()} mounted`, {
        href: typeof window !== "undefined" ? window.location.href : undefined,
        code_present: !!code,
        state_present: !!state,
        has_code_verifier: hasCodeVerifier,
        API,
        OAUTH_REDIRECT_URI,
        runtime_config: typeof window !== "undefined" ? window.RUNTIME_CONFIG : undefined,
      });

      if (!code || !state) {
        console.error(`[OAuthCB][${traceId}] missing query params`, { code, state });
        toast.error("No se pudo completar el inicio de sesión (falta code/state).");
        navigate("/login", { replace: true });
        return;
      }

      try {
        // 1) Intercambio con backend
        const data = await exchangeCodeForTokens({ code, state });

        // 2) Onboarding
        if (data?.needs_onboarding) {
          console.log(`[OAuthCB][${traceId}] redirecting to /signup`, {
            has_pending_token: !!data?.pending_token,
          });
          navigate("/signup", {
            replace: true,
            state: {
              pendingToken: data.pending_token,
              prefill: data.prefill || {},
              returnTo: data.return_to || "/",
            },
          });
          return;
        }

        // 3) Sesión completa
        const dest = await setAuthFromOAuth(data);
        console.log(`[OAuthCB][${traceId}] login completed; navigating to`, dest);
        navigate(dest || "/", { replace: true });
      } catch (err) {
        const resp = err?.response;
        const detail = resp?.data?.detail || resp?.data || err?.message;

        console.error(`[OAuthCB][${traceId}] error`, {
          status: resp?.status,
          data: resp?.data,
          detail,
        });

        // Mensajes más claros según error típico
        if (detail === "missing_pkce" || /missing_pkce|code_verifier/i.test(String(detail))) {
          toast.error("No se pudo validar el inicio (PKCE faltante). Probá iniciar sesión de nuevo.");
        } else if (resp?.status === 400) {
          toast.error("No se pudo completar el inicio de sesión (400). Reintentá desde la pantalla de login.");
        } else if (resp?.status === 403) {
          toast.error("Acceso no autorizado para este usuario o dominio.");
        } else {
          toast.error(
            typeof detail === "string"
              ? detail
              : "No se pudo completar el inicio de sesión."
          );
        }

        // Evita loop: NO relanzamos el flujo. Vamos a /login.
        navigate("/login", { replace: true });
      }
    };

    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Box
      minH="60vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      flexDir="column"
      gap={4}
    >
      <Spinner size="lg" />
      <Text fontSize="sm" color="gray.500">
        Procesando inicio de sesión…
      </Text>
    </Box>
  );
};

export default OAuthCallback;
