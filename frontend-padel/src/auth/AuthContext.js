// src/auth/AuthContext.js

import React, { createContext, useState, useEffect, useCallback, useContext } from "react";
import axios from "axios";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { applyAuthInterceptor } from "./axiosInterceptor";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

export const AuthContext = createContext();

const AuthProviderBase = ({ children, onLogoutNavigate }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem("user");
    return storedUser ? JSON.parse(storedUser) : null;
  });

  const [accessToken, setAccessToken] = useState(() => localStorage.getItem("access"));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem("refresh"));
  const [loadingUser, setLoadingUser] = useState(true);  // ✅ Nuevo

  const logout = useCallback(() => {
    console.log("[AUTH] Logout ejecutado.");
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    localStorage.clear();
    delete axios.defaults.headers.common["Authorization"];
    if (onLogoutNavigate) onLogoutNavigate("/login");
  }, [onLogoutNavigate]);

  const attemptRefreshToken = useCallback(async () => {
    if (!refreshToken) return false;
    try {
      console.log("[AUTH] Intentando refresh token...");
      const res = await axios.post(`${API_BASE_URL}/api/token/refresh/`, { refresh: refreshToken });
      const { access } = res.data;
      const decoded = jwtDecode(access);

      localStorage.setItem("access", access);
      localStorage.setItem("access_exp", decoded.exp);
      setAccessToken(access);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      console.log("[AUTH] Refresh token exitoso.");
      return true;
    } catch (err) {
      console.error("[AUTH] Falló el refresh token. Forzando logout.");
      logout();
      return false;
    }
  }, [refreshToken, logout]);

  const login = async (email, password) => {
    console.log("[AUTH] Intentando login con email:", email);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/token/`, { email, password });
      const { access, refresh } = res.data;
      const decoded = jwtDecode(access);

      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("access_exp", decoded.exp);

      setAccessToken(access);
      setRefreshToken(refresh);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      console.log("[AUTH] Login exitoso. Tokens recibidos.");

      const perfilRes = await axios.get(`${API_BASE_URL}/api/auth/yo/`);
      setUser(perfilRes.data);
      localStorage.setItem("user", JSON.stringify(perfilRes.data));

      toast.success("Inicio de sesión exitoso");
    } catch (err) {
      toast.error("Credenciales inválidas");
      throw err;
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      if (accessToken) {
        const now = Math.floor(Date.now() / 1000);
        const exp = parseInt(localStorage.getItem("access_exp") || "0", 10);

        if (exp < now) {
          await attemptRefreshToken();
        } else {
          axios.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;
        }
      }
      setLoadingUser(false);  // ✅ Importante: señaliza fin de carga inicial
    };
    initializeAuth();
  }, [accessToken, attemptRefreshToken]);

  useEffect(() => {
    applyAuthInterceptor(axios, logout);
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
