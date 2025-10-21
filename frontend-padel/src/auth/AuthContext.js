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

  // ---- Login por email/clave (nuevo endpoint) ------------------------------
  const login = async (email, password) => {
    console.log("[AUTH] 🔐 Intentando login con email:", maskEmail(email));
    console.log("[AUTH] 🔐 Datos de login:", { email: maskEmail(email), password: "***" });
    
    try {
      console.log("[AUTH] 📡 Enviando request a:", `${API}/auth/login/`);
      console.log("[AUTH] 📡 Payload enviado:", { email, password: "***" });
      
      const res = await axios.post(`${API}/auth/login/`, { email, password });
      
      console.log("[AUTH] ✅ Response recibido:", res.status, res.statusText);
      console.log("[AUTH] 📦 Response data:", res.data);
      
      const { access, refresh, user: userPayload } = res.data;
      
      if (!access || !refresh) {
        console.error("[AUTH] ❌ Respuesta de login sin tokens");
        console.error("[AUTH] ❌ Access token:", !!access);
        console.error("[AUTH] ❌ Refresh token:", !!refresh);
        throw new Error("Respuesta de login sin tokens");
      }

      console.log("[AUTH] 🔑 Tokens recibidos - Procesando...");
      const exp = safeDecodeExp(access);
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("access_exp", exp);

      setAccessToken(access);
      setRefreshToken(refresh);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      console.log("[AUTH] ✅ Login exitoso. Tokens recibidos.");

      // SIEMPRE obtener perfil completo para tener la estructura con cliente_actual
      console.log("[AUTH] 👤 Obteniendo perfil completo...");
      const perfilRes = await axios.get(`${API}/auth/yo/`);
      console.log("[AUTH] 👤 Perfil obtenido:", perfilRes.data);
      setUser(perfilRes.data);
      localStorage.setItem("user", JSON.stringify(perfilRes.data));

      console.log("[AUTH] ⏰ Programando refresh automático...");
      scheduleProactiveRefresh();
      console.log("[AUTH] ✅ Login completado exitosamente");
    } catch (err) {
      console.error("[AUTH] ❌ Error en login:");
      console.error("[AUTH] ❌ Status:", err?.response?.status);
      console.error("[AUTH] ❌ Message:", err?.message);
      console.error("[AUTH] ❌ Response data:", err?.response?.data);
      console.error("[AUTH] ❌ Stack:", err?.stack);
      
      const errorMsg = err?.response?.data?.detail || err?.response?.data?.error || err?.response?.data?.message || "Credenciales inválidas";
      console.error("[AUTH] ❌ Error message final:", errorMsg);
      toast.error(errorMsg);
      throw new Error(errorMsg);
    }
  };

  // ---- Envío de código de verificación --------------------------------------
  const sendVerificationCode = async (data) => {
    console.log("[AUTH] Enviando código de verificación para:", maskEmail(data.email));
    try {
      const response = await axios.post(`${API}/auth/send-verification-code/`, data);
      console.log("[AUTH] Código de verificación enviado exitosamente", response.data);
      return response.data;
    } catch (err) {
      console.error("[AUTH] Error enviando código:", err?.response?.status, err?.response?.data, err?.message);
      const errorMsg = err?.response?.data?.detail || err?.response?.data?.error || err?.response?.data?.message || "Error al enviar el código";
      throw new Error(errorMsg);
    }
  };

  // ---- Verificación de código -----------------------------------------------
  const verifyCode = async (data) => {
    console.log("[AUTH] 🔍 Verificando código para:", maskEmail(data.email));
    console.log("[AUTH] 🔍 Datos recibidos:", { 
      email: maskEmail(data.email), 
      codigo: data.codigo, 
      intent: data.intent 
    });
    console.log("[AUTH] 🔍 API_BASE:", API);
    console.log("[AUTH] 🔍 axios config:", axios.defaults);
    
    try {
      console.log("[AUTH] 📡 Enviando request a:", `${API}/auth/verify-code/`);
      console.log("[AUTH] 📡 Payload enviado:", { 
        email: data.email, 
        codigo: data.codigo, 
        intent: data.intent,
        password: data.password ? "***" : "undefined"
      });
      console.log("[AUTH] 📡 Headers enviados:", axios.defaults.headers);
      
      console.log("[AUTH] ⏳ INICIANDO REQUEST A BACKEND...");
      const res = await axios.post(`${API}/auth/verify-code/`, data);
      console.log("[AUTH] ⏳ REQUEST A BACKEND COMPLETADO");
      
      console.log("[AUTH] ✅ Response recibido:", res.status, res.statusText);
      console.log("[AUTH] 📦 Response data:", res.data);
      console.log("[AUTH] 📦 Response headers:", res.headers);
      
      // Si es reset de contraseña, solo devolver éxito
      if (data.intent === 'reset_password') {
        console.log("[AUTH] 🔐 Reset de contraseña - Contraseña actualizada exitosamente");
        console.log("[AUTH] 🔐 Retornando:", res.data);
        console.log("[AUTH] 🔐 Tipo de retorno:", typeof res.data);
        return res.data;
      }
      
      // Si es registro, manejar tokens
      console.log("[AUTH] 📝 Procesando registro - Extrayendo tokens...");
      const { access, refresh, user: userPayload } = res.data;
      
      if (!access || !refresh) {
        console.error("[AUTH] ❌ Respuesta de verificación sin tokens");
        console.error("[AUTH] ❌ Access token:", !!access);
        console.error("[AUTH] ❌ Refresh token:", !!refresh);
        throw new Error("Respuesta de verificación sin tokens");
      }

      console.log("[AUTH] 🔑 Tokens recibidos - Procesando...");
      const exp = safeDecodeExp(access);
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("access_exp", exp);

      setAccessToken(access);
      setRefreshToken(refresh);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      console.log("[AUTH] ✅ Código verificado exitosamente. Usuario autenticado.");

      // SIEMPRE obtener perfil completo para tener la estructura con cliente_actual
      console.log("[AUTH] 👤 Obteniendo perfil completo...");
      const perfilRes = await axios.get(`${API}/auth/yo/`);
      console.log("[AUTH] 👤 Perfil obtenido:", perfilRes.data);
      setUser(perfilRes.data);
      localStorage.setItem("user", JSON.stringify(perfilRes.data));

      console.log("[AUTH] ⏰ Programando refresh automático...");
      scheduleProactiveRefresh();
      console.log("[AUTH] ✅ verifyCode completado exitosamente");
      return res.data;
    } catch (err) {
      console.error("[AUTH] ❌ Error verificando código:");
      console.error("[AUTH] ❌ Status:", err?.response?.status);
      console.error("[AUTH] ❌ Message:", err?.message);
      console.error("[AUTH] ❌ Response data:", err?.response?.data);
      console.error("[AUTH] ❌ Stack:", err?.stack);
      
      const errorMsg = err?.response?.data?.detail || err?.response?.data?.error || err?.response?.data?.message || "Código inválido o expirado";
      console.error("[AUTH] ❌ Error message final:", errorMsg);
      throw new Error(errorMsg);
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
        sendVerificationCode, // <-- nuevo: envío de códigos
        verifyCode, // <-- nuevo: verificación de códigos
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
