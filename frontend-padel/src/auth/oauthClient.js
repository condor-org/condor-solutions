// src/auth/oauthClient.js
import axios from "axios";
import { randomString, sha256Base64Url } from "./pkce";

function readRuntimeConfig() {
  const w = typeof window !== "undefined" ? window : {};
  const cfg = w.RUNTIME_CONFIG || {};
  const API_BASE_URL_RAW = cfg.API_BASE_URL || "";
  const API_BASE_URL = API_BASE_URL_RAW.replace(/\/+$/, "");
  const API = /\/api$/.test(API_BASE_URL) ? API_BASE_URL : `${API_BASE_URL}/api`;
  const GOOGLE_CLIENT_ID = cfg.GOOGLE_CLIENT_ID || "";
  const OAUTH_REDIRECT_URI = cfg.OAUTH_REDIRECT_URI || `${w.location?.origin || ""}/oauth/google/callback`;
  return { API, GOOGLE_CLIENT_ID, OAUTH_REDIRECT_URI, API_BASE_URL };
}

const GOOGLE_AUTHZ_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth";
const OIDC_SCOPE = "openid email profile";
const RESPONSE_TYPE = "code";
const PROVIDER = "google";

// Mapea respuestas posibles del backend a un formato estable
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

export async function startGoogleLogin({ host, returnTo = "/" }) {
  const { API, GOOGLE_CLIENT_ID, OAUTH_REDIRECT_URI, API_BASE_URL } = readRuntimeConfig();

  const codeVerifier = randomString(96);
  const codeChallenge = await sha256Base64Url(codeVerifier);

  const { data } = await axios.post(
    `${API}/auth/oauth/state/`,
    { host, return_to: returnTo, provider: PROVIDER },
    { timeout: 10000 }
  );
  const { state, nonce } = data;
  sessionStorage.setItem("oauth_code_verifier", codeVerifier);
  sessionStorage.setItem("oauth_nonce", nonce);

  if (!GOOGLE_CLIENT_ID) throw new Error("config_missing_client_id");
  if (!OAUTH_REDIRECT_URI) throw new Error("config_missing_redirect_uri");

  console.log("[OAuth] authorize params", {
    client_id_present: !!GOOGLE_CLIENT_ID,
    redirect_uri: OAUTH_REDIRECT_URI,
    api_base_url: API_BASE_URL,
    api_prefix_usado: API,
  });

  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: OAUTH_REDIRECT_URI,
    response_type: RESPONSE_TYPE,
    scope: OIDC_SCOPE,
    state,
    nonce,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });

  window.location.assign(`${GOOGLE_AUTHZ_ENDPOINT}?${params.toString()}`);
}

export async function exchangeCodeForTokens({ code, state }) {
  const { API } = readRuntimeConfig();

  const codeVerifier = sessionStorage.getItem("oauth_code_verifier");
  const nonce = sessionStorage.getItem("oauth_nonce");
  if (!codeVerifier || !nonce) throw new Error("missing_pkce_or_nonce");

  const resp = await axios.post(
    `${API}/auth/oauth/callback/`,
    { code, state, code_verifier: codeVerifier, provider: PROVIDER },
    { timeout: 15000 }
  );

  // Limpieza de PKCE/nonce siempre
  sessionStorage.removeItem("oauth_code_verifier");
  sessionStorage.removeItem("oauth_nonce");

  // Normalizamos para el AuthContext
  const norm = normalizeOAuthResponse(resp.data);
  if (!norm.access || !norm.refresh) {
    console.error("[OAuth] Respuesta callback sin tokens esperados:", resp.data);
  }
  return norm;
}
