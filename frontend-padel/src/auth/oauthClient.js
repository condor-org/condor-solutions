// src/auth/oauthClient.js
import { axiosAuth } from "../utils/axiosAuth";
import { randomString, sha256Base64Url } from "./pkce";

const PROVIDER = "google";
const GOOGLE_AUTHZ_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth";
const OIDC_SCOPE = "openid email profile";
const RESPONSE_TYPE = "code";

function nowTs() {
  return new Date().toISOString();
}

export function readRuntimeConfig() {
  const w = typeof window !== "undefined" ? window : {};
  const cfg = w.RUNTIME_CONFIG || {};

  // /api o absoluto. Normalizamos SIN barra final.
  const API_BASE_URL_RAW = cfg.API_BASE_URL || "";
  const API_BASE_URL = API_BASE_URL_RAW.replace(/\/+$/, "");
  const API = /\/api$/.test(API_BASE_URL) ? API_BASE_URL : `${API_BASE_URL || ""}/api`;

  const GOOGLE_CLIENT_ID = cfg.GOOGLE_CLIENT_ID || "";
  const OAUTH_REDIRECT_URI =
    cfg.OAUTH_REDIRECT_URI || `${w.location?.origin || ""}/oauth/google/callback`;

  return { API, GOOGLE_CLIENT_ID, OAUTH_REDIRECT_URI, API_BASE_URL };
}

// Normaliza posibles formatos del backend
function normalizeOAuthResponse(raw) {
  if (!raw || typeof raw !== "object") return {};
  const access =
    raw.access ??
    raw.access_token ??
    raw.token?.access ??
    raw.tokens?.access ??
    raw.data?.access;

  const refresh =
    raw.refresh ??
    raw.refresh_token ??
    raw.token?.refresh ??
    raw.tokens?.refresh ??
    raw.data?.refresh;

  const user =
    raw.user ??
    raw.profile ??
    raw.data?.user ??
    raw.result?.user;

  const return_to =
    raw.return_to ??
    raw.next ??
    raw.redirect ??
    raw.data?.return_to ??
    "/";

  return { access, refresh, user, return_to };
}

/**
 * Inicia login con Google:
 * - Limpia residuos de intentos previos (defensivo).
 * - Genera PKCE (code_verifier / code_challenge).
 * - Pide STATE al backend (tenant-aware via Host) y usa el NONCE del backend.
 * - Redirige a Google con todos los parámetros.
 */
export async function startGoogleLogin({ host, returnTo = "/", invite } = {}) {
  const traceId = `oauth_start_${Date.now()}`;
  const t0 = performance.now();
  const { API, GOOGLE_CLIENT_ID, OAUTH_REDIRECT_URI, API_BASE_URL } = readRuntimeConfig();

  // Si no me pasan host explícito, uso el del navegador (tenant actual)
  const resolvedHost =
    host ||
    (typeof window !== "undefined" ? window.location.host : undefined);
  if (!resolvedHost) {
    console.error(`[OAuth][${traceId}] host missing: no param and no window.location.host`);
    throw new Error("tenant_host_missing");
  }

  console.log(`[OAuth][${traceId}] ${nowTs()} startGoogleLogin`, {
    host: resolvedHost,
    returnTo,
    invitePresent: !!invite,
    API,
    API_BASE_URL,
    OAUTH_REDIRECT_URI,
    GOOGLE_CLIENT_ID_present: !!GOOGLE_CLIENT_ID,
    location_origin: typeof window !== "undefined" ? window.location.origin : undefined,
  });

  if (!GOOGLE_CLIENT_ID) throw new Error("config_missing_client_id");
  if (!OAUTH_REDIRECT_URI) throw new Error("config_missing_redirect_uri");

  // Limpieza defensiva antes de iniciar (evita confusiones de PKCE viejo)
  try {
    sessionStorage.removeItem("oauth_code_verifier");
    sessionStorage.removeItem("oauth_nonce");
    // no borro el fallback aún (por si el navegador pierde sessionStorage en la redirección)
  } catch {}

  // PKCE (solo PKCE se genera en FE)
  const codeVerifier = randomString(96);
  const codeChallenge = await sha256Base64Url(codeVerifier);

  // Pedimos STATE + NONCE al backend (same-origin si PUBLIC_API_BASE_URL=/api)
  let stateResp;
  try {
    stateResp = await axiosAuth(null, null).post(
      `/auth/oauth/state/`,
      { host: resolvedHost, return_to: returnTo, provider: PROVIDER, invite },
      { timeout: 10000 }
    );
  } catch (err) {
    const resp = err?.response;
    console.error(`[OAuth][${traceId}] state request failed`, {
      url: `/auth/oauth/state/`,
      status: resp?.status,
      data: resp?.data,
      msg: err?.message,
      hint: "Verifica /api routing y ALLOWED_HOSTS / TENANT_STRICT_HOST",
    });
    throw err;
  }

  const { state, nonce: backendNonce } = stateResp?.data || {};
  if (!state) {
    console.error(`[OAuth][${traceId}] state missing in response`, stateResp?.data);
    throw new Error("state_missing");
  }

  // Usar SIEMPRE el nonce del backend; si no vino por alguna razón, fallback local.
  const localNonce = randomString(32);
  const nonceToUse = backendNonce || localNonce;
  if (!backendNonce) {
    console.warn(`[OAuth][${traceId}] backend did not return nonce; using local nonce as fallback`);
  }
  console.log(`[OAuth][${traceId}] will use nonce`, {
    from_backend: !!backendNonce,
    length: nonceToUse?.length,
  });

  // Persistencia: sessionStorage + fallback en localStorage
  try {
    sessionStorage.setItem("oauth_code_verifier", codeVerifier);
    sessionStorage.setItem("oauth_nonce", nonceToUse);
    localStorage.setItem("oauth_code_verifier", codeVerifier);
  } catch (e) {
    console.warn(`[OAuth][${traceId}] No se pudo persistir PKCE/nonce`, e?.message);
  }

  // Armado de URL de autorización
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: OAUTH_REDIRECT_URI,
    response_type: RESPONSE_TYPE,
    scope: OIDC_SCOPE,
    state,
    nonce: nonceToUse,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
    // Evita auto-login silencioso con la cuenta previa
    prompt: "select_account",
  });

  const authorizeUrl = `${GOOGLE_AUTHZ_ENDPOINT}?${params.toString()}`;
  console.log(`[OAuth][${traceId}] redirecting to Google`, {
    authorizeUrl,
    t_ms: Math.round(performance.now() - t0),
  });

  window.location.assign(authorizeUrl);
}

