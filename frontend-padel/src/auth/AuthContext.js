// src/auth/AuthContext.js

import React, { createContext, useState, useEffect, useCallback, useContext, useRef } from "react";
import axios from "axios";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { applyAuthInterceptor } from "./axiosInterceptor";

// REACT_APP_API_BASE_URL puede ser "" (same-origin) o "http://localhost:8080"
const RAW_BASE = process.env.REACT_APP_API_BASE_URL || "";
const API_BASE = RAW_BASE.replace(/\/+$/, "");
const API = `${API_BASE}/api`;

export const AuthContext = createContext();

const REFRESH_SAFETY_SECONDS = 60; // refrescar 60s antes del vencimiento

const AuthProviderBase = ({ children, onLogoutNavigate }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem("user");
    return storedUser ? JSON.parse(storedUser) : null;
  });

  const [accessToken, setAccessToken] = useState(() => localStorage.getItem("access"));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem("refresh"));
  const [loadingUser, setLoadingUser] = useState(true);

  const refreshTimerRef = useRef(null);

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
      // si ya está por vencer o vencido, refrescamos enseguida
      refreshTimerRef.current = setTimeout(() => attemptRefreshToken(), 0);
    } else {
      refreshTimerRef.current = setTimeout(() => attemptRefreshToken(), secondsLeft * 1000);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const logout = useCallback(() => {
    console.log("[AUTH] Logout ejecutado.");
    clearRefreshTimer();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);

    // limpiamos sólo lo que pusimos nosotros
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("access_exp");
    localStorage.removeItem("user");

    // removemos header global
    delete axios.defaults.headers.common["Authorization"];

    if (onLogoutNavigate) onLogoutNavigate("/login");
  }, [onLogoutNavigate]);

  const attemptRefreshToken = useCallback(async () => {
    const refresh = localStorage.getItem("refresh");
    if (!refresh) return false;

    try {
      console.log("[AUTH] Intentando refresh token...");
      const res = await axios.post(`${API}/token/refresh/`, { refresh });
      const { access } = res.data;
      if (!access) throw new Error("Respuesta de refresh sin 'access'");

      const decoded = jwtDecode(access);
      localStorage.setItem("access", access);
      localStorage.setItem("access_exp", decoded.exp);
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

  const login = async (email, password) => {
    console.log("[AUTH] Intentando login con email:", email);
    try {
      const res = await axios.post(`${API}/token/`, { email, password });
      const { access, refresh } = res.data;
      if (!access || !refresh) throw new Error("Respuesta de login sin tokens");

      const decoded = jwtDecode(access);
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("access_exp", decoded.exp);

      setAccessToken(access);
      setRefreshToken(refresh);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      console.log("[AUTH] Login exitoso. Tokens recibidos.");

      const perfilRes = await axios.get(`${API}/auth/yo/`);
      setUser(perfilRes.data);
      localStorage.setItem("user", JSON.stringify(perfilRes.data));

      scheduleProactiveRefresh();
    } catch (err) {
      console.error("[AUTH] Error en login:", err?.response?.status, err?.message);
      toast.error("Credenciales inválidas");
      throw err;
    }
  };

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
        }
      } finally {
        setLoadingUser(false); // señaliza fin de la carga inicial SIEMPRE
      }
    };
    initializeAuth();

    return () => clearRefreshTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, attemptRefreshToken]);

  // Registramos el interceptor global de axios UNA sola vez, con logout cableado
  useEffect(() => {
    applyAuthInterceptor(axios, logout, { apiBasePath: API }); // 👈 asegura usar /api correcto (abs o relative)
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, login, logout, accessToken, loadingUser }}>
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
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return context;
};
