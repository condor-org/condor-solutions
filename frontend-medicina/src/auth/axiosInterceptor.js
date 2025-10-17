// src/auth/axiosInterceptor.js
import { jwtDecode } from "jwt-decode";

let isRefreshing = false;
let refreshWaiters = [];

function onRefreshed(newAccess) {
  refreshWaiters.forEach((cb) => cb(newAccess));
  refreshWaiters = [];
}

/**
 * @param {import('axios').AxiosInstance} axiosInstance
 * @param {Function} logoutCallback
 * @param {{ apiBasePath?: string }} options
 *   - apiBasePath: puede ser "/api" o "https://dominio/api" (AuthContext se lo pasa como `${API_BASE}/api`)
 */
export const applyAuthInterceptor = (axiosInstance, logoutCallback, options = {}) => {
  const { apiBasePath = "/api" } = options;

  axiosInstance.interceptors.request.use((config) => {
    const base = config.baseURL?.replace(/\/+$/, "") || "";
    const url = `${base}${config.url || ""}`;
    // si no hay Authorization en el request pero existe en defaults, axios lo pone igual.
    console.log("[AXIOS REQUEST]", config.method?.toUpperCase(), url, "Auth:", !!config.headers?.Authorization, "BaseURL:", config.baseURL, "OriginalURL:", config.url);
    return config;
  });

  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const status = error?.response?.status;
      const originalRequest = error?.config || {};
      const url = originalRequest?.url || "";

      console.log("[INTERCEPTOR] Status recibido:", status, "URL:", url);

      // 🚫 1) NO refrescar si el 401 viene del propio refresh o del login
      if (
        status === 401 &&
        (url.includes("/api/token/refresh/") || url.includes("/api/token/") ||
         url.includes("/token/refresh/") || url.includes("/token/"))
      ) {
        console.warn("[INTERCEPTOR] 401 en endpoint de token, no refrescar. Forzando logout.");
        logoutCallback?.();
        return Promise.reject(error);
      }

      // 2) Refrescar sólo una vez por request
      if (status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        const refresh = localStorage.getItem("refresh");
        if (!refresh) {
          console.warn("[INTERCEPTOR] No hay refresh token. Logout.");
          logoutCallback?.();
          return Promise.reject(error);
        }

        // 👇 Single-flight: si ya hay un refresh en curso, encolarse
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            refreshWaiters.push((newAccessBearer) => {
              if (!newAccessBearer) return reject(error);
              originalRequest.headers = {
                ...(originalRequest.headers || {}),
                Authorization: newAccessBearer,
              };
              resolve(axiosInstance(originalRequest));
            });
          });
        }

        try {
          isRefreshing = true;

          // 👈 usar solo el path relativo, no el baseURL completo
          const refreshEndpoint = `/token/refresh/`;
          
          // Debug: verificar que no se duplique la URL
          console.log("[INTERCEPTOR] apiBasePath:", apiBasePath);
          console.log("[INTERCEPTOR] refreshEndpoint:", refreshEndpoint);

          const res = await axiosInstance.post(refreshEndpoint, { refresh });
          const newAccess = res?.data?.access;
          if (!newAccess) throw new Error("Refresh sin access");

          const bearer = `Bearer ${newAccess}`;
          localStorage.setItem("access", newAccess);
          localStorage.setItem("access_exp", jwtDecode(newAccess).exp);

          // actualizar default y el request original
          axiosInstance.defaults.headers.common["Authorization"] = bearer;
          originalRequest.headers = {
            ...(originalRequest.headers || {}),
            Authorization: bearer,
          };

          console.log("[INTERCEPTOR] Refresh OK. Reintentando:", originalRequest.url);
          onRefreshed(bearer);
          return axiosInstance(originalRequest);
        } catch (e) {
          console.error("[INTERCEPTOR] Refresh falló. Logout forzado.");
          onRefreshed(null); // despierta a los que estaban esperando con fracaso
          logoutCallback?.();
          return Promise.reject(e);
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(error);
    }
  );
};
