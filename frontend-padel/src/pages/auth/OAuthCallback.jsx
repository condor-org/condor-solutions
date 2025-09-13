// src/pages/auth/OAuthCallback.jsx
import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { exchangeCodeForTokens } from "../../auth/oauthClient";
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

      try {
        const params = new URLSearchParams(location.search);
        const code = params.get("code");
        const state = params.get("state");

        console.log(`[OAuthCB][${traceId}] ${nowTs()} mounted`, {
          href: window.location.href,
          code_present: !!code,
          state_present: !!state,
          runtime_config: window.RUNTIME_CONFIG,
          has_code_verifier: !!sessionStorage.getItem("oauth_code_verifier"),
        });

        if (!code || !state) {
          console.error(`[OAuthCB][${traceId}] missing query params`, { code, state });
          toast.error("No se pudo completar el inicio de sesión (falta code/state).");
          navigate("/login", { replace: true });
          return;
        }

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

        // Evita loop: NO relanzamos el flujo. Solo mostramos error.
        toast.error(
          typeof detail === "string"
            ? detail
            : "No se pudo completar el inicio de sesión."
        );
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
