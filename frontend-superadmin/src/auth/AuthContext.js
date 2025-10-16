// src/auth/AuthContext.js

import React, {
  createContext,
  useState,
  useEffect,
  useCallback,
  useContext,
  useRef,
} from "react";
import axios from "axios";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { applyAuthInterceptor } from "./axiosInterceptor";

/**
 * REACT_APP_API_BASE_URL puede ser:
 *  - "" (same-origin detrás del proxy)
 *  - "http://localhost:8080" (si apuntás directo)
 */
const RAW_BASE = process.env.REACT_APP_API_BASE_URL || "";
const API_BASE = RAW_BASE.replace(/\/+$/, "");
const API = `${API_BASE}/api`;

export const AuthContext = createContext();

// Helpers de resiliencia / logs (sin PII)
const safeDecodeExp = (jwt) => {
  try {
    const { exp } = jwtDecode(jwt);
    return typeof exp === "number" ? exp : 0;
  } catch (e) {
    console.warn("[AUTH] jwtDecode falló:", e?.message);
    // Fallback conservador: 5 minutos desde ahora para reintentar refresh
    return Math.floor(Date.now() / 1000) + 300;
  }
};
const maskEmail = (value = "") => {
  try {
    const [u, d] = String(value).split("@");
    return u && d ? `${u.slice(0, 2)}***@${d}` : "***";
  } catch {
    return "***";
  }
};

const REFRESH_SAFETY_SECONDS = 60; // Refrescar 60s antes del vencimiento