/**
 * Intercambia code+state por tokens en backend usando PKCE.
 * - Recupera code_verifier de sessionStorage (y fallback localStorage si hace falta).
 * - No exige nonce en FE: backend valida nonce con id_token de Google.
 * - Limpia storage al finalizar (éxito o error) para evitar residuos.
 */
export async function exchangeCodeForTokens({ code, state }) {
  const traceId = `oauth_cb_${Date.now()}`;
  const t0 = performance.now();
  const { API } = readRuntimeConfig();

  console.log(`[OAuth][${traceId}] ${nowTs()} exchangeCodeForTokens() begin`, {
    href: typeof window !== "undefined" ? window.location.href : undefined,
    API,
    code_present: !!code,
    state_present: !!state,
  });

  if (!code || !state) throw new Error("missing_code_or_state");

  // PKCE: sessionStorage primero; si no está, usamos fallback de localStorage
  let codeVerifier = null;
  try {
    codeVerifier = sessionStorage.getItem("oauth_code_verifier");
    if (!codeVerifier) {
      const fallback = localStorage.getItem("oauth_code_verifier");
      if (fallback) {
        console.warn(`[OAuth][${traceId}] sessionStorage vacío; usando fallback de localStorage para code_verifier`);
        sessionStorage.setItem("oauth_code_verifier", fallback);
        codeVerifier = fallback;
      }
    }
  } catch (e) {
    console.warn(`[OAuth][${traceId}] storage read error`, e?.message);
  }

  if (!codeVerifier) {
    console.error(`[OAuth][${traceId}] missing_pkce`, {
      hint: "El navegador pudo limpiar sessionStorage al redirigir. Probá iniciar login nuevamente.",
    });
    throw new Error("missing_pkce");
  }

  const url = `/auth/oauth/callback/`;
  console.log(`[OAuth][${traceId}] POST ${url}`);

  try {
    const resp = await axiosAuth(null, null).post(
      url,
      { code, state, code_verifier: codeVerifier, provider: PROVIDER },
      { timeout: 15000 }
    );

    console.log(`[OAuth][${traceId}] POST succeeded`, {
      status: resp?.status,
      t_ms: Math.round(performance.now() - t0),
      keys: Object.keys(resp?.data || {}),
    });

    // Limpieza
    try {
      sessionStorage.removeItem("oauth_code_verifier");
      sessionStorage.removeItem("oauth_nonce");
      localStorage.removeItem("oauth_code_verifier");
    } catch (e) {
      console.warn(`[OAuth][${traceId}] storage cleanup warn`, e?.message);
    }

    const raw = resp.data;

    if (raw?.needs_onboarding) {
      console.log(`[OAuth][${traceId}] needs_onboarding`, {
        has_pending_token: !!raw?.pending_token,
      });
      return {
        needs_onboarding: true,
        pending_token: raw.pending_token,
        prefill: raw.prefill || {},
        return_to: raw.return_to || "/",
      };
    }

    const norm = normalizeOAuthResponse(raw);
    if (!norm.access || !norm.refresh) {
      console.error(`[OAuth][${traceId}] callback OK pero faltan tokens`, { raw });
    }
    return norm;
  } catch (err) {
    const resp = err?.response;

    console.error(`[OAuth][${traceId}] POST failed`, {
      status: resp?.status,
      data: resp?.data,
      msg: err?.message,
      hint:
        resp?.status === 400
          ? "400 del backend: revisar code_verifier (PKCE) y state/nonce. Es común si Google re-usa code o si se perdió PKCE entre dominios."
          : resp?.status === 403
          ? "403: política de dominio de email / tenant mismatch / email no verificado."
          : resp?.status === 502
          ? "502: error al pedir token a Google (timeout)."
          : "Ver logs del backend [OAUTH CB] para detalle.",
    });

    // Limpieza también en error (evita loops con PKCE viejo)
    try {
      sessionStorage.removeItem("oauth_code_verifier");
      sessionStorage.removeItem("oauth_nonce");
      localStorage.removeItem("oauth_code_verifier");
    } catch {}

    throw err;
  }
}