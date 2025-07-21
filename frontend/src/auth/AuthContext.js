import React, { createContext, useState, useEffect, useCallback, useContext } from "react";
import axios from "axios";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

export const AuthContext = createContext();

export const applyAuthInterceptor = (axiosInstance) => {
  axiosInstance.interceptors.response.use(
    res => res,
    error => {
      const originalRequest = error.config;
      const refresh = localStorage.getItem("refresh");
      const now = Math.floor(Date.now() / 1000);
      const exp = parseInt(localStorage.getItem("access_exp") || "0", 10);

      const expired = exp < now;
      const shouldRetry = !expired && error.response?.status === 401 && !originalRequest._retry;

      if (expired) {
        toast.warning("Tu sesión expiró. Por seguridad cerramos sesión.", {
          position: "top-center",
          autoClose: 5000,
        });
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (shouldRetry) {
        originalRequest._retry = true;
        return axios.post(`${API_BASE_URL}/api/token/refresh/`, { refresh })
          .then(res => {
            const newAccess = res.data.access;
            const decoded = jwtDecode(newAccess);
            localStorage.setItem("access", newAccess);
            localStorage.setItem("access_exp", decoded.exp);
            axiosInstance.defaults.headers["Authorization"] = `Bearer ${newAccess}`;
            originalRequest.headers["Authorization"] = `Bearer ${newAccess}`;
            return axiosInstance(originalRequest);
          })
          .catch(err => {
            localStorage.clear();
            window.location.href = "/login";
            return Promise.reject(err);
          });
      }

      return Promise.reject(error);
    }
  );
};

const AuthProviderBase = ({ children, onLogoutNavigate }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem("user");
    return storedUser ? JSON.parse(storedUser) : null;
  });

  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem("access")
  );

  const isAuthenticated = !!accessToken;

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    localStorage.clear();
    delete axios.defaults.headers.common["Authorization"];
    if (onLogoutNavigate) onLogoutNavigate("/login");
  }, [onLogoutNavigate]);

  const login = async (email, password) => {
    try {
      const res = await axios.post(`${API_BASE_URL}/api/token/`, {
        email,
        password,
      });

      const { access, refresh } = res.data;
      const decoded = jwtDecode(access);
      localStorage.setItem("access_exp", decoded.exp);
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);

      setAccessToken(access);
      axios.defaults.headers.common["Authorization"] = `Bearer ${access}`;

      const perfilRes = await axios.get(`${API_BASE_URL}/api/auth/yo/`);
      const userData = perfilRes.data;
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
    } catch (err) {
      console.error("Login failed:", err.response?.data || err.message);
      throw err;
    }
  };

  useEffect(() => {
    if (accessToken) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;
      const now = Math.floor(Date.now() / 1000);
      const exp = parseInt(localStorage.getItem("access_exp") || "0", 10);
      if (exp < now) {
        toast.warning("Tu sesión expiró. Por seguridad cerramos sesión.", {
          position: "top-center",
          autoClose: 5000,
        });
        logout();
      }
    }
  }, [accessToken, logout]);

  useEffect(() => {
    applyAuthInterceptor(axios);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout, accessToken }}>
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