const AuthProviderBase = ({ children, onLogoutNavigate }) => {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });

  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem("access")
  );
  const [refreshToken, setRefreshToken] = useState(() =>
    localStorage.getItem("refresh")
  );
  const [loadingUser, setLoadingUser] = useState(true);

  const refreshTimerRef = useRef(null);

  // ---- Utils de timers -------------------------------------------------------
  const clearRefreshTimer = () => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  };

  const scheduleProactiveRefresh = useCallback(() => {
    clearRefreshTimer();

    const exp = parseInt(localStorage.getItem("access_exp") || "0", 10);
    if (!exp) return;

    const now = Math.floor(Date.now() / 1000);
    const secondsLeft = exp - now - REFRESH_SAFETY_SECONDS;

    if (secondsLeft <= 0) {
      // Si falta poco o ya venció, refrescar enseguida
      refreshTimerRef.current = setTimeout(() => attemptRefreshToken(), 0);
    } else {
      refreshTimerRef.current = setTimeout(
        () => attemptRefreshToken(),
        secondsLeft * 1000
      );
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- Logout ---------------------------------------------------------------
  const logout = useCallback(() => {
    console.log("[AUTH] Logout ejecutado.");
    clearRefreshTimer();

    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);

    // Limpiar solo lo nuestro
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("access_exp");
    localStorage.removeItem("user");

    // Remover header global
    delete axios.defaults.headers.common["Authorization"];

    if (onLogoutNavigate) onLogoutNavigate("/login");
  }, [onLogoutNavigate]);

  // ---- Refresh token ---------------------------------------------------------
  const attemptRefreshToken = useCallback(async () => {
    const refresh = localStorage.getItem("refresh");
    if (!refresh) return false;

    try {
      console.log("[AUTH] Intentando refresh token...");
      const res = await axios.post(`${API}/token/refresh/`, { refresh });
      const { access } = res.data;
      if (!access) throw new Error("Respuesta de refresh sin 'access'");

      const exp = safeDecodeExp(access);
      localStorage.setItem("access", access);
      localStorage.setItem("access_exp", exp);
      setAccessToken(access);

      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;
      console.log("[AUTH] Refresh token exitoso.");

      scheduleProactiveRefresh(); // reprogramar
      return true;
    } catch (err) {
      console.error("[AUTH] Falló el refresh token. Forzando logout.");
      logout();
      return false;
    }
  }, [logout, scheduleProactiveRefresh]);

  // ---- Login por email/clave (flujo existente) ------------------------------
  const login = async (email, password) => {
    console.log("[AUTH] Intentando login con email:", maskEmail(email));
    try {
      const res = await axios.post(`${API}/token/`, { email, password });
      const { access, refresh } = res.data;
      if (!access || !refresh) throw new Error("Respuesta de login sin tokens");

      const exp = safeDecodeExp(access);
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("access_exp", exp);

      setAccessToken(access);
      setRefreshToken(refresh);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      console.log("[AUTH] Login exitoso. Tokens recibidos.");

      const perfilRes = await axios.get(`${API}/auth/yo/`);
      setUser(perfilRes.data);
      localStorage.setItem("user", JSON.stringify(perfilRes.data));

      scheduleProactiveRefresh();
    } catch (err) {
      console.error(
        "[AUTH] Error en login:",
        err?.response?.status,
        err?.message
      );
      toast.error("Credenciales inválidas");
      throw err;
    }
  };

  // ---- Login vía OAuth (nuevo) ----------------------------------------------
  /**
   * data: { access, refresh, user, return_to? }
   * - Guarda tokens, programa refresh, setea header global.
   */
  const setAuthFromOAuth = useCallback(
  async (data) => {
    try {
      const { access, refresh, user: userPayload, return_to } = data || {};
      if (!access || !refresh) throw new Error("OAuth: faltan tokens");
      if (!userPayload) throw new Error("OAuth: falta 'user'");

      const exp = safeDecodeExp(access);
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("access_exp", exp);

      setAccessToken(access);
      setRefreshToken(refresh);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;
      scheduleProactiveRefresh();

      // 🔽 Nuevo: obtener perfil “completo” del backend
      try {
        const perfilRes = await axios.get(`${API}/auth/yo/`);
        setUser(perfilRes.data);
        localStorage.setItem("user", JSON.stringify(perfilRes.data));
      } catch {
        // Fallback: si falla, al menos guardá lo que vino del token
        setUser(userPayload);
        localStorage.setItem("user", JSON.stringify(userPayload));
      }

      return return_to || "/";
    } catch (e) {
      console.error("[AUTH] setAuthFromOAuth falló:", e.message);
      throw e;
    }
  },
  [scheduleProactiveRefresh]
);
  // ---- Inicialización al montar ---------------------------------------------
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        if (accessToken) {
          const now = Math.floor(Date.now() / 1000);
          const exp = parseInt(localStorage.getItem("access_exp") || "0", 10);

          if (exp < now) {
            await attemptRefreshToken();
          } else {
            axios.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;
            scheduleProactiveRefresh();
          }

          // Si hay tokens pero no hay user persistido, intentamos traerlo.
          if (!user) {
            try {
              const perfilRes = await axios.get(`${API}/auth/yo/`);
              setUser(perfilRes.data);
              localStorage.setItem("user", JSON.stringify(perfilRes.data));
            } catch (e) {
              console.warn(
                "[AUTH] No se pudo obtener /auth/yo al iniciar.",
                e?.message
              );
            }
          }
        }
      } finally {
        setLoadingUser(false); // Terminó la carga inicial SIEMPRE
      }
    };
    initializeAuth();

    return () => clearRefreshTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, attemptRefreshToken]);

  // ---- Interceptor global de axios (401 → logout) ---------------------------
  useEffect(() => {
    applyAuthInterceptor(axios, logout, { apiBasePath: API });
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        accessToken,
        refreshToken,
        loadingUser,
        setAuthFromOAuth, // <-- expuesto para OAuth callback y signup
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const onLogoutNavigate = (path) => {
    navigate(path, { replace: true });
  };

  return (
    <AuthProviderBase onLogoutNavigate={onLogoutNavigate}>
      {children}
    </AuthProviderBase>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return ctx;
};
