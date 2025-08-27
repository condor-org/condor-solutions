// src/auth/axiosInterceptor.js

import { jwtDecode } from "jwt-decode";

export const applyAuthInterceptor = (axiosInstance, logoutCallback) => {
  axiosInstance.interceptors.request.use(config => {
    const base = config.baseURL?.replace(/\/+$/, "") || "";
    const url  = `${base}${config.url || ""}`;
    console.log("[AXIOS REQUEST]", config.method?.toUpperCase(), url, "Auth:", !!config.headers?.Authorization);
    return config;
  });

  axiosInstance.interceptors.response.use(
    response => response,
    async error => {
      const status = error.response?.status;
      const originalRequest = error.config;

      console.log("[INTERCEPTOR] Status recibido:", status);

      if (status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;
        try {
          const refresh = localStorage.getItem("refresh");
          if (!refresh) throw new Error("No refresh token disponible.");

          // refresh en la MISMA instancia (usa baseURL="/api")
          const res = await axiosInstance.post("/token/refresh/", { refresh });

          const newAccess = res.data.access;
          localStorage.setItem("access", newAccess);
          localStorage.setItem("access_exp", jwtDecode(newAccess).exp);

          axiosInstance.defaults.headers.common["Authorization"] = `Bearer ${newAccess}`;
          originalRequest.headers["Authorization"] = `Bearer ${newAccess}`;

          console.log("[INTERCEPTOR] Refresh exitoso. Reintentando:", originalRequest.url);
          return axiosInstance(originalRequest);

        } catch (refreshError) {
          console.error("[INTERCEPTOR] Refresh falló. Logout forzado.");
          logoutCallback?.();
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );
};
