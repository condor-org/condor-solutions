// src/auth/axiosInterceptor.js

import { jwtDecode } from "jwt-decode";

export const applyAuthInterceptor = (axiosInstance, logoutCallback) => {
  axiosInstance.interceptors.request.use(config => {
    console.log("[AXIOS REQUEST] Request a:", config.url);
    console.log("[AXIOS REQUEST] Authorization header:", config.headers["Authorization"]);
    return config;
  });

  axiosInstance.interceptors.response.use(
    response => response,
    async error => {
      const status = error.response?.status;
      const originalRequest = error.config;

      console.log("[INTERCEPTOR] Status recibido:", status);

      if (status === 401 && !originalRequest._retry) {
        console.warn("[INTERCEPTOR] 401 detectado. Intentando refresh token...");

        originalRequest._retry = true;

        try {
          const refresh = localStorage.getItem("refresh");
          if (!refresh) throw new Error("No refresh token disponible.");

          console.log("[INTERCEPTOR] Enviando refresh token...");
          const res = await axiosInstance.post(
            `${process.env.REACT_APP_API_BASE_URL}/api/token/refresh/`,
            { refresh }
          );

          const newAccess = res.data.access;
          console.log("[INTERCEPTOR] Nuevo access token recibido:", newAccess);

          localStorage.setItem("access", newAccess);
          localStorage.setItem("access_exp", jwtDecode(newAccess).exp);

          axiosInstance.defaults.headers.common["Authorization"] = `Bearer ${newAccess}`;
          originalRequest.headers["Authorization"] = `Bearer ${newAccess}`;

          console.log("[INTERCEPTOR] Refresh exitoso. Reintentando request original:", originalRequest.url);

          return axiosInstance(originalRequest);

        } catch (refreshError) {
          console.error("[INTERCEPTOR] Falló el refresh desde interceptor. Ejecutando logout forzado.");
          logoutCallback();
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );
};
